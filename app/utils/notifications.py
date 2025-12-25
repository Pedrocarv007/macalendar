"""
Helpers para criação de notificações.
"""
from datetime import datetime

from typing import Optional

from app.extensions.database import db
from app.models.notification import Notification
from app.models.employee import Employee
from app.models.settings import UserSettings
from app.utils.email import send_email_async


def _user_notifications_enabled(user_id: int) -> bool:
    if not user_id:
        return False
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    return settings.notifications_enabled if settings else True


def notify_login(user: Employee, actor_id: Optional[int] = None):
    """Cria notificação de login para o próprio usuário (se habilitado)."""
    if not user or not _user_notifications_enabled(user.id):
        return
    notif = Notification(
        title="Login realizado",
        message=f"{user.name} acessou o sistema.",
        category="login",
        audience="employee",
        user_id=user.id,
        restaurant_id=user.restaurant_id,
        created_by=actor_id or user.id,
        created_at=datetime.utcnow(),
    )
    db.session.add(notif)
    db.session.commit()
    try:
        _send_notification_email(notif)
    except Exception:
        pass


def notify_employee_change(action: str, target: Employee, actor: Optional[Employee]):
    """Notifica o próprio colaborador e os gerentes do restaurante sobre mudanças."""
    if not target:
        return
    actor_id = actor.id if actor else None
    restaurant_id = target.restaurant_id

    # Notificar o próprio colaborador
    if _user_notifications_enabled(target.id):
        db.session.add(Notification(
            title=f"Atualização de cadastro ({action})",
            message=f"Seu cadastro foi {action}.",
            category="employee_change",
            audience="employee",
            user_id=target.id,
            restaurant_id=restaurant_id,
            created_by=actor_id,
            created_at=datetime.utcnow(),
        ))

    # Notificar gerentes do restaurante
    manager_roles = ['manager', 'shift_manager', 'sub_manager']
    managers = Employee.query.filter(
        Employee.restaurant_id == restaurant_id,
        Employee.role.in_(manager_roles),
        Employee.is_active.is_(True)
    ).all()
    for mgr in managers:
        if not _user_notifications_enabled(mgr.id):
            continue
        db.session.add(Notification(
            title=f"Colaborador {action}",
            message=f"{target.name} foi {action}.",
            category="employee_change",
            audience="manager",
            user_id=mgr.id,
            restaurant_id=restaurant_id,
            created_by=actor_id,
            created_at=datetime.utcnow(),
        ))

    db.session.commit()
    try:
        # Enviar emails para todas as notificações recém-criadas relacionadas ao target
        # Buscar últimas notificações desse target no último minuto
        recent = Notification.query.order_by(Notification.created_at.desc()).limit(20).all()
        for n in recent:
            _send_notification_email(n)
    except Exception:
        pass

def _send_notification_email(notification: Notification) -> None:
    """Enviar email de uma notificação ao destinatário se permitido."""
    if not notification:
        return
    # Determinar destinatários
    recipients: list[str] = []
    # Quando há user_id, enviar diretamente
    if notification.user_id:
        user = Employee.query.get(notification.user_id)
        if user and user.email:
            settings = UserSettings.query.filter_by(user_id=user.id).first()
            if (settings.email_notifications if settings else True):
                recipients.append(user.email)
    else:
        # Enviar por audiência
        if notification.audience == 'manager':
            roles = ['manager', 'shift_manager', 'sub_manager']
            q = Employee.query.filter(Employee.is_active.is_(True))
            if notification.restaurant_id:
                q = q.filter(Employee.restaurant_id == notification.restaurant_id)
            q = q.filter(Employee.role.in_(roles))
            for emp in q.all():
                st = UserSettings.query.filter_by(user_id=emp.id).first()
                if (st.email_notifications if st else True) and emp.email:
                    recipients.append(emp.email)
        elif notification.audience in ('employee', 'all'):
            q = Employee.query.filter(Employee.is_active.is_(True))
            if notification.restaurant_id:
                q = q.filter(Employee.restaurant_id == notification.restaurant_id)
            for emp in q.all():
                st = UserSettings.query.filter_by(user_id=emp.id).first()
                if (st.email_notifications if st else True) and emp.email:
                    recipients.append(emp.email)

    if not recipients:
        return
    subject = notification.title or 'Notificação'
    html = f"""
        <h3 style='margin:0 0 8px'>{notification.title or 'Notificação'}</h3>
        <p style='margin:0 0 12px'>{notification.message or ''}</p>
        <small style='color:#666'>Categoria: {notification.category or 'geral'}</small>
    """
    try:
        send_email_async(
            to=recipients,
            subject=subject,
            html=html,
            mail_profile="noreply",
        )
    except Exception:
        pass
