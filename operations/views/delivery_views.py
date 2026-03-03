# operations/views/delivery_views.py
"""
Delivery demand form views.
"""
from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from common.views import success_response, error_response
from core.models import ClientCompany
from ..models import (
    DailyCensus, DeliveryOrder, DeliveryItem
)
from ..serializers import (
    DeliveryOrderSerializer, DeliveryGenerateSerializer
)


class DeliveryGenerateView(APIView):
    """
    POST /api/delivery/generate/
    Generate delivery demand form from census data.

    Request body: {"date": "2026-02-25", "meal_time": "L"}
    """
    def post(self, request):
        serializer = DeliveryGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(error=serializer.errors, message="Validation failed")

        target_date = serializer.validated_data['date']
        meal_time = serializer.validated_data['meal_time']

        companies = ClientCompany.objects.all()
        results = []

        for company in companies:
            census_qs = DailyCensus.objects.filter(
                company=company, date=target_date
            ).select_related('region', 'diet_category')

            if not census_qs.exists():
                continue

            # Get or create delivery order (regenerate if exists)
            order, created = DeliveryOrder.objects.get_or_create(
                company=company,
                target_date=target_date,
                meal_time=meal_time,
            )

            if not created:
                order.items.all().delete()

            for census in census_qs:
                if census.count > 0:
                    DeliveryItem.objects.create(
                        delivery=order,
                        region=census.region,
                        diet_category=census.diet_category,
                        count=census.count,
                    )

            results.append(DeliveryOrderSerializer(order).data)

        return success_response(
            results=results,
            message=f"Generated {len(results)} delivery order(s)",
            http_status=status.HTTP_201_CREATED,
        )


class DeliveryDetailView(APIView):
    """
    GET /api/delivery/{id}/
    View delivery order detail.
    """
    def get(self, request, pk):
        try:
            order = DeliveryOrder.objects.prefetch_related(
                'items__region', 'items__diet_category'
            ).get(id=pk)
        except DeliveryOrder.DoesNotExist:
            return error_response(
                error="Delivery order not found",
                message="Delivery order not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        return success_response(results=DeliveryOrderSerializer(order).data)


class DeliveryByRegionView(APIView):
    """
    GET /api/delivery/{id}/by-region/
    View grouped by region (e.g. East Wing: Diet A x 30, Diet B x 20).
    """
    def get(self, request, pk):
        try:
            order = DeliveryOrder.objects.get(id=pk)
        except DeliveryOrder.DoesNotExist:
            return error_response(
                error="Delivery order not found",
                message="Delivery order not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        items = DeliveryItem.objects.filter(
            delivery=order
        ).select_related('region', 'diet_category')

        grouped = defaultdict(list)
        for item in items:
            grouped[item.region.name].append({
                "diet_category": item.diet_category.name,
                "count": item.count,
            })

        result = [
            {"region": k, "items": v, "total": sum(i["count"] for i in v)}
            for k, v in grouped.items()
        ]

        return success_response(results=result)


class DeliveryExportView(APIView):
    """
    GET /api/delivery/{id}/export/
    Export delivery order as structured printable data.
    """
    def get(self, request, pk):
        try:
            order = DeliveryOrder.objects.select_related('company').get(id=pk)
        except DeliveryOrder.DoesNotExist:
            return error_response(
                error="Delivery order not found",
                message="Delivery order not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        items = DeliveryItem.objects.filter(
            delivery=order
        ).select_related('region', 'diet_category').order_by('region__name')

        grouped = defaultdict(list)
        for item in items:
            grouped[item.region.name].append({
                "diet_category": item.diet_category.name,
                "count": item.count,
            })

        export_data = {
            "title": "Delivery Demand Form",
            "company": order.company.name,
            "date": str(order.target_date),
            "meal_time": order.get_meal_time_display(),
            "regions": [
                {
                    "region": region_name,
                    "diets": diets,
                    "total_count": sum(d["count"] for d in diets),
                }
                for region_name, diets in grouped.items()
            ],
            "grand_total": sum(item.count for item in items),
        }

        return success_response(results=export_data)
