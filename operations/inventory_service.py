# operations/inventory_service.py
"""
Inventory update service.
Called when a receiving record is confirmed to auto-update material stock.

Formula: new_stock = old_stock + actual_received - theoretical_usage
If new_stock < 0, set to 0 and record a warning.
"""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from core.models import RawMaterial, DishIngredient, RawMaterialYieldRate
from .models import (
    ReceivingRecord, ReceivingItem,
    DailyCensus, WeeklyMenu, WeeklyMenuDish,
)


def _get_yield_rate(raw_material_id: int, target_date):
    """Return the effective yield rate for a material on a given date."""
    rec = (
        RawMaterialYieldRate.objects
        .filter(raw_material_id=raw_material_id, effective_date__lte=target_date)
        .order_by("-effective_date", "-id")
        .first()
    )
    return rec.yield_rate if rec else Decimal("1.00")


def _weekday_1_to_7(date_obj):
    """Monday=1 … Sunday=7 (ISO weekday)."""
    return date_obj.weekday() + 1


def calculate_theoretical_usage(company_id: int, target_date) -> dict:
    """
    Calculate theoretical raw material usage for a given company + date.
    Returns: {raw_material_id: Decimal(gross_kg), ...}

    Logic mirrors ProcurementGenerateView: census × menu dishes × recipe / yield.
    """
    census_qs = DailyCensus.objects.filter(company_id=company_id, date=target_date)
    if not census_qs.exists():
        return {}

    diet_counts = {}
    for row in census_qs.values("diet_category_id").annotate(total=Sum("count")):
        diet_counts[row["diet_category_id"]] = int(row["total"] or 0)

    weekday = _weekday_1_to_7(target_date)
    meal_types = ["B", "L", "D"]
    totals = defaultdict(Decimal)  # raw_material_id -> gross_kg

    def get_dishes_for(diet_id: int, meal_type: str):
        """Returns list of (dish, quantity) tuples."""
        wm = WeeklyMenu.objects.filter(
            company_id=company_id,
            diet_category_id=diet_id,
            day_of_week=weekday,
            meal_time=meal_type,
        ).first()
        if wm:
            menu_dishes = WeeklyMenuDish.objects.filter(menu=wm).select_related("dish")
            return [(md.dish, md.quantity) for md in menu_dishes]
        return []

    for diet_id, people in diet_counts.items():
        if people <= 0:
            continue
        for meal in meal_types:
            dishes = get_dishes_for(diet_id, meal)
            for dish, dish_qty in dishes:
                recipe_rows = (
                    DishIngredient.objects
                    .filter(dish_id=dish.id)
                    .select_related("raw_material")
                )
                for ing in recipe_rows:
                    yield_rate = _get_yield_rate(ing.raw_material_id, target_date)
                    if yield_rate <= 0:
                        yield_rate = Decimal("1.00")
                    net_per_serv = ing.net_quantity * dish_qty
                    total_net = Decimal(people) * net_per_serv
                    total_gross = total_net / yield_rate
                    totals[ing.raw_material_id] += total_gross

    return dict(totals)


def update_inventory_on_receiving_confirm(receiving_record: ReceivingRecord):
    """
    Update material stock when a receiving record is confirmed.

    new_stock = old_stock + actual_received - theoretical_usage
    If new_stock < 0, set to 0 and add a warning.

    Returns:
        (updated_list, warnings)
        updated_list: [{"material_id", "name", "old_stock", "new_stock"}, ...]
        warnings: [str, ...]
    """
    procurement = receiving_record.procurement
    company_id = procurement.company_id
    target_date = procurement.target_date

    # 1. Gather actual received quantities from ReceivingItems
    # TODO: 当同事完成收货单确认功能后（手动确认 or 23:59 自动锁定），
    #       从已确认的收货单获取实际收货量。
    #       目前直接使用当前 ReceivingRecord 的 ReceivingItem.actual_quantity。
    received_items = ReceivingItem.objects.filter(
        receiving=receiving_record
    )
    received_qty = {}  # raw_material_id -> Decimal
    for item in received_items:
        received_qty[item.raw_material_id] = (
            received_qty.get(item.raw_material_id, Decimal("0"))
            + item.actual_quantity
        )

    # 2. Calculate theoretical usage
    usage = calculate_theoretical_usage(company_id, target_date)

    # 3. Collect all affected material IDs
    all_material_ids = set(received_qty.keys()) | set(usage.keys())
    if not all_material_ids:
        return [], []

    materials = {
        m.id: m
        for m in RawMaterial.objects.filter(id__in=all_material_ids)
    }

    updated_list = []
    warnings = []

    for mid in all_material_ids:
        mat = materials.get(mid)
        if not mat:
            continue

        old_stock = mat.stock or Decimal("0")
        actual_received = received_qty.get(mid, Decimal("0"))
        theoretical_used = usage.get(mid, Decimal("0"))

        new_stock = old_stock + actual_received - theoretical_used

        if new_stock < 0:
            warnings.append(
                f"{mat.name}: 库存将变为 {new_stock:.2f} kg，暂置为 0"
            )
            new_stock = Decimal("0")

        mat.stock = new_stock
        mat.save(update_fields=["stock"])

        updated_list.append({
            "material_id": mid,
            "name": mat.name,
            "old_stock": str(old_stock),
            "new_stock": str(mat.stock),
        })

    return updated_list, warnings
