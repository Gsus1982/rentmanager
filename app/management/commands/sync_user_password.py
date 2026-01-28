from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Sync user password'

    def handle(self, *args, **options):
        # Elimina usuario antiguo si existe
        User.objects.filter(username='Gsus82').delete()
        
        # Crea o actualiza el nuevo usuario
        user, created = User.objects.get_or_create(username='Gsus1982')
        user.set_password('ab12345678')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        
        status = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f'User {status}'))
