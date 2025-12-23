"""
API routes para Dashboard
"""
from flask import Blueprint, jsonify, session, g, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.models.document import Document
from app.models.calendar_event import CalendarEvent
from app.models.activity_log import ActivityLog
from app.extensions.database import db
from datetime import datetime, timedelta
from functools import wraps
from app.middleware.security import api_login_required

dashboard_bp = Blueprint('dashboard', __name__)

def session_required(f):
    """Decorator para requerer sessão de usuário"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/stats', methods=['GET'])
@api_login_required
def get_stats():
    """Obter estatísticas do dashboard com filtros de permissão"""
    try:
        user_role = (g.get('current_user_role') or '').lower()
        user_restaurant_id = g.get('current_user_restaurant_id')
        requested_restaurant_id = request.args.get('restaurant_id', type=int)

        # Determinar restaurante alvo com base no papel
        if user_role == 'admin':
            target_restaurant_id = requested_restaurant_id
        else:
            target_restaurant_id = user_restaurant_id or requested_restaurant_id

        # Base de queries
        emp_query = Employee.query.filter_by(is_active=True)
        rest_query = Restaurant.query.filter_by(is_active=True)
        doc_query = Document.query
        today = datetime.utcnow().date()
        events_query = CalendarEvent.query.filter(
            db.func.date(CalendarEvent.start_date) == today
        )

        # Aplicar filtro por restaurante quando definido
        if target_restaurant_id:
            emp_query = emp_query.filter(Employee.restaurant_id == target_restaurant_id)
            rest_query = rest_query.filter(Restaurant.id == target_restaurant_id)
            doc_query = doc_query.filter(Document.restaurant_id == target_restaurant_id)
            events_query = events_query.filter(CalendarEvent.restaurant_id == target_restaurant_id)

        total_employees = emp_query.count()
        today_events = events_query.count()
        total_restaurants = rest_query.count()
        total_documents = doc_query.count()

        return jsonify({
            'employees': total_employees,
            'todayEvents': today_events,
            'restaurants': total_restaurants,
            'documents': total_documents
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/events/recent', methods=['GET'])
@api_login_required
def get_recent_events():
    """Obter eventos recentes (próximos 7 dias) com filtros de permissão"""
    try:
        user_role = (g.get('current_user_role') or '').lower()
        user_restaurant_id = g.get('current_user_restaurant_id')
        requested_restaurant_id = request.args.get('restaurant_id', type=int)

        now = datetime.utcnow()
        week_later = now + timedelta(days=7)

        query = CalendarEvent.query.filter(
            CalendarEvent.start_date >= now,
            CalendarEvent.start_date <= week_later
        )

        # Aplicar filtro por restaurante conforme papel
        if user_role == 'admin':
            if requested_restaurant_id:
                query = query.filter(CalendarEvent.restaurant_id == requested_restaurant_id)
        else:
            target_restaurant_id = user_restaurant_id or requested_restaurant_id
            if target_restaurant_id:
                query = query.filter(CalendarEvent.restaurant_id == target_restaurant_id)
            else:
                return jsonify([]), 200

        events = query.order_by(CalendarEvent.start_date).limit(6).all()
        return jsonify([event.to_dict() for event in events]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/activities', methods=['GET'])
@api_login_required
def get_activities():
    """Obter feed de atividades recentes com permissões"""
    try:
        user_role = (g.get('current_user_role') or '').lower()
        user_restaurant_id = g.get('current_user_restaurant_id')

        # Permitir filtro explícito via querystring quando aplicável
        requested_restaurant_id = request.args.get('restaurant_id', type=int)

        # Construir query base e aplicar filtros ANTES de limitar/ordenar
        query = ActivityLog.query

        if user_role == 'admin':
            # Admin pode ver tudo; se houver restaurant_id explícito, filtra
            if requested_restaurant_id:
                query = query.filter(ActivityLog.restaurant_id == requested_restaurant_id)
        else:
            # RH, manager e abaixo veem apenas do próprio restaurante
            target_restaurant_id = user_restaurant_id or requested_restaurant_id
            if target_restaurant_id:
                query = query.filter(ActivityLog.restaurant_id == target_restaurant_id)
            else:
                # Sem restaurante associado, não retorna dados
                return jsonify([]), 200

        # Ordenação e limite após filtros
        query = query.order_by(ActivityLog.created_at.desc()).limit(50)

        activities = query.all()
        result = [activity.to_dict() for activity in activities]
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Erro ao buscar atividades'}), 500
