from django.urls import path

from . import views

urlpatterns = [
    path("csrf", views.CsrfView.as_view(), name="auth-csrf"),
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("me", views.MeView.as_view(), name="auth-me"),
    path("activity", views.ActivityView.as_view(), name="auth-activity"),
    path("password/recover", views.RecoveryView.as_view(), name="auth-recover"),
    path("password/reset", views.ResetView.as_view(), name="auth-reset"),
    path("password/change", views.ChangePasswordView.as_view(), name="auth-password-change"),
]
