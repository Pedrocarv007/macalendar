"""
Inicialização da aplicação Flask para MAC Calendar
Sistema de gestão para restaurantes com calendário e gestão de colaboradores
"""
from flask import Flask, session
from flask_cors import CORS

def create_app(config_name=None):
    """Factory para criar aplicação Flask"""
    
    # Criar instância Flask
    app = Flask(__name__)
    
    # Carregar configurações
    from app.config.settings import Config
    app.config.from_object(Config)
    
    # Inicializar extensões
    from app.extensions.database import init_db
    init_db(app)
    
    # Configurar CORS
    CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])
    
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
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(employees_bp, url_prefix='/api/employees')
    app.register_blueprint(restaurants_bp, url_prefix='/api/restaurants')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    
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
    
    # Manipuladores de erro
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Recurso não encontrado'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Erro interno do servidor'}, 500
    
    return app