#!/bin/bash

# Ścieżki
BACKUP_NAME="timo_backup_$(date +%Y%m%d_%H%M%S).zip"
BACKUP_DIR="/users/zeusjoan/documents/Projects/timo_backups"
PROJECT_DIR="/Users/zeusjoan/Documents/Projects/django-timo"
CHECKSUM_FILE="$BACKUP_DIR/last_checksums.txt"
LOG_FILE="$BACKUP_DIR/backup_log.txt"

# Tworzenie katalogu backupów
mkdir -p "$BACKUP_DIR"

# Tworzenie bieżącej listy plików z sumami kontrolnymi
CURRENT_CHECKSUM_FILE="$BACKUP_DIR/current_checksums.txt"
find "$PROJECT_DIR" -type f ! -path "$PROJECT_DIR/venv/*" ! -path "$PROJECT_DIR/.git/*" ! -path "$PROJECT_DIR/__pycache__/*" -exec md5 {} + > "$CURRENT_CHECKSUM_FILE"

# Tworzenie nagłówka w logu
{
    echo "====================="
    echo "Backup wykonano: $(date)"
} >> "$LOG_FILE"

# Sprawdzanie zmian
if [ -f "$CHECKSUM_FILE" ]; then
    # Porównanie starej i nowej listy
    DIFF=$(diff "$CHECKSUM_FILE" "$CURRENT_CHECKSUM_FILE")

    if [ -z "$DIFF" ]; then
        echo "Brak zmian, backup nie został utworzony." | tee -a "$LOG_FILE"
        rm "$CURRENT_CHECKSUM_FILE"
        exit 0
    else
        echo "Zmiany wykryte:" >> "$LOG_FILE"
        echo "$DIFF" >> "$LOG_FILE"
    fi
else
    echo "Pierwsze uruchomienie backupu, pełna lista plików zostanie zapisana." >> "$LOG_FILE"
fi

# Tworzenie backupu
zip -r "$BACKUP_DIR/$BACKUP_NAME" "$PROJECT_DIR" -x "$PROJECT_DIR/venv/*" -x "$PROJECT_DIR/*.pyc" -x "$PROJECT_DIR/__pycache__/*" -x "$PROJECT_DIR/.git/*" >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    # Aktualizacja listy sum kontrolnych
    mv "$CURRENT_CHECKSUM_FILE" "$CHECKSUM_FILE"
    echo "Backup został utworzony: $BACKUP_DIR/$BACKUP_NAME" | tee -a "$LOG_FILE"
else
    echo "Wystąpił błąd podczas tworzenia backupu!" | tee -a "$LOG_FILE" >&2
    rm "$CURRENT_CHECKSUM_FILE"
    exit 1
fi

# Podsumowanie
echo "=====================" >> "$LOG_FILE"


