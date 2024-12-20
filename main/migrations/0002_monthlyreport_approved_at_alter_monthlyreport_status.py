# Generated by Django 4.2.17 on 2024-12-13 12:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='monthlyreport',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='monthlyreport',
            name='status',
            field=models.CharField(choices=[('draft', 'Szkic'), ('approved', 'Zatwierdzone'), ('archived', 'Zarchiwizowane')], default='draft', max_length=20, verbose_name='Status'),
        ),
    ]
