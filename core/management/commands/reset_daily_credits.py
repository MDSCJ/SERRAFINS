from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Account


class Command(BaseCommand):
    help = "Reset user credits to the daily allowance when the date changes."

    def handle(self, *args, **options):
        today = timezone.localdate()
        updated_count = 0

        with transaction.atomic():
            for account in Account.objects.all().iterator():
                if account.sync_daily_credits():
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset {updated_count} account(s) for {today.isoformat()}."
            )
        )