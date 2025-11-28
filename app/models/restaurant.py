"""
Modelo de Restaurante
"""
from app.extensions.database import db
from datetime import datetime

class Restaurant(db.Model):
    """Modelo de Restaurante"""
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    manager = db.relationship('Employee', foreign_keys=[manager_id], backref='managed_restaurants', uselist=False)
    employees = db.relationship('Employee', foreign_keys='Employee.restaurant_id', backref='restaurant', lazy=True)
    events = db.relationship('CalendarEvent', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'manager_id': self.manager_id,
            'manager_name': self.manager.name if self.manager else None,
            'manager_email': self.manager.email if self.manager else None,
            'is_active': self.is_active,
            'employees_count': len([e for e in self.employees if e.is_active]),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'