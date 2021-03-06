import os
from pychunkedgraph.app import create_app
import redis
from rq import Connection, Worker, Queue
# This is for monitoring rq with supervisord
# For the flask app use a config class

# env REDIS_SERVICE_HOST and REDIS_SERVICE_PORT are added by Kubernetes
# REDIS_HOST = os.environ.get('REDIS_SERVICE_HOST')
# REDIS_PORT = os.environ.get('REDIS_SERVICE_PORT')
# REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
# if REDIS_PASSWORD is None:
#     REDIS_URL = f'redis://@{REDIS_HOST}:{REDIS_PORT}/0'
# else:
#     REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'

# Queues to listen on
QUEUES = ['mesh-chunks','mesh-chunks-low-priority']

# If you're using Sentry to collect your runtime exceptions, you can use this
# to configure RQ for it in a single step
# The 'sync+' prefix is required for raven: https://github.com/nvie/rq/issues/350#issuecomment-43592410
# SENTRY_DSN = 'sync+http://public:secret@example.com/1'

# If you want custom worker name
# NAME = 'worker-1024'

app = create_app()

redis_connection = redis.from_url(app.config["REDIS_URL"])
with app.app_context():
    with Connection(redis_connection):
        worker = Worker(QUEUES,
                        default_worker_ttl=600)
        worker.work()