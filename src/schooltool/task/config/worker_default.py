import kombu
import os

try:
    import celery.app.abstract
    assert celery.app.abstract  # silence pyflakes
    CELERY3 = False
except:
    CELERY3 = True

if CELERY3:
    CELERY_QUEUES = (
        kombu.Queue('default', kombu.Exchange('default'), routing_key='default'),
    #    kombu.Queue('import',  kombu.Exchange('zodb'),   routing_key='zodb.import'),
        kombu.Queue('report', kombu.Exchange('zodb'),   routing_key='zodb.report'),
    )
else:
    CELERY_QUEUES = {
        "default": {
            "exchange": "default",
            "binding_key": "default",
            },
        "zodb.report": {
            "exchange": "default",
            "binding_key": "zodb.report",
            },
        "zodb.import": {
            "exchange": "default",
            "binding_key": "zodb.import",
            },
        }

CELERY_DEFAULT_QUEUE = 'default'
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'default'

_REDIS_HOST = str(os.environ.get('REDIS_HOST', "localhost"))
_REDIS_PORT = int(os.environ.get('REDIS_PORT', 7079))
_REDIS_DB = 1

if CELERY3:
    CELERY_RESULT_BACKEND = "redis://%s:%d/%d" % (
        _REDIS_HOST, _REDIS_PORT, _REDIS_DB)
else:
    CELERY_RESULT_BACKEND = "redis"
    CELERY_REDIS_HOST = _REDIS_HOST
    CELERY_REDIS_PORT = _REDIS_PORT
    CELERY_REDIS_DB = _REDIS_DB

_BROKER_REDIS_DB = 0

BROKER_URL = "redis://%s:%d/%d" % (
    _REDIS_HOST, _REDIS_PORT, _BROKER_REDIS_DB)

CELERY_ENABLE_UTC = True

CELERY_IMPORTS = ("schooltool.task.tasks", )

#CELERYBEAT_OPTS="--schedule=/home/justas/src/schooltool/flourish_celery/instance/var/celerybeat-schedule"
#CELERYBEAT_SCHEDULE = {}

CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True
CELERY_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json', 'pickle']

SCHOOLTOOL_CONFIG = os.environ.get('SCHOOLTOOL_CONF')
SCHOOLTOOL_RETRY_DB_CONFLICTS = 3
