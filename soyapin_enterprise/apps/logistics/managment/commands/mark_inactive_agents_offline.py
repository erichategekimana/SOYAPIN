from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.logistics.models import DeliveryAgent

class Command(BaseCommand):
    help = 'Mark agents offline if no location update for X minutes'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=60)

    def handle(self, *args, **options):
        minutes = options['minutes']
        threshold = timezone.now() - timedelta(minutes=minutes)
        agents = DeliveryAgent.objects.filter(
            status=DeliveryAgent.Status.AVAILABLE,
            last_location_update__lt=threshold
        )
        count = agents.update(status=DeliveryAgent.Status.OFFLINE)
        self.stdout.write(f"Marked {count} agents offline due to inactivity")