"""Executable view annotations and response serializers for the public API contract."""

from django.conf import settings
from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers


class FieldErrorSerializer(serializers.Serializer):
    path = serializers.CharField(allow_blank=True)
    code = serializers.CharField()
    message = serializers.CharField()


class ErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    request_id = serializers.UUIDField()

    def get_fields(self):
        fields = super().get_fields()
        # `errors` is also a Serializer property; declare the wire field explicitly.
        fields["errors"] = serializers.ListSerializer(child=FieldErrorSerializer(), max_length=100)
        return fields


class StrictInputSchema(OpenApiSerializerExtension):
    target_class = "config.api.views.StrictInputSerializer"
    match_subclasses = True

    def map_serializer(self, auto_schema, direction):
        schema = auto_schema._map_serializer(self.target, direction, bypass_extensions=True)
        if direction == "request":
            schema["additionalProperties"] = False
        return schema


REQUEST_ID = OpenApiParameter(
    "X-Request-ID",
    OpenApiTypes.UUID,
    OpenApiParameter.HEADER,
    required=True,
    response=True,
    description="Fresh server-generated UUIDv4. Incoming caller IDs are replaced.",
)
CSRF = OpenApiParameter(
    "X-CSRFToken",
    OpenApiTypes.STR,
    OpenApiParameter.HEADER,
    required=True,
    description="Django CSRF token from GET /api/v1/auth/csrf; required even before login. "
    "Send same-origin cookies and refresh the token after login.",
)
ALLOW = OpenApiParameter(
    "Allow",
    OpenApiTypes.STR,
    OpenApiParameter.HEADER,
    response=[405],
    required=True,
)


def contract(
    operation_id, *, output=None, input=None, status=200, anonymous=False, throttled=False
):
    responses = {
        status: output,
        403: ErrorSerializer,
        405: ErrorSerializer,
        406: ErrorSerializer,
        500: ErrorSerializer,
        503: ErrorSerializer,
    }
    parameters = [REQUEST_ID, ALLOW]
    if input is not None:
        responses.update({400: ErrorSerializer, 415: ErrorSerializer})
        parameters.extend(
            [
                CSRF,
                OpenApiParameter(
                    settings.CSRF_COOKIE_NAME,
                    OpenApiTypes.STR,
                    OpenApiParameter.COOKIE,
                    required=True,
                    description="Same-origin CSRF cookie set by the bootstrap endpoint.",
                ),
            ]
        )
    if throttled:
        responses[429] = ErrorSerializer
        parameters.append(
            OpenApiParameter(
                "Retry-After",
                OpenApiTypes.INT,
                OpenApiParameter.HEADER,
                response=[429],
                required=True,
                description="Seconds until another attempt is allowed.",
            )
        )
    return extend_schema(
        operation_id=operation_id,
        request=input,
        responses=responses,
        parameters=parameters,
        description="Same-origin JSON API. Successful response shapes are stable. "
        "Errors use code/detail/errors/request_id. Responses are private and not cached. "
        "No idempotency key or pagination applies to this authentication operation.",
        auth=[] if anonymous else None,
    )
