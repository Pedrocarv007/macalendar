"""
API routes para Dashboard
"""
from flask import Blueprint, jsonify, session, g
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
@session_required
def get_stats():
    """Obter estatísticas do dashboard"""
    try:
        # Contar colaboradores ativos
        total_employees = Employee.query.filter_by(is_active=True).count()
        
        # Contar eventos de hoje
        today = datetime.utcnow().date()
        today_events = CalendarEvent.query.filter(
            db.func.date(CalendarEvent.start_date) == today
        ).count()
        
        # Contar restaurantes ativos
        total_restaurants = Restaurant.query.filter_by(is_active=True).count()
        
        # Contar documentos
        total_documents = Document.query.count()
        
        return jsonify({
            'employees': total_employees,
            'todayEvents': today_events,
            'restaurants': total_restaurants,
            'documents': total_documents
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/events/recent', methods=['GET'])
@session_required
def get_recent_events():
    """Obter eventos recentes (próximos 7 dias)"""
    try:
        now = datetime.utcnow()
        week_later = now + timedelta(days=7)
        
        events = CalendarEvent.query.filter(
            CalendarEvent.start_date >= now,
            CalendarEvent.start_date <= week_later
        ).order_by(CalendarEvent.start_date).limit(6).all()
        
        return jsonify([event.to_dict() for event in events]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/activities', methods=['GET'])
@api_login_required
def get_activities():
    """Obter feed de atividades recentes com permissões"""
    try:
        user_role = g.get('current_user_role')
        user_restaurant_id = g.get('current_user_restaurant_id')
        
        # Query base - últimos 50 logs ordenados por data
        query = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(50)
        
        # Filtrar por permissões
        if user_role in ['admin', 'rh']:
            # Admin e RH veem tudo
            pass
        elif user_role == 'manager' and user_restaurant_id:
            # Gerente só vê do seu restaurante
            query = query.filter(ActivityLog.restaurant_id == user_restaurant_id)
        else:
            # Outros não veem nada
            return jsonify([]), 200
        
        activities = query.all()
        
        print(f"📋 [ACTIVITIES] Encontrados {len(activities)} logs")
        if activities:
            first = activities[0]
            print(f"📋 [ACTIVITIES] Primeiro log - ID: {first.id}, created_at: {first.created_at}, tipo: {type(first.created_at)}")
        
        result = [activity.to_dict() for activity in activities]
        if result:
            print(f"📋 [ACTIVITIES] Primeiro resultado to_dict: {result[0]}")
        
        return jsonify(result), 200
    except Exception as e:
        print(f"❌ [ACTIVITIES] Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
