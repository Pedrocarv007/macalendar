"""
DEPRECATED: Use Employee model instead. This model is kept for backward compatibility only.
All user data has been migrated to the Employee model which now includes authentication fields.
"""
from app.extensions.database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """Modelo de Usuário - DEPRECATED, use Employee instead"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    department = db.Column(db.String(50), nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos - DISABLED during consolidation to Employee model
    # These are kept commented out to prevent foreign key conflicts
    # restaurant = db.relationship('Restaurant', foreign_keys=[restaurant_id], back_populates='users')
    # managed_restaurant = db.relationship('Restaurant', foreign_keys='Restaurant.manager_id', back_populates='manager', uselist=False)
    # created_events = db.relationship('CalendarEvent', foreign_keys='CalendarEvent.created_by', backref='creator_user', lazy=True)
    # created_documents = db.relationship('Document', foreign_keys='Document.created_by', backref='creator_user', lazy=True)
    # employee = db.relationship('Employee', foreign_keys=[employee_id], uselist=False)
    
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
            'employee_id': self.employee_id,
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