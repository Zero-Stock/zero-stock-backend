from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import ClientCompany, DietCategory, Dish, RawMaterial, Supplier
from operations.models import WeeklyMenu, WeeklyMenuDish
from core.management.commands.seed_menu_demo import (
    SEED_DISHES,
    SEED_DIETS,
    SEED_MATERIALS,
    SEED_MEAL_PLANS_BY_DIET,
    SEED_SUPPLIERS,
)


class SeedMenuDemoCommandTest(TestCase):
    def test_seed_menu_demo_creates_linked_records(self):
        out = StringIO()

        call_command("seed_menu_demo", stdout=out)

        company = ClientCompany.objects.get(code="testCompanyCode1")
        material = RawMaterial.objects.get(name="Chicken Breast")
        dish = Dish.objects.get(name="Herb Chicken Rice")
        menu = WeeklyMenu.objects.get(
            company=company,
            diet_category__name="Standard Menu",
            day_of_week=1,
            meal_time="L",
        )

        self.assertEqual(material.default_supplier.name, "Prime Protein Supply")
        self.assertEqual(
            DietCategory.objects.filter(name__in=SEED_DIETS).count(),
            len(SEED_DIETS),
        )
        self.assertTrue(
            WeeklyMenu.objects.filter(
                company__code="testCompanyCode1",
                diet_category__name="Light Diet",
            ).exists()
        )
        self.assertTrue(
            WeeklyMenu.objects.filter(
                company__code="testCompanyCode1",
                diet_category__name="High Protein",
            ).exists()
        )
        self.assertTrue(dish.ingredients.filter(raw_material__name="Chicken Breast").exists())
        self.assertTrue(WeeklyMenuDish.objects.filter(menu=menu, dish=dish, quantity=1).exists())
        self.assertIn(
            f"{sum(len(items) for items in SEED_MEAL_PLANS_BY_DIET.values())} meal plans",
            out.getvalue(),
        )

    def test_seed_menu_demo_is_idempotent(self):
        call_command("seed_menu_demo")
        call_command("seed_menu_demo")

        self.assertEqual(Supplier.objects.filter(name="Prime Protein Supply").count(), 1)
        self.assertEqual(RawMaterial.objects.filter(name="Chicken Breast").count(), 1)
        self.assertEqual(Dish.objects.filter(name="Herb Chicken Rice").count(), 1)
        self.assertEqual(Supplier.objects.filter(name__in=[item["name"] for item in SEED_SUPPLIERS]).count(), len(SEED_SUPPLIERS))
        self.assertEqual(RawMaterial.objects.filter(name__in=[item["name"] for item in SEED_MATERIALS]).count(), len(SEED_MATERIALS))
        self.assertEqual(Dish.objects.filter(name__in=[item["name"] for item in SEED_DISHES]).count(), len(SEED_DISHES))
        self.assertEqual(
            WeeklyMenu.objects.filter(
                company__code="testCompanyCode1",
                diet_category__name__in=SEED_DIETS,
            ).count(),
            sum(len(items) for items in SEED_MEAL_PLANS_BY_DIET.values()),
        )

    def test_seed_menu_demo_reset_restores_seeded_values(self):
        call_command("seed_menu_demo")
        RawMaterial.objects.filter(name="Chicken Breast").update(stock="99.99")

        call_command("seed_menu_demo", "--reset")

        material = RawMaterial.objects.get(name="Chicken Breast")
        self.assertEqual(str(material.stock), "25.00")

    def test_seed_menu_demo_delete_only_removes_seeded_records(self):
        call_command("seed_menu_demo")

        call_command("seed_menu_demo", "--delete-only")

        self.assertTrue(ClientCompany.objects.filter(code="testCompanyCode1").exists())
        self.assertFalse(RawMaterial.objects.filter(name="Chicken Breast").exists())
        self.assertFalse(Dish.objects.filter(name="Herb Chicken Rice").exists())
        self.assertEqual(
            WeeklyMenu.objects.filter(
                company__code="testCompanyCode1",
                diet_category__name="Standard Menu",
            ).count(),
            0,
        )
