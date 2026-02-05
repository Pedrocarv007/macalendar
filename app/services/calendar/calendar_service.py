import os
import re
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import current_app
from sqlalchemy import or_

from app.extensions.database import db
from app.models.calendar_event import CalendarEvent
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.services.base_service import BaseService


class CalendarService(BaseService):
    def list_events(self, start_date=None, end_date=None, include_global=False):
        """Lista eventos com filtros de permissão e data."""
        query = CalendarEvent.query

        # Filtrar por permissões
        if self.role in ['admin', 'rh', 'marketing']:
            # Podem ver tudo
            pass
        else:
            # Funcionários/Gerentes veem seu restaurante + globais opcionais
            if include_global:
                query = query.filter(or_(
                    CalendarEvent.restaurant_id == self.restaurant_id,
                    CalendarEvent.restaurant_id.is_(None)
                ))
            else:
                query = query.filter(CalendarEvent.restaurant_id == self.restaurant_id)

        # Filtrar por período
        if start_date:
            start_dt = self._parse_date(start_date)
            query = query.filter(CalendarEvent.end_date >= start_dt)
        
        if end_date:
            end_dt = self._parse_date(end_date)
            query = query.filter(CalendarEvent.start_date <= end_dt)

        return query.all()

    def create_event(self, data, file=None):
        """Cria um novo evento com validações."""
        self._validate_create_data(data)
        
        restaurant_id = data.get('restaurant_id') or self.restaurant_id
        
        # Validar permissão de criação
        if self.role not in ['admin', 'rh', 'marketing', 'manager']:
            if not self.restaurant_id or int(restaurant_id) != self.restaurant_id:
                raise PermissionError('Permissão negada')

        start_date = self._parse_date(data['start_date'])
        end_date = self._parse_date(data['end_date'])
        
        # Validar capacidade para festas de aniversário
        if data.get('event_type') == 'birthday_party':
            self._validate_party_capacity(restaurant_id, start_date, end_date, data.get('description'))

        # Upload de foto
        photo_path = self._handle_file_upload(file) if file else None

        is_all_day = self._parse_bool(data.get('is_all_day', False))
        is_recurring = self._parse_bool(data.get('recurring', False))

        event = CalendarEvent(
            title=data['title'],
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            event_type=data['event_type'],
            restaurant_id=restaurant_id,
            created_by=self.user_id,
            employee_id=data.get('employee_id'),
            is_all_day=is_all_day,
            color=data.get('color', '#3788d8'),
            location=data.get('location'),
            photo_path=photo_path,
            is_recurring=is_recurring
        )

        db.session.add(event)
        db.session.commit()
        return event

    def update_event(self, event_id, data):
        """Atualiza um evento existente."""
        event = CalendarEvent.query.get(event_id)
        if not event:
            return None

        # Permissão
        if self.role not in ['admin', 'rh', 'marketing']:
            if event.restaurant_id != self.restaurant_id:
                raise PermissionError('Permissão negada')

        if 'title' in data: event.title = data['title']
        if 'description' in data: event.description = data['description']
        if 'start_date' in data: event.start_date = self._parse_date(data['start_date'])
        if 'end_date' in data: event.end_date = self._parse_date(data['end_date'])
        if 'event_type' in data: event.event_type = data['event_type']
        if 'employee_id' in data: event.employee_id = data['employee_id']
        if 'is_all_day' in data: event.is_all_day = self._parse_bool(data['is_all_day'])
        if 'color' in data: event.color = data['color']
        if 'location' in data: event.location = data['location']
        if 'photo_path' in data: event.photo_path = data['photo_path'] # Caso venha a ser usado explicitamente

        event.updated_at = datetime.utcnow()
        db.session.commit()
        return event

    def delete_event(self, event_id):
        """Deleta um evento."""
        event = CalendarEvent.query.get(event_id)
        if not event:
            return False

        # Permissão
        if self.role not in ['admin', 'rh', 'marketing']:
            if event.restaurant_id != self.restaurant_id:
                raise PermissionError('Permissão negada')

        db.session.delete(event)
        db.session.commit()
        return True

    def mark_posted(self, event_id):
        """Marca evento como postado."""
        event = CalendarEvent.query.get(event_id)
        if not event:
            return None

        if self.role not in ['admin', 'rh', 'marketing']:
            if event.restaurant_id != self.restaurant_id:
                raise PermissionError('Permissão negada')

        meta = event.metadata_json or {}
        meta['is_posted'] = True
        event.metadata_json = meta
        event.color = '#2ecc71'
        event.updated_at = datetime.utcnow()
        
        db.session.commit()
        return event

    def get_birthdays(self, month, year):
        """Obtém aniversariantes do mês."""
        query = Employee.query.filter(Employee.is_active == True)
        
        if self.role not in ['admin', 'rh', 'marketing'] and self.restaurant_id:
            query = query.filter(Employee.restaurant_id == self.restaurant_id)
        
        query = query.filter(db.extract('month', Employee.birth_date) == month)
        employees = query.all()
        
        birthdays = []
        for emp in employees:
            bday_date = self._normalize_birthday(emp.birth_date, year)
            birthdays.append({
                'employee': emp.to_dict(),
                'birthday_date': bday_date.isoformat(),
                'age': year - emp.birth_date.year
            })
        
        birthdays.sort(key=lambda x: x['employee']['birth_date'][-2:]) # Ordenar por dia (string YYYY-MM-DD -> DD)
        # Nota: O original usava x['employee']['birth_date'] que é string ISO. [-2:] pega o dia. 
        # Mas 'birth_date' do to_dict() do Employee model deve ser string. Assumindo isso.
        return birthdays

    # --- Helpers ---

    def _validate_create_data(self, data):
        required = ['title', 'start_date', 'end_date', 'event_type']
        for field in required:
            if not data.get(field):
                raise ValueError(f'{field} é obrigatório')

    def _validate_party_capacity(self, restaurant_id, start_date, end_date, description):
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            raise ValueError('Restaurante não encontrado')
        
        people_count = 0
        if description:
            match = re.search(r'Pessoas:\s*(\d+)', description, re.IGNORECASE)
            if match:
                people_count = int(match.group(1))
        
        if people_count <= 0: return

        max_capacity = restaurant.capacity or 0
        allowed_capacity = max_capacity * 0.20
        
        time_buffer = timedelta(hours=1, minutes=30)
        conflicting = CalendarEvent.query.filter(
            CalendarEvent.restaurant_id == restaurant_id,
            CalendarEvent.event_type == 'birthday_party',
            CalendarEvent.start_date < end_date + time_buffer,
            CalendarEvent.end_date + time_buffer > start_date
        ).all()
        
        occupied = sum(
            int(re.search(r'Pessoas:\s*(\d+)', e.description or '', re.IGNORECASE).group(1) or 0)
            for e in conflicting
            if re.search(r'Pessoas:\s*(\d+)', e.description or '', re.IGNORECASE)
        )
        
        if people_count + occupied > allowed_capacity:
             raise ValueError(
                 f'Capacidade insuficiente. Disponível: {int(allowed_capacity - occupied)}. '
                 'Precisa de 1h30 de intervalo entre festas ou menos convidados.'
             )

    def _handle_file_upload(self, file):
        if not file or not file.filename: return None
        
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            raise ValueError('Formato de imagem não suportado')
            
        unique_name = f"event_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{ext}"
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'events')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_name)
        file.save(file_path)
        return unique_name # Retorna apenas o nome para salvar no banco relativo a uploads/events/

    def _parse_date(self, date_str):
        if isinstance(date_str, datetime): return date_str
        return datetime.fromisoformat(date_str.replace('Z', ''))

    def _parse_bool(self, val):
        if isinstance(val, bool): return val
        if isinstance(val, str): return val.lower() in ('true', '1', 'yes', 'on')
        return bool(val)

    def _normalize_birthday(self, original_date, target_year):
        try:
            return original_date.replace(year=target_year)
        except ValueError:
            return original_date.replace(year=target_year, day=28)
