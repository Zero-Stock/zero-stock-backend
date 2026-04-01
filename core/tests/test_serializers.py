# -*- coding: utf-8 -*-
"""
core/tests/test_serializers.py
Serializer layer unit tests.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.models import (
    DietCategory,
    Dish,
    DishIngredient,
    MaterialCategory,
    ProcessedMaterial,
    RawMaterial,
    RawMaterialYieldRate,
    Supplier,
    SupplierMaterial,
)
from core.serializers import (
    DishPrintSerializer,
    DishSerializer,
    MaterialCategorySerializer,
    RawMaterialSerializer,
    SupplierMaterialSerializer,
    SupplierSerializer,
)


class SerializerTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = MaterialCategory.objects.create(name="Fresh")
        cls.material = RawMaterial.objects.create(name="Potato", category=cls.category)
        cls.diet = DietCategory.objects.create(name="Standard A")


class MaterialCategorySerializerTest(SerializerTestBase):
    def test_serialize(self):
        s = MaterialCategorySerializer(self.category)
        self.assertEqual(s.data["name"], "Fresh")
        self.assertIn("id", s.data)

    def test_create(self):
        s = MaterialCategorySerializer(data={"name": "Frozen"})
        self.assertTrue(s.is_valid())
        obj = s.save()
        self.assertEqual(obj.name, "Frozen")

    def test_duplicate_name_rejected(self):
        s = MaterialCategorySerializer(data={"name": "Fresh"})
        self.assertFalse(s.is_valid())


class RawMaterialSerializerTest(SerializerTestBase):
    def test_serialize_includes_category_name(self):
        s = RawMaterialSerializer(self.material)
        self.assertEqual(s.data["category_name"], "Fresh")

    def test_create_basic(self):
        s = RawMaterialSerializer(data={"name": "Tomato", "category": self.category.id})
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertEqual(obj.name, "Tomato")

    def test_create_with_specs(self):
        data = {
            "name": "Carrot",
            "category": self.category.id,
            "specs": [{"method_name": "Shredded"}, {"method_name": "Diced"}],
        }
        s = RawMaterialSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertEqual(obj.specs.count(), 2)

    def test_create_with_yield_rate(self):
        data = {
            "name": "Onion",
            "category": self.category.id,
            "yield_rate": "0.85",
        }
        s = RawMaterialSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertTrue(
            RawMaterialYieldRate.objects.filter(raw_material=obj).exists()
        )

    def test_update_with_specs_replaces_existing(self):
        ProcessedMaterial.objects.create(
            raw_material=self.material,
            method_name="Sliced",
        )

        serializer = RawMaterialSerializer(
            self.material,
            data={
                "name": self.material.name,
                "category": self.category.id,
                "specs": [{"method_name": "Diced"}],
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.material.refresh_from_db()
        self.assertEqual(self.material.specs.count(), 1)
        self.assertTrue(self.material.specs.filter(method_name="Diced").exists())
        self.assertFalse(self.material.specs.filter(method_name="Sliced").exists())

    def test_current_yield_rate_default(self):
        mat = RawMaterial.objects.create(name="NoYieldMat", category=self.category)
        s = RawMaterialSerializer(mat)
        self.assertEqual(s.data["current_yield_rate"], "1.00")

    def test_current_yield_rate_uses_effective(self):
        today = timezone.localdate()
        RawMaterialYieldRate.objects.create(
            raw_material=self.material,
            yield_rate=Decimal("0.75"),
            effective_date=today - timedelta(days=10),
        )
        RawMaterialYieldRate.objects.create(
            raw_material=self.material,
            yield_rate=Decimal("0.85"),
            effective_date=today - timedelta(days=1),
        )
        RawMaterialYieldRate.objects.create(
            raw_material=self.material,
            yield_rate=Decimal("0.99"),
            effective_date=today + timedelta(days=30),
        )
        s = RawMaterialSerializer(self.material)
        self.assertEqual(s.data["current_yield_rate"], "0.85")

    def test_duplicate_specs_ignored(self):
        data = {
            "name": "Lettuce",
            "category": self.category.id,
            "specs": [
                {"method_name": "Washed"},
                {"method_name": "Washed"},
            ],
        }
        s = RawMaterialSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertEqual(obj.specs.count(), 1)


class DishSerializerTest(SerializerTestBase):
    def test_create_dish_with_ingredients(self):
        data = {
            "name": "Stir Fry Potato",
            "seasonings": "salt, soy",
            "cooking_method": "stir fry",
            "ingredients_write": [
                {"raw_material": self.material.id, "net_quantity": "0.500"},
            ],
        }
        s = DishSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        dish = s.save()
        self.assertEqual(dish.name, "Stir Fry Potato")
        self.assertEqual(dish.ingredients.count(), 1)
        ing = dish.ingredients.first()
        self.assertEqual(ing.raw_material, self.material)
        self.assertEqual(ing.net_quantity, Decimal("0.500"))

    def test_create_dish_without_ingredients(self):
        data = {"name": "White Rice"}
        s = DishSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        dish = s.save()
        self.assertEqual(dish.ingredients.count(), 0)

    def test_update_replaces_ingredients(self):
        dish = Dish.objects.create(name="Original Dish")
        DishIngredient.objects.create(
            dish=dish, raw_material=self.material, net_quantity=Decimal("1.000")
        )
        mat2 = RawMaterial.objects.create(name="Tomato", category=self.category)
        s = DishSerializer(
            dish,
            data={
                "ingredients_write": [
                    {"raw_material": mat2.id, "net_quantity": "2.000"},
                ],
            },
            partial=True,
        )
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertEqual(dish.ingredients.count(), 1)
        self.assertEqual(dish.ingredients.first().raw_material, mat2)

    def test_update_without_ingredients_keeps_existing(self):
        dish = Dish.objects.create(name="Keep Recipe Dish")
        DishIngredient.objects.create(
            dish=dish, raw_material=self.material, net_quantity=Decimal("1.000")
        )
        s = DishSerializer(dish, data={"name": "Renamed Dish"}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertEqual(dish.name, "Renamed Dish")
        self.assertEqual(dish.ingredients.count(), 1)

    def test_create_with_processing(self):
        pm = ProcessedMaterial.objects.create(
            raw_material=self.material, method_name="Peeled"
        )
        data = {
            "name": "Peeled Potato",
            "ingredients_write": [
                {
                    "raw_material": self.material.id,
                    "processing": pm.id,
                    "net_quantity": "0.300",
                },
            ],
        }
        s = DishSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        dish = s.save()
        ing = dish.ingredients.first()
        self.assertEqual(ing.processing, pm)


class DishPrintSerializerTest(SerializerTestBase):
    def test_ingredients_text_format(self):
        dish = Dish.objects.create(name="Tomato Egg")
        mat_tomato = RawMaterial.objects.create(name="Tomato", category=self.category)
        DishIngredient.objects.create(
            dish=dish, raw_material=mat_tomato, net_quantity=Decimal("0.200")
        )
        DishIngredient.objects.create(
            dish=dish, raw_material=self.material, net_quantity=Decimal("0.100")
        )
        s = DishPrintSerializer(dish)
        text = s.data["ingredients_text"]
        self.assertIn("200", text)
        self.assertIn("100", text)
        self.assertIn("g", text)

    def test_ingredients_text_with_processing(self):
        dish = Dish.objects.create(name="Shredded Potato")
        pm = ProcessedMaterial.objects.create(
            raw_material=self.material, method_name="Shredded"
        )
        DishIngredient.objects.create(
            dish=dish,
            raw_material=self.material,
            processing=pm,
            net_quantity=Decimal("0.500"),
        )
        s = DishPrintSerializer(dish)
        text = s.data["ingredients_text"]
        self.assertIn("[Shredded]", text)
        self.assertIn("500", text)
        self.assertIn("g", text)


class SupplierSerializerTest(SerializerTestBase):
    def test_create(self):
        s = SupplierSerializer(data={"name": "New Supplier", "phone": "12345678"})
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertEqual(obj.name, "New Supplier")

    def test_materials_read_only(self):
        supplier = Supplier.objects.create(name="S1")
        SupplierMaterial.objects.create(
            supplier=supplier, raw_material=self.material
        )
        s = SupplierSerializer(supplier)
        self.assertEqual(len(s.data["materials"]), 1)
        self.assertEqual(s.data["materials"][0]["raw_material_name"], "Potato")


class SupplierMaterialSerializerTest(SerializerTestBase):
    def test_create(self):
        supplier = Supplier.objects.create(name="SM Supplier")
        data = {
            "supplier": supplier.id,
            "raw_material": self.material.id,
            "unit_name": "box",
            "kg_per_unit": "10.00",
            "price": "50.00",
        }
        s = SupplierMaterialSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertEqual(obj.unit_name, "box")

    def test_read_only_names(self):
        supplier = Supplier.objects.create(name="ReadOnlyTest")
        sm = SupplierMaterial.objects.create(
            supplier=supplier, raw_material=self.material
        )
        s = SupplierMaterialSerializer(sm)
        self.assertEqual(s.data["supplier_name"], "ReadOnlyTest")
        self.assertEqual(s.data["raw_material_name"], "Potato")
