from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import User, normalize_email
from ...services import set_password
from ..passwords import read_password


class Command(BaseCommand):
    help = "Operator-only password recovery when email is unavailable. Revokes all user sessions."

    @transaction.atomic
    def handle(self, *args, **options):
        email = normalize_email(input("Account email: "))
        try:
            user = User.objects.select_for_update().get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            raise CommandError("No active account matches.") from None
        try:
            set_password(user, read_password())
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from None
        self.stdout.write(
            self.style.SUCCESS("Password changed. All existing sessions are invalidated.")
        )
