from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularJSONAPIView

from .health import LiveView, ReadyView

urlpatterns = [
    path("api/v1/auth/", include("financial_services.identity.urls")),
    path("api/v1/health/live", LiveView.as_view(), name="health-live"),
    path("api/v1/health/ready", ReadyView.as_view(), name="health-ready"),
]

if settings.API_SCHEMA_ENABLED:
    urlpatterns.append(path("api/v1/schema", SpectacularJSONAPIView.as_view(), name="api-schema"))

handler400 = "config.api.errors.bad_request"
handler404 = "config.api.errors.not_found"
handler500 = "config.api.errors.server_error"
