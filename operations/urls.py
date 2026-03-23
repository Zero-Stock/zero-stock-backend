# operations/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import WeeklyMenuViewSet
from .views import (
    # Region
    CompanyRegionListCreateView,
    # Census
    DailyCensusListView, DailyCensusBatchView, DailyCensusSummaryView,
    # Procurement
    ProcurementGenerateView, ProcurementListView,
    ProcurementDetailView, ProcurementItemsView, ProcurementSubmitView,
    ProcurementSheetView, ProcurementTemplateView, ProcurementAssignSuppliersView,
    # Receiving
    ReceivingTemplateView, ReceivingCreateView, ReceivingDetailView,
    # Processing
    ProcessingGenerateView, ProcessingDetailView,
    ProcessingByMaterialView, ProcessingByDishView, ProcessingByWorkshopView,
    # Cooking
    CookingTodayView, CookingRecipeView,
    # Delivery
    DeliveryGenerateView, DeliveryDetailView,
    DeliveryByRegionView, DeliveryExportView,
)
from .views.search_views import (
    WeeklyMenuSearchView, CensusSearchView, ProcurementSearchView, ReceivingSearchView, ProcessingSearchView, DeliverySearchView,
)

router = DefaultRouter()
router.register(r'weekly-menus', WeeklyMenuViewSet, basename='weekly-menus')

urlpatterns = [
    # ---- Region ----
    path(
        "companies/<int:company_id>/regions/",
        CompanyRegionListCreateView.as_view(),
        name="company-regions",
    ),

    # ---- Census ----
    path("census/", DailyCensusListView.as_view(), name="census-list"),
    path("census/batch/", DailyCensusBatchView.as_view(), name="census-batch"),
    path("census/summary/", DailyCensusSummaryView.as_view(), name="census-summary"),

    # ---- Procurement ----
    path("procurement/generate/", ProcurementGenerateView.as_view(), name="procurement-generate"),
    path("procurement/", ProcurementListView.as_view(), name="procurement-list"),
    path("procurement/<int:pk>/", ProcurementDetailView.as_view(), name="procurement-detail"),
    path("procurement/<int:pk>/items/", ProcurementItemsView.as_view(), name="procurement-items"),
    path("procurement/<int:pk>/submit/", ProcurementSubmitView.as_view(), name="procurement-submit"),
    path("procurement/<int:pk>/sheet/", ProcurementSheetView.as_view(), name="procurement-sheet"),
    path("procurement/template/", ProcurementTemplateView.as_view(), name="procurement-template"),
    path("procurement/assign-suppliers/", ProcurementAssignSuppliersView.as_view(), name="procurement-assign-suppliers"),

    # ---- Receiving ----
    path("receiving/", ReceivingCreateView.as_view(), name="receiving-create"),
    path("receiving/<int:pk>/", ReceivingDetailView.as_view(), name="receiving-detail"),
    path("receiving/<int:procurement_id>/template/", ReceivingTemplateView.as_view(), name="receiving-template"),

    # ---- Processing ----
    path("processing/generate/", ProcessingGenerateView.as_view(), name="processing-generate"),
    path("processing/<int:pk>/", ProcessingDetailView.as_view(), name="processing-detail"),
    path("processing/<int:pk>/by-material/", ProcessingByMaterialView.as_view(), name="processing-by-material"),
    path("processing/<int:pk>/by-dish/", ProcessingByDishView.as_view(), name="processing-by-dish"),
    path("processing/<int:pk>/by-workshop/", ProcessingByWorkshopView.as_view(), name="processing-by-workshop"),

    # ---- Cooking ----
    path("cooking/today/", CookingTodayView.as_view(), name="cooking-today"),
    path("cooking/recipe/<int:dish_id>/", CookingRecipeView.as_view(), name="cooking-recipe"),

    # ---- Delivery ----
    path("delivery/generate/", DeliveryGenerateView.as_view(), name="delivery-generate"),
    path("delivery/<int:pk>/", DeliveryDetailView.as_view(), name="delivery-detail"),
    path("delivery/<int:pk>/by-region/", DeliveryByRegionView.as_view(), name="delivery-by-region"),
    path("delivery/<int:pk>/export/", DeliveryExportView.as_view(), name="delivery-export"),

    # ---- Search endpoints ----
    path("weekly-menus/search/", WeeklyMenuSearchView.as_view(), name="weekly-menus-search"),
    path("census/search/", CensusSearchView.as_view(), name="census-search"),
    path("procurement/search/", ProcurementSearchView.as_view(), name="procurement-search"),
    path("receiving/search/", ReceivingSearchView.as_view(), name="receiving-search"),
    path("processing/search/", ProcessingSearchView.as_view(), name="processing-search"),
    path("delivery/search/", DeliverySearchView.as_view(), name="delivery-search"),

] + router.urls