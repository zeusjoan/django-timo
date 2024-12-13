import os
import django
from django.contrib.auth.hashers import make_password

# Ustawienie środowiska Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import modelu User
from django.contrib.auth.models import User

# Ustawienie nowego hasła dla admina
admin_user = User.objects.get(username='admin')
admin_user.password = make_password('admin123')  # Nowe hasło: admin123
admin_user.save()

print("Hasło administratora zostało zresetowane na: admin123")
