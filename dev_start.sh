#!/bin/bash
cd /apps/django_apps/django-timo
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings_dev
python manage.py runserver 0.0.0.0:8001
