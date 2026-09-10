import os
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY','development-only-change-me')
DEBUG=os.environ.get('DJANGO_DEBUG','0')=='1'
ALLOWED_HOSTS=[h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if h.strip()]
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','rest_framework','rest_framework.authtoken','apps.accounting.apps.AccountingConfig']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.middleware.common.CommonMiddleware','django.middleware.cors.CorsMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'; ASGI_APPLICATION='config.asgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.mysql','NAME':os.environ.get('MYSQL_DATABASE','jewellery_erp'),'USER':os.environ.get('MYSQL_USER','root'),'PASSWORD':os.environ.get('MYSQL_PASSWORD',''),'HOST':os.environ.get('MYSQL_HOST','127.0.0.1'),'PORT':os.environ.get('MYSQL_PORT','3306'),'OPTIONS':{'charset':'utf8mb4'}}}
LANGUAGE_CODE='en-us'; TIME_ZONE=os.environ.get('DJANGO_TIME_ZONE','Asia/Kolkata'); USE_I18N=True; USE_TZ=True
STATIC_URL='static/'; DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework.authentication.TokenAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated']}
CORS_ALLOW_ALL_ORIGINS=True
