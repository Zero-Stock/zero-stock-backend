# core/serializers.py
from django.utils import timezone
from datetime import date
from rest_framework import serializers
from .models import (
    ClientCompany, DietCategory, RawMaterial, ProcessedMaterial,
    Dish, DishIngredient, Supplier, SupplierMaterial, MaterialCategory, RawMaterialYieldRate
)
from .views.yield_views import compute_effective_date

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCompany
        fields = ["id", "name", "code"]


class DietCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DietCategory
        fields = ["id", "name"]


# ---- Material Categories ----

class MaterialCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialCategory
        fields = ["id", "name"]


# ---- Raw Materials ----

class ProcessedMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessedMaterial
        fields = ["id", "method_name"]

class RawMaterialSerializer(serializers.ModelSerializer):
    specs = ProcessedMaterialSerializer(many=True, required=False)
    category_name = serializers.CharField(source="category.name", read_only=True)

    # write-only: accept on create/update, not returned directly
    yield_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, write_only=True
    )

    # read-only: returned in GET
    current_yield_rate = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RawMaterial
        fields = [
            "id", "name", "category", "category_name",
            "specs", "yield_rate", "current_yield_rate"
        ]

    # ---------- helpers ----------
    def _upsert_yield_rate(self, raw_material, yield_rate):
        """
        Store yield_rate into RawMaterialYieldRate with effective_date computed.
        Use update_or_create to avoid duplicate dirty rows when user clicks save twice.
        """
        if yield_rate is None:
            return

        now = timezone.localtime()
        eff = compute_effective_date(now)  # returns a date

        RawMaterialYieldRate.objects.update_or_create(
            raw_material=raw_material,
            effective_date=eff,
            defaults={"yield_rate": yield_rate},
        )

    def _upsert_specs(self, raw_material, specs_data):
        """
        Add missing processing methods only.
        - specs_data == None: do nothing (means client didn't send specs)
        - specs_data == []: treat as "send empty": still do nothing (we do NOT delete existing)
          (If you want "empty means clear all", tell me, we can change it.)
        """
        if specs_data is None:
            return

        seen = set()
        for spec in specs_data:
            method = (spec or {}).get("method_name")
            if not method:
                continue
            method = method.strip()
            if not method or method in seen:
                continue
            seen.add(method)

            ProcessedMaterial.objects.get_or_create(
                raw_material=raw_material,
                method_name=method
            )

    # ---------- DRF hooks ----------
    def create(self, validated_data):
        yield_rate = validated_data.pop("yield_rate", None)
        specs_data = validated_data.pop("specs", None)  # None means not provided

        rm = super().create(validated_data)

        self._upsert_yield_rate(rm, yield_rate)
        self._upsert_specs(rm, specs_data)

        return rm

    def update(self, instance, validated_data):
        yield_rate = validated_data.pop("yield_rate", None)
        specs_data = validated_data.pop("specs", None)

        # update base fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._upsert_yield_rate(instance, yield_rate)
        self._upsert_specs(instance, specs_data)

        return instance

    def get_current_yield_rate(self, obj):
        # timezone-safe "today"
        today = timezone.localdate()
        rec = (
            RawMaterialYieldRate.objects
            .filter(raw_material=obj, effective_date__lte=today)
            .order_by("-effective_date", "-id")
            .first()
        )
        return str(rec.yield_rate) if rec else "1.00"

   

# ---- Dishes & Recipes ----

class DishIngredientSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    processing_name = serializers.SerializerMethodField()

    class Meta:
        model = DishIngredient
        fields = ["id", "raw_material", "raw_material_name", "processing", "yield_rate", "net_quantity"]

    def get_processing_name(self, obj):
        return obj.processing.method_name if obj.processing else None


class DishIngredientWriteSerializer(serializers.Serializer):
    """For nested create/update of recipe ingredients"""
    raw_material = serializers.IntegerField()
    processing = serializers.IntegerField(required=False, allow_null=True, default=None)
    net_quantity = serializers.DecimalField(max_digits=8, decimal_places=3)


class DishSerializer(serializers.ModelSerializer):
    ingredients = DishIngredientSerializer(many=True, read_only=True)
    ingredients_write = DishIngredientWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Dish
        fields = ["id", "name", "seasonings", "cooking_method", "ingredients", "ingredients_write"]

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients_write', [])
        dish = Dish.objects.create(**validated_data)
        for ing in ingredients_data:
            DishIngredient.objects.create(
                dish=dish,
                raw_material_id=ing['raw_material'],
                processing_id=ing.get('processing'),
                net_quantity=ing['net_quantity']
            )
        return dish

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients_write', None)

        instance.name = validated_data.get('name', instance.name)
        instance.seasonings = validated_data.get('seasonings', instance.seasonings)
        instance.cooking_method = validated_data.get('cooking_method', instance.cooking_method)
        instance.save()

        if ingredients_data is not None:
            instance.ingredients.all().delete()
            for ing in ingredients_data:
                DishIngredient.objects.create(
                    dish=instance,
                    raw_material_id=ing['raw_material'],
                    processing_id=ing.get('processing'),
                    net_quantity=ing['net_quantity']
                )
        return instance


class DishPrintSerializer(serializers.ModelSerializer):
    """用于打印/导出菜谱，原料格式化为字符串"""
    ingredients_text = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = ["id", "name", "ingredients_text", "seasonings", "cooking_method"]

    def get_ingredients_text(self, obj):
        parts = []
        for ing in obj.ingredients.select_related('raw_material', 'processing').all():
            name = ing.raw_material.name
            method = f"[{ing.processing.method_name}]" if ing.processing else ""
            weight = f"{ing.net_quantity * 1000:g}g"
            parts.append(f"{name}{method}{weight}")
        return "、".join(parts)


# ---- Diet Dishes sub-resource ----

class DietDishesSerializer(serializers.Serializer):
    """For POST /api/diets/{id}/dishes/ to batch-assign dishes to a diet"""
    dish_ids = serializers.ListField(child=serializers.IntegerField())


# ---- Suppliers ----

class SupplierMaterialSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)

    class Meta:
        model = SupplierMaterial
        fields = ["id", "raw_material", "raw_material_name", "unit_name", "kg_per_unit", "price", "notes"]


class SupplierSerializer(serializers.ModelSerializer):
    materials = SupplierMaterialSerializer(many=True, read_only=True)

    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "address", "materials"]