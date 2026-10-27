from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import RateLimitBucket


class Command(BaseCommand):
    help = "Remove expired authentication rate-limit buckets; run daily with clearsessions."

    def handle(self, *args, **options):
        RateLimitBucket.objects.filter(started_at__lt=timezone.now() - timedelta(days=1)).delete()
        self.stdout.write("Expired authentication rate-limit buckets removed.")
