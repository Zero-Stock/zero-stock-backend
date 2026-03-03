# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, MeView, CompanyListView, LogoutView, RawMaterialYieldRateUpdateView
from .views.search_views import (
    MaterialSearchView, DishSearchView, SupplierSearchView, DietSearchView,
)

from .viewsets import (
    DietCategoryViewSet, RawMaterialViewSet,
    DishViewSet, SupplierViewSet, MaterialCategoryViewSet, SupplierMaterialViewSet,
)

router = DefaultRouter()
router.register(r'material-categories', MaterialCategoryViewSet, basename='material-categories')
router.register(r'materials', RawMaterialViewSet, basename='materials')
router.register(r'dishes', DishViewSet, basename='dishes')
router.register(r'diets', DietCategoryViewSet, basename='diets')
router.register(r'suppliers', SupplierViewSet, basename='suppliers')
router.register(r'supplier-materials', SupplierMaterialViewSet, basename='supplier-materials')

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("companies/", CompanyListView.as_view(), name="companies-list"),
    path("raw-materials/<int:raw_material_id>/yield-rate/", RawMaterialYieldRateUpdateView.as_view()),

    # Search endpoints
    path("materials/search/", MaterialSearchView.as_view(), name="materials-search"),
    path("dishes/search/", DishSearchView.as_view(), name="dishes-search"),
    path("suppliers/search/", SupplierSearchView.as_view(), name="suppliers-search"),
    path("diets/search/", DietSearchView.as_view(), name="diets-search"),
] + router.urls