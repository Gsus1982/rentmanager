release: python manage.py migrate && python manage.py sync_user_password
web: gunicorn config.wsgi
