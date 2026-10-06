import os
from pathlib import Path
import environ



BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(
    BASE_DIR / '.env',
    overwrite=False    
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])


# Application definition

INSTALLED_APPS = [
    "aiohoush.admin_apps.AiohoushAdminConfig",
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',

    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',

    'user',
    'course',
    'notification',
    'order',
    'accounting',
    'product',
    'ticket',
    'project',
    'announcement',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aiohoush.urls'

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

WSGI_APPLICATION = 'aiohoush.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("DB_NAME"),
        "USER": env.str("DB_USER"),
        "PASSWORD": env.str("DB_PASS"),
        "HOST": env.str("DB_HOST"),
        "PORT": env.int("DB_PORT"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    },
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'fa-IR'

TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'public/static/'
# در production آدرس کامل عمومی را بدهید (مثلاً
# https://api.aiohoush.com/public/media/) تا آدرس فایل‌ها به هدر Host
# درخواستی که از سرور Next می‌رسد وابسته نباشد.
MEDIA_URL = env.str('MEDIA_URL', default='/public/media/')

MEDIA_ROOT = os.path.join(BASE_DIR, 'public', 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static') 

# فایل‌های محافظت‌شده (مثل سورس کد جلسات). این مسیر نباید توسط
# وب سرور به صورت عمومی سرو شود.
PRIVATE_MEDIA_ROOT = env.str(
    'PRIVATE_MEDIA_ROOT',
    default=os.path.join(BASE_DIR, 'private_media'),
)


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

AUTH_USER_MODEL = "user.User"

AUTHENTICATION_BACKENDS = [
    "user.backends.PermissionOverrideBackend",
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL"),
    },
    "throttling": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("THROTTLE_REDIS_URL"),
        "KEY_PREFIX": "aiohoush_throttle",
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "aiohoush.core.session_jwt_auth.SessionJWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "EXCEPTION_HANDLER": (
        "aiohoush.core.exceptions.custom_exception_handler"
    ),

     "DEFAULT_THROTTLE_RATES": {
        "otp_request_mobile": env(
            "OTP_MOBILE_THROTTLE_RATE"
        ) if not DEBUG else '1000/h',

        "otp_request_ip": env(
            "OTP_IP_THROTTLE_RATE"
        ) if not DEBUG else '1000/h',

         "otp_verify_mobile": env(
            "OTP_VERIFY_MOBILE_THROTTLE_RATE"
        ) if not DEBUG else '1000/h',

        "otp_verify_ip": env(
            "OTP_VERIFY_IP_THROTTLE_RATE"
        ) if not DEBUG else '1000/h',
        },
}

SIMPLE_JWT = {
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": env("JWT_SIGNING_KEY"),
}



OTP_EXPIRATION_SECONDS = env.int("OTP_EXPIRATION_SECONDS")

OTP_REQUEST_LIMIT_24H = env.int(
    "OTP_REQUEST_LIMIT_24H")
OTP_LENGTH=env.int('OTP_LENGTH')
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
PAYAMRESAN_API_URL = env("PAYAMRESAN_API_URL")
PAYAMRESAN_API_KEY = env("PAYAMRESAN_API_KEY")
PAYAMRESAN_SENDER = env("PAYAMRESAN_SENDER")
SMS_CONNECT_TIMEOUT = env.float("SMS_CONNECT_TIMEOUT")
SMS_READ_TIMEOUT = env.float("SMS_READ_TIMEOUT")
CORS_ALLOWED_ORIGINS=env.list('CORS_ALLOWED_ORIGINS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS')

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

VIDEOPOL_API_URL = env.str(
    "VIDEOPOL_API_URL",
)

VIDEOPOL_API_KEY = env.str(
    "VIDEOPOL_API_KEY",
)

VIDEOPOL_TIMEOUT_SECONDS = env.float(
    "VIDEOPOL_TIMEOUT_SECONDS",
    default=15,
)

# کلید مشترک بین BFF (Next.js) و جنگو. فقط درخواستی که این کلید را
# دارد می‌تواند IP کاربر را با هدر X-Aiohoush-Client-IP اعلام کند.
# خالی = به هیچ IP اعلام‌شده‌ای اعتماد نمی‌شود.
BFF_SHARED_SECRET = env.str(
    "BFF_SHARED_SECRET",
    default="",
)

# هدری که proxy جلوی جنگو IP کاربر را در آن می‌گذارد:
# HTTP_X_REAL_IP یا HTTP_X_FORWARDED_FOR. خالی = REMOTE_ADDR.
CLIENT_IP_META_KEY = env.str(
    "CLIENT_IP_META_KEY",
    default="",
)

# فقط برای HTTP_X_FORWARDED_FOR: تعداد proxyهای مورد اعتماد.
TRUSTED_PROXY_COUNT = env.int(
    "TRUSTED_PROXY_COUNT",
    default=1,
)

APP_ORIGIN = env.str(
    "APP_ORIGIN",
)

# آدرسی که ویدوپل بعد از درگاه کاربر را به آن برمی‌گرداند. hostname آن
# باید با AIOHOUSH_ALLOWED_CALLBACK_HOST در ویدوپل یکی باشد.
AI_PAYMENT_CALLBACK_URL = env.str(
    "AI_PAYMENT_CALLBACK_URL",
    default="https://api.aiohoush.com/order/ai-products/payment-return/",
)

# شارژ آنلاین کیف پول (ریال)
WALLET_TOPUP_MIN_RIAL = env.int(
    "WALLET_TOPUP_MIN_RIAL",
    default=100_000,
)

WALLET_TOPUP_MAX_RIAL = env.int(
    "WALLET_TOPUP_MAX_RIAL",
    default=2_000_000_000,
)

WALLET_TOPUP_CALLBACK_URL = env.str(
    "WALLET_TOPUP_CALLBACK_URL",
    default="https://api.aiohoush.com/accounting/wallet/top-up/payment-return/",
)

WALLET_TOPUP_RESULT_URL = env.str(
    "WALLET_TOPUP_RESULT_URL",
    default=f"{APP_ORIGIN.rstrip('/')}/dashboard/wallet",
)

# صفحهٔ فرانت که نتیجهٔ پرداخت را نشان می‌دهد.
AI_PAYMENT_RESULT_URL = env.str(
    "AI_PAYMENT_RESULT_URL",
    default=f"{APP_ORIGIN.rstrip('/')}/dashboard/ai",
)
