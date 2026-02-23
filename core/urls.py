# core/urls.py
from django.urls import path
from .auth_views import LoginView, MeView
from .views import CompanyListView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("companies/", CompanyListView.as_view(), name="companies-list"),
]