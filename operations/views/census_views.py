# operations/views/census_views.py
from django.db import IntegrityError, transaction
from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from common.views import success_response, error_response
from ..models import DailyCensus
from ..serializers import DailyCensusSerializer, DailyCensusBatchSerializer


from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework_simplejwt.authentication import JWTAuthentication

class DailyCensusListView(generics.ListAPIView):
    serializer_class = DailyCensusSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def _company_id(self):
        # return 1
        return 1

    def get_queryset(self):
        qp = self.request.query_params
        qs = DailyCensus.objects.filter(company_id=self._company_id())

        date = qp.get("date")
        start = qp.get("start")
        end = qp.get("end")

        if date:
            qs = qs.filter(date=date)
        else:
            if start:
                qs = qs.filter(date__gte=start)
            if end:
                qs = qs.filter(date__lte=end)

        if qp.get("region_id"):
            qs = qs.filter(region_id=qp["region_id"])
        if qp.get("diet_category_id"):
            qs = qs.filter(diet_category_id=qp["diet_category_id"])

        return qs.order_by("date", "region_id", "diet_category_id")


class DailyCensusBatchView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def _company_id(self):
        # return 1
        return 1

    def post(self, request):
        serializer = DailyCensusBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        date = serializer.validated_data["date"]
        items = serializer.validated_data["items"]
        company_id = self._company_id()

        created = 0
        updated = 0

        with transaction.atomic():
            for item in items:
                try:
                    _, is_created = DailyCensus.objects.update_or_create(
                        company_id=company_id,
                        date=date,
                        region_id=item["region_id"],
                        diet_category_id=item["diet_category_id"],
                        defaults={"count": item["count"]},
                    )
                    created += 1 if is_created else 0
                    updated += 0 if is_created else 1
                except IntegrityError:
                    raise ValidationError({"detail": "Error while saving census batch."})

        return success_response(
            results={"date": str(date), "created": created, "updated": updated},
            message=f"Created {created}, Updated {updated}",
        )


class DailyCensusSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def _company_id(self):
        # return 1
        return 1

    def get(self, request):
        qp = request.query_params
        qs = DailyCensus.objects.filter(company_id=self._company_id())

        date = qp.get("date")
        start = qp.get("start")
        end = qp.get("end")

        if date:
            qs = qs.filter(date=date)
        else:
            if start:
                qs = qs.filter(date__gte=start)
            if end:
                qs = qs.filter(date__lte=end)

        total = qs.aggregate(total=Sum("count"))["total"] or 0
        by_diet = (
            qs.values("diet_category_id", "diet_category__name")
            .annotate(count=Sum("count"))
            .order_by("diet_category_id")
        )

        return success_response(
            results={
                "date": date,
                "start": start,
                "end": end,
                "total": total,
                "by_diet_category": [
                    {
                        "diet_category_id": r["diet_category_id"],
                        "diet_category_name": r["diet_category__name"],
                        "count": r["count"],
                    }
                    for r in by_diet
                ],
            }
        )