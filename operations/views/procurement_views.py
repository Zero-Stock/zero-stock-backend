from rest_framework_simplejwt.authentication import JWTAuthentication
# operations/views/procurement_views.py
import math
from django.db.models import Sum
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from decimal import Decimal
from collections import defaultdict

from common.views import success_response, error_response
from ..models import ProcurementRequest, ProcurementItem, DailyCensus, WeeklyMenu, WeeklyMenuDish
from core.models import DishIngredient, SupplierMaterial, RawMaterialYieldRate
from ..serializers import ProcurementRequestSerializer, ProcurementItemSerializer, ProcurementGenerateSerializer


def require_rw(user):
    pass


def get_yield_rate_for(raw_material_id: int, target_date):
    """
    Return the yield rate effective on target_date.
    Logic:
    - Find the latest yield_rate where effective_date <= target_date
    - If none found, return 1.00
    """
    rec = (
        RawMaterialYieldRate.objects
        .filter(raw_material_id=raw_material_id,
                effective_date__lte=target_date)
        .order_by("-effective_date", "-id")
        .first()
    )

    return rec.yield_rate if rec else Decimal("1.00")


class ProcurementListView(generics.ListAPIView):
    serializer_class = ProcurementRequestSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        company_id = 1
        return ProcurementRequest.objects.filter(company_id=company_id).order_by("-target_date", "-id")


class ProcurementDetailView(generics.RetrieveAPIView):
    serializer_class = ProcurementRequestSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get_object(self):
        company_id = 1
        obj = ProcurementRequest.objects.filter(company_id=company_id, id=self.kwargs["pk"]).first()
        if not obj:
            raise NotFound("Procurement request not found.")
        return obj


class ProcurementItemsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, pk):
        company_id = 1
        pr = ProcurementRequest.objects.filter(company_id=company_id, id=pk).first()
        if not pr:
            raise NotFound("Procurement request not found.")

        qs = ProcurementItem.objects.filter(request=pr).select_related("raw_material")

        group_by = request.query_params.get("group_by")
        if not group_by:
            return success_response(results=ProcurementItemSerializer(qs, many=True).data)

        if group_by == "supplier":
            rows = (
                qs.values("supplier__name")
                .annotate(total=Sum("purchase_quantity"))
                .order_by("supplier__name")
            )
            return success_response(results=[
                {
                    "supplier": r["supplier__name"] or "未分配",
                    "purchase_quantity": str(r["total"] or 0),
                }
                for r in rows
            ])

        if group_by == "category":
            rows = (
                qs.values("raw_material__category__name")
                .annotate(total=Sum("purchase_quantity"))
                .order_by("raw_material__category__name")
            )
            return success_response(results=[
                {
                    "category": r["raw_material__category__name"],
                    "purchase_quantity": str(r["total"] or 0),
                }
                for r in rows
            ])

        raise ValidationError({"group_by": "Must be supplier or category."})


