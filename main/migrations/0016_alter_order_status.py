# Generated by Django 4.2.17 on 2024-12-21 17:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('active', 'Aktywne'), ('completed', 'Zakończone'), ('canceled', 'Anulowane')], default='active', max_length=20, verbose_name='Status'),
        ),
    ]