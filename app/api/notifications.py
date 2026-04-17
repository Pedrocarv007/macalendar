"""
API de Notificações
"""
from datetime import datetime

from flask import Blueprint, jsonify, request, g
from sqlalchemy import or_, and_

from app.extensions.database import db
from app.middleware.security import api_login_required, role_required
from app.models.notification import Notification
from app.utils.notifications import _send_notification_email

notifications_bp = Blueprint('notifications', __name__)


def _audience_filter(user_id, user_role, restaurant_id):
    """Mesmo filtro usado no modelo, mas inline para queries nesta rota."""
    audience_roles = ['all']
    if user_role == 'manager':
        audience_roles.append('manager')
    else:
        audience_roles.append('employee')

    return or_(
        Notification.user_id == user_id,
        and_(
            Notification.user_id.is_(None),
            Notification.audience.in_(audience_roles),
            or_(Notification.restaurant_id.is_(None), Notification.restaurant_id == restaurant_id)
        )
    )


@notifications_bp.route('', methods=['GET'])
@api_login_required
def list_notifications():
    user_id = g.get('current_user_id')
    user_role = g.get('current_user_role')
    restaurant_id = g.get('current_user_restaurant_id')

    limit = request.args.get('limit', default=20, type=int)
    offset = request.args.get('offset', default=0, type=int)
    unread_only = request.args.get('unread_only', default='false').lower() in ['1', 'true', 'yes', 'on']

    query = Notification.query.filter(_audience_filter(user_id, user_role, restaurant_id)).order_by(Notification.created_at.desc())
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return jsonify({
        'notifications': [n.to_dict() for n in items],
        'total': total,
        'unread_count': Notification.unread_count_for(user_id, user_role, restaurant_id)
    }), 200


@notifications_bp.route('/mark-read', methods=['POST'])
@api_login_required
def mark_notifications_read():
    user_id = g.get('current_user_id')
    user_role = g.get('current_user_role')
    restaurant_id = g.get('current_user_restaurant_id')

    data = request.get_json() or {}
    ids = data.get('notification_ids') or []
    if isinstance(ids, int):
        ids = [ids]

    if not ids:
        return jsonify({'error': 'notification_ids é obrigatório'}), 400

    # Apenas notificações que o usuário pode ver
    query = Notification.query.filter(
        Notification.id.in_(ids),
        _audience_filter(user_id, user_role, restaurant_id)
    )

    now = datetime.utcnow()
    updated = 0
    for n in query.all():
        if n.read_at is None:
            n.read_at = now
            updated += 1
    db.session.commit()

    return jsonify({'updated': updated}), 200


@notifications_bp.route('', methods=['POST'])
@api_login_required
@role_required('admin', 'rh', 'manager')
def create_notification():
    user_id = g.get('current_user_id')
    user_role = g.get('current_user_role')
    restaurant_id = g.get('current_user_restaurant_id')

    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title é obrigatório'}), 400

    notification = Notification(
        title=title,
        message=(data.get('message') or '').strip() or None,
        category=(data.get('category') or '').strip() or None,
        audience=(data.get('audience') or 'all').strip().lower() or 'all',
        restaurant_id=data.get('restaurant_id') or restaurant_id,
        user_id=data.get('user_id') or None,
        created_by=user_id,
    )

    db.session.add(notification)
    db.session.commit()
    try:
        _send_notification_email(notification)
    except Exception:
        pass
    return jsonify({'notification': notification.to_dict()}), 201

