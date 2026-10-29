"""HTTP input and output representations; identity services remain authoritative."""

from rest_framework import serializers

from config.api.views import StrictInputSerializer


class LoginInput(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False, max_length=1024, write_only=True)


class EmailInput(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)


class ResetInput(StrictInputSerializer):
    uid = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=128, write_only=True)
    new_password = serializers.CharField(trim_whitespace=False, max_length=1024, write_only=True)


class ChangePasswordInput(StrictInputSerializer):
    current_password = serializers.CharField(
        trim_whitespace=False, max_length=1024, write_only=True
    )
    new_password = serializers.CharField(trim_whitespace=False, max_length=1024, write_only=True)


class WorkspaceOutput(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.ChoiceField(choices=["owner", "editor", "viewer"])


class UserOutput(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    display_name = serializers.CharField(allow_blank=True)
    timezone = serializers.CharField()
    workspaces = WorkspaceOutput(many=True)


class CsrfOutput(serializers.Serializer):
    csrf_token = serializers.CharField()


class LoginOutput(CsrfOutput):
    user = UserOutput()


class MeOutput(serializers.Serializer):
    user = UserOutput()


class MessageOutput(serializers.Serializer):
    detail = serializers.CharField()
