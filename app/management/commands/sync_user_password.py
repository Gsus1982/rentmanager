from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Sync user password'

    def handle(self, *args, **options):
        user = User.objects.get(username='Gsus82')
        user.set_password('ab12345678')
        user.save()
        self.stdout.write(self.style.SUCCESS('Password updated'))
