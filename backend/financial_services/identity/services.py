"""Identity operations shared by API and operator commands."""

import math
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import Throttled

from .models import (
    Membership,
    MembershipAuditEvent,
    RateLimitBucket,
    User,
    Workspace,
    normalize_email,
)


def consume_rate_limit(scope: str, account: str, ip: str) -> None:
    """Serialize counters in PostgreSQL; shared across workers, with bounded windows."""
    now = timezone.now()
    wait = 0
    with transaction.atomic():
        # Stable lock order prevents deadlocks. Denied requests still consume counters.
        for signal, value in (("account", account), ("ip", ip)):
            limit, seconds = settings.AUTH_RATE_LIMITS[scope][signal]
            digest = salted_hmac(
                "identity.rate-limit", f"{scope}:{signal}:{value}", algorithm="sha256"
            ).hexdigest()
            RateLimitBucket.objects.get_or_create(key=digest, defaults={"started_at": now})
            bucket = RateLimitBucket.objects.select_for_update().get(key=digest)
            if now >= bucket.started_at + timedelta(seconds=seconds):
                bucket.started_at, bucket.attempts = now, 0
            if bucket.attempts >= limit:
                wait = max(wait, math.ceil(seconds - (now - bucket.started_at).total_seconds()))
            bucket.attempts = min(bucket.attempts + 1, limit + 1)
            bucket.save(update_fields=["started_at", "attempts"])
    if wait:
        raise Throttled(wait=wait, detail="Too many attempts. Please try again later.")


@transaction.atomic
def provision_owner(
    *, email: str, password: str, display_name: str, timezone_name: str, workspace_name: str
) -> User:
    # Lock a stable PostgreSQL advisory key, including when no users exist yet.
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [610006])
    if User.objects.exists():
        raise ValidationError(
            "Initial owner already exists. Additional-user provisioning is not available."
        )
    user = User(email=normalize_email(email), display_name=display_name, timezone=timezone_name)
    password_validation.validate_password(password, user=user)
    user.set_password(password)
    user.full_clean()
    user.save()
    workspace = Workspace(name=workspace_name, timezone=timezone_name)
    workspace.full_clean()
    workspace.save()
    Membership.objects.create(user=user, workspace=workspace, role=Membership.Role.OWNER)
    MembershipAuditEvent.objects.create(
        workspace=workspace, actor=user, subject_user_id=user.pk, new_role="owner"
    )
    return user


def visible_memberships(user: User):
    if not user.is_active:
        return Membership.objects.none()
    return (
        Membership.objects.filter(user=user, user__is_active=True)
        .select_related("workspace")
        .order_by("workspace__created_at")
    )


def require_workspace(user: User, workspace_id, capability="view") -> Workspace:
    roles = {
        "view": {"owner", "editor", "viewer"},
        "write": {"owner", "editor"},
        "import": {"owner", "editor"},
        "reconcile": {"owner", "editor"},
        "export": {"owner"},
        "manage": {"owner"},
        "delete": {"owner"},
    }
    membership = (
        visible_memberships(user)
        .filter(workspace_id=workspace_id, role__in=roles[capability])
        .first()
    )
    if not membership:
        raise PermissionDenied("Workspace access denied.")
    return membership.workspace


@transaction.atomic
def change_membership(*, actor: User, workspace_id, user_id, role: str | None) -> None:
    Workspace.objects.select_for_update().get(pk=workspace_id)
    require_workspace(actor, workspace_id, "manage")
    membership = Membership.objects.get(workspace_id=workspace_id, user_id=user_id)
    if role is not None and role not in Membership.Role.values:
        raise ValidationError("Invalid role.")
    if membership.role == "owner" and role != "owner":
        if (
            not Membership.objects.filter(workspace_id=workspace_id, role="owner")
            .exclude(pk=membership.pk)
            .exists()
        ):
            raise ValidationError("The final owner cannot be removed or demoted.")
    previous_role = membership.role
    if role is None:
        membership.delete()
    else:
        membership.role = role
        membership.save(update_fields=["role"])
    MembershipAuditEvent.objects.create(
        workspace_id=workspace_id,
        actor=actor,
        subject_user_id=user_id,
        previous_role=previous_role,
        new_role=role or "",
    )


def send_password_recovery(email: str) -> None:
    user = User.objects.filter(email__iexact=normalize_email(email), is_active=True).first()
    if not user or not user.has_usable_password():
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    # Fragment keeps reset credentials out of HTTP request targets and access logs.
    link = f"{settings.APP_URL}/reset-password#uid={uid}&token={token}"
    send_mail(
        "Reset your Financial Services password",
        f"Use this link within one hour to reset your password:\n\n{link}\n\n"
        "If you did not request this, ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


@transaction.atomic
def reset_password(uid: str, token: str, password: str) -> None:
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        # Lock before validating the token; a concurrent successful reset changes its hash.
        user = User.objects.select_for_update().get(pk=user_id, is_active=True)
    except ValueError, UnicodeError, ValidationError, User.DoesNotExist:
        raise ValidationError("This reset link is invalid or has expired.") from None
    if not default_token_generator.check_token(user, token):
        raise ValidationError("This reset link is invalid or has expired.")
    set_password(user, password)


def set_password(user: User, password: str) -> None:
    password_validation.validate_password(password, user=user)
    # Django session auth hashes invalidate every existing session on its next request.
    # Deliberately do not call update_session_auth_hash.
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    password_validation.password_changed(password, user=user)


@transaction.atomic
def change_password(user: User, current_password: str, new_password: str) -> None:
    locked = User.objects.select_for_update().get(pk=user.pk, is_active=True)
    if not locked.check_password(current_password):
        raise ValidationError("The current password is incorrect.")
    set_password(locked, new_password)
