import os
import sys
from pathlib import Path
from datetime import timedelta
import dj_database_url
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# Cho phép Domain của Railway và localhost
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['https://*.ngrok-free.app']

# Application definition

FACE_SERVICE_URL = config('FACE_SERVICE_URL', default="http://127.0.0.1:8002/api/v1/extract-face")
PLATE_SERVICE_URL = config('PLATE_SERVICE_URL', default="http://127.0.0.1:8001/api/v1/predict-vehicle")

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_yasg',
    'rest_framework',
    # My Apps
    'apps.users',
    'apps.parking',
    'apps.finance',
]



MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Cấu hình Authentication cho Django Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'PAGE_SIZE': 10,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ROOT_URLCONF = 'core.urls'

# Cho phép tất cả (chỉ dùng cho môi trường Local/Development)
CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "ngrok-skip-browser-warning",  # Nếu dùng ngrok
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# Đường dẫn đến thư mục Media
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# thư mục con 'temp_ai' để chứa ảnh đang chờ AI xử lý
TEMP_AI_ROOT = os.path.join(MEDIA_ROOT, 'temp_ai')

# Tự động tạo thư mục nếu chưa có
if not os.path.exists(TEMP_AI_ROOT):
    os.makedirs(TEMP_AI_ROOT)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# Cấu hình Redis làm Broker cho Celery
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Cấu hình Channel Layer cho WebSockets
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

from decouple import config

if config('DATABASE_URL', default=None):
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default=None),
            'USER': config('DB_USER', default=None),
            'PASSWORD': config('DB_PASS', default=None),
            'HOST': config('DB_HOST', default=None),
            'PORT': config('DB_PORT', default=None),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Ho_Chi_Minh'

USE_I18N = True

USE_TZ = False

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

import os
import sys

sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Cấu hình Cloudinary
from decouple import config

import cloudinary

cloudinary.config(
    cloud_name=config('CLOUDINARY_NAME'),
    api_key=config('CLOUDINARY_API_KEY'),
    api_secret=config('CLOUDINARY_API_SECRET'),
    secure=True
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

AUTH_USER_MODEL = "users.User"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# Cấu hình chi tiết cho Token
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),  # Token sống 2 giờ
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # Refresh sống 7 ngày
    'ROTATE_REFRESH_TOKENS': True,  # Bảo mật: Đổi refresh token mỗi lần dùng
    'BLACKLIST_AFTER_ROTATION': True,  # Vô hiệu hóa token cũ sau khi đổi

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,  # Dùng Secret Key của Django làm chữ ký
    'AUTH_HEADER_TYPES': ('Bearer',),  # Header khi gọi API: Authorization: Bearer <token>
}
