"""
Rotas da interface web principal
"""
from flask import Blueprint, render_template, request, redirect, url_for, session
from functools import wraps

# Blueprint principal da web
web_bp = Blueprint('web', __name__)

def login_required(f):
    """Decorator para verificar se o usuário está logado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Para desenvolvimento, vamos permitir acesso sem autenticação
        # mas adicionar uma verificação JavaScript no frontend
        return f(*args, **kwargs)
    return decorated_function

@web_bp.route('/')
def index():
    """Página inicial - redireciona para login ou dashboard"""
    # Se o usuário estiver autenticado, vai para dashboard
    # Senão, vai para login
    return redirect(url_for('auth_web.login'))

@web_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal"""
    return render_template('dashboard.html')

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