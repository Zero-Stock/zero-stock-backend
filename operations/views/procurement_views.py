from django.db.models import Sum
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from decimal import Decimal
from collections import defaultdict
from ..models import ProcurementRequest, ProcurementItem, DailyCensus, WeeklyMenu, DailyMenu
from core.models import DishIngredient, SupplierMaterial
from ..serializers import ProcurementRequestSerializer, ProcurementItemSerializer, ProcurementGenerateSerializer


def require_rw(user):
    if getattr(user.profile, "role", "RO") != "RW":
        raise PermissionDenied("RW role required.")


def meal_to_period(meal_type: str) -> str:
    """B/L -> AM (morning), D -> PM (afternoon)"""
    return "PM" if meal_type == "D" else "AM"


class ProcurementListView(generics.ListAPIView):
    serializer_class = ProcurementRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company_id = self.request.user.profile.company_id
        return ProcurementRequest.objects.filter(company_id=company_id).order_by("-target_date", "-id")


class ProcurementDetailView(generics.RetrieveAPIView):
    serializer_class = ProcurementRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        company_id = self.request.user.profile.company_id
        obj = ProcurementRequest.objects.filter(company_id=company_id, id=self.kwargs["pk"]).first()
        if not obj:
            raise NotFound("Procurement request not found.")
        return obj


class ProcurementItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        company_id = request.user.profile.company_id
        pr = ProcurementRequest.objects.filter(company_id=company_id, id=pk).first()
        if not pr:
            raise NotFound("Procurement request not found.")

        qs = ProcurementItem.objects.filter(request=pr).select_related("raw_material")

        group_by = request.query_params.get("group_by")
        if not group_by:
            return Response(ProcurementItemSerializer(qs, many=True).data)

        if group_by == "supplier":
            rows = (
                qs.values("supplier__name")
                .annotate(total=Sum("total_gross_quantity"))
                .order_by("supplier__name")
            )
            return Response([
                {
                    "supplier": r["supplier__name"] or "未分配",
                    "total_gross_quantity": str(r["total"] or 0),
                }
                for r in rows
            ])

        if group_by == "category":
            rows = (
                qs.values("raw_material__category__name")
                .annotate(total=Sum("total_gross_quantity"))
                .order_by("raw_material__category__name")
            )
            return Response([
                {
                    "category": r["raw_material__category__name"],
                    "total_gross_quantity": str(r["total"] or 0),
                }
                for r in rows
            ])

        raise ValidationError({"group_by": "Must be supplier or category."})


class ProcurementConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        require_rw(request.user)

        company_id = request.user.profile.company_id
        pr = ProcurementRequest.objects.filter(company_id=company_id, id=pk).first()
        if not pr:
            raise NotFound("Procurement request not found.")

        if pr.status == "CONFIRMED":
            return Response({"detail": "Already confirmed."}, status=status.HTTP_200_OK)

        pr.status = "CONFIRMED"
        pr.save(update_fields=["status"])
        return Response({"id": pr.id, "status": pr.status})


