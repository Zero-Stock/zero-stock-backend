# operations/urls.py
from django.urls import path
from .views.region_views import CompanyRegionListCreateView
from .views.census_views import DailyCensusListView, DailyCensusBatchView, DailyCensusSummaryView

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
]