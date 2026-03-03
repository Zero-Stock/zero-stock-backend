# -*- coding: utf-8 -*-
"""
operations/tests/test_models.py
Model layer unit tests for operations app.
"""
from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from core.models import (
    ClientCompany,
    DietCategory,
    Dish,
    MaterialCategory,
    ProcessedMaterial,
    RawMaterial,
)
from operations.models import (
    ClientCompanyRegion,
    DailyCensus,
    DailyMenu,
    DeliveryItem,
    DeliveryOrder,
    ProcessingItem,
    ProcessingOrder,
    ProcurementItem,
    ProcurementRequest,
    ReceivingRecord,
    StapleDemand,
    StapleType,
    WeeklyMenu,
    WeeklyMenuDish,
)


class OpsModelTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = ClientCompany.objects.create(name="Test Hospital", code="HOSP01")
        cls.category = MaterialCategory.objects.create(name="Fresh")
        cls.material = RawMaterial.objects.create(name="Potato", category=cls.category)
        cls.diet = DietCategory.objects.create(name="Standard A")
        cls.dish = Dish.objects.create(name="Stir Fry Potato")
        cls.region = ClientCompanyRegion.objects.create(
            company=cls.company, name="East Wing"
        )


class ClientCompanyRegionTest(OpsModelTestBase):
    def test_str(self):
        s = str(self.region)
        self.assertIn("East Wing", s)
        self.assertIn("HOSP01", s)

    def test_unique_together(self):
        with self.assertRaises(IntegrityError):
            ClientCompanyRegion.objects.create(
                company=self.company, name="East Wing"
            )

    def test_different_company_same_name(self):
        co2 = ClientCompany.objects.create(name="Other", code="OTHER01")
        region2 = ClientCompanyRegion.objects.create(company=co2, name="East Wing")
        self.assertIsNotNone(region2.id)


class WeeklyMenuTest(OpsModelTestBase):
    def test_str(self):
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="L",
        )
        s = str(menu)
        self.assertIn("Standard A", s)
        self.assertIn("Monday", s)
        self.assertIn("Lunch", s)

    def test_unique_together(self):
        WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="L",
        )
        with self.assertRaises(IntegrityError):
            WeeklyMenu.objects.create(
                company=self.company,
                diet_category=self.diet,
                day_of_week=1,
                meal_time="L",
            )

    def test_different_meal_time_ok(self):
        WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="B",
        )
        menu2 = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="D",
        )
        self.assertIsNotNone(menu2.id)


class WeeklyMenuDishTest(OpsModelTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.menu = WeeklyMenu.objects.create(
            company=cls.company,
            diet_category=cls.diet,
            day_of_week=1,
            meal_time="L",
        )

    def test_str(self):
        md = WeeklyMenuDish.objects.create(
            menu=self.menu, dish=self.dish, quantity=2
        )
        s = str(md)
        self.assertIn("Stir Fry Potato", s)
        self.assertIn("x2", s)

    def test_default_quantity(self):
        md = WeeklyMenuDish.objects.create(menu=self.menu, dish=self.dish)
        self.assertEqual(md.quantity, 1)

    def test_unique_together(self):
        WeeklyMenuDish.objects.create(menu=self.menu, dish=self.dish)
        with self.assertRaises(IntegrityError):
            WeeklyMenuDish.objects.create(menu=self.menu, dish=self.dish)


class DailyCensusTest(OpsModelTestBase):
    def test_str(self):
        dc = DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        s = str(dc)
        self.assertIn("2026-03-01", s)
        self.assertIn("East Wing", s)
        self.assertIn("50", s)

    def test_unique_together(self):
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        with self.assertRaises(IntegrityError):
            DailyCensus.objects.create(
                company=self.company,
                date=date(2026, 3, 1),
                region=self.region,
                diet_category=self.diet,
                count=30,
            )


class ProcurementRequestTest(OpsModelTestBase):
    def test_str(self):
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        s = str(pr)
        self.assertIn("2026-03-01", s)
        self.assertIn("HOSP01", s)

    def test_default_status(self):
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        self.assertEqual(pr.status, "DRAFT")


class DailyMenuTest(OpsModelTestBase):
    def test_unique_together(self):
        DailyMenu.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            diet=self.diet,
            meal_type="L",
        )
        with self.assertRaises(IntegrityError):
            DailyMenu.objects.create(
                company=self.company,
                date=date(2026, 3, 1),
                diet=self.diet,
                meal_type="L",
            )

    def test_m2m_dishes(self):
        dm = DailyMenu.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            diet=self.diet,
            meal_type="B",
        )
        dm.dishes.add(self.dish)
        self.assertEqual(dm.dishes.count(), 1)


