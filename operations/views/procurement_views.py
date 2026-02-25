from django.db.models import Sum
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from decimal import Decimal
from ..models import ProcurementRequest, ProcurementItem, DailyCensus, WeeklyMenu, DailyMenu
from core.models import DishIngredient
from ..serializers import ProcurementRequestSerializer, ProcurementItemSerializer, ProcurementGenerateSerializer


def require_rw(user):
    if getattr(user.profile, "role", "RO") != "RW":
        raise PermissionDenied("RW role required.")


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

        qs = ProcurementItem.objects.filter(request=pr).select_related("raw_material", "raw_material__default_unit")

        group_by = request.query_params.get("group_by")
        if not group_by:
            return Response(ProcurementItemSerializer(qs, many=True).data)

        if group_by == "supplier":
            rows = (
                qs.values("raw_material__supplier")
                .annotate(total=Sum("total_gross_quantity"))
                .order_by("raw_material__supplier")
            )
            return Response([
                {
                    "supplier": r["raw_material__supplier"] or "Unknown",
                    "total_gross_quantity": str(r["total"] or 0),
                }
                for r in rows
            ])

        if group_by == "category":
            rows = (
                qs.values("raw_material__category")
                .annotate(total=Sum("total_gross_quantity"))
                .order_by("raw_material__category")
            )
            return Response([
                {
                    "category": r["raw_material__category"],
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

    Generates ONE procurement request for that date (B/L/D all meals),
    based on DailyCensus + (DailyMenu fallback WeeklyMenu) + DishIngredient recipes,
    and converts net -> gross using yield_rate.
    """
    permission_classes = [IsAuthenticated]

    def _company_id(self, request):
        return request.user.profile.company_id

    def _weekday_1_to_7(self, date_obj):
        # Python weekday(): Monday=0..Sunday=6 -> +1 to match WeeklyMenu.DAY_CHOICES
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

        # diet_id -> headcount
        diet_counts = {}
        for row in census_qs.values("diet_category_id").annotate(total=Sum("count")):
            diet_counts[row["diet_category_id"]] = int(row["total"] or 0)

        meal_types = ["B", "L", "D"]

        # 2) build total gross per raw_material
        # raw_material_id -> {"gross": Decimal, "notes": [str], "raw_material": obj}
        totals = {}

        def add_gross(raw_material, gross_qty: Decimal, note: str):
            rid = raw_material.id
            if rid not in totals:
                totals[rid] = {"gross": Decimal("0"), "notes": [], "raw_material": raw_material}
            totals[rid]["gross"] += gross_qty
            totals[rid]["notes"].append(note)

        # Helper to get dishes for (diet, meal) on this date:
        def get_dishes_for(diet_id: int, meal_type: str):
            # A) DailyMenu priority
            dm = DailyMenu.objects.filter(
                company_id=company_id,
                date=target_date,
                diet_id=diet_id,
                meal_type=meal_type,
            ).prefetch_related("dishes").first()
            if dm:
                return list(dm.dishes.all())

            # B) Fallback WeeklyMenu
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
                dishes = get_dishes_for(diet_id, meal)
                if not dishes:
                    # No menu configured for this diet/meal; skip gracefully
                    continue

                for dish in dishes:
                    # DishIngredient ties dish -> ProcessedMaterial + net_quantity per serving
                    recipe_rows = (
                        DishIngredient.objects
                        .filter(dish_id=dish.id)
                        .select_related("material", "material__raw_material")
                    )

                    for ing in recipe_rows:
                        processed = ing.material  # ProcessedMaterial
                        raw = processed.raw_material
                        yield_rate = processed.yield_rate or Decimal("1.00")
                        if yield_rate <= 0:
                            raise ValidationError(
                                {"detail": f"Invalid yield_rate for {raw.name} [{processed.method_name}]."}
                            )

                        net_per_serv = ing.net_quantity  # Decimal
                        # total net for this dish ingredient
                        total_net = Decimal(people) * net_per_serv
                        total_gross = (total_net / yield_rate)

                        note = (
                            f"{target_date} {meal} | diet={diet_id} "
                            f"| {dish.name} | {raw.name}[{processed.method_name}] "
                            f"net={net_per_serv} * {people} / yield={yield_rate} => gross={total_gross}"
                        )
                        add_gross(raw, total_gross, note)

        if not totals:
            raise ValidationError({"detail": "No procurement items generated. Check menu/recipes."})

        # 4) write to DB
        with transaction.atomic():
            # Strategy: if same date already has a DRAFT, overwrite; if CONFIRMED, block
            existing = ProcurementRequest.objects.filter(company_id=company_id, target_date=target_date).first()
            if existing and existing.status == "CONFIRMED":
                raise ValidationError({"detail": "Procurement request already CONFIRMED. Cannot regenerate."})

            if existing:
                pr = existing
                # wipe old items then regenerate
                ProcurementItem.objects.filter(request=pr).delete()
                pr.status = "DRAFT"
                pr.save(update_fields=["status"])
            else:
                pr = ProcurementRequest.objects.create(company_id=company_id, target_date=target_date, status="DRAFT")

            # create items
            items = []
            for rid, data in totals.items():
                raw = data["raw_material"]
                gross = data["gross"]
                notes = "\n".join(data["notes"])[:5000]  
                items.append(
                    ProcurementItem(
                        request=pr,
                        raw_material=raw,
                        total_gross_quantity=gross,
                        notes=notes,
                    )
                )
            ProcurementItem.objects.bulk_create(items)

        return Response(ProcurementRequestSerializer(pr).data, status=status.HTTP_201_CREATED)
    
