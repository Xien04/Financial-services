"""Enforce idle and absolute expiry without letting passive polling keep sessions alive."""

import time

from django.conf import settings
from django.contrib.auth import logout
from django.utils.cache import patch_cache_control


class SessionPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Probes must not read sessions or extend their life.
        if request.path.startswith("/api/v1/health/"):
            return self.get_response(request)
        now = time.time()
        authenticated = request.user.is_authenticated
        if authenticated:
            started = request.session.get("auth_started", 0)
            active = request.session.get("auth_active", 0)
            if (
                now - started >= settings.AUTH_SESSION_ABSOLUTE_SECONDS
                or now - active >= settings.AUTH_SESSION_IDLE_SECONDS
            ):
                logout(request)
        response = self.get_response(request)
        if (
            request.user.is_authenticated
            and request.method not in {"GET", "HEAD", "OPTIONS"}
            and response.status_code < 400
        ):
            request.session["auth_active"] = now
            remaining = min(
                settings.AUTH_SESSION_IDLE_SECONDS,
                settings.AUTH_SESSION_ABSOLUTE_SECONDS - (now - request.session["auth_started"]),
            )
            request.session.set_expiry(max(1, int(remaining)))
        if authenticated or request.path.startswith("/api/v1/auth/"):
            patch_cache_control(response, private=True, no_store=True)
            response["Referrer-Policy"] = "no-referrer"
        return response
