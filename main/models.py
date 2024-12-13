from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
from django.conf import settings
from datetime import datetime
import PyPDF2

class Order(models.Model):
    class Status:
        ACTIVE = 'active'
        ARCHIVED = 'archived'
        COMPLETED = 'completed'
        
        CHOICES = [
            (ACTIVE, 'Aktywne'),
            (ARCHIVED, 'Zarchiwizowane'),
            (COMPLETED, 'Zakończone'),
        ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    number = models.CharField(max_length=50, verbose_name="Numer zamówienia")
    description = models.TextField(verbose_name="Opis")
    
    # Dates
    document_date = models.DateField(verbose_name="Data dokumentu")
    delivery_date = models.DateField(null=True, blank=True, verbose_name="Data dostawy")
    
    # Contract details
    contract = models.CharField(max_length=100, null=True, blank=True, verbose_name="Numer umowy")
    supplier_number = models.CharField(max_length=100, null=True, blank=True, verbose_name="Numer dostawcy")
    
    # Budget fields
    budget_capex = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Budżet CAPEX (godziny)")
    budget_opex = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Budżet OPEX (godziny)")
    budget_consultation = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Budżet konsultacji (godziny)")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Stawka godzinowa (PLN)")
    
    # Files
    attachment = models.FileField(upload_to='orders/', null=True, blank=True, verbose_name="Załącznik")
    
    # Status and timestamps
    status = models.CharField(max_length=20, choices=Status.CHOICES, default=Status.ACTIVE, verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data aktualizacji")

    def get_status_display(self):
        return dict(self.Status.CHOICES).get(self.status, self.status)

    class Meta:
        verbose_name = "Zamówienie"
        verbose_name_plural = "Zamówienia"
        ordering = ['-created_at']
        unique_together = ['user', 'number']

    def __str__(self):
        return f"{self.number} - {self.contract}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    address = models.TextField(blank=True, null=True, verbose_name="Adres")
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name="Stanowisko")
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="Dział")
    employee_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Numer pracownika")
    hire_date = models.DateField(blank=True, null=True, verbose_name="Data zatrudnienia")

    class Meta:
        verbose_name = "Profil użytkownika"
        verbose_name_plural = "Profile użytkowników"

    def __str__(self):
        return f"Profil użytkownika {self.user.username}"

class MonthlyReport(models.Model):
    REPORT_STATUS = [
        ('active', 'Aktywne'),
        ('archived', 'Zarchiwizowane'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name="Zamówienie",
        related_name='monthly_reports',
        null=True,
        blank=True
    )
    month = models.DateField(verbose_name="Miesiąc rozliczeniowy", default=timezone.now)
    invoice_number = models.CharField(max_length=50, verbose_name="Numer faktury", null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=REPORT_STATUS,
        default='active',
        verbose_name="Status"
    )
    capex_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Przepracowane godziny CAPEX",
        default=0
    )
    opex_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Przepracowane godziny OPEX",
        default=0
    )
    consultation_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Przepracowane godziny konsultacji",
        default=0
    )
    invoice_file = models.FileField(
        upload_to='monthly_reports/invoices/',
        verbose_name="Faktura",
        null=True,
        blank=True
    )
    pzo_file = models.FileField(
        upload_to='monthly_reports/pzo/',
        verbose_name="PZO",
        null=True,
        blank=True
    )
    merged_file = models.FileField(
        upload_to='monthly_reports/merged/',
        verbose_name="Połączony dokument",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        
        # Próbuj połączyć pliki tylko jeśli oba są dostępne
        if self.invoice_file and self.pzo_file and (is_new or 'invoice_file' in kwargs.get('update_fields', []) or 'pzo_file' in kwargs.get('update_fields', [])):
            try:
                # Upewnij się, że katalog istnieje
                merged_dir = os.path.join(settings.MEDIA_ROOT, 'monthly_reports', 'merged')
                os.makedirs(merged_dir, exist_ok=True)

                # Przygotuj nazwę pliku
                month_str = self.month.strftime('%Y-%m')
                invoice_part = f"_{self.invoice_number}" if self.invoice_number else ""
                merged_filename = f'Rozliczenie_{month_str}{invoice_part}.pdf'
                merged_path = os.path.join(merged_dir, merged_filename)

                # Sprawdź czy pliki istnieją i poczekaj na ich dostępność
                if not os.path.exists(self.invoice_file.path):
                    raise ValidationError("Nie znaleziono pliku faktury")
                if not os.path.exists(self.pzo_file.path):
                    raise ValidationError("Nie znaleziono pliku PZO")

                # Połącz pliki
                merger = PyPDF2.PdfMerger()
                merger.append(self.invoice_file.path)
                merger.append(self.pzo_file.path)
                
                # Zapisz połączony plik
                with open(merged_path, 'wb') as output_file:
                    merger.write(output_file)
                merger.close()
                
                # Zaktualizuj ścieżkę w modelu
                self.merged_file.name = f'monthly_reports/merged/{merged_filename}'
                super().save(update_fields=['merged_file'])
                
            except Exception as e:
                print(f"Szczegóły błędu łączenia plików: {str(e)}")
                # Nie przerywaj zapisu jeśli łączenie się nie powiedzie
                self.merged_file = None
                super().save(update_fields=['merged_file'])

    class Meta:
        verbose_name = "Rozliczenie miesięczne"
        verbose_name_plural = "Rozliczenia miesięczne"
        ordering = ['-month']
        unique_together = ['user', 'month', 'order']

    def __str__(self):
        month_str = self.month.strftime('%Y-%m')
        return f"Rozliczenie za {month_str}"

class Overtime(models.Model):
    OVERTIME_STATUS = [
        ('active', 'Aktywne'),
        ('archived', 'Zarchiwizowane'),
    ]

    OVERTIME_TYPE = [
        ('opex', 'OPEX'),
        ('capex', 'CAPEX')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name="Zamówienie",
        related_name='overtimes',
        null=True,
        blank=True
    )
    start_time = models.DateTimeField(verbose_name="Czas rozpoczęcia", default=timezone.now)
    end_time = models.DateTimeField(verbose_name="Czas zakończenia", default=timezone.now)
    incident_number = models.CharField(max_length=50, verbose_name="Numer incydentu", blank=True, null=True)
    description = models.TextField(verbose_name="Opis prac", default="")
    status = models.CharField(
        max_length=20,
        choices=OVERTIME_STATUS,
        default='active',
        verbose_name="Status"
    )
    type = models.CharField(
        max_length=10,
        choices=OVERTIME_TYPE,
        default='opex',
        verbose_name="Typ"
    )
    hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        verbose_name="Liczba godzin",
        editable=False,
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        time_diff = self.end_time - self.start_time
        hours = time_diff.total_seconds() / 3600
        self.hours = round(hours, 1)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Nadgodziny"
        verbose_name_plural = "Nadgodziny"
        ordering = ['-start_time']

    def __str__(self):
        return f"Nadgodziny {self.start_time.date()} - {self.hours}h ({self.get_type_display()})"