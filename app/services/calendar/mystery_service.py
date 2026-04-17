import os
import random
import string
import calendar as pycalendar
from datetime import datetime, timedelta
from flask import current_app
from app.extensions.database import db
from app.models.calendar_event import CalendarEvent
from app.api.ai import get_client
from app.services.base_service import BaseService

class MysteryService(BaseService):
    
    def generate_tuesdays(self, data):
        """Gera eventos de Desafio Mistério para todas as terças do mês."""
        # Validations
        restaurant_id = data.get('restaurant_id') or self.restaurant_id
        if not restaurant_id: raise ValueError('restaurant_id é obrigatório')
        
        if self.role not in ['admin', 'rh', 'marketing'] and int(restaurant_id) != self.restaurant_id:
             raise PermissionError('Permissão negada')

        image_url = data.get('image_url')
        if not image_url: raise ValueError('image_url é obrigatório')

        month = int(data.get('month') or datetime.utcnow().month)
        year = int(data.get('year') or datetime.utcnow().year)
        start_hour = int(data.get('start_hour') or 10)
        duration = int(data.get('duration_minutes') or 30)
        
        topics_raw = data.get('topics', '')
        custom_topics = [t.strip() for t in topics_raw.split(',') if t.strip()]

        # Generate dates
        tuesdays = []
        cal = pycalendar.Calendar()
        for week in cal.monthdatescalendar(year, month):
            for day in week:
                if day.month == month and day.weekday() == 1:
                    tuesdays.append(day)

        client = get_client()
        created_events = []
        generated_texts = [] # Context for AI to avoid repetition
        
        styles = [
            'poético e enigmático', 'rimado e brincalhão', 'curto e direto',
            'misterioso e provocativo', 'divertido e leve', 'com metáforas sutis'
        ]

        for idx, day in enumerate(tuesdays, start=1):
            start_dt = datetime(year, month, day.day, start_hour, 0)
            end_dt = start_dt + timedelta(minutes=duration)
            
            topic = custom_topics[idx - 1] if custom_topics and idx <= len(custom_topics) else f"Desafio Mistério – Terça {idx}"
            seed = ''.join(random.choice(string.ascii_lowercase) for _ in range(6))
            style = styles[(idx - 1) % len(styles)]
            
            # AI Generation
            text = self._gen_text(client, topic, style, seed, generated_texts)
            generated_texts.append(text)
            
            # Create Event
            event = CalendarEvent(
                title='Desafio Mistério McD',
                description=text,
                start_date=start_dt,
                end_date=end_dt,
                event_type='desafio_misterio',
                restaurant_id=restaurant_id,
                created_by=self.user_id,
                is_all_day=False,
                color='#9b59b6',
                location=image_url,
                metadata_json={
                    "style": style, "seed": seed, 
                    "generator": "openai", "answer": topic
                }
            )
            db.session.add(event)
            db.session.flush() 
            created_events.append(event)
            
            # Auto-generate answer for Saturday? No, the original code did do that!
            # Look at original: it calculates next saturday and generates answer immediately.
            self._create_answer_event(client, event, topic, image_url, day, start_hour, duration, restaurant_id, created_events)

        db.session.commit()
        return created_events

    def generate_answers_bulk(self, data):
        """Gera respostas para todos os sábados baseado nas terças anteriores."""
        # Logic from generate_mystery_answers endpoint
        restaurant_id = data.get('restaurant_id') or self.restaurant_id
        if not restaurant_id: raise ValueError('restaurant_id é obrigatório')
         
        if self.role not in ['admin', 'rh', 'marketing'] and int(restaurant_id) != self.restaurant_id:
             raise PermissionError('Permissão negada')

        month = int(data.get('month') or datetime.utcnow().month)
        year = int(data.get('year') or datetime.utcnow().year)
        start_hour = int(data.get('start_hour') or 10)
        duration = int(data.get('duration_minutes') or 30)

        saturdays = []
        cal = pycalendar.Calendar()
        for week in cal.monthdatescalendar(year, month):
            for day in week:
                if day.month == month and day.weekday() == 5:
                    saturdays.append(day)

        client = get_client()
        created_events = []

        for saturday in saturdays:
            prev_tuesday = self._get_previous_tuesday(saturday)
            if not prev_tuesday: continue
            
            # Find Tuesday Event
            tue_start = datetime(prev_tuesday.year, prev_tuesday.month, prev_tuesday.day)
            tue_event = CalendarEvent.query.filter(
                CalendarEvent.restaurant_id == restaurant_id,
                CalendarEvent.event_type == 'desafio_misterio',
                CalendarEvent.start_date >= tue_start,
                CalendarEvent.start_date < tue_start + timedelta(days=1)
            ).first()

            if not tue_event: continue
            
            # Check existance
            exists = CalendarEvent.query.filter(
                CalendarEvent.restaurant_id == restaurant_id,
                CalendarEvent.event_type == 'desafio_misterio_resposta',
                db.func.date(CalendarEvent.start_date) == saturday
            ).first()
            if exists: continue

            # Generate Answer Text
            correct_answer = tue_event.metadata_json.get('answer') if tue_event.metadata_json else "a resposta"
            answer_text = self._gen_answer_text(client, correct_answer, tue_event.description)

            # Create Event
            start_dt = datetime(year, month, saturday.day, start_hour, 0)
            event = CalendarEvent(
                title='Resposta do Desafio',
                description=answer_text,
                start_date=start_dt,
                end_date=start_dt + timedelta(minutes=duration),
                event_type='desafio_misterio_resposta',
                restaurant_id=restaurant_id,
                created_by=self.user_id,
                color='#3498db',
                location=tue_event.location,
                metadata_json={
                    "source_event_id": tue_event.id,
                    "generator": "openai",
                    "answer": correct_answer
                }
            )
            db.session.add(event)
            created_events.append(event)
        
        db.session.commit()
        return created_events

    # --- Helpers ---
    def _gen_text(self, client, topic, style, seed, context_list):
        model = os.getenv('OPENAI_MODEL') or 'gpt-4o-mini'
        try:
             resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você é um redator criativo do McDonald's especializado em enigmas curtos."},
                    {"role": "user", "content": f"Crie um enigma sobre: {topic}. Estilo: {style}. Semente: {seed}. Contexto anterior: {len(context_list)} enigmas. Estrutura: 🎯Desafio Misterio Da Semana🎯 + texto divertido/misterioso. Não revele a resposta."}
                ],
                temperature=0.9, max_tokens=220
            )
             text = resp.choices[0].message.content.strip()
             if '🎯' not in text: text = "🎯Desafio Misterio Da Semana🎯\n\n" + text
             return text
        except Exception as e:
            return f"🎯Desafio Misterio Da Semana🎯\n\n[Erro IA: {str(e)}]"

    def _create_answer_event(self, client, tuesday_event, topic, image, tue_date, hour, dur, rid, created_list):
        # Calculate next Saturday
        days_until_sat = (5 - tue_date.weekday()) % 7
        if days_until_sat == 0: days_until_sat = 7
        sat_date = tue_date + timedelta(days=days_until_sat)
        
        text = self._gen_answer_text(client, topic)
        
        start_dt = datetime(sat_date.year, sat_date.month, sat_date.day, hour, 0)
        evt = CalendarEvent(
            title='Resposta do Desafio', description=text,
            start_date=start_dt, end_date=start_dt + timedelta(minutes=dur),
            event_type='desafio_misterio_resposta', restaurant_id=rid,
            created_by=self.user_id, color='#3498db', location=image,
            metadata_json={"source_event_id": tuesday_event.id, "answer": topic}
        )
        db.session.add(evt)
        created_list.append(evt)

    def _gen_answer_text(self, client, answer, riddle_context=''):
        model = os.getenv('OPENAI_MODEL') or 'gpt-4o-mini'
        try:
             resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Redator McDonald's revelando respostas."},
                    {"role": "user", "content": f"Revele a resposta: {answer}. Use '🔍Resposta do Desafio🎯'. Seja curto e entusiasta."}
                ],
                temperature=0.6, max_tokens=160
            )
             t = resp.choices[0].message.content.strip()
             if '🔍' not in t: t = "🔍Resposta do Desafio🎯\n\n" + t
             return t
        except:
            return f"🔍Resposta do Desafio🎯\n\nA resposta é: {answer}!"

    def _get_previous_tuesday(self, saturday_date):
        d = saturday_date - timedelta(days=1)
        while d.month == saturday_date.month:
            if d.weekday() == 1: return d
            d -= timedelta(days=1)
        return None
