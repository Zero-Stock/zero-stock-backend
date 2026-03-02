# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, MeView, CompanyListView, LogoutView, RawMaterialYieldRateUpdateView

from .viewsets import (
    DietCategoryViewSet, RawMaterialViewSet,
    DishViewSet, SupplierViewSet, MaterialCategoryViewSet
)

router = DefaultRouter()
router.register(r'material-categories', MaterialCategoryViewSet, basename='material-categories')
router.register(r'materials', RawMaterialViewSet, basename='materials')
router.register(r'dishes', DishViewSet, basename='dishes')
router.register(r'diets', DietCategoryViewSet, basename='diets')
router.register(r'suppliers', SupplierViewSet, basename='suppliers')

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("companies/", CompanyListView.as_view(), name="companies-list"),
    path("raw-materials/<int:raw_material_id>/yield-rate/", RawMaterialYieldRateUpdateView.as_view()),
] + router.urls