"""
Inicialização da aplicação Flask para MAC Calendar
Sistema de gestão para restaurantes com calendário e gestão de colaboradores
"""
from flask import Flask, session
from flask_cors import CORS
import os

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
    from app.config.settings import Config
    app.config.from_object(Config)
    
    # Adicionar middleware WSGI para proxy reverso
    app_root = app.config.get('APPLICATION_ROOT', '/mac')
    app.wsgi_app = ScriptNameMiddleware(app.wsgi_app, app_root)
    
    # Inicializar extensões
    from app.extensions.database import init_db
    init_db(app)
    
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

    # Registrar middlewares
    from app.middleware.security import init_security
    init_security(app)
    
    # Registrar blueprints da API
    from app.api.auth import auth_bp
    from app.api.calendar import calendar_bp
    from app.api.employees import employees_bp
    from app.api.restaurants import restaurants_bp
    from app.api.documents import documents_bp
    from app.api.profile import profile_bp
    from app.api.dashboard import dashboard_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(employees_bp, url_prefix='/api/employees')
    app.register_blueprint(restaurants_bp, url_prefix='/api/restaurants')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    
    # Registrar blueprints de interface web
    from app.auth.routes import auth_web_bp
    from app.web.routes import web_bp
    
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
        from datetime import datetime
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'mac-calendar'
        }
    
    # Servir arquivos gerados (documentos, cartões, etc)
    @app.route('/uploads/generated/<filename>')
    def serve_generated_file(filename):
        from flask import send_from_directory
        import os
        
        # Validar filename para evitar path traversal
        if '..' in filename or filename.startswith('/'):
            return {'error': 'Acesso negado'}, 403
        
        try:
            uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'generated')
            return send_from_directory(uploads_dir, filename, as_attachment=False)
        except FileNotFoundError:
            return {'error': 'Arquivo não encontrado'}, 404
        except Exception as e:
            return {'error': f'Erro ao servir arquivo: {str(e)}'}, 500
    
    # Manipuladores de erro
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Recurso não encontrado'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Erro interno do servidor'}, 500
    
    return app