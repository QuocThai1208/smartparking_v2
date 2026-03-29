import  os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('smartparking')
# Đọc cấu hình từ settings.py với prefix 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')
# Tự động tìm các file task.py nằm trong các app
app.autodiscover_tasks()