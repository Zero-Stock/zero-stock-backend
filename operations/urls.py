# operations/urls.py
from django.urls import path
from .views.region_views import CompanyRegionListCreateView
from .views.census_views import DailyCensusListView, DailyCensusBatchView, DailyCensusSummaryView
from .views.procurement_views import (
    ProcurementListView,
    ProcurementDetailView,
    ProcurementItemsView,
    ProcurementConfirmView,
    ProcurementGenerateView  
)

urlpatterns = [
    # region
    path(
        "companies/<int:company_id>/regions/",
        CompanyRegionListCreateView.as_view(),
        name="company-regions",
    ),

    # census
    path(
        "census/",
        DailyCensusListView.as_view(),
        name="census-list",
    ),
    path(
        "census/batch/",
        DailyCensusBatchView.as_view(),
        name="census-batch",
    ),
    path(
        "census/summary/",
        DailyCensusSummaryView.as_view(),
        name="census-summary",
    ),   
    # procurement
    path(
        "procurement/generate/",
        ProcurementGenerateView.as_view(),
        name="procurement-generate",
    ),
    path(
        "procurement/",
        ProcurementListView.as_view(),
        name="procurement-list",
    ),
    path(
        "procurement/<int:pk>/",
        ProcurementDetailView.as_view(),
        name="procurement-detail",
    ),
    path(
        "procurement/<int:pk>/items/",
        ProcurementItemsView.as_view(),
        name="procurement-items",
    ),
    path(
        "procurement/<int:pk>/confirm/",
        ProcurementConfirmView.as_view(),
        name="procurement-confirm",
    ),
]