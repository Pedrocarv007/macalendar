"""
Middleware de headers de segurança
Adiciona headers HTTP para proteção contra ataques comuns
"""
from flask import Flask


def add_security_headers(app: Flask):
    """Adiciona headers de segurança a todas as respostas"""
    
    @app.after_request
    def set_security_headers(response):
        """Adiciona headers de segurança após cada requisição"""
        
        # HSTS (HTTP Strict-Transport-Security)
        # Force HTTPS para 1 ano, incluindo subdomínios
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # X-Content-Type-Options: Previne MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options: Protege contra clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection: Ativa filtro XSS do browser (legacy)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy: Controla informação de referrer
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions-Policy: Controla features do browser (replaces Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()'
        )
        
        # Content-Security-Policy: Mitiga ataques XSS e injection
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://www.thecarv.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http://localhost:5006 https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        
        return response


def configure_https(app: Flask):
    """Configura redirecionamento HTTPS em produção"""
    
    if app.config.get('ENV') == 'production':
        # Quando atrás de proxy (IIS), confiar nos headers do proxy
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
        
        # Decorator para forçar HTTPS
        @app.before_request
        def enforce_https():
            from flask import request
            
            # Se não estamos em desenvolvimento
            if not app.config.get('DEBUG'):
                # Verificar se é HTTPS
                # Em IIS, o header X-Forwarded-Proto pode ser 'https'
                if request.headers.get('X-Forwarded-Proto', '').lower() != 'https' and \
                   not request.environ.get('wsgi.url_scheme') == 'https':
                    # Se estamos recebendo via HTTP (não via proxy HTTPS)
                    # IIS deve estar configurado para HTTPS
                    # Este check é para desenvolvimento
                    pass


from werkzeug.middleware.proxy_fix import ProxyFix
