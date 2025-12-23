"""
Error handlers centralizados para a aplicação
Fornece respostas JSON padronizadas para todos os tipos de erro
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException
import os


class APIError(Exception):
    """Classe base para erros da API"""
    def __init__(self, message, status_code=400, error_code=None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or 'API_ERROR'
        super().__init__(self.message)


class ValidationError(APIError):
    """Erro de validação de entrada"""
    def __init__(self, message, field=None):
        self.field = field
        super().__init__(message, 400, 'VALIDATION_ERROR')


class AuthenticationError(APIError):
    """Erro de autenticação"""
    def __init__(self, message='Autenticação falhou'):
        super().__init__(message, 401, 'AUTHENTICATION_ERROR')


class AuthorizationError(APIError):
    """Erro de autorização (sem permissão)"""
    def __init__(self, message='Acesso negado'):
        super().__init__(message, 403, 'AUTHORIZATION_ERROR')


class NotFoundError(APIError):
    """Recurso não encontrado"""
    def __init__(self, resource='Recurso'):
        message = f'{resource} não encontrado'
        super().__init__(message, 404, 'NOT_FOUND')


class ConflictError(APIError):
    """Conflito (ex: recurso já existe)"""
    def __init__(self, message='Recurso já existe'):
        super().__init__(message, 409, 'CONFLICT')


class RateLimitError(APIError):
    """Limite de requisições excedido"""
    def __init__(self, message='Muitas requisições. Tente novamente mais tarde.'):
        super().__init__(message, 429, 'RATE_LIMIT_EXCEEDED')


def register_error_handlers(app):
    """Registar error handlers na aplicação Flask"""
    
    # Erro de validação customizado
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        response = {
            'error': error.error_code,
            'message': error.message,
        }
        if hasattr(error, 'field') and error.field:
            response['field'] = error.field
        return jsonify(response), error.status_code
    
    # Erro de autenticação
    @app.errorhandler(AuthenticationError)
    def handle_auth_error(error):
        return jsonify({
            'error': error.error_code,
            'message': error.message
        }), error.status_code
    
    # Erro de autorização
    @app.errorhandler(AuthorizationError)
    def handle_auth_error(error):
        return jsonify({
            'error': error.error_code,
            'message': error.message
        }), error.status_code
    
    # Erro genérico da API
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return jsonify({
            'error': error.error_code,
            'message': error.message
        }), error.status_code
    
    # 404 - Not Found
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'error': 'NOT_FOUND',
            'message': 'Recurso não encontrado'
        }), 404
    
    # 405 - Method Not Allowed
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'METHOD_NOT_ALLOWED',
            'message': 'Método HTTP não permitido'
        }), 405
    
    # 400 - Bad Request
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'BAD_REQUEST',
            'message': 'Requisição inválida'
        }), 400
    
    # 500 - Internal Server Error
    @app.errorhandler(500)
    def internal_server_error(error):
        # Em produção, não expor detalhes do erro
        debug = app.config.get('DEBUG', False)
        message = 'Erro interno do servidor'
        
        if debug:
            message = str(error)
        
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': message
        }), 500
    
    # 503 - Service Unavailable
    @app.errorhandler(503)
    def service_unavailable(error):
        return jsonify({
            'error': 'SERVICE_UNAVAILABLE',
            'message': 'Serviço temporariamente indisponível'
        }), 503
    
    # Capturar exceções gerais
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handler para exceções não previstas"""
        debug = app.config.get('DEBUG', False)
        
        # Se for erro HTTP, deixar os handlers específicos tratarem
        if isinstance(error, HTTPException):
            return error
        
        # Log do erro (será substituído por logging real depois)
        # app.logger.error(f'Unexpected error: {str(error)}')
        
        message = 'Erro interno do servidor'
        if debug:
            message = str(error)
        
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': message
        }), 500
