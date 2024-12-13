from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_merge_20241213_1409'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='hours_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Całkowita liczba godzin'),
            preserve_default=False,
        ),
    ]
