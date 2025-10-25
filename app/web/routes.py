"""
Rotas da interface web principal
"""
from flask import Blueprint, render_template, request, redirect, url_for

# Blueprint principal da web
web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Página inicial - redireciona para login ou dashboard"""
    # Se o usuário estiver autenticado, vai para dashboard
    # Senão, vai para login
    return redirect(url_for('auth_web.login'))

@web_bp.route('/dashboard')
def dashboard():
    """Dashboard principal"""
    return render_template('dashboard.html')

@web_bp.route('/calendar')
def calendar():
    """Página do calendário"""
    return render_template('calendar.html')

@web_bp.route('/employees')
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