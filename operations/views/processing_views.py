# operations/views/processing_views.py
"""
Processing demand list views.
"""
from collections import defaultdict

from rest_framework import status
from rest_framework.views import APIView

from common.views import success_response, error_response
from core.models import ClientCompany
from ..models import (
    WeeklyMenu,
    WeeklyMenuDish,
    DailyCensus,
    ProcessingOrder,
    ProcessingItem,
)
from ..serializers import (
    ProcessingGenerateSerializer,
    ProcessingSearchSerializer,
)


def get_processing_time_label(meal_time: str):
    """
    Map meal_time to frontend processing time label.

    Current rule:
    - Breakfast / Lunch -> Morning
    - Dinner -> Afternoon
    """
    if meal_time in ["B", "L"]:
        return "Morning"
    if meal_time == "D":
        return "Afternoon"
    return None


class ProcessingGenerateView(APIView):
    """
    POST /api/processing/generate/
    Generate processing demand list from daily menu + headcount.

    Current assumptions:
    - company_id is hard coded as 1
    - if processing data for the same date already exists, delete and regenerate
    """

    def post(self, request):
        serializer = ProcessingGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                error=serializer.errors,
                message="Validation failed",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        target_date = serializer.validated_data["date"]
        day_of_week = target_date.isoweekday()
        company_id = 1

        try:
            company = ClientCompany.objects.get(id=company_id)
        except ClientCompany.DoesNotExist:
            return error_response(
                error="Company not found",
                message="Company not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        census_qs = DailyCensus.objects.filter(
            company=company,
            date=target_date,
        )
        if not census_qs.exists():
            return error_response(
                error="No daily census found for target date",
                message="No daily census found for target date",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        menus = WeeklyMenu.objects.filter(
            company=company,
            day_of_week=day_of_week,
        )

        if not menus.exists():
            return error_response(
                error="No weekly menu found for target date",
                message="No weekly menu found for target date",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        # Delete existing processing data for this date
        # ProcessingItem will be deleted by cascade
        ProcessingOrder.objects.filter(
            company=company,
            target_date=target_date,
        ).delete()

        # Aggregate headcount per diet category
        diet_counts = defaultdict(int)
        for census in census_qs:
            diet_counts[census.diet_category_id] += census.count

        order = ProcessingOrder.objects.create(
            company=company,
            target_date=target_date,
        )

        created_items_count = 0
        touched_material_ids = set()

        for menu in menus:
            headcount = diet_counts.get(menu.diet_category_id, 0)
            if headcount == 0:
                continue

            menu_dishes = WeeklyMenuDish.objects.filter(menu=menu).select_related(
                "dish"
            ).prefetch_related(
                "dish__ingredients__raw_material",
                "dish__ingredients__processing",
                "dish__ingredients__raw_material__category",
            )

            for menu_dish in menu_dishes:
                dish = menu_dish.dish
                dish_qty = menu_dish.quantity

                for ingredient in dish.ingredients.all():
                    raw = ingredient.raw_material
                    processing = ingredient.processing
                    net_qty = ingredient.net_quantity * headcount * dish_qty
                    gross_qty = net_qty

                    ProcessingItem.objects.create(
                        order=order,
                        raw_material=raw,
                        processed_material=processing,
                        dish=dish,
                        meal_time=menu.meal_time,
                        net_quantity=net_qty,
                        gross_quantity=gross_qty,
                    )

                    created_items_count += 1
                    touched_material_ids.add(raw.id)

        return success_response(
            results={
                "id": order.id,
                "company_id": company.id,
                "target_date": order.target_date,
                "status": order.status,
                "items_count": created_items_count,
                "material_count": len(touched_material_ids),
            },
            message="Processing order generated successfully",
            http_status=status.HTTP_201_CREATED,
        )


class ProcessingSearchView(APIView):
    """
    POST /api/processing/search/
    Search processing data by date, with optional material_id.

    Request body:
    {
        "date": "2026-03-25",
        "material_id": 3
    }

    Response:
    A flat aggregated table-friendly list.
    """

    def post(self, request):
        serializer = ProcessingSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                error=serializer.errors,
                message="Validation failed",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        target_date = serializer.validated_data["date"]
        material_id = serializer.validated_data.get("material_id")
        company_id = 1

        order = ProcessingOrder.objects.filter(
            company_id=company_id,
            target_date=target_date,
        ).order_by("-created_at").first()

        if not order:
            return error_response(
                error="Processing data not found",
                message="Processing data not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        items = ProcessingItem.objects.filter(order=order).select_related(
            "raw_material",
            "processed_material",
            "dish",
            "raw_material__category",
        )

        if material_id is not None:
            items = items.filter(raw_material_id=material_id)

        # Aggregate rows for frontend table:
        # one row per material + processing method + processing time
        grouped = defaultdict(
            lambda: {
                "material_id": None,
                "material_name": None,
                "category": None,
                "processing_method": None,
                "processing_requirement": 0.0,
                "processing_time": None,
            }
        )

        for item in items:
            material_id_val = item.raw_material.id
            material_name = item.raw_material.name
            category_name = (
                item.raw_material.category.name
                if item.raw_material.category
                else None
            )
            method_name = (
                item.processed_material.method_name
                if item.processed_material
                else "无加工"
            )
            processing_time = get_processing_time_label(item.meal_time)

            key = (material_id_val, method_name, processing_time)

            grouped[key]["material_id"] = material_id_val
            grouped[key]["material_name"] = material_name
            grouped[key]["category"] = category_name
            grouped[key]["processing_method"] = method_name
            grouped[key]["processing_time"] = processing_time
            grouped[key]["processing_requirement"] += float(item.gross_quantity)

        results = list(grouped.values())

        return success_response(
            results=results,
            message="Processing data retrieved successfully",
            http_status=status.HTTP_200_OK,
        )