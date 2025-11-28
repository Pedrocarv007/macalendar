"""
Modelo de Colaborador/Funcionário
Agora inclui campos de autenticação (consolidado com users)
"""
from app.extensions.database import db
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

class Employee(db.Model):
    """Modelo de Colaborador (agora também user)"""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    position = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50), nullable=True)
    birth_date = db.Column(db.Date, nullable=False, index=True)
    hire_date = db.Column(db.Date, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Campos de autenticação (consolidados de users)
    role = db.Column(db.String(20), nullable=False, default='employee', index=True)  # admin, rh, marketing, manager, employee
    last_login = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    events = db.relationship('CalendarEvent', foreign_keys='CalendarEvent.employee_id', lazy=True)
    documents = db.relationship('Document', foreign_keys='Document.employee_id', lazy=True)
    created_documents = db.relationship('Document', foreign_keys='Document.created_by', lazy=True)
    created_events = db.relationship('CalendarEvent', foreign_keys='CalendarEvent.created_by', lazy=True)
    
    def set_password(self, password):
        """Definir senha com hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar senha"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
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
            return self.birth_date.replace(year=today.year + 1)
        return birthday_this_year
    
    @property
    def days_until_birthday(self):
        """Dias até o próximo aniversário"""
        return (self.next_birthday - date.today()).days
    
    @property
    def is_birthday_today(self):
        """Verifica se hoje é aniversário"""
        today = date.today()
        return (today.month, today.day) == (self.birth_date.month, self.birth_date.day)
    
    @property
    def work_years(self):
        """Anos de trabalho"""
        if not self.hire_date:
            return 0
        today = date.today()
        return today.year - self.hire_date.year - ((today.month, today.day) < (self.hire_date.month, self.hire_date.day))
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'position': self.position,
            'department': self.department,
            'birth_date': self.birth_date.isoformat(),
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'photo_filename': self.photo_filename,
            'restaurant_id': self.restaurant_id,
            'restaurant_name': self.restaurant.name if self.restaurant else None,
            'is_active': self.is_active,
            'address': self.address,
            'notes': self.notes,
            'role': self.role,
            'age': self.age,
            'work_years': self.work_years,
            'next_birthday': self.next_birthday.isoformat(),
            'days_until_birthday': self.days_until_birthday,
            'is_birthday_today': self.is_birthday_today,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Employee {self.name}>'