"""
Gunicorn configuration file for production deployment.
"""
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '4000')}"
backlog = 2048

# Worker processes
# Default to 1 worker for Render's 512MB free tier
# Set WEB_CONCURRENCY env var to override
workers = int(os.getenv('WEB_CONCURRENCY', 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'union-budget-rag'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed in future)
# keyfile = None
# certfile = None

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Union Budget RAG API server")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Union Budget RAG API server is ready. Spawning workers")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass

def worker_abort(worker):
    """Called when a worker times out."""
    worker.log.warning("Worker timeout (pid: %s)", worker.pid)
