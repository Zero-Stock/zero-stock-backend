# operations/views/receiving_views.py
"""
Receiving record views.
"""
from datetime import datetime, time
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from core.models import RawMaterial


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
        # company_id = request.user.profile.company_id 
        company_id = 1

        procurement = ProcurementRequest.objects.filter(
            id=procurement_id,
            company_id=company_id,
        ).select_related("company").first()

        if not procurement:
            return error_response(
                error="Procurement request not found",
                message="Procurement request not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if procurement.status != "SUBMITTED":
            return error_response(
                error=f"Cannot generate receiving template: procurement status is {procurement.status}",
                message=f"Only SUBMITTED procurement can generate receiving template. Current status: {procurement.status}",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        items = ProcurementItem.objects.filter(
            request=procurement
        ).select_related("raw_material", "raw_material__category")

        template = {
            "procurement_id": procurement.id,
            "target_date": procurement.target_date,
            "company": procurement.company.name,
            "status": procurement.status,
            "items": [
                {
                    "raw_material_id": item.raw_material.id,
                    "raw_material_name": item.raw_material.name,
                    "expected_quantity": float(item.purchase_quantity),
                    "category": item.raw_material.category.name if item.raw_material.category else None,
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

    On first receiving for a procurement:
    - Sets procurement status to CONFIRMED
    - Updates RawMaterial.default_supplier from procurement items

    Deadline: cannot create/update after target_date 23:59.

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
            return error_response(
                error=serializer.errors,
                message="Validation failed",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        # company_id = request.user.profile.company_id
        company_id = 1

        procurement = ProcurementRequest.objects.filter(
            id=data["procurement_id"],
            company_id=company_id,
        ).first()

        if not procurement:
            return error_response(
                error="Procurement request not found",
                message="Procurement request not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if procurement.status != "SUBMITTED":
            return error_response(
                error=f"Cannot create receiving: procurement status is {procurement.status}",
                message=f"Only SUBMITTED procurement can be received. Current status: {procurement.status}",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        # Deadline check: cannot receive after target_date 23:59
        deadline = datetime.combine(procurement.target_date, time(23, 59, 59))
        if timezone.is_aware(timezone.now()):
            deadline = timezone.make_aware(deadline)
        if timezone.now() > deadline:
            return error_response(
                error="Receiving deadline passed",
                message=f"Receiving deadline has passed ({procurement.target_date} 23:59)",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        proc_items_qs = ProcurementItem.objects.filter(request=procurement).select_related("supplier")
        proc_items_map = {pi.raw_material_id: pi for pi in proc_items_qs}

        incoming_raw_material_ids = {item["raw_material_id"] for item in data["items"]}
        valid_raw_material_ids = set(proc_items_map.keys())

        missing_ids = valid_raw_material_ids - incoming_raw_material_ids
        invalid_ids = incoming_raw_material_ids - valid_raw_material_ids
        if invalid_ids:
            return error_response(
                error=f"Some raw materials are not part of this procurement: {sorted(invalid_ids)}",
                message="Invalid raw_material_id in receiving items",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            receiving = ReceivingRecord.objects.create(
                procurement=procurement,
                company=procurement.company,
                notes=data.get("notes", ""),
                status="COMPLETED",
            )

            incoming_items_map = {
                item["raw_material_id"]: item
                for item in data["items"]
            }

            for raw_material_id, proc_item in proc_items_map.items():
                item_data = incoming_items_map.get(raw_material_id)

                if item_data:
                    actual_quantity = item_data["actual_quantity"]
                    notes = item_data.get("notes", "")
                else:
                    actual_quantity = 0
                    notes = ""

                ReceivingItem.objects.create(
                    receiving=receiving,
                    raw_material_id=raw_material_id,
                    expected_quantity=proc_item.purchase_quantity,
                    actual_quantity=actual_quantity,
                    notes=notes,
                )

            procurement.status = "CONFIRMED"
            procurement.save(update_fields=["status"])

            
            for pi in proc_items_qs:
                if pi.supplier_id:
                    RawMaterial.objects.filter(id=pi.raw_material_id).update(
                        default_supplier=pi.supplier
                    )

            from ..inventory_service import update_inventory_on_receiving_confirm
            updated_list, warnings = update_inventory_on_receiving_confirm(receiving)

        msg = "Receiving record created"

        if warnings:
            msg += " Inventory warnings: " + "; ".join(warnings)
        result = ReceivingRecordSerializer(receiving).data
        result["inventory_updates"] = updated_list

        # ⭐ 加在这里
        if missing_ids:
            result["warnings"] = [
                "Some items were not provided and defaulted to 0"
            ]

        return success_response(
            results=result,
            message=msg,
            http_status=status.HTTP_201_CREATED,
        )



class ReceivingDetailView(APIView):
    """
    GET /api/receiving/{id}/
    View receiving detail (actual vs expected comparison).
    """
    def get(self, request, pk):
        # company_id = request.user.profile.company_id
        company_id = 1
        
        receiving = ReceivingRecord.objects.filter(
            id=pk,
            company_id=company_id,
        ).prefetch_related("items__raw_material").first()

        if not receiving:
            return error_response(
                error="Receiving record not found",
                message="Receiving record not found",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReceivingRecordSerializer(receiving)
        return success_response(results=serializer.data)