class ProcurementSubmitView(APIView):
    """
    POST /api/procurement/{pk}/submit/
    Submit a CREATED procurement → SUBMITTED.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, pk):
        require_rw(request.user)

        company_id = 1
        pr = ProcurementRequest.objects.filter(company_id=company_id, id=pk).first()
        if not pr:
            raise NotFound("Procurement request not found.")

        if pr.status != "CREATED":
            return success_response(
                results={"id": pr.id, "status": pr.status},
                message=f"Cannot submit: current status is {pr.status}.",
            )

        pr.status = "SUBMITTED"
        pr.save(update_fields=["status"])
        return success_response(
            results={"id": pr.id, "status": pr.status},
            message="Submitted",
        )


class ProcurementGenerateView(APIView):
    """
    POST /api/procurement/generate/
    Body: { "date": "YYYY-MM-DD" }

    Generates a procurement request for the given date covering B/L/D meals.
    Factors in current stock. Pre-fills supplier from RawMaterial.default_supplier.
    Status: CREATED.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def _company_id(self, request):
        return 1

    def _weekday_1_to_7(self, date_obj):
        return date_obj.weekday() + 1

    def post(self, request):
        require_rw(request.user)

        s = ProcurementGenerateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        target_date = s.validated_data["date"]
        company_id = self._company_id(request)
        weekday = self._weekday_1_to_7(target_date)

        # 1) pull census rows
        census_qs = DailyCensus.objects.filter(company_id=company_id, date=target_date)
        if not census_qs.exists():
            raise ValidationError({"date": "No census found for this date."})

        diet_counts = {}
        for row in census_qs.values("diet_category_id").annotate(total=Sum("count")):
            diet_counts[row["diet_category_id"]] = int(row["total"] or 0)

        meal_types = ["B", "L", "D"]

        # 2) build demand totals per raw_material
        # raw_material_id -> {"demand": Decimal, "notes": [str], "raw_material": obj}
        totals = {}

        def add_demand(raw_material, gross_qty: Decimal, note: str):
            rid = raw_material.id
            if rid not in totals:
                totals[rid] = {
                    "demand": Decimal("0"),
                    "notes": [], "raw_material": raw_material,
                }
            totals[rid]["demand"] += gross_qty
            totals[rid]["notes"].append(note)

        def get_dishes_for(diet_id: int, meal_type: str):
            """Returns list of (dish, quantity) tuples for this diet+meal combo."""
            wm = WeeklyMenu.objects.filter(
                company_id=company_id,
                diet_category_id=diet_id,
                day_of_week=weekday,
                meal_time=meal_type,
            ).first()
            if wm:
                menu_dishes = WeeklyMenuDish.objects.filter(menu=wm).select_related('dish')
                return [(md.dish, md.quantity) for md in menu_dishes]
            return []

        # 3) compute demand
        for diet_id, people in diet_counts.items():
            if people <= 0:
                continue

            for meal in meal_types:
                dishes = get_dishes_for(diet_id, meal)
                if not dishes:
                    continue

                for dish, dish_qty in dishes:
                    recipe_rows = (
                        DishIngredient.objects
                        .filter(dish_id=dish.id)
                        .select_related("raw_material", "processing")
                    )
                    for ing in recipe_rows:
                        raw = ing.raw_material
                        processing = ing.processing
                        yield_rate = get_yield_rate_for(raw.id, target_date)
                        if yield_rate <= 0:
                            raise ValidationError(
                                {"detail": f"Invalid yield_rate for {raw.name}."}
                            )

                        net_per_serv = ing.net_quantity * dish_qty
                        total_net = Decimal(people) * net_per_serv
                        total_gross = total_net / yield_rate

                        processing_name = processing.method_name if processing else "raw"
                        note = (
                            f"{target_date} {meal} | diet={diet_id} "
                            f"| {dish.name} x{dish_qty} | {raw.name}[{processing_name}] "
                            f"net={ing.net_quantity}*{dish_qty} * {people} / yield={yield_rate} => gross={total_gross}"
                        )
                        add_demand(raw, total_gross, note)

        if not totals:
            raise ValidationError({"detail": "No procurement items generated. Check menu/recipes."})

        # 4) write to DB
        with transaction.atomic():
            existing = ProcurementRequest.objects.filter(company_id=company_id, target_date=target_date).first()
            if existing and existing.status in ("SUBMITTED", "CONFIRMED"):
                raise ValidationError(
                    {"detail": f"Procurement request already {existing.status}. Cannot regenerate."}
                )

            if existing:
                pr = existing
                ProcurementItem.objects.filter(request=pr).delete()
                pr.status = "CREATED"
                pr.save(update_fields=["status"])
            else:
                pr = ProcurementRequest.objects.create(
                    company_id=company_id, target_date=target_date, status="CREATED"
                )

            items = []
            for rid, data in totals.items():
                raw = data["raw_material"]
                demand = data["demand"]
                stock = raw.stock or Decimal("0")
                purchase = max(demand - stock, Decimal("0"))

                # Pre-fill supplier from RawMaterial.default_supplier
                supplier_fields = {}
                if raw.default_supplier_id:
                    sm = SupplierMaterial.objects.filter(
                        supplier_id=raw.default_supplier_id, raw_material_id=rid
                    ).first()
                    if sm:
                        supplier_fields = {
                            "supplier_id": raw.default_supplier_id,
                            "supplier_unit_name": sm.unit_name,
                            "supplier_kg_per_unit": sm.kg_per_unit,
                            "supplier_price": sm.price,
                        }

                items.append(ProcurementItem(
                    request=pr,
                    raw_material=raw,
                    demand_quantity=demand,
                    stock_quantity=stock,
                    purchase_quantity=purchase,
                    notes="\n".join(data["notes"])[:5000],
                    **supplier_fields,
                ))
            ProcurementItem.objects.bulk_create(items)

        return success_response(
            results=ProcurementRequestSerializer(pr).data,
            message="Procurement request generated",
            http_status=status.HTTP_201_CREATED,
        )


DAY_NAMES_CN = {
    0: "周一", 1: "周二", 2: "周三",
    3: "周四", 4: "周五", 5: "周六", 6: "周日",
}


