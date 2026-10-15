from django.core.management.base import BaseCommand

from accounts.models import Role

ROLES = {
    "Owner": ["analytics", "branches", "menu", "orders", "kitchen", "billing", "inventory", "staff"],
    "Manager": ["analytics", "menu", "orders", "inventory", "staff"],
    "Cashier": ["billing"],
    "Waiter": ["orders"],
    "Kitchen": ["kitchen"],
}


class Command(BaseCommand):
    help = "Create the 5 default roles"

    def handle(self, *args, **options):
        for name, perms in ROLES.items():
            Role.objects.update_or_create(name=name, defaults={"permissions_json": perms})
            self.stdout.write(self.style.SUCCESS(f"Role ready: {name}"))