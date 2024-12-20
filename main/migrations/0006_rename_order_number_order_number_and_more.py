# Generated by Django 4.2.17 on 2024-12-13 16:07

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('main', '0005_add_hours_total'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='order_number',
            new_name='number',
        ),
        migrations.RemoveField(
            model_name='monthlyreport',
            name='approved_at',
        ),
        migrations.AlterField(
            model_name='monthlyreport',
            name='status',
            field=models.CharField(choices=[('active', 'Aktywne'), ('archived', 'Zarchiwizowane')], default='active', max_length=20, verbose_name='Status'),
        ),
        migrations.AlterUniqueTogether(
            name='order',
            unique_together={('user', 'number')},
        ),
        migrations.RemoveField(
            model_name='order',
            name='hours_total',
        ),
        migrations.RemoveField(
            model_name='order',
            name='hours_used',
        ),
    ]
