"""Strict JSON/serializer boundary and normalization of explicitly returned errors."""

import json

from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView

from .errors import STATUS_CODES, envelope
from .middleware import get_request_id


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Ambiguous JSON")
        value[key] = item
    return value


def reject_constant(value):
    raise ValueError("Invalid JSON constant")


class StrictJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return json.load(
                stream, object_pairs_hook=unique_object, parse_constant=reject_constant
            )
        except ValueError, UnicodeError, RecursionError:
            raise ParseError() from None


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict) and data.keys() - self.fields.keys():
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        serializers.ErrorDetail("Unexpected fields.", code="unknown_field")
                    ]
                }
            )
        return super().to_internal_value(data)


class EmptyInput(StrictInputSerializer):
    pass


class ContractAPIView(APIView):
    parser_classes = [StrictJSONParser]
    input_serializer_class: type[StrictInputSerializer] = EmptyInput
    health_probe = False

    def validated_input(self, request):
        serializer = self.input_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def finalize_response(self, request, response, *args, **kwargs):
        preserve_probe = self.health_probe and response.status_code == 503
        if (
            response.status_code >= 400
            and not preserve_probe
            and not getattr(response, "exception", False)
        ):
            response.data = envelope(
                request, STATUS_CODES.get(response.status_code, "internal_error")
            )
        response = super().finalize_response(request, response, *args, **kwargs)
        response["X-Request-ID"] = get_request_id(request)
        if not self.health_probe:
            response["Cache-Control"] = "private, no-store"
        return response
