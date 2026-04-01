# operations/serializers.py
from rest_framework import serializers
from .models import (
    ClientCompanyRegion, DailyCensus, WeeklyMenu,
    ProcurementRequest, ProcurementItem,
    ReceivingRecord, ReceivingItem,
    DeliveryOrder, DeliveryItem
)


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCompanyRegion
        fields = ["id", "name", "company"]
        read_only_fields = ["id", "company"]
    def validate(self, attrs):
        """
        Prevent duplicate region name under the same company.
        """
        company_id = self.context.get("company_id")
        name = attrs.get("name")

        if company_id and name:
            exists = ClientCompanyRegion.objects.filter(company_id=company_id, name=name).exists()
            if exists:
                raise serializers.ValidationError({"name": "This region already exists in this company."})

        return attrs

class DailyCensusSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    diet_category_name = serializers.CharField(source="diet_category.name", read_only=True)

    class Meta:
        model = DailyCensus
        fields = [
            "id",
            "company",
            "date",
            "region",
            "region_name",
            "diet_category",
            "diet_category_name",
            "count",
        ]
        read_only_fields = ["id", "company"]


class DailyCensusBatchItemSerializer(serializers.Serializer):
    region_id = serializers.IntegerField()
    diet_category_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=0)


class DailyCensusBatchSerializer(serializers.Serializer):
    date = serializers.DateField()
    company_id = serializers.IntegerField(required=False)
    items = DailyCensusBatchItemSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("This list may not be empty.")

        seen = set()
        for it in items:
            key = (it["region_id"], it["diet_category_id"])
            if key in seen:
                raise serializers.ValidationError(
                    "Duplicate (region_id, diet_category_id) found in items."
                )
            seen.add(key)
        return items

class ProcurementItemSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source="raw_material.name", read_only=True)
    category = serializers.CharField(source="raw_material.category.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)

    # Computed dual-unit fields
    demand_unit_qty = serializers.SerializerMethodField()
    stock_unit_qty = serializers.SerializerMethodField()
    purchase_unit_qty = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementItem
        fields = [
            "id",
            "raw_material",
            "raw_material_name",
            "category",
            "demand_quantity",
            "stock_quantity",
            "purchase_quantity",
            "demand_unit_qty",
            "stock_unit_qty",
            "purchase_unit_qty",
            "supplier",
            "supplier_name",
            "supplier_unit_name",
            "supplier_kg_per_unit",
            "supplier_price",
            "notes",
        ]

    def _to_unit(self, kg_value, kg_per_unit, ceiling=False):
        """Convert kg to supplier unit. Optionally apply ceiling."""
        if not kg_per_unit or kg_per_unit <= 0:
            return None
        import math
        result = float(kg_value) / float(kg_per_unit)
        return math.ceil(result) if ceiling else round(result, 2)

    def get_demand_unit_qty(self, obj):
        return self._to_unit(obj.demand_quantity, obj.supplier_kg_per_unit)

    def get_stock_unit_qty(self, obj):
        return self._to_unit(obj.stock_quantity, obj.supplier_kg_per_unit)

    def get_purchase_unit_qty(self, obj):
        return self._to_unit(obj.purchase_quantity, obj.supplier_kg_per_unit, ceiling=True)


class ProcurementRequestSerializer(serializers.ModelSerializer):
    items = ProcurementItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProcurementRequest
        fields = [
            "id",
            "company",
            "target_date",
            "status",
            "created_at",
            "items",
        ]
        read_only_fields = ["id", "company", "status", "created_at", "items"]

class ProcurementGenerateSerializer(serializers.Serializer):
    date = serializers.DateField()


# ---- Weekly Menu ----

class WeeklyMenuDishSerializer(serializers.Serializer):
    """Serializer for WeeklyMenuDish through table entries"""
    dish_id = serializers.IntegerField(source='dish.id')
    dish_name = serializers.CharField(source='dish.name', read_only=True)
    quantity = serializers.IntegerField()


class WeeklyMenuSerializer(serializers.ModelSerializer):
    diet_category_name = serializers.CharField(source='diet_category.name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    meal_display = serializers.CharField(source='get_meal_time_display', read_only=True)
    dish_names = serializers.SerializerMethodField()
    dishes_detail = serializers.SerializerMethodField()

    class Meta:
        model = WeeklyMenu
        fields = [
            "id", "company", "company_name",
            "diet_category", "diet_category_name",
            "day_of_week", "day_display",
            "meal_time", "meal_display",
            "dishes", "dish_names", "dishes_detail",
        ]
        read_only_fields = ["dishes"]

    def get_dish_names(self, obj):
        return [d.name for d in obj.dishes.all()]

    def get_dishes_detail(self, obj):
        from .models import WeeklyMenuDish
        menu_dishes = WeeklyMenuDish.objects.filter(menu=obj).select_related('dish')
        return [
            {"dish_id": md.dish_id, "dish_name": md.dish.name, "quantity": md.quantity}
            for md in menu_dishes
        ]


class WeeklyMenuBatchItemSerializer(serializers.Serializer):
    company = serializers.IntegerField()
    diet_category = serializers.IntegerField()
    day_of_week = serializers.IntegerField()
    meal_time = serializers.CharField()
    # Accept either plain list of IDs [1,2,3] or list of objects [{"dish_id":1,"quantity":2}]
    dishes = serializers.ListField()


class WeeklyMenuBatchSerializer(serializers.Serializer):
    menus = WeeklyMenuBatchItemSerializer(many=True)

    def validate_menus(self, menus):
        valid_meal_times = {"B", "L", "D"}

        for menu in menus:
            meal_time = menu.get("meal_time")
            if meal_time not in valid_meal_times:
                raise serializers.ValidationError(
                    f"Invalid meal_time: {meal_time}"
                )

            dishes = menu.get("dishes", [])
            for d in dishes:
                if isinstance(d, dict):
                    quantity = d.get("quantity", 1)
                    if quantity <= 0:
                        raise serializers.ValidationError(
                            "Dish quantity must be greater than 0."
                        )

        return menus

    def create(self, validated_data):
        from .models import WeeklyMenuDish

        results = []
        for item in validated_data["menus"]:
            menu, _ = WeeklyMenu.objects.update_or_create(
                company_id=item["company"],
                diet_category_id=item["diet_category"],
                day_of_week=item["day_of_week"],
                meal_time=item["meal_time"],
            )

            WeeklyMenuDish.objects.filter(menu=menu).delete()

            for d in item["dishes"]:
                if isinstance(d, dict):
                    dish_id = d.get("dish_id") or d.get("id")
                    quantity = d.get("quantity", 1)
                else:
                    dish_id = int(d)
                    quantity = 1

                WeeklyMenuDish.objects.create(
                    menu=menu,
                    dish_id=dish_id,
                    quantity=quantity,
                )

            results.append(menu)

        return results


# ---- Receiving ----

class ReceivingItemSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source="raw_material.name", read_only=True)
    unit = serializers.CharField(source="raw_material.unit", read_only=True)
    spec = serializers.CharField(source="raw_material.spec", read_only=True)
    difference = serializers.SerializerMethodField()

    class Meta:
        model = ReceivingItem
        fields = [
            "id", "raw_material", "raw_material_name",
            "expected_quantity", "actual_quantity",
            "unit", "spec", "difference", "notes",
        ]

    def get_difference(self, obj):
        return float(obj.actual_quantity - obj.expected_quantity)


class ReceivingCreateItemSerializer(serializers.Serializer):
    raw_material_id = serializers.IntegerField()
    actual_quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

class ReceivingRecordSerializer(serializers.ModelSerializer):
    items = ReceivingItemSerializer(many=True, read_only=True)

    class Meta:
        model = ReceivingRecord
        fields = ["id", "procurement", "company", "received_date", "status", "notes", "items"]
        read_only_fields = ["id", "company", "received_date"]

class ReceivingCreateSerializer(serializers.Serializer):
    """For POST /api/receiving/ - record actual received quantities"""
    procurement_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = ReceivingCreateItemSerializer(many=True)

    def validate_items(self, items):
        seen = set()
        for item in items:
            raw_material_id = item["raw_material_id"]
            if raw_material_id in seen:
                raise serializers.ValidationError(
                    f"Duplicate raw_material_id found: {raw_material_id}"
                )
            seen.add(raw_material_id)

        return items


# ---- Processing ----
class ProcessingGenerateSerializer(serializers.Serializer):
    date = serializers.DateField()

class ProcessingSearchSerializer(serializers.Serializer):
    date = serializers.DateField()
    material_id = serializers.IntegerField(required=False)


# ---- Delivery ----

class DeliveryItemSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    diet_category_name = serializers.CharField(source="diet_category.name", read_only=True)

    class Meta:
        model = DeliveryItem
        fields = [
            "id", "region", "region_name",
            "diet_category", "diet_category_name", "count",
        ]


class DeliveryOrderSerializer(serializers.ModelSerializer):
    items = DeliveryItemSerializer(many=True, read_only=True)
    meal_display = serializers.CharField(source="get_meal_time_display", read_only=True)

    class Meta:
        model = DeliveryOrder
        fields = [
            "id", "company", "target_date",
            "meal_time", "meal_display",
            "created_at", "items",
        ]
        read_only_fields = ["id", "company", "created_at"]


class DeliveryGenerateSerializer(serializers.Serializer):
    date = serializers.DateField()
    meal_time = serializers.ChoiceField(choices=['B', 'L', 'D'])

class DeliveryUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=0)


class DeliveryUpdateSerializer(serializers.Serializer):
    items = DeliveryUpdateItemSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("items cannot be empty.")

        seen = set()
        for item in items:
            if item["id"] in seen:
                raise serializers.ValidationError(
                    f"Duplicate item id: {item['id']}"
                )
            seen.add(item["id"])

        return items