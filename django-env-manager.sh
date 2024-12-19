#!/bin/bash

# Kolory do lepszej czytelności
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Konfiguracja
APP_PATH="/apps/django_apps/django-timo"
VENV_PATH="$APP_PATH/venv"
LOG_FILE="$APP_PATH/dev.log"
PID_FILE="$APP_PATH/dev.pid"

# Funkcja sprawdzająca proces na porcie
check_port() {
    local port=$1
    netstat -tulpn 2>/dev/null | grep ":$port"
}

# Funkcja sprawdzająca status środowisk
check_environments_status() {
    echo -e "${YELLOW}Status środowisk:${NC}"
    echo "------------------------"
    
    # Sprawdzanie środowiska deweloperskiego
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo -e "DEV  (port 8001): ${GREEN}URUCHOMIONE${NC} (PID: $(cat $PID_FILE))"
    else
        echo -e "DEV  (port 8001): ${RED}ZATRZYMANE${NC}"
        # Usuń stary plik PID jeśli istnieje
        [ -f "$PID_FILE" ] && rm "$PID_FILE"
    fi
    
    # Sprawdzanie środowiska produkcyjnego
    if systemctl is-active --quiet gunicorn && systemctl is-active --quiet nginx; then
        echo -e "PROD (port 8080): ${GREEN}URUCHOMIONE${NC}"
    else
        GUNICORN_STATUS=$(systemctl is-active gunicorn)
        NGINX_STATUS=$(systemctl is-active nginx)
        if [ "$GUNICORN_STATUS" != "active" ] && [ "$NGINX_STATUS" != "active" ]; then
            echo -e "PROD (port 8080): ${RED}ZATRZYMANE${NC}"
        else
            echo -e "PROD (port 8080): ${YELLOW}CZĘŚCIOWO URUCHOMIONE${NC}"
            echo "  - Gunicorn: $GUNICORN_STATUS"
            echo "  - Nginx: $NGINX_STATUS"
        fi
    fi
}

# Funkcja wyświetlająca sposób użycia
show_usage() {
    echo -e "${YELLOW}Użycie:${NC}"
    echo -e "  $0 [środowisko] [akcja]"
    echo
    echo -e "${YELLOW}Środowiska:${NC}"
    echo "  dev   - środowisko deweloperskie (port 8001)"
    echo "  prod  - środowisko produkcyjne (port 8080)"
    echo "  all   - wszystkie środowiska (tylko dla status)"
    echo
    echo -e "${YELLOW}Akcje:${NC}"
    echo "  start  - uruchom środowisko"
    echo "  stop   - zatrzymaj środowisko"
    echo "  status - sprawdź status środowiska"
    echo "  logs   - pokaż logi"
    echo
    echo -e "${YELLOW}Przykłady:${NC}"
    echo "  $0 dev start   - uruchom środowisko deweloperskie"
    echo "  $0 prod stop   - zatrzymaj środowisko produkcyjne"
    echo "  $0 all status  - sprawdź status wszystkich środowisk"
}

# Funkcja do zarządzania środowiskiem deweloperskim
manage_dev() {
    case $1 in
        start)
            if check_port 8001 > /dev/null; then
                echo -e "${RED}Port 8001 jest już zajęty!${NC}"
                return 1
            fi
            if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
                echo -e "${RED}Serwer deweloperski już działa (PID: $(cat $PID_FILE))${NC}"
                return 1
            fi
            echo -e "${GREEN}Uruchamiam środowisko deweloperskie w tle...${NC}"
            cd $APP_PATH
            source $VENV_PATH/bin/activate
            export DJANGO_SETTINGS_MODULE=config.settings_dev
            nohup python manage.py runserver 0.0.0.0:8001 > "$LOG_FILE" 2>&1 & echo $! > "$PID_FILE"
            echo -e "${GREEN}Serwer uruchomiony (PID: $(cat $PID_FILE))${NC}"
            echo -e "Logi dostępne w pliku: $LOG_FILE"
            echo -e "Użyj '${YELLOW}$0 dev logs${NC}' aby śledzić logi"
            ;;
        stop)
            if [ -f "$PID_FILE" ]; then
                echo -e "${GREEN}Zatrzymuję środowisko deweloperskie...${NC}"
                kill $(cat "$PID_FILE") 2>/dev/null
                rm "$PID_FILE"
                echo -e "${GREEN}Zatrzymano${NC}"
            else
                echo -e "${RED}Serwer deweloperski nie jest uruchomiony${NC}"
            fi
            ;;
        status)
            if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
                echo -e "${GREEN}Środowisko deweloperskie jest uruchomione (PID: $(cat $PID_FILE))${NC}"
            else
                echo -e "${RED}Środowisko deweloperskie nie jest uruchomione${NC}"
                # Usuń stary plik PID jeśli istnieje
                [ -f "$PID_FILE" ] && rm "$PID_FILE"
            fi
            ;;
        logs)
            echo -e "${YELLOW}Śledzenie logów deweloperskich:${NC}"
            tail -f "$LOG_FILE"
            ;;
        *)
            show_usage
            ;;
    esac
}

# Funkcja do zarządzania środowiskiem produkcyjnym
manage_prod() {
    case $1 in
        start)
            echo -e "${GREEN}Uruchamiam środowisko produkcyjne...${NC}"
            sudo systemctl start gunicorn
            sudo systemctl start nginx
            ;;
        stop)
            echo -e "${GREEN}Zatrzymuję środowisko produkcyjne...${NC}"
            sudo systemctl stop gunicorn
            sudo systemctl stop nginx
            ;;
        status)
            echo -e "${YELLOW}Status produkcyjny:${NC}"
            if systemctl is-active --quiet gunicorn && systemctl is-active --quiet nginx; then
                echo -e "${GREEN}Środowisko produkcyjne jest uruchomione (port 8080)${NC}"
            else
                GUNICORN_STATUS=$(systemctl is-active gunicorn)
                NGINX_STATUS=$(systemctl is-active nginx)
                echo -e "${RED}Środowisko produkcyjne nie jest w pełni uruchomione:${NC}"
                echo "  - Gunicorn: $GUNICORN_STATUS"
                echo "  - Nginx: $NGINX_STATUS"
            fi
            ;;
        logs)
            echo -e "${YELLOW}Logi Gunicorn:${NC}"
            sudo journalctl -u gunicorn -n 50
            echo -e "\n${YELLOW}Logi Nginx (error):${NC}"
            sudo tail -n 20 /var/log/nginx/error.log
            ;;
        *)
            show_usage
            ;;
    esac
}

# Główna logika skryptu
case $1 in
    dev)
        manage_dev $2
        ;;
    prod)
        manage_prod $2
        ;;
    all)
        if [ "$2" = "status" ]; then
            check_environments_status
        else
            echo -e "${RED}Opcja 'all' jest dostępna tylko dla komendy 'status'${NC}"
            show_usage
        fi
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
