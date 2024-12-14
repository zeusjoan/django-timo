# Generated by Django 4.2.17 on 2024-12-13 23:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_alter_overtime_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='monthlyreport',
            name='status',
            field=models.CharField(choices=[('draft', 'Wersja robocza'), ('active', 'Aktywne'), ('completed', 'Zakończone'), ('archived', 'Zarchiwizowane')], default='active', max_length=20, verbose_name='Status'),
        ),
    ]