class ProcurementGenerateView(APIView):
    """
    POST /api/procurement/generate/
    Body: { "date": "YYYY-MM-DD" }

    Generates a procurement request for the given date covering B/L/D meals.
    Tracks AM (Breakfast + Lunch) and PM (Dinner) quantities separately
    for the sheet view format.
    """
    permission_classes = [IsAuthenticated]

    def _company_id(self, request):
        return request.user.profile.company_id

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

        # 2) build totals per raw_material with AM/PM split
        # raw_material_id -> {"gross": D, "am": D, "pm": D, "notes": [str], "raw_material": obj}
        totals = {}

        def add_gross(raw_material, gross_qty: Decimal, note: str, period: str):
            rid = raw_material.id
            if rid not in totals:
                totals[rid] = {
                    "gross": Decimal("0"), "am": Decimal("0"), "pm": Decimal("0"),
                    "notes": [], "raw_material": raw_material,
                }
            totals[rid]["gross"] += gross_qty
            totals[rid][period.lower()] += gross_qty
            totals[rid]["notes"].append(note)

        def get_dishes_for(diet_id: int, meal_type: str):
            dm = DailyMenu.objects.filter(
                company_id=company_id,
                date=target_date,
                diet_id=diet_id,
                meal_type=meal_type,
            ).prefetch_related("dishes").first()
            if dm:
                return list(dm.dishes.all())

            wm = WeeklyMenu.objects.filter(
                company_id=company_id,
                diet_category_id=diet_id,
                day_of_week=weekday,
                meal_time=meal_type,
            ).prefetch_related("dishes").first()
            if wm:
                return list(wm.dishes.all())
            return []

        # 3) compute
        for diet_id, people in diet_counts.items():
            if people <= 0:
                continue

            for meal in meal_types:
                period = meal_to_period(meal)
                dishes = get_dishes_for(diet_id, meal)
                if not dishes:
                    continue

                for dish in dishes:
                    recipe_rows = (
                        DishIngredient.objects
                        .filter(dish_id=dish.id)
                        .select_related("raw_material", "processing")
                    )
                    for ing in recipe_rows:
                        raw = ing.raw_material
                        processing = ing.processing
                        yield_rate = processing.yield_rate if processing else Decimal("1.00")
                        if yield_rate <= 0:
                            method_name = processing.method_name if processing else "N/A"
                            raise ValidationError(
                                {"detail": f"Invalid yield_rate for {raw.name} [{method_name}]."}
                            )

                        net_per_serv = ing.net_quantity
                        total_net = Decimal(people) * net_per_serv
                        total_gross = total_net / yield_rate

                        method_name = processing.method_name if processing else "无加工"
                        note = (
                            f"{target_date} {meal} | diet={diet_id} "
                            f"| {dish.name} | {raw.name}[{method_name}] "
                            f"net={net_per_serv} * {people} / yield={yield_rate} => gross={total_gross}"
                        )
                        add_gross(raw, total_gross, note, period)

        if not totals:
            raise ValidationError({"detail": "No procurement items generated. Check menu/recipes."})

        # 4) write to DB
        with transaction.atomic():
            existing = ProcurementRequest.objects.filter(company_id=company_id, target_date=target_date).first()
            if existing and existing.status == "CONFIRMED":
                raise ValidationError({"detail": "Procurement request already CONFIRMED. Cannot regenerate."})

            if existing:
                pr = existing
                ProcurementItem.objects.filter(request=pr).delete()
                pr.status = "DRAFT"
                pr.save(update_fields=["status"])
            else:
                pr = ProcurementRequest.objects.create(
                    company_id=company_id, target_date=target_date, status="PENDING"
                )

            items = []
            for rid, data in totals.items():
                items.append(ProcurementItem(
                    request=pr,
                    raw_material=data["raw_material"],
                    total_gross_quantity=data["gross"],
                    am_quantity=data["am"],
                    pm_quantity=data["pm"],
                    notes="\n".join(data["notes"])[:5000],
                ))
            ProcurementItem.objects.bulk_create(items)

            pr.status = "PENDING"
            pr.save(update_fields=["status"])

        return Response(ProcurementRequestSerializer(pr).data, status=status.HTTP_201_CREATED)


DAY_NAMES_CN = {
    0: "周一", 1: "周二", 2: "周三",
    3: "周四", 4: "周五", 5: "周六", 6: "周日",
}


class ProcurementSheetView(APIView):
    """
    GET /api/procurement/{id}/sheet/
    Returns the final procurement list with supplier unit info.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        company_id = request.user.profile.company_id
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

        items_list = []
        for item in items:
            raw = item.raw_material
            items_list.append({
                "name": raw.name,
                "category": raw.category.name,
                "total_kg": float(item.total_gross_quantity),
                "am_kg": float(item.am_quantity),
                "pm_kg": float(item.pm_quantity),
                "supplier": item.supplier.name if item.supplier else None,
                "supplier_unit_name": item.supplier_unit_name or None,
                "supplier_unit_qty": float(item.supplier_unit_qty) if item.supplier_unit_qty else None,
                "supplier_price": float(item.supplier_price) if item.supplier_price else None,
            })

        day_cn = DAY_NAMES_CN.get(pr.target_date.weekday(), "")

        return Response({
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
    Returns the kg template with available suppliers for each material.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company_id = request.user.profile.company_id
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
                "total_kg": float(item.total_gross_quantity),
                "am_kg": float(item.am_quantity),
                "pm_kg": float(item.pm_quantity),
                "current_supplier_id": item.supplier_id,
                "available_suppliers": available_suppliers,
            })

        return Response({
            "id": pr.id,
            "date": str(pr.target_date),
            "status": pr.status,
            "items": result_items,
        })


class ProcurementAssignSuppliersView(APIView):
    """
    POST /api/procurement/assign-suppliers/?date=2026-02-27
    Assign suppliers to procurement items and calculate supplier unit quantities.

    Body:
    {
        "assignments": [
            {"item_id": 101, "supplier_material_id": 10},
            {"item_id": 102, "supplier_material_id": 15}
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        require_rw(request.user)

        company_id = request.user.profile.company_id
        date_str = request.query_params.get("date")
        if not date_str:
            raise ValidationError({"date": "date query parameter is required."})

        pr = ProcurementRequest.objects.filter(
            company_id=company_id, target_date=date_str
        ).first()
        if not pr:
            raise NotFound("No procurement request found for this date.")

        if pr.status == "CONFIRMED":
            raise ValidationError({"detail": "Already confirmed. Cannot reassign."})

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

                # Calculate supplier unit quantity
                kg_per_unit = sm.kg_per_unit or Decimal("1.00")
                unit_qty = item.total_gross_quantity / kg_per_unit

                item.supplier = sm.supplier
                item.supplier_unit_name = sm.unit_name
                item.supplier_unit_qty = unit_qty
                item.supplier_price = sm.price
                item.save(update_fields=[
                    "supplier", "supplier_unit_name",
                    "supplier_unit_qty", "supplier_price"
                ])

            pr.status = "CONFIRMED"
            pr.save(update_fields=["status"])

        return Response(ProcurementRequestSerializer(pr).data)
