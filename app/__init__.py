"""
Inicialização da aplicação Flask para MAC Calendar
Sistema de gestão para restaurantes com calendário e gestão de colaboradores
"""
import os
from datetime import datetime

from flask import Flask, session, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_cors import CORS

from app.api.auth import auth_bp
from app.api.calendar import calendar_bp
from app.api.dashboard import dashboard_bp
from app.api.documents import documents_bp
from app.api.employees import employees_bp
from app.api.profile import profile_bp
from app.api.restaurants import restaurants_bp
from app.api.ai import ai_bp
from app.auth.routes import auth_web_bp
from app.config.settings import Config, config as CONFIG_MAP
from app.extensions.database import init_db
from app.middleware.security import init_security
from app.middleware.security_headers import add_security_headers, configure_https
from app.web.routes import web_bp
from app.errors import register_error_handlers

class ScriptNameMiddleware:
    """Middleware WSGI que define SCRIPT_NAME para proxy reverso"""
    def __init__(self, app, script_name):
        self.app = app
        self.script_name = script_name
    
    def __call__(self, environ, start_response):
        # Definir SCRIPT_NAME para Flask gerar URLs corretas
        environ['SCRIPT_NAME'] = self.script_name
        
        # Se PATH_INFO começa com o script_name, remover
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith(self.script_name):
            environ['PATH_INFO'] = path_info[len(self.script_name):]
            if not environ['PATH_INFO']:
                environ['PATH_INFO'] = '/'
        
        return self.app(environ, start_response)

def create_app(config_name=None):
    """Factory para criar aplicação Flask"""
    
    # Criar instância Flask
    app = Flask(__name__)
    
    # Carregar configurações
    selected_config = config_name or os.environ.get('FLASK_CONFIG') or 'default'
    config_class = CONFIG_MAP.get(selected_config, Config)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Ajustes quando atrás de proxy (IIS/ARR): respeitar X-Forwarded-*
    if os.getenv('RUNNING_ON_IIS', '0') in ('1', 'true', 'True') or os.getenv('BEHIND_PROXY', '0') in ('1', 'true', 'True'):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Adicionar middleware WSGI para proxy reverso com subpath (ex.: /mac)
    app_root = app.config.get('APPLICATION_ROOT') or '/mac'
    if app_root and isinstance(app_root, str):
        app.wsgi_app = ScriptNameMiddleware(app.wsgi_app, app_root)
    
    # Inicializar extensões
    init_db(app)
    # CSRF Protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Configurar CORS (permitir qualquer origem via proxy)
    CORS(app)
    
    @app.context_processor
    def inject_current_user():
        if 'user_id' in session:
            return {
                'current_user': {
                    'id': session.get('user_id'),
                    'name': session.get('user_name'),
                    'email': session.get('user_email'),
                    'role': session.get('user_role'),
                    'restaurant_id': session.get('restaurant_id')
                }
            }
        return {'current_user': None}

    @app.context_processor
    def inject_valid_roles():
        return {
            'VALID_ROLES': app.config.get('VALID_ROLES')
        }

    @app.context_processor
    def inject_csrf_token():
        # Disponibiliza csrf_token() para templates
        return {'csrf_token': generate_csrf}

    # Registrar middlewares
    init_security(app)
    add_security_headers(app)
    configure_https(app)
    
    # Registrar blueprints da API
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(employees_bp, url_prefix='/api/employees')
    app.register_blueprint(restaurants_bp, url_prefix='/api/restaurants')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    
    # Registrar blueprints de interface web
    app.register_blueprint(auth_web_bp, url_prefix='/auth')
    app.register_blueprint(web_bp)
    
    # Rotas da API de estado
    @app.route('/api')
    def api_index():
        return {
            'name': 'MAC Calendar API',
            'version': '1.0.0',
            'description': 'Sistema de gestão para restaurantes MAC',
            'status': 'running'
        }
    
    @app.route('/api/health')
    def api_health():
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'mac-calendar'
        }
    
    # Servir arquivos gerados (documentos, cartões, etc)
    @app.route('/uploads/generated/<filename>')
    def serve_generated_file(filename):
        # Validar filename para evitar path traversal
        if '..' in filename or filename.startswith('/'):
            return {'error': 'Acesso negado'}, 403
        
        try:
            uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'generated')
            return send_from_directory(uploads_dir, filename, as_attachment=False)
        except FileNotFoundError:
            return {'error': 'Arquivo não encontrado'}, 404
        except Exception:
            return {'error': 'Erro ao servir arquivo'}, 500
    
    # Servir fotos de colaboradores via rota estática
    @app.route('/uploads/employees/<filename>')
    def serve_employee_photo(filename):
        # Validar filename para evitar path traversal
        if '..' in filename or filename.startswith('/'):
            return {'error': 'Acesso negado'}, 403
        
        try:
            uploads_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'employees')
            return send_from_directory(uploads_dir, filename, as_attachment=False)
        except FileNotFoundError:
            return {'error': 'Arquivo não encontrado'}, 404
        except Exception:
            return {'error': 'Erro ao servir arquivo'}, 500
    
    # Registar error handlers centralizados
    register_error_handlers(app)
    
    return app