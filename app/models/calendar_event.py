"""
Modelo de Evento de Calendário
"""
from app.extensions.database import db
from datetime import datetime

class CalendarEvent(db.Model):
    """Modelo de Evento de Calendário"""
    __tablename__ = 'calendar_events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False, index=True)
    end_date = db.Column(db.DateTime, nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)  # meeting, birthday, holiday, shift, training, etc.
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    is_all_day = db.Column(db.Boolean, default=False, nullable=False)
    color = db.Column(db.String(7), default='#3788d8', nullable=False)  # Cor do evento em hex
    location = db.Column(db.String(200), nullable=True)
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_rule = db.Column(db.String(500), nullable=True)  # Regra de recorrência (RRULE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    employee_ref = db.relationship('Employee', foreign_keys=[employee_id], overlaps='events')
    creator = db.relationship('Employee', foreign_keys=[created_by], overlaps='created_events')
    # Restaurant relationship is auto-created by Restaurant.calendar_events backref
    
    @property
    def duration_minutes(self):
        """Duração do evento em minutos"""
        return int((self.end_date - self.start_date).total_seconds() / 60)
    
    @property
    def is_past(self):
        """Verifica se o evento já passou"""
        return self.end_date < datetime.utcnow()
    
    @property
    def is_today(self):
        """Verifica se o evento é hoje"""
        today = datetime.utcnow().date()
        return self.start_date.date() <= today <= self.end_date.date()
    
    @property
    def employee(self):
        """Get employee for backward compatibility"""
        return self.employee_ref
    
    def to_dict(self):
        """Converter para dicionário (formato FullCalendar)"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start': self.start_date.isoformat(),
            'end': self.end_date.isoformat(),
            'allDay': self.is_all_day,
            'color': self.color,
            'backgroundColor': self.color,
            'borderColor': self.color,
            'extendedProps': {
                'event_type': self.event_type,
                'restaurant_id': self.restaurant_id,
                'restaurant_name': self.restaurant.name if self.restaurant else None,
                'created_by': self.created_by,
                'creator_name': self.creator.name if self.creator else None,
                'employee_id': self.employee_id,
                'employee_name': self.employee.name if self.employee else None,
                'location': self.location,
                'is_recurring': self.is_recurring,
                'recurrence_rule': self.recurrence_rule,
                'duration_minutes': self.duration_minutes,
                'is_past': self.is_past,
                'is_today': self.is_today,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat()
            }
        }
    
    def __repr__(self):
        return f'<CalendarEvent {self.title}>'