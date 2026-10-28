"""Probe responses contain no configuration or database exception details."""

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .api.schema import ALLOW, REQUEST_ID, ErrorSerializer
from .api.views import ContractAPIView


class LiveOutput(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok"])


class ReadyOutput(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ready"])


class UnavailableOutput(serializers.Serializer):
    status = serializers.ChoiceField(choices=["unavailable"])


class LiveView(ContractAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    health_probe = True

    @extend_schema(
        operation_id="health_live",
        auth=[],
        parameters=[REQUEST_ID, ALLOW],
        responses={
            200: LiveOutput,
            405: ErrorSerializer,
            406: ErrorSerializer,
            500: ErrorSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadyView(ContractAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    health_probe = True

    @extend_schema(
        operation_id="health_ready",
        auth=[],
        parameters=[REQUEST_ID, ALLOW],
        description="Readiness retains its small probe body, including dependency failure.",
        responses={
            200: ReadyOutput,
            503: UnavailableOutput,
            405: ErrorSerializer,
            406: ErrorSerializer,
            500: ErrorSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ready"})
