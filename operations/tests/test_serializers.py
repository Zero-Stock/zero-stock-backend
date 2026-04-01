# -*- coding: utf-8 -*-
"""operations/tests/test_serializers.py"""
from django.test import TestCase

from core.models import ClientCompany, DietCategory, Dish
from operations.models import ClientCompanyRegion, WeeklyMenu, WeeklyMenuDish
from operations.serializers import (
    DailyCensusBatchSerializer,
    RegionSerializer,
    WeeklyMenuBatchSerializer,
    WeeklyMenuSerializer,
)


class OpsSerializerTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = ClientCompany.objects.create(
            name="Test Hospital",
            code="HOSP01",
        )
        cls.diet = DietCategory.objects.create(name="Standard A")
        cls.region = ClientCompanyRegion.objects.create(
            company=cls.company,
            name="East Wing",
        )
        cls.dish1 = Dish.objects.create(name="Tomato Egg")
        cls.dish2 = Dish.objects.create(name="Pepper Pork")


class RegionSerializerTest(OpsSerializerTestBase):
    def test_serializer(self):
        s = RegionSerializer(self.region)
        self.assertEqual(s.data["name"], "East Wing")

    def test_duplicate_name_rejected(self):
        s = RegionSerializer(
            data={"name": "East Wing"},
            context={"company_id": self.company.id},
        )
        self.assertFalse(s.is_valid(), s.errors)

    def test_different_company_accepted(self):
        co2 = ClientCompany.objects.create(name="Other", code="OTHER01")
        s = RegionSerializer(
            data={"name": "East Wing"},
            context={"company_id": co2.id},
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_empty_name_rejected(self):
        s = RegionSerializer(
            data={"name": ""},
            context={"company_id": self.company.id},
        )
        self.assertFalse(s.is_valid(), s.errors)


class DailyCensusBatchSerializerTest(OpsSerializerTestBase):
    def test_valid_batch(self):
        diet2 = DietCategory.objects.create(name="Diabetic")
        data = {
            "date": "2026-03-01",
            "items": [
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": 50,
                },
                {
                    "region_id": self.region.id,
                    "diet_category_id": diet2.id,
                    "count": 10,
                },
            ],
        }
        s = DailyCensusBatchSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_duplicate_pair_rejected(self):
        data = {
            "date": "2026-03-01",
            "items": [
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": 50,
                },
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": 30,
                },
            ],
        }
        s = DailyCensusBatchSerializer(data=data)
        self.assertFalse(s.is_valid(), s.errors)

    def test_negative_count_rejected(self):
        data = {
            "date": "2026-03-01",
            "items": [
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": -5,
                },
            ],
        }
        s = DailyCensusBatchSerializer(data=data)
        self.assertFalse(s.is_valid(), s.errors)

    def test_missing_date_rejected(self):
        data = {
            "items": [
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": 50,
                },
            ],
        }
        s = DailyCensusBatchSerializer(data=data)
        self.assertFalse(s.is_valid(), s.errors)

    def test_empty_items_rejected(self):
        data = {
            "date": "2026-03-01",
            "items": [],
        }
        s = DailyCensusBatchSerializer(data=data)
        self.assertFalse(s.is_valid(), s.errors)


class WeeklyMenuSerializerTest(OpsSerializerTestBase):
    def test_serialize_fields(self):
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=2)

        s = WeeklyMenuSerializer(menu)
        self.assertEqual(s.data["day_display"], "Monday")
        self.assertEqual(s.data["meal_display"], "Lunch")
        self.assertEqual(len(s.data["dishes_detail"]), 1)


class WeeklyMenuBatchSerializerTest(OpsSerializerTestBase):
    def test_batch_with_plain_ids(self):
        data = {
            "menus": [
                {
                    "company": self.company.id,
                    "diet_category": self.diet.id,
                    "day_of_week": 1,
                    "meal_time": "L",
                    "dishes": [self.dish1.id, self.dish2.id],
                }
            ]
        }
        s = WeeklyMenuBatchSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

        menus = s.save()
        self.assertEqual(
            WeeklyMenuDish.objects.filter(menu=menus[0]).count(),
            2,
        )

    def test_batch_with_objects(self):
        data = {
            "menus": [
                {
                    "company": self.company.id,
                    "diet_category": self.diet.id,
                    "day_of_week": 2,
                    "meal_time": "B",
                    "dishes": [
                        {"dish_id": self.dish1.id, "quantity": 3},
                        {"dish_id": self.dish2.id, "quantity": 5},
                    ],
                }
            ]
        }
        s = WeeklyMenuBatchSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

        menus = s.save()
        md = WeeklyMenuDish.objects.filter(menu=menus[0])
        q_map = {m.dish_id: m.quantity for m in md}
        self.assertEqual(q_map[self.dish1.id], 3)
        self.assertEqual(q_map[self.dish2.id], 5)

    def test_batch_update_replaces_dishes(self):
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=3,
            meal_time="D",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1)

        data = {
            "menus": [
                {
                    "company": self.company.id,
                    "diet_category": self.diet.id,
                    "day_of_week": 3,
                    "meal_time": "D",
                    "dishes": [self.dish2.id],
                }
            ]
        }
        s = WeeklyMenuBatchSerializer(data=data)
        s.is_valid(raise_exception=True)
        s.save()

        md = WeeklyMenuDish.objects.filter(menu=menu)
        self.assertEqual(md.count(), 1)
        self.assertEqual(md.first().dish, self.dish2)

    def test_batch_rejects_zero_quantity(self):
        data = {
            "menus": [
                {
                    "company": self.company.id,
                    "diet_category": self.diet.id,
                    "day_of_week": 1,
                    "meal_time": "L",
                    "dishes": [
                        {"dish_id": self.dish1.id, "quantity": 0},
                    ],
                }
            ]
        }
        s = WeeklyMenuBatchSerializer(data=data)
        self.assertFalse(s.is_valid(), s.errors)

    def test_batch_invalid_meal_time(self):
        data = {
            "menus": [
                {
                    "company": self.company.id,
                    "diet_category": self.diet.id,
                    "day_of_week": 1,
                    "meal_time": "X",
                    "dishes": [self.dish1.id],
                }
            ]
        }
        s = WeeklyMenuBatchSerializer(data=data)
        self.assertFalse(s.is_valid(), s.errors)