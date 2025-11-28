"""
Rotas da API do Calendário
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import get_jwt_identity, get_jwt
from datetime import datetime, date
from app.extensions.database import db
from app.models.calendar_event import CalendarEvent
from app.models.employee import Employee
from app.middleware.security import api_login_required, role_required

calendar_bp = Blueprint('calendar', __name__)

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
        
        # Query base
        query = CalendarEvent.query
        
        # Filtrar por permissões
        if user_role in ['admin', 'rh', 'marketing']:
            # RH e Marketing podem ver todos os eventos
            pass
        elif user_role == 'manager' and user_restaurant_id:
            # Gerente só vê eventos do seu restaurante
            query = query.filter(CalendarEvent.restaurant_id == user_restaurant_id)
        else:
            # Funcionários só veem eventos do seu restaurante
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
        # claims via g
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validar dados obrigatórios
        required_fields = ['title', 'start_date', 'end_date', 'event_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400
        
        # Verificar permissões
        restaurant_id = data.get('restaurant_id')
        if user_role not in ['admin', 'rh', 'marketing']:
            if not user_restaurant_id or restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Permissão negada'}), 403
        
        # Converter datas
        try:
            start_date = datetime.fromisoformat(data['start_date'].replace('Z', ''))
            end_date = datetime.fromisoformat(data['end_date'].replace('Z', ''))
        except ValueError:
            return jsonify({'error': 'Formato de data inválido'}), 400
        
        # Criar evento
        event = CalendarEvent(
            title=data['title'],
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            event_type=data['event_type'],
            restaurant_id=restaurant_id,
            created_by=current_user_id,
            employee_id=data.get('employee_id'),
            is_all_day=data.get('is_all_day', False),
            color=data.get('color', '#3788d8'),
            location=data.get('location')
        )
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'message': 'Evento criado com sucesso',
            'event': event.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
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
        # claims via g
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
            birthday_this_year = employee.birth_date.replace(year=year)
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
