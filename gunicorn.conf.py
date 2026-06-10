import os

bind = f"0.0.0.0:{os.getenv('PORT', '8001')}"
workers = int(os.getenv('WEB_CONCURRENCY', '3'))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '5'))
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
