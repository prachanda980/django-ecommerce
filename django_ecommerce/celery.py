import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_ecommerce.settings')

app = Celery('django_ecommerce')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')



app.conf.beat_schedule = {
    'update-trending-products-hourly': {
        'task': 'apps.notifications.tasks.update_trending_products',
        'schedule': crontab(minute=0), # Every hour
    },
    'cleanup-abandoned-carts': {
        'task': 'apps.notifications.tasks.cleanup_abandoned_carts',
        'schedule': crontab(minute='*/30'), # Every 30 minutes
    },
}