# operations/views/receiving_views.py
"""
Receiving record views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from common.views import success_response, error_response
from ..models import (
    ProcurementRequest, ProcurementItem,
    ReceivingRecord, ReceivingItem
)
from ..serializers import (
    ReceivingRecordSerializer, ReceivingCreateSerializer
)


class ReceivingTemplateView(APIView):
    """
    GET /api/receiving/{procurement_id}/template/
    Generate a receiving template from a procurement request (expected quantities).
    """
    def get(self, request, procurement_id):
        try:
            procurement = ProcurementRequest.objects.get(id=procurement_id)
        except ProcurementRequest.DoesNotExist:
            return error_response(
                error="Procurement request not found",
                message="Procurement request not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        items = ProcurementItem.objects.filter(
            request=procurement
        ).select_related('raw_material')

        template = {
            "procurement_id": procurement.id,
            "target_date": procurement.target_date,
            "company": procurement.company.name,
            "status": procurement.status,
            "items": [
                {
                    "raw_material_id": item.raw_material.id,
                    "raw_material_name": item.raw_material.name,
                    "expected_quantity": float(item.total_gross_quantity),
                    "unit": item.raw_material.unit,
                    "spec": item.raw_material.spec,
                    "supplier": item.raw_material.supplier,
                    "category": item.raw_material.category,
                    "actual_quantity": 0,
                }
                for item in items
            ]
        }

        return success_response(results=template)


class ReceivingCreateView(APIView):
    """
    POST /api/receiving/
    Record actual received quantities.

    Request body:
    {
        "procurement_id": 1,
        "notes": "...",
        "items": [
            {"raw_material_id": 1, "actual_quantity": 50.0, "notes": ""},
            {"raw_material_id": 2, "actual_quantity": 30.5, "notes": "short 2kg"}
        ]
    }
    """
    def post(self, request):
        serializer = ReceivingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(error=serializer.errors, message="Validation failed")

        data = serializer.validated_data
        try:
            procurement = ProcurementRequest.objects.get(id=data['procurement_id'])
        except ProcurementRequest.DoesNotExist:
            return error_response(
                error="Procurement request not found",
                message="Procurement request not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        receiving = ReceivingRecord.objects.create(
            procurement=procurement,
            company=procurement.company,
            notes=data.get('notes', ''),
            status='COMPLETED',
        )

        # Build expected quantity lookup from procurement items
        proc_items = {
            pi.raw_material_id: pi.total_gross_quantity
            for pi in ProcurementItem.objects.filter(request=procurement)
        }

        for item_data in data['items']:
            raw_material_id = item_data.get('raw_material_id')
            expected = proc_items.get(raw_material_id, 0)
            ReceivingItem.objects.create(
                receiving=receiving,
                raw_material_id=raw_material_id,
                expected_quantity=expected,
                actual_quantity=item_data.get('actual_quantity', 0),
                notes=item_data.get('notes', ''),
            )

        result = ReceivingRecordSerializer(receiving).data
        return success_response(
            results=result,
            message="Receiving record created",
            http_status=status.HTTP_201_CREATED,
        )


class ReceivingDetailView(APIView):
    """
    GET /api/receiving/{id}/
    View receiving detail (actual vs expected comparison).
    """
    def get(self, request, pk):
        try:
            receiving = ReceivingRecord.objects.prefetch_related(
                'items__raw_material'
            ).get(id=pk)
        except ReceivingRecord.DoesNotExist:
            return error_response(
                error="Receiving record not found",
                message="Receiving record not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReceivingRecordSerializer(receiving)
        return success_response(results=serializer.data)
