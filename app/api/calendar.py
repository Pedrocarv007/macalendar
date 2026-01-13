"""
Rotas da API do Calendário
"""
from flask import Blueprint, request, jsonify, g, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import os
import calendar as pycalendar
from app.api.ai import get_client
from app.extensions.database import db
from app.models.calendar_event import CalendarEvent
from app.models.employee import Employee
from app.middleware.security import api_login_required, role_required
import random
import string
from sqlalchemy import or_
import re
from app.models.restaurant import Restaurant

calendar_bp = Blueprint('calendar', __name__)


def _normalize_birthday(original_date, target_year):
    """Ajusta datas para lidar com aniversários em 29/02."""
    try:
        return original_date.replace(year=target_year)
    except ValueError:
        # Ajusta 29/02 para 28/02 em anos não bissextos
        return original_date.replace(year=target_year, day=28)

@calendar_bp.route('/events', methods=['GET'])
@api_login_required
def get_events():
    """Obter eventos do calendário"""
    try:
        current_user_id = g.get('current_user_id')
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Parâmetros de data
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        include_global = (request.args.get('include_global') or '').lower() == 'true'
        
        # Query base
        query = CalendarEvent.query
        
        # Filtrar por permissões
        if user_role in ['admin', 'rh', 'marketing']:
            # RH e Marketing podem ver todos os eventos
            pass
        elif user_role == 'manager' and user_restaurant_id:
            # Gerente só vê eventos do seu restaurante (+ opcionais globais)
            if include_global:
                query = query.filter(or_(CalendarEvent.restaurant_id == user_restaurant_id,
                                         CalendarEvent.restaurant_id.is_(None)))
            else:
                query = query.filter(CalendarEvent.restaurant_id == user_restaurant_id)
        else:
            # Funcionários só veem eventos do seu restaurante (+ opcionais globais)
            if include_global:
                query = query.filter(or_(CalendarEvent.restaurant_id == user_restaurant_id,
                                         CalendarEvent.restaurant_id.is_(None)))
            else:
                query = query.filter(CalendarEvent.restaurant_id == user_restaurant_id)
        
        # Filtrar por período
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', ''))
            query = query.filter(CalendarEvent.end_date >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', ''))
            query = query.filter(CalendarEvent.start_date <= end_dt)
        
        events = query.all()
        
        return jsonify({
            'events': [event.to_dict() for event in events]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@calendar_bp.route('/events', methods=['POST'])
@api_login_required
def create_event():
    """Criar novo evento"""
    try:
        current_user_id = g.get('current_user_id')
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')

        # Suporte a form-data (upload de arquivo)
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
            file = request.files.get('photo')
        else:
            data = request.get_json()
            file = None

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        required_fields = ['title', 'start_date', 'end_date', 'event_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400

        restaurant_id = data.get('restaurant_id') or user_restaurant_id
        if user_role not in ['admin', 'rh', 'marketing', 'manager']:
            if not user_restaurant_id or restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403

        try:
            start_date = datetime.fromisoformat(data['start_date'].replace('Z', ''))
            end_date = datetime.fromisoformat(data['end_date'].replace('Z', ''))
        except ValueError:
            return jsonify({'error': 'Formato de data inválido'}), 400
                         
        # Extrair número de pessoas da descrição
        people_count = 0
        if data.get('description'):
            match = re.search(r'Pessoas:\s*(\d+)', data['description'], re.IGNORECASE)
            if match:
                people_count = int(match.group(1))

        if data['event_type'] == 'birthday_party' and people_count > 0:
            # Buscar restaurante para obter capacidade
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurante não encontrado'}), 404
            
            max_capacity = restaurant.capacity 
            allowed_capacity = max_capacity * 0.20
            
            # Buscar festas na mesma hora com espaço de 1:30
            time_buffer = timedelta(hours=1, minutes=30)
            conflicting_events = CalendarEvent.query.filter(
                CalendarEvent.restaurant_id == restaurant_id,
                CalendarEvent.event_type == 'birthday_party',
                CalendarEvent.start_date < end_date + time_buffer,
                CalendarEvent.end_date + time_buffer > start_date
            ).all()
            
            # Calcular capacidade total ocupada
            occupied_capacity = sum(
                int(re.search(r'Pessoas:\s*(\d+)', e.description or '', re.IGNORECASE).group(1) or 0)
                for e in conflicting_events
                if re.search(r'Pessoas:\s*(\d+)', e.description or '', re.IGNORECASE)
            )
            
            if people_count + occupied_capacity > allowed_capacity:
                return jsonify({
                    'error': f'Capacidade insuficiente. Capacidade disponível: {int(allowed_capacity - occupied_capacity)} pessoas. '
                             f'Por favor escolha outro horário com pelo menos 1h30 de espaço entre festas.'
                }), 400
            



        # Upload da foto
        photo_path = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                return jsonify({'error': 'Formato de imagem não suportado'}), 400
            unique_name = f"event_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{ext}"
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'events')
            try:
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, unique_name)
                file.save(file_path)
            except Exception as upload_err:
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Erro ao salvar imagem: {upload_err}'}), 500

        def parse_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ('true', '1', 'yes', 'on')
            return bool(val)

        is_all_day = parse_bool(data.get('is_all_day', False))
        is_recurring = parse_bool(data.get('recurring', False))

        event = CalendarEvent(
            title=data['title'],
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            event_type=data['event_type'],
            restaurant_id=restaurant_id,
            created_by=current_user_id,
            employee_id=data.get('employee_id'),
            is_all_day=is_all_day,
            color=data.get('color', '#3788d8'),
            location=data.get('location'),
            photo_path=photo_path,
            is_recurring=is_recurring
        )

        db.session.add(event)
        db.session.commit()

        return jsonify({
            'message': 'Evento criado com sucesso',
            'event': event.to_dict()
        }), 201
        
    except Exception as e:
        import traceback
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500




@calendar_bp.route('/events/<int:event_id>', methods=['PUT'])
@api_login_required
def update_event(event_id):
    """Atualizar evento"""
    try:
        current_user_id = g.get('current_user_id')
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        event = CalendarEvent.query.get(event_id)
        if not event:
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh', 'marketing']:
            if event.restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Atualizar campos
        if 'title' in data:
            event.title = data['title']
        if 'description' in data:
            event.description = data['description']
        if 'start_date' in data:
            event.start_date = datetime.fromisoformat(data['start_date'].replace('Z', ''))
        if 'end_date' in data:
            event.end_date = datetime.fromisoformat(data['end_date'].replace('Z', ''))
        if 'event_type' in data:
            event.event_type = data['event_type']
        if 'employee_id' in data:
            event.employee_id = data['employee_id']
        if 'is_all_day' in data:
            event.is_all_day = data['is_all_day']
        if 'color' in data:
            event.color = data['color']
        if 'location' in data:
            event.location = data['location']
        
        event.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Evento atualizado com sucesso',
            'event': event.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/events/<int:event_id>', methods=['DELETE'])
@api_login_required
def delete_event(event_id):
    """Deletar evento"""
    try:
        current_user_id = g.get('current_user_id')
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        event = CalendarEvent.query.get(event_id)
        if not event:
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Verificar permissões
        if user_role not in ['admin', 'rh', 'marketing']:
            if event.restaurant_id != user_restaurant_id or event.created_by != current_user_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'message': 'Evento deletado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/events/<int:event_id>/mark-posted', methods=['PUT'])
@api_login_required
def mark_event_posted(event_id):
    """Marcar evento (desafio) como postado usando a cor como flag."""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        current_user_id = g.get('current_user_id')
        event = CalendarEvent.query.get(event_id)
        if not event:
            return jsonify({'error': 'Evento não encontrado'}), 404
        if user_role not in ['admin', 'rh', 'marketing']:
            if event.restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        # usar cor verde para indicar postado
        event.color = '#2ecc71'
        event.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Evento marcado como postado', 'event': event.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@calendar_bp.route('/generate/mystery-tuesdays', methods=['POST'])
@api_login_required
def generate_mystery_tuesdays():
    """Gerar eventos de Desafio Mistério para todas as terças do mês, com texto via IA."""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        current_user_id = g.get('current_user_id')

        data = request.get_json() or {}
        month = int(data.get('month') or datetime.utcnow().month)
        year = int(data.get('year') or datetime.utcnow().year)
        restaurant_id = data.get('restaurant_id') or user_restaurant_id
        image_url = data.get('image_url')
        start_hour = int(data.get('start_hour') or 10)
        duration_minutes = int(data.get('duration_minutes') or 30)
        
        # 🔹 Parse topics from comma-separated string
        topics_raw = data.get('topics', '')
        custom_topics = []
        if topics_raw and topics_raw.strip():
            custom_topics = [t.strip() for t in topics_raw.split(',') if t.strip()]

        if not restaurant_id:
            return jsonify({'error': 'restaurant_id é obrigatório'}), 400
        if user_role not in ['admin', 'rh', 'marketing'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403
        if not image_url:
            return jsonify({'error': 'image_url é obrigatório'}), 400

        # 🔹 Calcular todas as terças do mês
        tuesdays = []
        cal = pycalendar.Calendar()
        for week in cal.monthdatescalendar(year, month):
            for day in week:
                if day.month == month and day.weekday() == 1:
                    tuesdays.append(day)

        client = get_client()
        created_events = []
        generated_texts = []

        styles = [
            'poético e enigmático',
            'rimado e brincalhão',
            'curto e direto',
            'misterioso e provocativo',
            'divertido e leve',
            'com metáforas sutis'
        ]

        # 🔹 Utilitários
        def _normalize(s):
            return ' '.join(
                ''.join(ch.lower() for ch in s if ch.isalnum() or ch.isspace()).split()
            )

        def _strip_header(text):
            return text.replace('🎯Desafio Misterio Da Semana🎯', '').strip()

        def _similar(a, b):
            wa = set(_normalize(a).split())
            wb = set(_normalize(b).split())
            if not wa or not wb:
                return 0.0
            return len(wa & wb) / len(wa | wb)

        def _gen_text(topic, style, seed, extra_hint=''):
            return client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL') or 'gpt-4o-mini',
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um redator criativo do McDonald's especializado em enigmas "
                            "curtos para redes sociais. Nunca revele a resposta. "
                            "Nunca explique nada. Responda apenas com o texto final."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Crie um enigma ORIGINAL seguindo EXATAMENTE esta estrutura:\n\n"
                            "🎯Desafio Misterio Da Semana🎯\n\n"
                            "- 4 a 6 linhas curtas\n"
                            "- Tom divertido, curioso e misterioso\n"
                            "- Não usar perguntas diretas\n"
                            "- Não mencionar McDonald's explicitamente\n"
                            "- Não repetir frases, rimas ou metáforas comuns\n\n"
                            f"Tema oculto: {topic}\n"
                            f"Estilo literário: {style}\n"
                            f"Semente criativa: {seed}\n\n"
                            "O enigma deve sugerir o tema sem o nomear."
                            + (" " + extra_hint if extra_hint else "")
                        ),
                    },
                ],
                temperature=0.95,
                presence_penalty=0.6,
                frequency_penalty=0.4,
                max_tokens=220,
            )

        # 🔹 Geração dos eventos
        for idx, day in enumerate(tuesdays, start=1):
            start_dt = datetime(year, month, day.day, start_hour, 0)
            end_dt = start_dt + timedelta(minutes=duration_minutes)

            # Use custom topic if provided, otherwise generate generic
            if custom_topics and idx <= len(custom_topics):
                topic = custom_topics[idx - 1]
            else:
                topic = f"Desafio Mistério – Terça {idx} ({day.strftime('%d/%m/%Y')})"
            
            seed = ''.join(random.choice(string.ascii_lowercase) for _ in range(6))
            style = styles[(idx - 1) % len(styles)]

            try:
                resp = _gen_text(topic, style, seed)
                text = resp.choices[0].message.content.strip()

                if not text.startswith('🎯Desafio Misterio Da Semana🎯'):
                    text = f"🎯Desafio Misterio Da Semana🎯\n\n{text}"

                too_similar = any(
                    _similar(
                        _strip_header(text),
                        _strip_header(prev)
                    ) > 0.6
                    for prev in generated_texts
                )

                if too_similar:
                    alt_style = styles[idx % len(styles)]
                    resp2 = _gen_text(
                        topic,
                        alt_style,
                        seed,
                        extra_hint='Use vocabulário totalmente diferente das terças anteriores.'
                    )
                    alt_text = resp2.choices[0].message.content.strip()
                    if not alt_text.startswith('🎯Desafio Misterio Da Semana🎯'):
                        alt_text = f"🎯Desafio Misterio Da Semana🎯\n\n{alt_text}"

                    sim1 = max(
                        (_similar(_strip_header(text), _strip_header(p)) for p in generated_texts),
                        default=0
                    )
                    sim2 = max(
                        (_similar(_strip_header(alt_text), _strip_header(p)) for p in generated_texts),
                        default=0
                    )

                    if sim2 < sim1:
                        text = alt_text
                        style = alt_style

            except Exception as e:
                print(f"[ERRO] Falha ao gerar enigma para {day}: {str(e)}")
                text = (
                    "🎯Desafio Misterio Da Semana🎯\n\n"
                    f"[Erro ao gerar enigma automaticamente]"
                )

            generated_texts.append(text)

            # 🔹 Criar evento de terça
            tuesday_event = CalendarEvent(
                title='Desafio Mistério McD',
                description=text,
                start_date=start_dt,
                end_date=end_dt,
                event_type='desafio_misterio',
                restaurant_id=restaurant_id,
                created_by=current_user_id,
                is_all_day=False,
                color='#9b59b6',
                location=image_url,
                is_recurring=False
            )
            # Adicionar metadata após criar o objeto
            tuesday_event.metadata_json = {
                "style": style,
                "seed": seed,
                "generator": "openai",
                "answer": topic
            }

            db.session.add(tuesday_event)
            db.session.flush()  # Get the ID
            created_events.append(tuesday_event)

            # 🔹 Calcular próximo sábado após a terça (terça é dia 1, sábado é dia 5)
            days_until_saturday = (5 - day.weekday()) % 7
            if days_until_saturday == 0:  # Se terça cair num sábado (impossível, mas garantir)
                days_until_saturday = 7
            next_saturday = day + timedelta(days=days_until_saturday)
            
            
            # 🔹 Gerar texto de resposta via IA
            try:
                resp_answer = client.chat.completions.create(
                    model=os.getenv('OPENAI_MODEL') or 'gpt-4o-mini',
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Você é um redator do McDonald's responsável por revelar respostas "
                                "de desafios semanais. Seja claro, curto e envolvente."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Crie um post de RESPOSTA para redes sociais seguindo exatamente este formato:\n\n"
                                "🔍Resposta do Desafio🎯\n\n"
                                f"- 1 linha revelando que a resposta é: {topic}\n"
                                "- 1 a 2 linhas de encerramento amigável e engajador\n"
                                "- Linguagem simples e positiva\n"
                                "- Mencionar o produto/tema de forma entusiasmada"
                            ),
                        },
                    ],
                    temperature=0.6,
                    max_tokens=160,
                )
                answer_text = resp_answer.choices[0].message.content.strip()
                if not answer_text.startswith('🔍Resposta do Desafio🎯'):
                    answer_text = f"🔍Resposta do Desafio🎯\n\n{answer_text}"
            except Exception as e:
                print(f"[ERRO] Falha ao gerar resposta: {str(e)}")
                answer_text = (
                    "🔍Resposta do Desafio🎯\n\n"
                    f"A resposta é: {topic}! "
                    "Parabéns a quem acertou 👏"
                )
            
            # 🔹 Criar evento de resposta no sábado
            saturday_start = datetime(next_saturday.year, next_saturday.month, next_saturday.day, start_hour, 0)
            saturday_end = saturday_start + timedelta(minutes=duration_minutes)
            
            answer_event = CalendarEvent(
                title='Resposta do Desafio',
                description=answer_text,
                start_date=saturday_start,
                end_date=saturday_end,
                event_type='desafio_misterio_resposta',
                restaurant_id=restaurant_id,
                created_by=current_user_id,
                is_all_day=False,
                color='#3498db',
                location=image_url,
                is_recurring=False
            )
            # Adicionar metadata após criar o objeto
            answer_event.metadata_json = {
                "source_event_id": tuesday_event.id,
                "generator": "openai",
                "answer": topic
            }
            
            db.session.add(answer_event)
            created_events.append(answer_event)
            print(f"[DEBUG] Evento de resposta criado para {saturday_start}")

        db.session.commit()

        return jsonify({
            'message': 'Desafios e respostas gerados com sucesso',
            'count': len(created_events),
            'events': [e.to_dict() for e in created_events]
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@calendar_bp.route('/generate/mystery-answers', methods=['POST'])
@api_login_required
def generate_mystery_answers():
    """
    Gera eventos de Resposta do Desafio aos sábados.
    Para cada sábado do mês, encontra a terça anterior com 'desafio_misterio'
    e cria um evento de resposta usando IA.
    """
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        current_user_id = g.get('current_user_id')

        data = request.get_json() or {}
        month = int(data.get('month') or datetime.utcnow().month)
        year = int(data.get('year') or datetime.utcnow().year)
        restaurant_id = data.get('restaurant_id') or user_restaurant_id
        start_hour = int(data.get('start_hour') or 10)
        duration_minutes = int(data.get('duration_minutes') or 30)

        if not restaurant_id:
            return jsonify({'error': 'restaurant_id é obrigatório'}), 400
        if user_role not in ['admin', 'rh', 'marketing'] and restaurant_id != user_restaurant_id:
            return jsonify({'error': 'Permissão negada para este restaurante'}), 403

        # 🔹 Listar sábados do mês
        saturdays = []
        cal = pycalendar.Calendar()
        for week in cal.monthdatescalendar(year, month):
            for day in week:
                if day.month == month and day.weekday() == 5:  # Saturday
                    saturdays.append(day)

        client = get_client()
        created_events = []

        # 🔹 Função para encontrar a terça anterior
        def get_previous_tuesday(saturday):
            d = saturday - timedelta(days=1)
            while d.month == saturday.month:
                if d.weekday() == 1:
                    return d
                d -= timedelta(days=1)
            return None

        for saturday in saturdays:
            prev_tuesday = get_previous_tuesday(saturday)
            if not prev_tuesday:
                continue

            # 🔹 Buscar evento de terça
            tue_start = datetime(prev_tuesday.year, prev_tuesday.month, prev_tuesday.day)
            tue_end = tue_start + timedelta(days=1)

            tuesday_event = (
                CalendarEvent.query
                .filter(CalendarEvent.restaurant_id == restaurant_id)
                .filter(CalendarEvent.event_type == 'desafio_misterio')
                .filter(CalendarEvent.start_date >= tue_start)
                .filter(CalendarEvent.start_date < tue_end)
                .first()
            )

            if not tuesday_event:
                continue

            # 🔹 Evitar duplicar resposta
            existing_answer = (
                CalendarEvent.query
                .filter(CalendarEvent.restaurant_id == restaurant_id)
                .filter(CalendarEvent.event_type == 'desafio_misterio_resposta')
                .filter(CalendarEvent.start_date.date() == saturday)
                .first()
            )
            if existing_answer:
                continue

            riddle_text = tuesday_event.description or ''
            image_url = tuesday_event.location
            
            # 🔹 Extrair resposta do metadata do evento de terça
            correct_answer = None
            if tuesday_event.metadata_json and isinstance(tuesday_event.metadata_json, dict):
                correct_answer = tuesday_event.metadata_json.get('answer')
            
            # Se não encontrou resposta no metadata, tentar inferir
            if not correct_answer:
                correct_answer = "a resposta correta"

            # 🔹 Gerar resposta via IA
            try:
                resp = client.chat.completions.create(
                    model=os.getenv('OPENAI_MODEL') or 'gpt-4o-mini',
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Você é um redator do McDonald's responsável por revelar respostas "
                                "de desafios semanais. Seja claro, curto e envolvente. "
                                "Nunca repita o enigma."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Crie um post de RESPOSTA para redes sociais seguindo exatamente este formato:\n\n"
                                "🔍Resposta do Desafio🎯\n\n"
                                f"- 1 linha revelando que a resposta é: {correct_answer}\n"
                                "- 1 a 2 linhas de encerramento amigável e engajador\n"
                                "- Linguagem simples e positiva\n"
                                "- Mencionar o produto/tema de forma entusiasmada\n\n"
                                "Enigma original (apenas para contexto):\n"
                                f"{riddle_text}"
                            ),
                        },
                    ],
                    temperature=0.6,
                    max_tokens=160,
                )

                answer_text = resp.choices[0].message.content.strip()
                if not answer_text.startswith('🔍Resposta do Desafio🎯'):
                    answer_text = f"🔍Resposta do Desafio🎯\n\n{answer_text}"

            except Exception:
                answer_text = (
                    "🔍Resposta do Desafio🎯\n\n"
                    f"A resposta é: {correct_answer}! "
                    "Parabéns a quem acertou 👏 Nos vemos no próximo mistério!"
                )

            # 🔹 Criar evento de sábado
            start_dt = datetime(year, month, saturday.day, start_hour, 0)
            end_dt = start_dt + timedelta(minutes=duration_minutes)

            event = CalendarEvent(
                title='Resposta do Desafio',
                description=answer_text,
                start_date=start_dt,
                end_date=end_dt,
                event_type='desafio_misterio_resposta',
                restaurant_id=restaurant_id,
                created_by=current_user_id,
                is_all_day=False,
                color='#3498db',
                location=image_url,
                is_recurring=False,
                metadata_json={
                    "source_event_id": tuesday_event.id,
                    "generator": "openai",
                    "answer": correct_answer
                }
            )

            db.session.add(event)
            created_events.append(event)

        db.session.commit()

        return jsonify({
            'message': 'Respostas de sábado geradas com sucesso',
            'count': len(created_events),
            'events': [e.to_dict() for e in created_events]
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@calendar_bp.route('/birthdays', methods=['GET'])
@api_login_required
def get_birthdays():
    """Obter aniversários do mês"""
    try:
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Mês atual ou específico
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Query base
        query = Employee.query.filter(Employee.is_active == True)
        
        # Filtrar por permissões
        if user_role not in ['admin', 'rh', 'marketing'] and user_restaurant_id:
            query = query.filter(Employee.restaurant_id == user_restaurant_id)
        
        # Filtrar por mês de aniversário
        query = query.filter(
            db.extract('month', Employee.birth_date) == month
        )
        
        employees = query.all()
        
        # Preparar dados dos aniversários
        birthdays = []
        for employee in employees:
            birthday_this_year = _normalize_birthday(employee.birth_date, year)
            birthdays.append({
                'employee': employee.to_dict(),
                'birthday_date': birthday_this_year.isoformat(),
                'age': year - employee.birth_date.year
            })
        
        # Ordenar por dia do mês
        birthdays.sort(key=lambda x: x['employee']['birth_date'][-2:])
        
        return jsonify({'birthdays': birthdays}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
