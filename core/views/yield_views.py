from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied

from core.models import RawMaterial, RawMaterialYieldRate

def require_rw(user):
    if getattr(user.profile, "role", "RO") != "RW":
        raise PermissionDenied("RW role required.")

def compute_effective_date(now_local):
    """
    Rule:
    - If update happens during the "same calendar day" before 23:59 => effective tomorrow
    - If update happens after midnight (new day) => effective day after tomorrow
    """
    return now_local.date() + timedelta(days=1)

class RawMaterialYieldRateUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, raw_material_id: int):
        require_rw(request.user)

        rm = RawMaterial.objects.filter(id=raw_material_id).first()
        if not rm:
            raise NotFound("Raw material not found.")

        y = request.data.get("yield_rate", None)
        if y is None:
            raise ValidationError({"yield_rate": "This field is required."})

        try:
            y_dec = Decimal(str(y))
        except Exception:
            raise ValidationError({"yield_rate": "Invalid decimal."})

        if y_dec <= 0 or y_dec > Decimal("1.00"):
            raise ValidationError({"yield_rate": "Must be in (0, 1.00]."})

        now_local = timezone.localtime(timezone.now())
        eff_date = compute_effective_date(now_local)

        obj, created = RawMaterialYieldRate.objects.update_or_create(
            raw_material=rm,
            effective_date=eff_date,
            defaults={"yield_rate": y_dec},
        )

        return Response(
            {
                "raw_material_id": rm.id,
                "raw_material_name": rm.name,
                "yield_rate": str(obj.yield_rate),
                "effective_date": str(obj.effective_date),
                "created": created,
            },
            status=status.HTTP_201_CREATED,
        )