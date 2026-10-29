"""Same-origin JSON authentication endpoints. Anonymous mutations require CSRF too."""

import logging
import time

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.api.errors import InvalidCredentials
from config.api.schema import contract
from config.api.views import ContractAPIView, EmptyInput

from . import services
from .models import User, normalize_email
from .serializers import (
    ChangePasswordInput,
    CsrfOutput,
    EmailInput,
    LoginInput,
    LoginOutput,
    MeOutput,
    MessageOutput,
    ResetInput,
)

logger = logging.getLogger(__name__)


def password_input_error(error):
    if error.messages == ["This reset link is invalid or has expired."]:
        return ValidationError({"non_field_errors": [ErrorDetail("", code="invalid_reset")]})
    if error.messages == ["The current password is incorrect."]:
        return ValidationError({"current_password": [ErrorDetail("", code="incorrect_password")]})
    return ValidationError(
        {
            "new_password": [
                ErrorDetail("", code=item.code or "invalid") for item in error.error_list
            ]
        }
    )


def user_payload(user: User):
    return {
        "id": str(user.pk),
        "email": user.email,
        "display_name": user.display_name,
        "timezone": user.timezone,
        "workspaces": [
            {"id": str(m.workspace_id), "name": m.workspace.name, "role": m.role}
            for m in services.visible_memberships(user)
        ],
    }


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(sensitive_post_parameters(), name="dispatch")
class AuthView(ContractAPIView):
    pass


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(AuthView):
    permission_classes = [AllowAny]

    @contract("auth_csrf", output=CsrfOutput, anonymous=True)
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class LoginView(AuthView):
    permission_classes = [AllowAny]
    input_serializer_class = LoginInput

    @contract("auth_login", input=LoginInput, output=LoginOutput, anonymous=True, throttled=True)
    def post(self, request):
        values = self.validated_input(request)
        email = normalize_email(values["email"])
        services.consume_rate_limit("login", email, request.META.get("REMOTE_ADDR", "unknown"))
        user = authenticate(request, email=email, password=values["password"])
        if user is None:
            raise InvalidCredentials()
        login(request, user)
        # Django preserves a session key when the same user reauthenticates.
        # ADR 0006 requires rotation on every successful login.
        request.session.cycle_key()
        request.session["auth_started"] = time.time()
        request.session["auth_active"] = request.session["auth_started"]
        return Response({"user": user_payload(user), "csrf_token": get_token(request)})


class LogoutView(AuthView):
    permission_classes = [AllowAny]

    @contract("auth_logout", input=EmptyInput, status=204, anonymous=True)
    def post(self, request):
        self.validated_input(request)
        logout(request)
        return Response(status=204)


class MeView(AuthView):
    @contract("auth_me", output=MeOutput)
    def get(self, request):
        return Response({"user": user_payload(request.user)})


class ActivityView(AuthView):
    @contract("auth_activity", input=EmptyInput, status=204)
    def post(self, request):
        self.validated_input(request)
        return Response(status=204)


class RecoveryView(AuthView):
    permission_classes = [AllowAny]
    input_serializer_class = EmailInput

    @contract(
        "auth_recover", input=EmailInput, output=MessageOutput, anonymous=True, throttled=True
    )
    def post(self, request):
        values = self.validated_input(request)
        email = normalize_email(values["email"])
        services.consume_rate_limit("recovery", email, request.META.get("REMOTE_ADDR", "unknown"))
        try:
            services.send_password_recovery(email)
        except Exception:
            # Email failures must not reveal account existence or log tokens/server responses.
            logger.error("Password recovery delivery failed; check mail configuration.")
        return Response(
            {"detail": "If an active account matches, a password reset email will be sent."}
        )


class ResetView(AuthView):
    permission_classes = [AllowAny]
    input_serializer_class = ResetInput

    @contract("auth_reset", input=ResetInput, output=MessageOutput, anonymous=True, throttled=True)
    def post(self, request):
        values = self.validated_input(request)
        services.consume_rate_limit(
            "reset", values["uid"], request.META.get("REMOTE_ADDR", "unknown")
        )
        try:
            services.reset_password(values["uid"], values["token"], values["new_password"])
        except DjangoValidationError as error:
            raise password_input_error(error) from None
        logout(request)
        return Response({"detail": "Password reset. Sign in with your new password."})


class ChangePasswordView(AuthView):
    input_serializer_class = ChangePasswordInput

    @contract(
        "auth_password_change", input=ChangePasswordInput, output=MessageOutput, throttled=True
    )
    def post(self, request):
        values = self.validated_input(request)
        services.consume_rate_limit(
            "login", request.user.email, request.META.get("REMOTE_ADDR", "unknown")
        )
        try:
            services.change_password(request.user, **values)
        except DjangoValidationError as error:
            raise password_input_error(error) from None
        logout(request)
        return Response({"detail": "Password changed. Sign in again."})
