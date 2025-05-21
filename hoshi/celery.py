import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')

app = Celery('hoshi')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure Celery Beat schedule
app.conf.beat_schedule = {
    'cleanup-expired-stories': {
        'task': 'posts.tasks.cleanup_expired_stories',
        'schedule': 60 * 60,  # Run every hour
    },
    'send-notification-digest': {
        'task': 'notify.tasks.send_notification_digest',
        'schedule': 60 * 60 * 24,  # Run daily
    },
    'cleanup-inactive-sessions': {
        'task': 'accounts.tasks.cleanup_inactive_sessions',
        'schedule': 60 * 60 * 24 * 7,  # Run weekly
    },
    'process-data-download-requests': {
        'task': 'accounts.tasks.process_data_download_requests',
        'schedule': 60 * 30,  # Run every 30 minutes
    },
    'cleanup-expired-data-downloads': {
        'task': 'accounts.tasks.cleanup_expired_data_downloads',
        'schedule': 60 * 60 * 12,  # Run twice daily
    },
    'permanently-delete-accounts': {
        'task': 'accounts.tasks.permanently_delete_accounts',
        'schedule': 60 * 60 * 24,  # Run daily
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 