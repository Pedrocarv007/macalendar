"""
Rate Limiting e Cache para OpenAI
Limita requisições por utilizador e implementa cache de respostas
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import g, jsonify
import hashlib
import json


class RateLimiter:
    """Rate limiter em memória com limite por utilizador"""
    
    def __init__(self):
        # Estrutura: {user_id: [(timestamp, endpoint), ...]}
        self.requests = {}
        self.limits = {
            '/api/ai/posts': {
                'requests': 100,  # 100 requisições
                'window': 3600    # por hora
            },
            '/api/calendar/generate_riddles': {
                'requests': 10,
                'window': 86400   # por dia
            },
            '/api/documents/generate': {
                'requests': 50,
                'window': 3600
            }
        }
    
    def is_rate_limited(self, user_id, endpoint):
        """Verifica se utilizador excedeu limite"""
        if endpoint not in self.limits:
            return False
        
        limit_config = self.limits[endpoint]
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=limit_config['window'])
        
        # Limpar requisições antigas
        if user_id in self.requests:
            self.requests[user_id] = [
                (ts, ep) for ts, ep in self.requests[user_id]
                if ts > window_start
            ]
        
        # Contar requisições no intervalo
        if user_id in self.requests:
            count = sum(1 for ts, ep in self.requests[user_id] if ep == endpoint)
        else:
            count = 0
        
        # Verificar limite
        if count >= limit_config['requests']:
            return True
        
        # Registar nova requisição
        if user_id not in self.requests:
            self.requests[user_id] = []
        self.requests[user_id].append((now, endpoint))
        
        return False
    
    def get_remaining(self, user_id, endpoint):
        """Retorna requisições restantes"""
        if endpoint not in self.limits:
            return None
        
        limit_config = self.limits[endpoint]
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=limit_config['window'])
        
        if user_id in self.requests:
            count = sum(1 for ts, ep in self.requests[user_id]
                       if ep == endpoint and ts > window_start)
        else:
            count = 0
        
        return max(0, limit_config['requests'] - count)


class ResponseCache:
    """Cache de respostas OpenAI em memória"""
    
    def __init__(self, ttl_seconds=3600):
        # Estrutura: {cache_key: (response, timestamp)}
        self.cache = {}
        self.ttl = ttl_seconds
    
    def _generate_key(self, endpoint, **kwargs):
        """Gera chave de cache baseada no endpoint e parâmetros"""
        # Ordenar kwargs para garantir mesma chave
        sorted_kwargs = json.dumps(kwargs, sort_keys=True)
        key_string = f"{endpoint}:{sorted_kwargs}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, endpoint, **kwargs):
        """Retorna resposta em cache se disponível e válida"""
        key = self._generate_key(endpoint, **kwargs)
        
        if key not in self.cache:
            return None
        
        response, timestamp = self.cache[key]
        
        # Verificar se expirou
        if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[key]
            return None
        
        return response
    
    def set(self, endpoint, response, **kwargs):
        """Armazena resposta em cache"""
        key = self._generate_key(endpoint, **kwargs)
        self.cache[key] = (response, datetime.utcnow())
    
    def clear(self):
        """Limpa todo o cache"""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove entradas expiradas"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp > timedelta(seconds=self.ttl)
        ]
        for key in expired_keys:
            del self.cache[key]


# Instâncias globais
rate_limiter = RateLimiter()
response_cache = ResponseCache(ttl_seconds=3600)  # Cache por 1 hora


def check_rate_limit(f):
    """Decorator para verificar rate limiting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = g.get('current_user_id')
        if not user_id:
            return jsonify({'error': 'Autenticação necessária'}), 401
        
        endpoint = f.endpoint or f.__name__
        
        if rate_limiter.is_rate_limited(user_id, endpoint):
            remaining = rate_limiter.get_remaining(user_id, endpoint)
            return jsonify({
                'error': 'RATE_LIMIT_EXCEEDED',
                'message': 'Muitas requisições. Tente novamente mais tarde.',
                'retry_after': 3600,
                'remaining': remaining
            }), 429
        
        # Adicionar informação de rate limit aos headers de resposta (depois)
        return f(*args, **kwargs)
    
    return decorated_function


def with_cache(f):
    """Decorator para cachear respostas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        
        # Criar cache key a partir dos parâmetros da requisição
        cache_params = {}
        if request.method == 'POST':
            cache_params = request.get_json() or {}
        else:
            cache_params = request.args.to_dict()
        
        # Tentar obter do cache
        endpoint = f.endpoint or f.__name__
        cached = response_cache.get(endpoint, **cache_params)
        
        if cached is not None:
            return cached
        
        # Executar função
        result = f(*args, **kwargs)
        
        # Armazenar em cache (só respostas 200)
        if isinstance(result, tuple) and len(result) >= 2:
            response_data, status_code = result[0], result[1]
            if status_code == 200:
                response_cache.set(endpoint, result, **cache_params)
        
        return result
    
    return decorated_function
