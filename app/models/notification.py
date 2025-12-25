"""
Modelo de Notificação para usuários e grupos (managers/employees/all).
"""
from datetime import datetime

from sqlalchemy import or_, and_

from app.extensions.database import db


class Notification(db.Model):
    """Notificações direcionadas a usuários ou públicos (audience)."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)  # login, employee_change, system, etc
    audience = db.Column(db.String(20), nullable=True)  # all, manager, employee
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'category': self.category,
            'audience': self.audience,
            'restaurant_id': self.restaurant_id,
            'user_id': self.user_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }

    @staticmethod
    def _audience_filter(user_id, user_role, restaurant_id):
        """Retorna filtro OR para notificações destinadas ao usuário ou ao seu público."""
        audience_roles = ['all']
        if user_role == 'manager':
            audience_roles.append('manager')
        else:
            audience_roles.append('employee')

        # Notificações direcionadas diretamente ao usuário OU ao público/restaurant.
        filters = [Notification.user_id == user_id]
        filters.append(
            and_(
                Notification.user_id.is_(None),
                Notification.audience.in_(audience_roles),
                or_(Notification.restaurant_id.is_(None), Notification.restaurant_id == restaurant_id)
            )
        )
        return or_(*filters)

    @classmethod
    def unread_count_for(cls, user_id, user_role, restaurant_id):
        if not user_id:
            return 0
        return cls.query.filter(
            cls.read_at.is_(None),
            cls._audience_filter(user_id, user_role, restaurant_id)
        ).count()

    @classmethod
    def query_for_user(cls, user_id, user_role, restaurant_id):
        return cls.query.filter(cls._audience_filter(user_id, user_role, restaurant_id))
