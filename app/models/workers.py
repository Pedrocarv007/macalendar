"""
Modelo para os não usuários do sistema mas que trabalham na empresa.
"""

from app.extensions.database import db
from datetime import datetime, date



class Worker(db.Model):
    """Modelo de Trabalhador (não usuário do sistema)"""
    __tablename__ = 'workers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False, index=True)
    hire_date = db.Column(db.Date, nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    photo_filename = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def age(self):
        """Calcular idade atual"""
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
    
    @property
    def next_birthday(self):
        """Próximo aniversário"""
        today = date.today()
        birthday_this_year = self.birth_date.replace(year=today.year)
        if birthday_this_year < today:
            birthday_this_year = birthday_this_year.replace(year=today.year + 1)
        return birthday_this_year

    @property
    def photo_url(self):
        """URL pública da foto se existir"""
        if self.photo_filename:
            return f'/uploads/workers/{self.photo_filename}'
        return None

    def to_dict(self):
        """Converter para dicionário simples usado pelas rotas de templates"""
        return {
            'id': self.id,
            'name': self.name,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'restaurant_id': self.restaurant_id,
            'photo_filename': self.photo_filename,
            'photo_url': self.photo_url,
            'is_active': self.is_active,
            'is_worker': True,
            'age': self.age,
            'next_birthday': self.next_birthday.isoformat() if self.birth_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }