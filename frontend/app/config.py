import logging
import os


class BaseConfig(object):
    DEBUG = False
    TESTING = False
    HOME = os.path.expanduser("~")
    CORS_ORIGINS = '*'
    CORS_HEADERS = 'Content-Type'
    SECRET_KEY = '1d94e52c-1c89-4515-b87a-f48cf3cb7f0b'

    LOGGING_FORMAT = '{"source":"%(name)s","time":"%(asctime)s","severity":"%(levelname)s","message":"%(message)s"}'
    LOGGING_DATEFORMAT = '%Y-%m-%dT%H:%M:%S.0Z'
    LOGGING_LEVEL = logging.DEBUG
    JSON_SORT_KEYS = False


# class DeploymentWithRedisConfig(BaseConfig):
#     """Deployment configuration with Redis."""
#     USE_REDIS_JOBS = True
#     REDIS_HOST = os.environ.get('REDIS_SERVICE_HOST')
#     REDIS_PORT = os.environ.get('REDIS_SERVICE_PORT')
#     REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
#     REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'
