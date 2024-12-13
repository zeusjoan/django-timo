#!/bin/bash

# Ścieżki
BACKUP_NAME="timo_last5_backup_$(date +%Y%m%d_%H%M%S).zip"
BACKUP_DIR="/users/zeusjoan/documents/Projects/timo_backups"

# Tworzenie katalogu backupów
mkdir -p "$BACKUP_DIR"

# Tworzenie backupu
zip -r "$BACKUP_DIR/$BACKUP_NAME" . -x "venv/*" -x "*.pyc" -x "__pycache__/*" -x ".git/*"
if [ $? -eq 0 ]; then
    echo "Backup został utworzony: $BACKUP_DIR/$BACKUP_NAME"

    # Usuwanie starych backupów
    BACKUP_COUNT=$(ls "$BACKUP_DIR" | wc -l)
    if [ "$BACKUP_COUNT" -gt 5 ]; then
        OLDEST_BACKUP=$(ls -t "$BACKUP_DIR" | tail -1)
        rm "$BACKUP_DIR/$OLDEST_BACKUP"
        echo "Usunięto stary backup: $OLDEST_BACKUP"
    fi
else
    echo "Wystąpił błąd podczas tworzenia backupu!" >&2
    exit 1
fi

