# app/services/base_service.py

class BaseService:
    def __init__(self, user_id, user_role, user_restaurant_id):
        self.user_id = user_id
        self.role = user_role
        self.restaurant_id = user_restaurant_id

    def log_activity(self, activity_type, description, target_id, target_type):
        """Método global de log disponível para todos os serviços."""
        from app.models.activity_log import ActivityLog
        from app.extensions.database import db

        ActivityLog.log_activity(
            activity_type=activity_type,
            description=description,
            user_id=self.user_id,
            restaurant_id=self.restaurant_id,
            target_id=target_id,
            target_type=target_type
        )
        db.session.commit()