class ProcurementSheetView(APIView):
    """
    GET /api/procurement/{id}/sheet/
    Returns the final procurement list with dual-unit display.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, pk):
        company_id = 1
        pr = ProcurementRequest.objects.filter(
            company_id=company_id, id=pk
        ).select_related("company").first()
        if not pr:
            raise NotFound("Procurement request not found.")

        items = ProcurementItem.objects.filter(
            request=pr
        ).select_related(
            "raw_material", "raw_material__category", "supplier"
        ).order_by("raw_material__category__name", "raw_material__name")

        def to_unit(kg, kg_per_unit, ceiling=False):
            if not kg_per_unit or kg_per_unit <= 0:
                return None
            result = float(kg) / float(kg_per_unit)
            return math.ceil(result) if ceiling else round(result, 2)

        items_list = []
        for item in items:
            raw = item.raw_material
            kpu = item.supplier_kg_per_unit
            items_list.append({
                "name": raw.name,
                "category": raw.category.name,
                "demand_kg": float(item.demand_quantity),
                "demand_unit_qty": to_unit(item.demand_quantity, kpu),
                "stock_kg": float(item.stock_quantity),
                "stock_unit_qty": to_unit(item.stock_quantity, kpu),
                "purchase_kg": float(item.purchase_quantity),
                "purchase_unit_qty": to_unit(item.purchase_quantity, kpu, ceiling=True),
                "supplier": item.supplier.name if item.supplier else None,
                "supplier_unit_name": item.supplier_unit_name or None,
                "supplier_kg_per_unit": float(item.supplier_kg_per_unit) if item.supplier_kg_per_unit else None,
                "supplier_price": float(item.supplier_price) if item.supplier_price else None,
            })

        day_cn = DAY_NAMES_CN.get(pr.target_date.weekday(), "")

        return success_response(results={
            "id": pr.id,
            "date": str(pr.target_date),
            "day_of_week": day_cn,
            "company": pr.company.name,
            "status": pr.status,
            "items": items_list,
        })


class ProcurementTemplateView(APIView):
    """
    GET /api/procurement/template/?date=2026-02-27
    Returns the procurement template with available suppliers for each material.
    Shows demand, stock, purchase in both kg and supplier units.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        company_id = 1
        date_str = request.query_params.get("date")
        if not date_str:
            raise ValidationError({"date": "date query parameter is required."})

        pr = ProcurementRequest.objects.filter(
            company_id=company_id, target_date=date_str
        ).first()
        if not pr:
            raise NotFound("No procurement request found for this date.")

        items = ProcurementItem.objects.filter(
            request=pr
        ).select_related("raw_material", "raw_material__category")

        result_items = []
        for item in items:
            raw = item.raw_material
            # Get available suppliers for this material
            supplier_materials = SupplierMaterial.objects.filter(
                raw_material=raw
            ).select_related("supplier")

            available_suppliers = []
            for sm in supplier_materials:
                available_suppliers.append({
                    "supplier_material_id": sm.id,
                    "supplier_id": sm.supplier_id,
                    "supplier_name": sm.supplier.name,
                    "unit_name": sm.unit_name,
                    "kg_per_unit": float(sm.kg_per_unit),
                    "price": float(sm.price) if sm.price else None,
                })

            result_items.append({
                "item_id": item.id,
                "raw_material_id": raw.id,
                "raw_material_name": raw.name,
                "category": raw.category.name,
                "demand_kg": float(item.demand_quantity),
                "stock_kg": float(item.stock_quantity),
                "purchase_kg": float(item.purchase_quantity),
                "current_supplier_id": item.supplier_id,
                "available_suppliers": available_suppliers,
            })

        return success_response(results={
            "id": pr.id,
            "date": str(pr.target_date),
            "status": pr.status,
            "items": result_items,
        })


class ProcurementAssignSuppliersView(APIView):
    """
    POST /api/procurement/assign-suppliers/?date=2026-02-27
    Assign suppliers to procurement items. Does NOT change procurement status.
    Only allowed on CREATED status.

    Body:
    {
        "assignments": [
            {"item_id": 101, "supplier_material_id": 10},
            {"item_id": 102, "supplier_material_id": 15}
        ]
    }
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        require_rw(request.user)

        company_id = 1
        date_str = request.query_params.get("date")
        if not date_str:
            raise ValidationError({"date": "date query parameter is required."})

        pr = ProcurementRequest.objects.filter(
            company_id=company_id, target_date=date_str
        ).first()
        if not pr:
            raise NotFound("No procurement request found for this date.")

        if pr.status != "CREATED":
            raise ValidationError({"detail": f"Cannot reassign: status is {pr.status}."})

        assignments = request.data.get("assignments", [])
        if not assignments:
            raise ValidationError({"detail": "assignments list is required."})

        # Validate and apply assignments
        with transaction.atomic():
            for assignment in assignments:
                item_id = assignment.get("item_id")
                sm_id = assignment.get("supplier_material_id")

                try:
                    item = ProcurementItem.objects.get(id=item_id, request=pr)
                except ProcurementItem.DoesNotExist:
                    raise ValidationError(
                        {"detail": f"Item {item_id} not found in this procurement."}
                    )

                try:
                    sm = SupplierMaterial.objects.select_related("supplier").get(
                        id=sm_id, raw_material_id=item.raw_material_id
                    )
                except SupplierMaterial.DoesNotExist:
                    raise ValidationError(
                        {"detail": f"SupplierMaterial {sm_id} not valid for material {item.raw_material_id}."}
                    )

                item.supplier = sm.supplier
                item.supplier_unit_name = sm.unit_name
                item.supplier_kg_per_unit = sm.kg_per_unit
                item.supplier_price = sm.price
                item.save(update_fields=[
                    "supplier", "supplier_unit_name",
                    "supplier_kg_per_unit", "supplier_price"
                ])

        return success_response(
            results=ProcurementRequestSerializer(pr).data,
            message="Suppliers assigned",
        )
