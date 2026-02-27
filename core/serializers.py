# core/serializers.py
from rest_framework import serializers
from .models import (
    ClientCompany, DietCategory, RawMaterial, ProcessedMaterial,
    Dish, DishIngredient, Supplier, SupplierMaterial, MaterialCategory
)


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
        fields = ["id", "method_name", "yield_rate"]


class RawMaterialSerializer(serializers.ModelSerializer):
    specs = ProcessedMaterialSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = RawMaterial
        fields = ["id", "name", "category", "category_name", "specs"]


# ---- Dishes & Recipes ----

class DishIngredientSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    processing_name = serializers.SerializerMethodField()
    yield_rate = serializers.SerializerMethodField()

    class Meta:
        model = DishIngredient
        fields = ["id", "raw_material", "raw_material_name", "processing", "processing_name", "yield_rate", "net_quantity"]

    def get_processing_name(self, obj):
        return obj.processing.method_name if obj.processing else None

    def get_yield_rate(self, obj):
        return float(obj.processing.yield_rate) if obj.processing else None


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