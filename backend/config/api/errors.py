"""Safe, stable envelopes for DRF exceptions and Django boundary failures."""

from django.db import InterfaceError, OperationalError
from django.http import JsonResponse
from django.views import defaults
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from .middleware import get_request_id, is_api

ERRORS = {
    "validation_error": "Check the highlighted fields.",
    "parse_error": "The request must contain valid, unambiguous JSON.",
    "invalid_credentials": "Email or password is incorrect.",
    "authentication_required": "Sign in to continue.",
    "permission_denied": "You do not have permission to perform this action.",
    "csrf_failed": "Your security token is missing or expired. Refresh and try again.",
    "not_found": "The requested resource was not found.",
    "method_not_allowed": "This request method is not supported.",
    "not_acceptable": "The requested response format is not supported.",
    "unsupported_media_type": "Use application/json for this request.",
    "rate_limited": "Too many attempts. Please try again later.",
    "internal_error": "We could not complete the request. Please try again later.",
    "service_unavailable": "The service is temporarily unavailable. Please try again later.",
}
STATUS_CODES = {
    400: "validation_error",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    406: "not_acceptable",
    415: "unsupported_media_type",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}
FIELD_MESSAGES = {
    "required": "This field is required.",
    "blank": "This field may not be blank.",
    "null": "This field may not be null.",
    "invalid": "Enter a valid value.",
    "max_length": "This value is too long.",
    "min_length": "This value is too short.",
    "unknown_field": "The request contains unexpected fields.",
    "password_too_short": "Use a password with at least 12 characters.",  # pragma: allowlist secret
    "password_too_common": "Choose a less common password.",  # pragma: allowlist secret
    # pragma: allowlist nextline secret
    "password_entirely_numeric": "The password cannot be entirely numeric.",
    # pragma: allowlist nextline secret
    "password_too_similar": "Choose a password less similar to your profile.",
    "invalid_reset": "This reset link is invalid or has expired.",
    "incorrect_password": "The current password is incorrect.",  # pragma: allowlist secret
}


class InvalidCredentials(exceptions.APIException):
    status_code = 400
    default_code = "invalid_credentials"
    default_detail = ERRORS["invalid_credentials"]


def envelope(request, code: str, errors=None):
    return {
        "code": code,
        "detail": ERRORS[code],
        "errors": errors or [],
        "request_id": get_request_id(request),
    }


def field_errors(detail, serializer=None):
    """Allow only declared field paths and fixed messages, never submitted names/values."""
    result: list[dict[str, str]] = []

    def visit(value, path, declared):
        if len(result) >= 100:
            return
        if isinstance(value, dict):
            for name, child in value.items():
                if name in {"non_field_errors", "detail"}:
                    visit(child, path, None)
                elif declared is not None and name in declared.fields:
                    escaped = name.replace("~", "~0").replace("/", "~1")
                    visit(child, f"{path}/{escaped}", declared.fields[name])
                else:
                    visit(exceptions.ErrorDetail("", code="unknown_field"), "", None)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                nested = isinstance(child, (dict, list))
                visit(
                    child,
                    f"{path}/{index}" if nested else path,
                    getattr(declared, "child", declared),
                )
        else:
            code = str(getattr(value, "code", "invalid"))
            if code not in FIELD_MESSAGES:
                code = "invalid"
            result.append({"path": path, "code": code, "message": FIELD_MESSAGES[code]})

    visit(detail, "", serializer)
    return result


def exception_handler(exc, context):
    request = context["request"]
    response = drf_exception_handler(exc, context)
    if response is None:
        set_rollback()
        status = 503 if isinstance(exc, (OperationalError, InterfaceError)) else 500
        response = Response(status=status)
    code = STATUS_CODES.get(response.status_code, "internal_error")
    errors = []
    if isinstance(exc, exceptions.ValidationError):
        input_class = getattr(context.get("view"), "input_serializer_class", None)
        errors = field_errors(exc.detail, input_class() if input_class else None)
    elif isinstance(exc, exceptions.ParseError):
        code = "parse_error"
    elif isinstance(exc, InvalidCredentials):
        code = "invalid_credentials"
    elif isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        code = "authentication_required"
    elif isinstance(exc, exceptions.PermissionDenied) and str(exc.detail).startswith(
        "CSRF Failed:"
    ):
        code = "csrf_failed"
    response.data = envelope(request, code, errors)
    response.exception = True
    response["X-Request-ID"] = get_request_id(request)
    return response


def django_error(request, code, status):
    response = JsonResponse(envelope(request, code), status=status)
    response["X-Request-ID"] = get_request_id(request)
    response["Cache-Control"] = "private, no-store"
    return response


def csrf_failure(request, reason=""):
    if is_api(request):
        return django_error(request, "csrf_failed", 403)
    return defaults.permission_denied(request, exception=PermissionError())


def bad_request(request, exception):
    if is_api(request):
        return django_error(request, "parse_error", 400)
    return defaults.bad_request(request, exception)


def not_found(request, exception):
    if is_api(request):
        return django_error(request, "not_found", 404)
    return defaults.page_not_found(request, exception)


def server_error(request):
    if is_api(request):
        return django_error(request, "internal_error", 500)
    return defaults.server_error(request)
