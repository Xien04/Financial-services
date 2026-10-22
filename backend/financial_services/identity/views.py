"""Same-origin JSON authentication endpoints. Anonymous mutations require CSRF too."""

import logging
import time

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import User, normalize_email

logger = logging.getLogger(__name__)


class LoginInput(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False, max_length=1024)


class EmailInput(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class ResetInput(serializers.Serializer):
    uid = serializers.CharField(max_length=128)
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(trim_whitespace=False, max_length=1024)


class ChangePasswordInput(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False, max_length=1024)
    new_password = serializers.CharField(trim_whitespace=False, max_length=1024)


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
class AuthView(APIView):
    parser_classes = [JSONParser]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(AuthView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class LoginView(AuthView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = LoginInput(data=request.data)
        data.is_valid(raise_exception=True)
        email = normalize_email(data.validated_data["email"])
        services.consume_rate_limit("login", email, request.META.get("REMOTE_ADDR", "unknown"))
        user = authenticate(request, email=email, password=data.validated_data["password"])
        if user is None:
            return Response({"detail": "Email or password is incorrect."}, status=400)
        login(request, user)
        # Django preserves a session key when the same user reauthenticates.
        # ADR 0006 requires rotation on every successful login.
        request.session.cycle_key()
        request.session["auth_started"] = time.time()
        request.session["auth_active"] = request.session["auth_started"]
        return Response({"user": user_payload(user), "csrf_token": get_token(request)})


class LogoutView(AuthView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=204)


class MeView(AuthView):
    def get(self, request):
        return Response({"user": user_payload(request.user)})


class ActivityView(AuthView):
    def post(self, request):
        return Response(status=204)


class RecoveryView(AuthView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = EmailInput(data=request.data)
        data.is_valid(raise_exception=True)
        email = normalize_email(data.validated_data["email"])
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

    def post(self, request):
        data = ResetInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        services.consume_rate_limit(
            "reset", values["uid"], request.META.get("REMOTE_ADDR", "unknown")
        )
        try:
            services.reset_password(values["uid"], values["token"], values["new_password"])
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.messages}) from None
        logout(request)
        return Response({"detail": "Password reset. Sign in with your new password."})


class ChangePasswordView(AuthView):
    def post(self, request):
        data = ChangePasswordInput(data=request.data)
        data.is_valid(raise_exception=True)
        services.consume_rate_limit(
            "login", request.user.email, request.META.get("REMOTE_ADDR", "unknown")
        )
        try:
            services.change_password(request.user, **data.validated_data)
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.messages}) from None
        logout(request)
        return Response({"detail": "Password changed. Sign in again."})
