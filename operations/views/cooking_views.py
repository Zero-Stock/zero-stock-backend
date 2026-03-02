# operations/views/cooking_views.py
"""
Cooking / recipe viewing views (read-only, calculation-based).
"""
from datetime import date

from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import ClientCompany, Dish
from ..models import WeeklyMenu, WeeklyMenuDish, DailyCensus


class CookingTodayView(APIView):
    """
    GET /api/cooking/today/
    Get today's cooking tasks (auto-matched from weekly menu).

    Supports filters:
    ?meal_time=L  - filter by lunch only
    ?company=1    - filter by company
    """
    def get(self, request):
        today = date.today()
        day_of_week = today.isoweekday()

        filters = {"day_of_week": day_of_week}

        meal_time = request.query_params.get("meal_time")
        if meal_time:
            filters["meal_time"] = meal_time

        company_id = request.query_params.get("company")
        if company_id:
            filters["company_id"] = company_id

        menus = WeeklyMenu.objects.filter(**filters).select_related(
            'company', 'diet_category'
        ).prefetch_related(
            'dishes__ingredients__raw_material',
            'dishes__ingredients__processing'
        )

        result = []
        for menu in menus:
            # Get total headcount for this diet category today
            headcount = DailyCensus.objects.filter(
                company=menu.company,
                date=today,
                diet_category=menu.diet_category,
            ).aggregate(total=Sum('count'))
            total_count = headcount['total'] or 0

            dishes_data = []
            menu_dishes = WeeklyMenuDish.objects.filter(menu=menu).select_related(
                'dish'
            ).prefetch_related(
                'dish__ingredients__raw_material',
                'dish__ingredients__processing'
            )
            for md in menu_dishes:
                dish = md.dish
                dish_qty = md.quantity
                ingredients = []
                for ing in dish.ingredients.all():
                    raw = ing.raw_material
                    processing = ing.processing
                    net_per_serving = ing.net_quantity
                    net_total = net_per_serving * total_count * dish_qty if total_count else 0
                    yield_rate = processing.yield_rate if processing else 1
                    gross_total = (net_total / yield_rate) if yield_rate else net_total

                    ingredients.append({
                        "material": raw.name,
                        "method": processing.method_name if processing else None,
                        "net_per_serving": float(net_per_serving),
                        "net_total": float(net_total),
                        "gross_total": float(gross_total),
                    })

                dishes_data.append({
                    "dish_id": dish.id,
                    "dish_name": dish.name,
                    "quantity": dish_qty,
                    "ingredients": ingredients,
                })

            result.append({
                "company": menu.company.name,
                "diet_category": menu.diet_category.name,
                "meal_time": menu.get_meal_time_display(),
                "headcount": total_count,
                "dishes": dishes_data,
            })

        return Response(result)


class CookingRecipeView(APIView):
    """
    GET /api/cooking/recipe/{dish_id}/
    View a single dish recipe with full ingredient details.

    Supports parameter:
    ?count=100  - scale recipe for N servings
    """
    def get(self, request, dish_id):
        try:
            dish = Dish.objects.prefetch_related(
                'ingredients__raw_material', 'ingredients__processing'
            ).get(id=dish_id)
        except Dish.DoesNotExist:
            return Response({"error": "Dish not found"}, status=status.HTTP_404_NOT_FOUND)

        count = int(request.query_params.get("count", 1))

        ingredients = []
        for ing in dish.ingredients.all():
            raw = ing.raw_material
            processing = ing.processing
            net_qty = ing.net_quantity * count
            yield_rate = processing.yield_rate if processing else 1
            gross_qty = (net_qty / yield_rate) if yield_rate else net_qty

            ingredients.append({
                "material": raw.name,
                "method": processing.method_name if processing else None,
                "yield_rate": float(yield_rate),
                "net_per_serving": float(ing.net_quantity),
                "net_total": float(net_qty),
                "gross_total": float(gross_qty),
                "unit": "kg",
            })

        return Response({
            "dish_id": dish.id,
            "dish_name": dish.name,
            "count": count,
            "ingredients": ingredients,
        })
