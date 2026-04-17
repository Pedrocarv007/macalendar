"""
configura;oes de preferencias do usuario para o seu sistema
"""
from app.extensions.database import db
from datetime import datetime

class UserSettings(db.Model):
    """Modelo de Configurações do Usuário"""
    __tablename__ = 'user_settings'
    
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)
    two_factor_enabled = db.Column(db.Boolean, default=False, nullable=False)
    auto_logout_enabled = db.Column(db.Boolean, default=True, nullable=False)
    session_timeout_minutes = db.Column(db.Integer, default=30, nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, unique=True)
    timezone = db.Column(db.String(50), default='Europe/Lisbon', nullable=False)
    notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)
    items_per_page = db.Column(db.Integer, default=20, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    user = db.relationship('Employee', backref=db.backref('settings', uselist=False))
    
    def to_dict(self):
        """Converter para dicionário simples"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timezone': self.timezone,
            'notifications_enabled': self.notifications_enabled,
            'items_per_page': self.items_per_page,
            'dark_mode': self.dark_mode,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
