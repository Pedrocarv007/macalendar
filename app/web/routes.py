"""
Rotas da interface web principal
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.middleware.security import login_required, web_role_required
from app.extensions.database import db
from datetime import datetime, timedelta

# Blueprint principal da web
web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Página inicial - redireciona para login ou dashboard"""
    # Se o usuário estiver autenticado, vai para dashboard
    if 'user_id' in session:
        return redirect(url_for('web.dashboard'))
    # Senão, vai para login
    return redirect(url_for('auth_web.login'))

@web_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal"""
    return render_template('dashboard.html')

@web_bp.route('/dashboard/stats')
@login_required
def dashboard_stats():
    """Estatísticas do dashboard"""
    from app.models.employee import Employee
    from app.models.restaurant import Restaurant
    from app.models.document import Document
    from app.models.calendar_event import CalendarEvent
    from datetime import datetime
    
    try:
        # Contar colaboradores
        total_employees = Employee.query.filter_by(is_active=True).count()
        
        # Contar eventos de hoje
        today = datetime.utcnow().date()
        today_events = CalendarEvent.query.filter(
            db.func.date(CalendarEvent.start_date) == today
        ).count()
        
        # Contar restaurantes
        total_restaurants = Restaurant.query.filter_by(is_active=True).count()
        
        # Contar documentos
        total_documents = Document.query.count()
        
        return jsonify({
            'employees': total_employees,
            'todayEvents': today_events,
            'restaurants': total_restaurants,
            'documents': total_documents
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_bp.route('/calendar/events/recent')
@login_required
def recent_events():
    """Eventos recentes"""
    from app.models.calendar_event import CalendarEvent
    from datetime import datetime, timedelta
    
    try:
        # Buscar eventos dos próximos 7 dias
        now = datetime.utcnow()
        week_later = now + timedelta(days=7)
        
        events = CalendarEvent.query.filter(
            CalendarEvent.start_date >= now,
            CalendarEvent.start_date <= week_later
        ).order_by(CalendarEvent.start_date).limit(6).all()
        
        return jsonify([event.to_dict() for event in events])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_bp.route('/dashboard/activities')
@login_required
def dashboard_activities():
    """Atividades recentes"""
    # Por enquanto retornar dados mock
    # Você pode implementar um sistema de logs/atividades depois
    return jsonify([
        {
            'title': 'Novo colaborador adicionado',
            'description': 'João Silva foi adicionado ao sistema',
            'timestamp': '2024-01-15T10:30:00',
            'type': 'success',
            'icon': 'user-plus'
        },
        {
            'title': 'Evento criado',
            'description': 'Reunião de equipe agendada para amanhã',
            'timestamp': '2024-01-15T09:15:00',
            'type': 'info',
            'icon': 'calendar-plus'
        },
        {
            'title': 'Documento gerado',
            'description': 'Relatório mensal de vendas',
            'timestamp': '2024-01-14T16:45:00',
            'type': 'warning',
            'icon': 'file-alt'
        }
    ])

@web_bp.route('/calendar')
@login_required
def calendar():
    """Página do calendário"""
    return render_template('calendar.html')

@web_bp.route('/employees')
@login_required
def employees():
    """Página de colaboradores"""
    return render_template('employees.html')

@web_bp.route('/employees/new')
def new_employee():
    """Página para adicionar novo colaborador"""
    return render_template('employees/new.html')

@web_bp.route('/employees/<int:employee_id>')
def employee_detail(employee_id):
    """Página de detalhes do colaborador"""
    return render_template('employees/detail.html', employee_id=employee_id)

@web_bp.route('/restaurants')
@login_required
def restaurants():
    """Página de restaurantes"""
    return render_template('restaurants.html')

@web_bp.route('/restaurants/new')
def new_restaurant():
    """Página para adicionar novo restaurante"""
    return render_template('restaurants/new.html')

@web_bp.route('/restaurants/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    """Página de detalhes do restaurante"""
    return render_template('restaurants/detail.html', restaurant_id=restaurant_id)

@web_bp.route('/documents')
@login_required
def documents():
    """Página de documentos"""
    return render_template('documents.html')

@web_bp.route('/documents/new')
def new_document():
    """Página para gerar novo documento"""
    return render_template('documents/new.html')

@web_bp.route('/profile')
def profile():
    """Página de perfil do usuário"""
    return render_template('profile.html')

@web_bp.route('/settings')
def settings():
    """Página de configurações"""
    return render_template('settings.html')