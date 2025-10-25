"""
Modelos de dados para MAC Calendar
"""
from app.extensions.database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """Modelo de Usuário"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # admin, rh, marketing, manager, employee
    department = db.Column(db.String(50), nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    restaurant = db.relationship('Restaurant', foreign_keys='User.restaurant_id', lazy=True)
    managed_restaurant = db.relationship('Restaurant', foreign_keys='Restaurant.manager_id', lazy=True)
    created_events = db.relationship('CalendarEvent', foreign_keys='CalendarEvent.created_by', backref='creator', lazy=True)
    created_documents = db.relationship('Document', foreign_keys='Document.created_by', backref='creator', lazy=True)
    
    def set_password(self, password):
        """Definir senha com hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar senha"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_sensitive=False):
        """Converter para dicionário"""
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'department': self.department,
            'restaurant_id': self.restaurant_id,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_sensitive:
            data['password_hash'] = self.password_hash
            
        return data
    
    def __repr__(self):
        return f'<User {self.email}>'