class StapleDemandTest(OpsModelTestBase):
    def test_unique_together(self):
        StapleDemand.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            diet=self.diet,
            meal_type="L",
            staple_type=StapleType.RICE,
            quantity=Decimal("120.00"),
        )
        with self.assertRaises(IntegrityError):
            StapleDemand.objects.create(
                company=self.company,
                date=date(2026, 3, 1),
                diet=self.diet,
                meal_type="L",
                staple_type=StapleType.RICE,
                quantity=Decimal("99.00"),
            )

    def test_different_staple_ok(self):
        StapleDemand.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            diet=self.diet,
            meal_type="L",
            staple_type=StapleType.RICE,
            quantity=Decimal("120.00"),
        )
        sd = StapleDemand.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            diet=self.diet,
            meal_type="L",
            staple_type=StapleType.NOODLE,
            quantity=Decimal("30.00"),
        )
        self.assertIsNotNone(sd.id)


class ReceivingRecordTest(OpsModelTestBase):
    def test_str(self):
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        rr = ReceivingRecord.objects.create(
            procurement=pr, company=self.company
        )
        s = str(rr)
        self.assertIn("RCV", s)

    def test_default_status(self):
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        rr = ReceivingRecord.objects.create(
            procurement=pr, company=self.company
        )
        self.assertEqual(rr.status, "PENDING")


class ProcessingOrderTest(OpsModelTestBase):
    def test_str(self):
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        s = str(po)
        self.assertIn("PROC", s)
        self.assertIn("HOSP01", s)

    def test_default_status(self):
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        self.assertEqual(po.status, "DRAFT")


class ProcessingItemTest(OpsModelTestBase):
    def test_str_with_processing(self):
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        pm = ProcessedMaterial.objects.create(
            raw_material=self.material, method_name="Diced"
        )
        pi = ProcessingItem.objects.create(
            order=po,
            raw_material=self.material,
            processed_material=pm,
            dish=self.dish,
            net_quantity=Decimal("5.00"),
            gross_quantity=Decimal("6.25"),
        )
        s = str(pi)
        self.assertIn("Potato", s)
        self.assertIn("Diced", s)

    def test_str_without_processing(self):
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        pi = ProcessingItem.objects.create(
            order=po,
            raw_material=self.material,
            dish=self.dish,
            net_quantity=Decimal("5.00"),
            gross_quantity=Decimal("5.00"),
        )
        s = str(pi)
        # Without processing, it shows the no-processing indicator
        self.assertIn("Potato", s)


class DeliveryOrderTest(OpsModelTestBase):
    def test_str(self):
        do = DeliveryOrder.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            meal_time="L",
        )
        s = str(do)
        self.assertIn("DLV", s)
        self.assertIn("Lunch", s)

    def test_unique_together(self):
        DeliveryOrder.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            meal_time="L",
        )
        with self.assertRaises(IntegrityError):
            DeliveryOrder.objects.create(
                company=self.company,
                target_date=date(2026, 3, 1),
                meal_time="L",
            )


class DeliveryItemTest(OpsModelTestBase):
    def test_str(self):
        do = DeliveryOrder.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            meal_time="L",
        )
        di = DeliveryItem.objects.create(
            delivery=do,
            region=self.region,
            diet_category=self.diet,
            count=20,
        )
        s = str(di)
        self.assertIn("East Wing", s)
        self.assertIn("Standard A", s)
        self.assertIn("20", s)
