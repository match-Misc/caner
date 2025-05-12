# Server Socket
# Using 127.0.0.1:8000 as a default, adjust if needed
bind = "127.0.0.1:8000"

# Worker Processes
workers = 1  # Explicitly set to 1 worker
worker_class = 'gevent'  # Using gevent for async
timeout = 120  # Request timeout in seconds

# Process Naming
proc_name = 'caner_production'

# Logging
accesslog = 'access.log'
errorlog = 'error.log'
loglevel = "info"  # Set log level directly
# Format for logs when behind a proxy (like nginx)
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Server Mechanics
preload_app = False  # Important for background tasks/threads compatibility
daemon = False  # Run in the foreground (standard for container/service management)
