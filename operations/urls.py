# operations/urls.py
from django.urls import path
from .views import CompanyRegionListCreateView

urlpatterns = [
     path("companies/<int:company_id>/regions/", CompanyRegionListCreateView.as_view(), name="company-regions"),
]