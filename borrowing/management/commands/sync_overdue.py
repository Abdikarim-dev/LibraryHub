from django.core.management.base import BaseCommand

from borrowing.services import sync_overdue_statuses


class Command(BaseCommand):
    help = (
        "Promote past-due BORROWED records to OVERDUE. "
        "Run on a schedule (cron) so list endpoints stay read-only."
    )

    def handle(self, *args, **options):
        updated = sync_overdue_statuses()
        self.stdout.write(
            self.style.SUCCESS(f"Marked {updated} borrow(s) as OVERDUE.")
        )
