import multiprocessing

# Bind address and port
bind = "0.0.0.0:8000"

# Worker count: (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class — sync is best for CPU-bound Django apps
worker_class = "sync"

# Seconds a worker is allowed to handle a single request
timeout = 30
graceful_timeout = 30

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging to stdout/stderr (captured by Docker)
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Security limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Process naming
proc_name = "taskflow"

# Load application code before forking workers (improves startup time)
preload_app = True
