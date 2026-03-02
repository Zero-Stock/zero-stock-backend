# operations/views/processing_views.py
"""
Processing demand list views.
"""
from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import ClientCompany
from ..models import (
    WeeklyMenu, DailyCensus,
    ProcessingOrder, ProcessingItem
)
from ..serializers import (
    ProcessingOrderSerializer, ProcessingGenerateSerializer
)


class ProcessingGenerateView(APIView):
    """
    POST /api/processing/generate/
    Generate processing demand list from daily menu + headcount.

    Request body: {"date": "2026-02-25"}
    """
    def post(self, request):
        serializer = ProcessingGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target_date = serializer.validated_data['date']
        day_of_week = target_date.isoweekday()  # 1=Monday ... 7=Sunday

        companies = ClientCompany.objects.all()
        results = []

        for company in companies:
            census_qs = DailyCensus.objects.filter(
                company=company, date=target_date
            )
            if not census_qs.exists():
                continue

            # Aggregate headcount per diet category
            diet_counts = defaultdict(int)
            for c in census_qs:
                diet_counts[c.diet_category_id] += c.count

            # Get weekly menus for this day
            menus = WeeklyMenu.objects.filter(
                company=company, day_of_week=day_of_week
            ).prefetch_related('dishes__ingredients__raw_material', 'dishes__ingredients__processing')

            order = ProcessingOrder.objects.create(
                company=company,
                target_date=target_date,
            )

            # Calculate processing demand for each dish
            for menu in menus:
                headcount = diet_counts.get(menu.diet_category_id, 0)
                if headcount == 0:
                    continue

                for dish in menu.dishes.all():
                    for ingredient in dish.ingredients.all():
                        raw = ingredient.raw_material
                        processing = ingredient.processing
                        net_qty = ingredient.net_quantity * headcount
                        gross_qty = net_qty

                        ProcessingItem.objects.create(
                            order=order,
                            raw_material=raw,
                            processed_material=processing,
                            dish=dish,
                            net_quantity=net_qty,
                            gross_quantity=gross_qty,
                        )

            results.append(ProcessingOrderSerializer(order).data)

        return Response(results, status=status.HTTP_201_CREATED)


class ProcessingDetailView(APIView):
    """
    GET /api/processing/{id}/
    View processing order detail.
    """
    def get(self, request, pk):
        try:
            order = ProcessingOrder.objects.prefetch_related(
                'items__raw_material', 'items__processed_material', 'items__dish'
            ).get(id=pk)
        except ProcessingOrder.DoesNotExist:
            return Response({"error": "Processing order not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(ProcessingOrderSerializer(order).data)


class ProcessingByMaterialView(APIView):
    """
    GET /api/processing/{id}/by-material/
    View grouped by raw material (e.g. Potato: sliced 30kg, diced 20kg).
    """
    def get(self, request, pk):
        try:
            order = ProcessingOrder.objects.get(id=pk)
        except ProcessingOrder.DoesNotExist:
            return Response({"error": "Processing order not found"}, status=status.HTTP_404_NOT_FOUND)

        items = ProcessingItem.objects.filter(order=order).select_related(
            'raw_material', 'processed_material', 'dish'
        )

        grouped = defaultdict(lambda: {"methods": defaultdict(lambda: {"quantity": 0, "dishes": []})})

        for item in items:
            mat_name = item.raw_material.name
            method = item.processed_material.method_name if item.processed_material else "无加工"
            grouped[mat_name]["methods"][method]["quantity"] += float(item.gross_quantity)
            grouped[mat_name]["methods"][method]["dishes"].append({
                "dish": item.dish.name,
                "net_qty": float(item.net_quantity),
                "gross_qty": float(item.gross_quantity),
            })

        result = []
        for mat_name, data in grouped.items():
            methods = []
            for method_name, method_data in data["methods"].items():
                methods.append({
                    "method": method_name,
                    "total_quantity": method_data["quantity"],
                    "dishes": method_data["dishes"],
                })
            result.append({"material": mat_name, "methods": methods})

        return Response(result)


class ProcessingByDishView(APIView):
    """
    GET /api/processing/{id}/by-dish/
    View grouped by dish (e.g. Stir-fried potato: potato sliced 20kg...).
    """
    def get(self, request, pk):
        try:
            order = ProcessingOrder.objects.get(id=pk)
        except ProcessingOrder.DoesNotExist:
            return Response({"error": "Processing order not found"}, status=status.HTTP_404_NOT_FOUND)

        items = ProcessingItem.objects.filter(order=order).select_related(
            'raw_material', 'processed_material', 'dish'
        )

        grouped = defaultdict(list)
        for item in items:
            grouped[item.dish.name].append({
                "material": item.raw_material.name,
                "method": item.processed_material.method_name if item.processed_material else None,
                "net_quantity": float(item.net_quantity),
                "gross_quantity": float(item.gross_quantity),
            })

        result = [{"dish": k, "ingredients": v} for k, v in grouped.items()]
        return Response(result)


class ProcessingByWorkshopView(APIView):
    """
    GET /api/processing/{id}/by-workshop/
    View grouped by material category (maps to different workshops).
    """
    def get(self, request, pk):
        try:
            order = ProcessingOrder.objects.get(id=pk)
        except ProcessingOrder.DoesNotExist:
            return Response({"error": "Processing order not found"}, status=status.HTTP_404_NOT_FOUND)

        items = ProcessingItem.objects.filter(order=order).select_related(
            'raw_material', 'processed_material', 'dish'
        )

        grouped = defaultdict(list)
        for item in items:
            category = item.raw_material.category or "Other"
            grouped[category].append({
                "dish": item.dish.name,
                "material": item.raw_material.name,
                "method": item.processed_material.method_name if item.processed_material else None,
                "net_quantity": float(item.net_quantity),
                "gross_quantity": float(item.gross_quantity),
            })

        result = [{"workshop": k, "items": v} for k, v in grouped.items()]
        return Response(result)
