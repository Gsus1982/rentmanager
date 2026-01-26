release: python manage.py migrate && python manage.py create_default_user
web: gunicorn config.wsgi
