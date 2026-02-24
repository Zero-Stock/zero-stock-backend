from django.shortcuts import render

# Create your views here.
# operations/region_views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import ClientCompanyRegion
from .serializers import RegionSerializer


class CompanyRegionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/companies/<company_id>/regions/  -> list regions for that company
    POST /api/companies/<company_id>/regions/  -> create region under that company

    Body example:
      { "name": "ICU" }
    """
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]

    def _company_id_from_url(self) -> int:
        return int(self.kwargs["company_id"])

    def _check_company_access(self, company_id: int):
        # 现在是单公司逻辑：只能访问自己 profile.company
        if self.request.user.profile.company_id != company_id:
            raise PermissionDenied("You don't have access to this company.")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["company_id"] = self._company_id_from_url()
        return ctx

    def get_queryset(self):
        company_id = self._company_id_from_url()
        self._check_company_access(company_id)
        return ClientCompanyRegion.objects.filter(company_id=company_id).order_by("name")

    def perform_create(self, serializer):
        company_id = self._company_id_from_url()
        self._check_company_access(company_id)

        try:
            serializer.save(company_id=company_id)
        except IntegrityError:
            # 防并发：两个请求同时创建同名 region 时，DB unique 会报错
            raise ValidationError({"name": "This region already exists in this company."})