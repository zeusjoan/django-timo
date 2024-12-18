from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
from django.conf import settings
from datetime import datetime, date
import PyPDF2
from django.db.models import Sum

class Order(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktywne'
        COMPLETED = 'completed', 'Zakończone'
        CANCELED = 'canceled', 'Anulowane'

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    number = models.CharField(max_length=100, verbose_name="Numer zamówienia")
    contract = models.CharField(max_length=100, null=True, blank=True, verbose_name="Numer umowy")
    supplier_number = models.CharField(max_length=100, null=True, blank=True, verbose_name="Numer dostawcy")
    document_date = models.DateField(verbose_name="Data dokumentu", default=timezone.now)
    delivery_date = models.DateField(verbose_name="Data dostawy", null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Stawka godzinowa")
    capex_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Budżet CAPEX (h)")
    opex_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Budżet OPEX (h)")
    consultation_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Budżet konsultacji (h)")
    attachment = models.FileField(upload_to='orders/attachments/', verbose_name="Załącznik", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Zamówienie"
        verbose_name_plural = "Zamówienia"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.number} - {self.contract}"

class OrderValue(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='order_value', verbose_name="Zamówienie")
    capex_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Godziny CAPEX")
    opex_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Godziny OPEX")
    consultation_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Godziny konsultacji")
    total_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Wartość całkowita")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wartość zamówienia"
        verbose_name_plural = "Wartości zamówień"

    def __str__(self):
        return f"Wartość dla zamówienia {self.order.number}"

    def calculate_total_value(self):
        """Oblicza wartość całkowitą na podstawie godzin i stawki."""
        total_hours = float(self.capex_hours or 0) + float(self.opex_hours or 0) + float(self.consultation_hours or 0)
        hourly_rate = float(self.order.hourly_rate or 0)
        self.total_value = total_hours * hourly_rate
        return self.total_value

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

class MonthlyReportSummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Zamówienie", related_name='monthly_summaries')
    month = models.DateField(verbose_name="Miesiąc rozliczeniowy")
    
    # Sumy godzin (z uwzględnieniem nadgodzin)
    total_capex_hours = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Suma godzin CAPEX", default=0, help_text="Suma godzin CAPEX (włącznie z nadgodzinami)")
    total_opex_hours = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Suma godzin OPEX", default=0, help_text="Suma godzin OPEX (włącznie z nadgodzinami)")
    total_consultation_hours = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Suma godzin konsultacji", default=0)
    
    # Wartość w PLN
    total_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Wartość całkowita", default=0, help_text="Wartość = (suma wszystkich godzin) × stawka godzinowa")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Podsumowanie miesięczne"
        verbose_name_plural = "Podsumowania miesięczne"
        ordering = ['-month']
        unique_together = ['user', 'month', 'order']

    def __str__(self):
        month_str = self.month.strftime('%Y-%m')
        return f"Podsumowanie za {month_str} - {self.order.number}"

class MonthlyReport(models.Model):
    REPORT_STATUS = [
        ('draft', 'Wersja robocza'),
        ('active', 'Aktywne'),
        ('completed', 'Zakończone'),
        ('archived', 'Zarchiwizowane'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Zamówienie", related_name='monthly_reports', null=True, blank=True)
    month = models.DateField(verbose_name="Miesiąc rozliczeniowy", default=timezone.now)
    invoice_number = models.CharField(max_length=50, verbose_name="Numer faktury", null=True, blank=True)
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='active', verbose_name="Status")
    capex_hours = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Przepracowane godziny CAPEX", default=0)
    opex_hours = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Przepracowane godziny OPEX", default=0)
    consultation_hours = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Przepracowane godziny konsultacji", default=0)
    invoice_file = models.FileField(upload_to='monthly_reports/invoices/', verbose_name="Faktura", null=True, blank=True)
    pzo_file = models.FileField(upload_to='monthly_reports/pzo/', verbose_name="PZO", null=True, blank=True)
    merged_file = models.FileField(upload_to='monthly_reports/merged/', verbose_name="Połączony dokument", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        old_status = None
        
        if not is_new:
            try:
                old_obj = MonthlyReport.objects.get(pk=self.pk)
                old_status = old_obj.status
            except MonthlyReport.DoesNotExist:
                pass
            
        super().save(*args, **kwargs)
        
        # Jeśli status zmienił się na 'completed', zaktualizuj lub utwórz podsumowanie
        if self.status == 'completed' and old_status != 'completed' and self.order:
            print(f"\nDEBUG - Tworzenie/aktualizacja podsumowania:")
            print(f"- Zamówienie: {self.order.number}")
            print(f"- Miesiąc: {self.month}")
            print(f"- Stawka godzinowa: {self.order.hourly_rate} PLN/h")
            
            # Pobierz wszystkie zakończone rozliczenia dla tego miesiąca i zamówienia
            reports = MonthlyReport.objects.filter(order=self.order, month__month=self.month.month, month__year=self.month.year, status='completed').aggregate(total_capex=Sum('capex_hours'), total_opex=Sum('opex_hours'), total_consultation=Sum('consultation_hours'))
            
            print("\nZakończone rozliczenia w tym miesiącu:")
            print(f"- CAPEX: {reports['total_capex']} h")
            print(f"- OPEX: {reports['total_opex']} h")
            print(f"- Konsultacje: {reports['total_consultation']} h")
            
            # Pobierz zakończone nadgodziny dla tego miesiąca i zamówienia
            overtimes = Overtime.objects.filter(order=self.order, start_time__month=self.month.month, start_time__year=self.month.year, status='completed').aggregate(overtime_capex=Sum('hours', filter=models.Q(type='capex')), overtime_opex=Sum('hours', filter=models.Q(type='opex')))

            print("\nZakończone nadgodziny w tym miesiącu:")
            print(f"- CAPEX: {overtimes['overtime_capex']} h")
            print(f"- OPEX: {overtimes['overtime_opex']} h")

            # Oblicz sumy z uwzględnieniem nadgodzin
            total_capex = float(reports['total_capex'] or 0) + float(overtimes['overtime_capex'] or 0)
            total_opex = float(reports['total_opex'] or 0) + float(overtimes['overtime_opex'] or 0)
            total_consultation = float(reports['total_consultation'] or 0)
            
            # Oblicz wartość całkowitą
            total_hours = total_capex + total_opex + total_consultation
            total_value = total_hours * float(self.order.hourly_rate or 0)

            print("\nPodsumowanie końcowe:")
            print(f"- Suma godzin CAPEX: {total_capex} h")
            print(f"- Suma godzin OPEX: {total_opex} h")
            print(f"- Suma godzin konsultacji: {total_consultation} h")
            print(f"- Całkowita liczba godzin: {total_hours} h")
            print(f"- Wartość całkowita: {total_value} PLN")

            # Zaktualizuj lub utwórz podsumowanie
            summary, created = MonthlyReportSummary.objects.update_or_create(user=self.user, order=self.order, month=self.month.replace(day=1), defaults={'total_capex_hours': total_capex, 'total_opex_hours': total_opex, 'total_consultation_hours': total_consultation, 'total_value': total_value})

        # Próbuj połączyć pliki tylko jeśli oba są dostępne
        if self.invoice_file and self.pzo_file and (is_new or 'invoice_file' in kwargs.get('update_fields', []) or 'pzo_file' in kwargs.get('update_fields', [])):
            try:
                # Upewnij się, że katalog istnieje
                merged_dir = os.path.join(settings.MEDIA_ROOT, 'monthly_reports', 'merged')
                os.makedirs(merged_dir, exist_ok=True)

                # Przygotuj nazwę pliku
                month_str = self.month.strftime('%Y-%m')
                invoice_part = f"_{self.invoice_number.replace('/', '-')}" if self.invoice_number else ""
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
        ('draft', 'Wersja robocza'),
        ('active', 'Aktywne'),
        ('completed', 'Zakończone'),
        ('archived', 'Zarchiwizowane'),
    ]

    OVERTIME_TYPE = [
        ('opex', 'OPEX'),
        ('capex', 'CAPEX')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Użytkownik")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Zamówienie", related_name='overtimes', null=True, blank=True)
    start_time = models.DateTimeField(verbose_name="Czas rozpoczęcia", default=timezone.now)
    end_time = models.DateTimeField(verbose_name="Czas zakończenia", default=timezone.now)
    incident_number = models.CharField(max_length=50, verbose_name="Numer incydentu", blank=True, null=True)
    description = models.TextField(verbose_name="Opis prac", default="")
    status = models.CharField(max_length=20, choices=OVERTIME_STATUS, default='active', verbose_name="Status")
    type = models.CharField(max_length=10, choices=OVERTIME_TYPE, default='opex', verbose_name="Typ")
    hours = models.DecimalField(max_digits=4, decimal_places=1, validators=[MinValueValidator(0)], verbose_name="Liczba godzin", editable=False, default=0)
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