# core/urls.py
from django.urls import path
from .views import LoginView, MeView
from .views import CompanyListView
from .views import DietCategoryListView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("companies/", CompanyListView.as_view(), name="companies-list"),
    path("diet-categories/", DietCategoryListView.as_view(), name="diet-categories"),
]