"""
Modelo de Documento
"""
from app.extensions.database import db
from datetime import datetime
import os

class Document(db.Model):
    """Modelo de Documento"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    document_type = db.Column(db.String(50), nullable=False, index=True)  # birthday, praise, certificate, memo
    template_name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Conteúdo específico (como texto do elogio)
    filename = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # Tamanho em bytes
    status = db.Column(db.String(20), default='draft', nullable=False)  # draft, generated, sent
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @property
    def file_exists(self):
        """Verifica se o arquivo existe no sistema"""
        if not self.file_path:
            return False
        return os.path.exists(self.file_path)
    
    @property
    def file_size_mb(self):
        """Tamanho do arquivo em MB"""
        if not self.file_size:
            return 0
        return round(self.file_size / (1024 * 1024), 2)
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'id': self.id,
            'title': self.title,
            'document_type': self.document_type,
            'template_name': self.template_name,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'restaurant_id': self.restaurant_id,
            'restaurant_name': self.restaurant.name if self.restaurant else None,
            'created_by': self.created_by,
            'creator_name': self.creator.name if self.creator else None,
            'content': self.content,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'status': self.status,
            'file_exists': self.file_exists,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Document {self.title}>'