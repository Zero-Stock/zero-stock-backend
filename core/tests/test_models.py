# -*- coding: utf-8 -*-
"""
core/tests/test_models.py
Model layer unit tests.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from core.models import (
    ClientCompany,
    DietCategory,
    Dish,
    DishIngredient,
    MaterialCategory,
    ProcessedMaterial,
    RawMaterial,
    RawMaterialYieldRate,
    Supplier,
    SupplierMaterial,
    UserProfile,
)


class CoreModelTestBase(TestCase):
    """Shared fixtures for core model tests."""

    @classmethod
    def setUpTestData(cls):
        cls.company = ClientCompany.objects.create(name="Test Hospital", code="HOSP01")
        cls.category = MaterialCategory.objects.create(name="Fresh")
        cls.material = RawMaterial.objects.create(name="Potato", category=cls.category)
        cls.diet = DietCategory.objects.create(name="Standard A")
        cls.supplier = Supplier.objects.create(name="Fresh Farms")


class ClientCompanyModelTest(CoreModelTestBase):
    def test_str(self):
        self.assertEqual(str(self.company), "Test Hospital")

    def test_code_unique(self):
        with self.assertRaises(IntegrityError):
            ClientCompany.objects.create(name="Other", code="HOSP01")

    def test_created_at_auto(self):
        self.assertIsNotNone(self.company.created_at)


class UserProfileModelTest(CoreModelTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="testuser", password="pass1234")
        cls.profile = UserProfile.objects.create(
            user=cls.user, company=cls.company, role="RW"
        )

    def test_str(self):
        self.assertIn("testuser", str(self.profile))
        self.assertIn("HOSP01", str(self.profile))
        self.assertIn("Read/Write", str(self.profile))

    def test_default_role(self):
        user2 = User.objects.create_user(username="viewer", password="pass1234")
        profile2 = UserProfile.objects.create(user=user2, company=self.company)
        self.assertEqual(profile2.role, "RO")


class MaterialCategoryModelTest(CoreModelTestBase):
    def test_str(self):
        self.assertEqual(str(self.category), "Fresh")

    def test_name_unique(self):
        with self.assertRaises(IntegrityError):
            MaterialCategory.objects.create(name="Fresh")


class RawMaterialModelTest(CoreModelTestBase):
    def test_str(self):
        self.assertEqual(str(self.material), "Potato")

    def test_name_unique(self):
        with self.assertRaises(IntegrityError):
            RawMaterial.objects.create(name="Potato", category=self.category)

    def test_category_protect(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.category.delete()


class RawMaterialYieldRateModelTest(CoreModelTestBase):
    def test_unique_together(self):
        eff = date(2026, 3, 1)
        RawMaterialYieldRate.objects.create(
            raw_material=self.material, yield_rate=Decimal("0.80"), effective_date=eff
        )
        with self.assertRaises(IntegrityError):
            RawMaterialYieldRate.objects.create(
                raw_material=self.material,
                yield_rate=Decimal("0.90"),
                effective_date=eff,
            )

    def test_ordering(self):
        r1 = RawMaterialYieldRate.objects.create(
            raw_material=self.material,
            yield_rate=Decimal("0.80"),
            effective_date=date(2026, 1, 1),
        )
        r2 = RawMaterialYieldRate.objects.create(
            raw_material=self.material,
            yield_rate=Decimal("0.90"),
            effective_date=date(2026, 6, 1),
        )
        rates = list(
            RawMaterialYieldRate.objects.filter(raw_material=self.material)
        )
        self.assertEqual(rates[0], r2)
        self.assertEqual(rates[1], r1)

    def test_str(self):
        r = RawMaterialYieldRate.objects.create(
            raw_material=self.material,
            yield_rate=Decimal("0.80"),
            effective_date=date(2026, 3, 1),
        )
        s = str(r)
        self.assertIn("Potato", s)
        self.assertIn("0.80", s)


class ProcessedMaterialModelTest(CoreModelTestBase):
    def test_str(self):
        pm = ProcessedMaterial.objects.create(
            raw_material=self.material, method_name="Peeled"
        )
        self.assertIn("Potato", str(pm))
        self.assertIn("Peeled", str(pm))

    def test_unique_together(self):
        ProcessedMaterial.objects.create(
            raw_material=self.material, method_name="Sliced"
        )
        with self.assertRaises(IntegrityError):
            ProcessedMaterial.objects.create(
                raw_material=self.material, method_name="Sliced"
            )


class DishModelTest(CoreModelTestBase):
    def test_str(self):
        dish = Dish.objects.create(name="Tomato Egg")
        self.assertEqual(str(dish), "Tomato Egg")

    def test_name_unique(self):
        Dish.objects.create(name="Unique Dish")
        with self.assertRaises(IntegrityError):
            Dish.objects.create(name="Unique Dish")

    def test_allowed_diets_m2m(self):
        dish = Dish.objects.create(name="Test Dish")
        diet2 = DietCategory.objects.create(name="Diabetic")
        dish.allowed_diets.add(self.diet, diet2)
        self.assertEqual(dish.allowed_diets.count(), 2)


class DishIngredientModelTest(CoreModelTestBase):
    def test_str_without_processing(self):
        dish = Dish.objects.create(name="Stir Fry Potato")
        ing = DishIngredient.objects.create(
            dish=dish, raw_material=self.material, net_quantity=Decimal("0.500")
        )
        s = str(ing)
        self.assertIn("Stir Fry Potato", s)
        self.assertIn("Potato", s)

    def test_str_with_processing(self):
        dish = Dish.objects.create(name="Shredded Potato")
        pm = ProcessedMaterial.objects.create(
            raw_material=self.material, method_name="Shredded"
        )
        ing = DishIngredient.objects.create(
            dish=dish,
            raw_material=self.material,
            processing=pm,
            net_quantity=Decimal("0.500"),
        )
        s = str(ing)
        self.assertIn("Shredded", s)


class SupplierModelTest(CoreModelTestBase):
    def test_str(self):
        self.assertEqual(str(self.supplier), "Fresh Farms")

    def test_name_unique(self):
        with self.assertRaises(IntegrityError):
            Supplier.objects.create(name="Fresh Farms")


class SupplierMaterialModelTest(CoreModelTestBase):
    def test_str(self):
        sm = SupplierMaterial.objects.create(
            supplier=self.supplier,
            raw_material=self.material,
            unit_name="box",
            kg_per_unit=Decimal("10.00"),
        )
        s = str(sm)
        self.assertIn("Fresh Farms", s)
        self.assertIn("Potato", s)
        self.assertIn("box", s)

    def test_unique_together(self):
        SupplierMaterial.objects.create(
            supplier=self.supplier, raw_material=self.material
        )
        with self.assertRaises(IntegrityError):
            SupplierMaterial.objects.create(
                supplier=self.supplier, raw_material=self.material
            )

    def test_default_values(self):
        sm = SupplierMaterial.objects.create(
            supplier=self.supplier, raw_material=self.material
        )
        self.assertEqual(sm.unit_name, "kg")
        self.assertEqual(sm.kg_per_unit, Decimal("1.00"))
