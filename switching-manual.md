# Instrukcja przełączania między wersjami aplikacji Django-Timo

## Uruchamianie wersji developerskiej

1. Najpierw zatrzymaj wersję produkcyjną (jeśli działa):
```bash
sudo systemctl stop gunicorn
sudo systemctl stop nginx
```

2. Uruchom wersję dev:
```bash
cd /apps/django_apps/django-timo
./dev_start.sh
```

Aplikacja dev będzie dostępna pod adresem: http://ip-serwera:8001

## Uruchamianie wersji produkcyjnej

1. Jeśli działa wersja dev, zatrzymaj ją:
   - Wciśnij Ctrl+C w terminalu gdzie uruchomiony jest dev_start.sh

2. Uruchom usługi produkcyjne:
```bash
sudo systemctl start gunicorn
sudo systemctl start nginx
```

Aplikacja prod będzie dostępna pod adresem: http://ip-serwera:8080

## Sprawdzanie statusu

1. Sprawdzenie statusu Gunicorn:
```bash
sudo systemctl status gunicorn
```

2. Sprawdzenie statusu Nginx:
```bash
sudo systemctl status nginx
```

## Sprawdzanie logów

1. Logi Gunicorn:
```bash
sudo journalctl -u gunicorn
```

2. Logi Nginx:
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

## Restart usług (w razie problemów)

1. Restart Gunicorn:
```bash
sudo systemctl restart gunicorn
```

2. Restart Nginx:
```bash
sudo systemctl restart nginx
```

## Uwagi
- Nie uruchamiaj jednocześnie wersji dev i prod
- Zawsze sprawdzaj logi w przypadku problemów
- Po zmianach w kodzie w wersji prod należy zrestartować Gunicorn
