import multiprocessing
import os
from dotenv import load_dotenv

# Load environment variables from .secrets
dotenv_path = os.path.join(os.path.dirname(__file__), ".secrets")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

# Server Socket
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gevent'  # Using gevent for better async performance
worker_connections = 1000
timeout = 300  # Increased timeout
keepalive = 5  # Increased keepalive
max_requests = 1000  # Limit max requests per worker
max_requests_jitter = 50  # Add jitter to help prevent all workers restarting at once

# Process Naming
proc_name = 'caner_production'
default_proc_name = 'caner_production'

# Logging
accesslog = 'access.log'
errorlog = 'error.log'
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# SSL (uncomment and configure if using SSL directly with Gunicorn)
# keyfile = 'path/to/keyfile'
# certfile = 'path/to/certfile'

# Server Mechanics
preload_app = True
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL SETTINGS (if using SSL termination at Gunicorn)
# keyfile = '/etc/ssl/private/ssl-cert-snakeoil.key'
# certfile = '/etc/ssl/certs/ssl-cert-snakeoil.pem'
# ssl_version = 'TLS'
# cert_reqs = 'CERT_NONE'

# Server Hooks
def on_starting(server):
    # Ensure Python's garbage collection is aggressive
    import gc
    gc.enable()
    gc.set_threshold(700, 10, 5)

def on_reload(server):
    import gc
    gc.collect()

def when_ready(server):
    pass

def post_worker_init(worker):
    # Set worker-specific configurations
    import resource
    # Increase worker memory limit (1GB)
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, -1))

def worker_abort(worker):
    import gc
    gc.collect()

def on_exit(server):
    pass