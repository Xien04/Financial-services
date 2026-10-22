from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from ...services import provision_owner
from ..passwords import read_password


class Command(BaseCommand):
    help = "Create the initial owner and personal workspace. No public registration is available."

    def handle(self, *args, **options):
        email = input("Owner email: ").strip()
        name = input("Display name: ").strip()
        timezone_name = input("Timezone [Asia/Manila]: ").strip() or "Asia/Manila"
        workspace_name = input("Workspace name [Personal]: ").strip() or "Personal"
        password = read_password()
        try:
            provision_owner(
                email=email,
                password=password,
                display_name=name,
                timezone_name=timezone_name,
                workspace_name=workspace_name,
            )
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from None
        except IntegrityError:
            raise CommandError(
                "Owner could not be created; no partial workspace was saved."
            ) from None
        self.stdout.write(self.style.SUCCESS("Initial owner and workspace created."))
