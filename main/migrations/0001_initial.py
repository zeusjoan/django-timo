# Generated by Django 4.2.17 on 2024-12-13 09:29

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=50, verbose_name='Numer zamówienia')),
                ('description', models.TextField(verbose_name='Opis')),
                ('document_date', models.DateField(verbose_name='Data dokumentu')),
                ('delivery_date', models.DateField(blank=True, null=True, verbose_name='Data dostawy')),
                ('contract', models.CharField(blank=True, max_length=100, null=True, verbose_name='Numer umowy')),
                ('supplier_number', models.CharField(blank=True, max_length=100, null=True, verbose_name='Numer dostawcy')),
                ('budget_capex', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Budżet CAPEX (godziny)')),
                ('budget_opex', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Budżet OPEX (godziny)')),
                ('budget_consultation', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Budżet konsultacji (godziny)')),
                ('hourly_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Stawka godzinowa (PLN)')),
                ('attachment', models.FileField(blank=True, null=True, upload_to='orders/', verbose_name='Załącznik')),
                ('status', models.CharField(choices=[('active', 'Aktywne'), ('archived', 'Zarchiwizowane'), ('completed', 'Zakończone')], default='active', max_length=20, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
            ],
            options={
                'verbose_name': 'Zamówienie',
                'verbose_name_plural': 'Zamówienia',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'number')},
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=20, null=True, verbose_name='Telefon')),
                ('address', models.TextField(blank=True, null=True, verbose_name='Adres')),
                ('position', models.CharField(blank=True, max_length=100, null=True, verbose_name='Stanowisko')),
                ('department', models.CharField(blank=True, max_length=100, null=True, verbose_name='Dział')),
                ('employee_id', models.CharField(blank=True, max_length=50, null=True, verbose_name='Numer pracownika')),
                ('hire_date', models.DateField(blank=True, null=True, verbose_name='Data zatrudnienia')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Profil użytkownika',
                'verbose_name_plural': 'Profile użytkowników',
            },
        ),
        migrations.CreateModel(
            name='Overtime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Czas rozpoczęcia')),
                ('end_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Czas zakończenia')),
                ('incident_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='Numer incydentu')),
                ('description', models.TextField(default='', verbose_name='Opis prac')),
                ('status', models.CharField(choices=[('active', 'Aktywne'), ('archived', 'Zarchiwizowane')], default='active', max_length=20, verbose_name='Status')),
                ('type', models.CharField(choices=[('opex', 'OPEX'), ('capex', 'CAPEX')], default='opex', max_length=10, verbose_name='Typ')),
                ('hours', models.DecimalField(decimal_places=1, default=0, editable=False, max_digits=4, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Liczba godzin')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_archived', models.BooleanField(default=False)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='overtimes', to='main.order', verbose_name='Zamówienie')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
            ],
            options={
                'verbose_name': 'Nadgodziny',
                'verbose_name_plural': 'Nadgodziny',
                'ordering': ['-start_time'],
            },
        ),
        migrations.CreateModel(
            name='MonthlyReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(default=django.utils.timezone.now, verbose_name='Miesiąc rozliczeniowy')),
                ('invoice_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='Numer faktury')),
                ('status', models.CharField(choices=[('active', 'Aktywne'), ('archived', 'Zarchiwizowane')], default='active', max_length=20, verbose_name='Status')),
                ('capex_hours', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Przepracowane godziny CAPEX')),
                ('opex_hours', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Przepracowane godziny OPEX')),
                ('consultation_hours', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Przepracowane godziny konsultacji')),
                ('invoice_file', models.FileField(blank=True, null=True, upload_to='monthly_reports/invoices/', verbose_name='Faktura')),
                ('pzo_file', models.FileField(blank=True, null=True, upload_to='monthly_reports/pzo/', verbose_name='PZO')),
                ('merged_file', models.FileField(blank=True, null=True, upload_to='monthly_reports/merged/', verbose_name='Połączony dokument')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_archived', models.BooleanField(default=False)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='monthly_reports', to='main.order', verbose_name='Zamówienie')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
            ],
            options={
                'verbose_name': 'Rozliczenie miesięczne',
                'verbose_name_plural': 'Rozliczenia miesięczne',
                'ordering': ['-month'],
                'unique_together': {('user', 'month', 'order')},
            },
        ),
    ]
