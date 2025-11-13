"""
Middleware de segurança e validações
"""
from flask import request, jsonify, g, session, redirect, url_for, flash
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from functools import wraps
import re

def init_security(app):
    """Inicializar middleware de segurança"""
    
    @app.before_request
    def before_request():
        """Executar antes de cada requisição"""
        
        # Log de requisições (opcional)
        if app.config.get('LOG_REQUESTS'):
            app.logger.info(f"{request.method} {request.path} - IP: {request.remote_addr}")
        
        # Verificar se é uma rota da API que precisa de autenticação
        if request.path.startswith('/api/') and request.endpoint != 'auth.login':
            # Pular verificação para rotas públicas
            public_routes = [
                '/api/auth/login',
                '/api/auth/register',
                '/api',
                '/api/health',
                '/',
                '/health'
            ]
            
            if request.path not in public_routes:
                try:
                    verify_jwt_in_request()
                    g.current_user_id = get_jwt_identity()
                    g.current_user_claims = get_jwt()
                except Exception as e:
                    return jsonify({'error': 'Token inválido ou expirado'}), 401

def role_required(*allowed_roles):
    """Decorator para verificar permissões por role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get('role')
                
                if user_role not in allowed_roles:
                    return jsonify({'error': 'Permissão insuficiente'}), 403
                
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': 'Token inválido'}), 401
        
        return decorated_function
    return decorator

def restaurant_access_required(f):
    """Decorator para verificar acesso ao restaurante"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role')
            user_restaurant_id = claims.get('restaurant_id')
            
            # Admin, RH e Marketing têm acesso a todos os restaurantes
            if user_role in ['admin', 'rh', 'marketing']:
                return f(*args, **kwargs)
            
            # Verificar se o usuário tem restaurante associado
            if not user_restaurant_id:
                return jsonify({'error': 'Usuário sem restaurante associado'}), 403
            
            # Verificar se está tentando acessar dados do próprio restaurante
            restaurant_id = kwargs.get('restaurant_id') or request.json.get('restaurant_id') if request.json else None
            
            if restaurant_id and restaurant_id != user_restaurant_id:
                return jsonify({'error': 'Acesso negado a este restaurante'}), 403
            
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Erro de autorização'}), 401
    
    return decorated_function

def validate_email(email):
    """Validar formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validar formato de telefone brasileiro"""
    if not phone:
        return True  # Telefone é opcional
    
    # Remover caracteres não numéricos
    clean_phone = re.sub(r'[^\d]', '', phone)
    
    # Verificar se tem 10 ou 11 dígitos (com DDD)
    return len(clean_phone) in [10, 11]

def validate_password_strength(password):
    """Validar força da senha"""
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    
    if not re.search(r'[a-z]', password):
        return False, "Senha deve conter pelo menos uma letra minúscula"
    
    if not re.search(r'[A-Z]', password):
        return False, "Senha deve conter pelo menos uma letra maiúscula"
    
    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', password):
        return False, "Senha deve conter pelo menos um caractere especial"
    
    # Verificar senhas comuns
    common_passwords = [
        'password', '12345678', 'qwerty123', 'admin123', 
        'password123', 'abc123456', 'senha123', 'Senha123'
    ]
    if password.lower() in [p.lower() for p in common_passwords]:
        return False, "Senha muito comum. Escolha uma senha mais forte"
    
    return True, "Senha válida"

def sanitize_filename(filename):
    """Sanitizar nome de arquivo"""
    # Remover caracteres perigosos
    filename = re.sub(r'[^\w\s-.]', '', filename)
    # Remover espaços múltiplos
    filename = re.sub(r'\s+', '_', filename)
    # Limitar tamanho
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = f"{name[:250]}.{ext}" if ext else name[:255]
    
    return filename

def allowed_file(filename, allowed_extensions):
    """Verificar se extensão do arquivo é permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def login_required(f):
    """Decorator para rotas web que precisam de autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('auth_web.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def web_role_required(*allowed_roles):
    """Decorator para verificar permissões por role em rotas web"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor, faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth_web.login', next=request.url))
            
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('web.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator