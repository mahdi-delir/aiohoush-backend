from django.core.management.base import BaseCommand

from ticket.services.tickets import close_stale_tickets


class Command(BaseCommand):
    help = "تیکت‌هایی که یک هفته از آخرین پیامشان گذشته را می‌بندد."

    def handle(self, *args, **options):
        closed = close_stale_tickets()
        self.stdout.write(self.style.SUCCESS(f"{closed} تیکت بسته شد."))
