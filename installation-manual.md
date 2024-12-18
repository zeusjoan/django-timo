# Instrukcja instalacji aplikacji Django-Timo

## Instalacja wersji developerskiej

1. Klonowanie repozytorium:
```bash
cd /apps/django_apps/
git clone [URL_REPO] django-timo
cd django-timo
```

2. Tworzenie i aktywacja środowiska wirtualnego:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Instalacja zależności:
```bash
pip install -r requirements.txt
```

4. Konfiguracja ustawień dev:
```bash
cp config/settings.py config/settings_dev.py
```

5. Edycja settings_dev.py:
```python
DEBUG = True
ALLOWED_HOSTS = ['*']
```

6. Tworzenie skryptu uruchomieniowego (dev_start.sh):
```bash
#!/bin/bash
cd /apps/django_apps/django-timo
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings_dev
python manage.py runserver 0.0.0.0:8001
```

7. Nadanie uprawnień:
```bash
chmod +x dev_start.sh
```

8. Migracja bazy danych:
```bash
python manage.py migrate
```

## Instalacja wersji produkcyjnej

1. Konfiguracja ustawień prod (po instalacji dev):
```bash
cp config/settings.py config/settings_prod.py
```

2. Edycja settings_prod.py:
```python
DEBUG = False
ALLOWED_HOSTS = ['twoja-domena-lub-ip']
```

3. Instalacja Gunicorn:
```bash
pip install gunicorn
```

4. Konfiguracja Gunicorn (/etc/systemd/system/gunicorn.service):
```ini
[Unit]
Description=Gunicorn daemon for Django Timo
After=network.target

[Service]
User=omnires
Group=www-data
WorkingDirectory=/apps/django_apps/django-timo
Environment="DJANGO_SETTINGS_MODULE=config.settings_prod"
RuntimeDirectory=gunicorn
RuntimeDirectoryMode=0775
ExecStart=/apps/django_apps/django-timo/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/gunicorn/gunicorn.sock \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

5. Dodanie użytkownika do grupy www-data:
```bash
sudo usermod -a -G www-data omnires
```

6. Konfiguracja Nginx (/etc/nginx/sites-available/django-timo):
```nginx
server {
    listen 8080;
    server_name twoj-server;

    location /static/ {
        alias /apps/django_apps/django-timo/static/;
    }

    location / {
        proxy_pass http://unix:/run/gunicorn/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. Aktywacja konfiguracji Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/django-timo /etc/nginx/sites-enabled/
sudo nginx -t
```

8. Zebranie plików statycznych:
```bash
python manage.py collectstatic
```

9. Uruchomienie usług:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl enable nginx
```
