from django.urls import include, path

from .health import LiveView, ReadyView

urlpatterns = [
    path("api/v1/auth/", include("financial_services.identity.urls")),
    path("api/v1/health/live", LiveView.as_view(), name="health-live"),
    path("api/v1/health/ready", ReadyView.as_view(), name="health-ready"),
]
