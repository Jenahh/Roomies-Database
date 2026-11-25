"""Small WSGI service for the public classroom demonstration."""
import os

port = int(os.environ.get('PORT', '8080'))
if not 1 <= port <= 65535:
    raise ValueError('PORT must be between 1 and 65535.')
bind = f'0.0.0.0:{port}'
workers = 1
worker_class = 'gthread'
threads = 4
# Initialize/migrate once before starting the worker.
preload_app = True
timeout = 30
graceful_timeout = 30
errorlog = '-'
accesslog = None
