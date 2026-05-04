import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartlife_project.settings')

app = Celery('smartlife_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Default beat schedule: call planner.reminders every 60 seconds
app.conf.beat_schedule = {
    'send-reminders-every-minute': {
        'task': 'planner.tasks.send_reminders',
        'schedule': 60.0,
    },
}
