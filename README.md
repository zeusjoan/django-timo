# Projekt Django Timo

## Przegląd
Django Timo to aplikacja webowa zaprojektowana do zarządzania zamówieniami, nadgodzinami i raportami miesięcznymi. Oferuje przyjazny interfejs do śledzenia i zarządzania różnymi operacjami biznesowymi.

## Funkcje
- **Zarządzanie Zamówieniami:** Tworzenie, edycja i przeglądanie szczegółowych informacji o zamówieniach.
- **Śledzenie Nadgodzin:** Rejestrowanie i zarządzanie godzinami nadliczbowymi z możliwością przeglądania i edycji.
- **Raporty Miesięczne:** Generowanie i zarządzanie raportami miesięcznymi z pełnymi szczegółami.

## Instalacja
1. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/zeusjoan/django-timo.git
   ```
2. Przejdź do katalogu projektu:
   ```bash
   cd django-timo
   ```
3. Utwórz i aktywuj środowisko wirtualne:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
4. Zainstaluj wymagane zależności:
   ```bash
   pip install -r requirements.txt
   ```

5. **Wykonanie migracji**  
   Aby wykonać migracje, użyj następującego polecenia:
   ```bash
   python manage.py migrate
   ```

6. **Stworzenie superużytkownika**  
   Aby stworzyć superużytkownika, użyj następującego polecenia:
   ```bash
   python manage.py createsuperuser
   ```

7. Uruchom serwer deweloperski:
   ```bash
   python manage.py runserver
   ```

## Wypychanie zmian na zdalne repozytorium
1. Dodaj zmiany do lokalnego repozytorium:
   ```bash
   git add .
   ```
2. Zatwierdź zmiany:
   ```bash
   git commit -m "Opis zmian"
   ```
3. Wypchnij zmiany na zdalne repozytorium:
   ```bash
   git push origin main
   ```

## Użytkowanie
- Uzyskaj dostęp do aplikacji pod adresem `http://localhost:8000`.
- Użyj paska nawigacyjnego, aby przełączać się między zamówieniami, nadgodzinami i raportami.

## Wkład
Wkłady są mile widziane! Proszę o forka repozytorium i przesłanie pull requesta do recenzji.

## Licencja
Ten projekt jest licencjonowany na warunkach licencji MIT.

##PLIK
