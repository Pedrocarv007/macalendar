"""
Modelo de Log de Atividades
"""
from app.extensions.database import db
from datetime import datetime

class ActivityLog(db.Model):
    """Modelo de Log de Atividades do Sistema"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)  # employee_created, document_created, etc.
    description = db.Column(db.Text, nullable=False)  # Descrição da atividade
    user_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)  # Quem fez a ação
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)  # Restaurante relacionado
    target_id = db.Column(db.Integer, nullable=True)  # ID do objeto afetado (employee_id, document_id, etc.)
    target_type = db.Column(db.String(50), nullable=True)  # Tipo do objeto (employee, document, etc.)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relacionamentos
    user = db.relationship('Employee', foreign_keys=[user_id])
    restaurant = db.relationship('Restaurant', foreign_keys=[restaurant_id])
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'id': self.id,
            'activity_type': self.activity_type,
            'description': self.description,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'restaurant_id': self.restaurant_id,
            'restaurant_name': self.restaurant.name if self.restaurant else None,
            'target_id': self.target_id,
            'target_type': self.target_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_at_relative': self._get_relative_time()
        }
    
    def _get_relative_time(self):
        """Retornar tempo relativo (ex: '2 horas atrás')"""
        if not self.created_at:
            return 'Data desconhecida'
        
        try:
            # Garantir que created_at é um objeto datetime
            if isinstance(self.created_at, str):
                created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            else:
                created_at = self.created_at
            
            now = datetime.utcnow()
            diff = now - created_at
            
            seconds = diff.total_seconds()
            
            # Se o timestamp for negativo (futuro), retornar "Agora mesmo"
            if seconds < 0:
                return 'Agora mesmo'
            
            if seconds < 60:
                return 'Agora mesmo'
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f'{minutes} minuto{"s" if minutes > 1 else ""} atrás'
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f'{hours} hora{"s" if hours > 1 else ""} atrás'
            elif seconds < 604800:
                days = int(seconds / 86400)
                return f'{days} dia{"s" if days > 1 else ""} atrás'
            else:
                return created_at.strftime('%d/%m/%Y às %H:%M')
        except Exception as e:
            print(f"[ERRO] Erro ao calcular tempo relativo: {e}")
            return 'Data desconhecida'
    
    @staticmethod
    def log_activity(activity_type, description, user_id, restaurant_id=None, target_id=None, target_type=None):
        """Helper para criar um log de atividade"""
        log = ActivityLog(
            activity_type=activity_type,
            description=description,
            user_id=user_id,
            restaurant_id=restaurant_id,
            target_id=target_id,
            target_type=target_type
        )
        db.session.add(log)
        return log
