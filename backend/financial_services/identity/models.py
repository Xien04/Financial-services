"""Identity persistence. No financial records belong in this module."""

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError, ValueError:
        raise ValidationError("Enter a valid IANA timezone.") from None


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        return normalize_email(email or "")

    def get_by_natural_key(self, username):
        return self.get(email__iexact=normalize_email(username))

    def create_user(self, email, password=None, **extra_fields):
        user = self.model(email=normalize_email(email), **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150)
    timezone = models.CharField(
        max_length=64, default="Asia/Manila", validators=[validate_timezone]
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="identity_user_email_ci_unique")
        ]

    def clean(self):
        super().clean()
        self.email = normalize_email(self.email)


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    timezone = models.CharField(
        max_length=64, default="Asia/Manila", validators=[validate_timezone]
    )
    base_currency = models.CharField(max_length=3, default="PHP", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_currency="PHP"), name="workspace_php_only"
            )
        ]


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="memberships")
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="memberships")
    role = models.CharField(max_length=6, choices=Role.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"], name="membership_workspace_user_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["owner", "editor", "viewer"]),
                name="membership_valid_role",
            ),
        ]


class RateLimitBucket(models.Model):
    """Only keyed digests are persisted, never submitted email addresses or IPs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=64, unique=True)
    started_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveIntegerField(default=0)


class MembershipAuditEvent(models.Model):
    """Minimal durable membership evidence, without names or authentication payloads."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT)
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    subject_user_id = models.UUIDField()
    previous_role = models.CharField(max_length=6, blank=True)
    new_role = models.CharField(max_length=6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
