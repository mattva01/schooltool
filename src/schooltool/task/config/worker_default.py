import kombu
import os

# Celery 3
#CELERY_QUEUES = (
#    kombu.Queue('default', kombu.Exchange('default'), routing_key='default'),
#    kombu.Queue('import',  kombu.Exchange('zodb'),   routing_key='zodb.import'),
#    kombu.Queue('report', kombu.Exchange('zodb'),   routing_key='zodb.report'),
#)

# Celery 2:
CELERY_QUEUES = {
    "default": {
        "exchange": "default",
        "binding_key": "default",
        },
    "zodb.report": {
        "exchange": "default",
        "binding_key": "zodb.report",
        },
#    "zodb.import": {
#        "exchange": "default",
#        "binding_key": "zodb.import",
#        },
    }

CELERY_DEFAULT_QUEUE = 'default'
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'default'

CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = str(os.environ.get('REDIS_HOST', "localhost"))
CELERY_REDIS_PORT = int(os.environ.get('REDIS_PORT', 7079))
CELERY_REDIS_DB = 1

_BROKER_REDIS_DB = 0

BROKER_URL = "redis://%s:%s/%d" % (
    CELERY_REDIS_HOST, CELERY_REDIS_PORT, _BROKER_REDIS_DB)

CELERY_ENABLE_UTC = True

CELERY_IMPORTS = ("schooltool.task.tasks", )

#CELERYBEAT_OPTS="--schedule=/home/justas/src/schooltool/flourish_celery/instance/var/celerybeat-schedule"
#CELERYBEAT_SCHEDULE = {}

CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True
CELERY_SERIALIZER = 'json'

SCHOOLTOOL_CONFIG = os.environ.get('SCHOOLTOOL_CONF')
SCHOOLTOOL_RETRY_DB_CONFLICTS = 3
