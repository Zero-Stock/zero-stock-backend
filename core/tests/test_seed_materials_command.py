from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import MaterialCategory, ProcessedMaterial, RawMaterial, RawMaterialYieldRate


class SeedMaterialsCommandTest(TestCase):
    def test_seed_materials_creates_demo_data(self):
        out = StringIO()

        call_command("seed_materials", stdout=out)

        material = RawMaterial.objects.get(name="Lean Pork")
        self.assertEqual(material.category.name, "fresh")
        self.assertEqual(material.stock, Decimal("18.50"))
        self.assertTrue(
            ProcessedMaterial.objects.filter(raw_material=material, method_name="Sliced").exists()
        )
        self.assertTrue(
            RawMaterialYieldRate.objects.filter(
                raw_material=material,
                yield_rate=Decimal("0.95"),
            ).exists()
        )
        self.assertIn("Seeded 10 materials", out.getvalue())

    def test_seed_materials_is_idempotent(self):
        call_command("seed_materials")
        call_command("seed_materials")

        self.assertEqual(MaterialCategory.objects.filter(name="fresh").count(), 1)
        self.assertEqual(RawMaterial.objects.filter(name="Lean Pork").count(), 1)
        material = RawMaterial.objects.get(name="Lean Pork")
        self.assertEqual(
            ProcessedMaterial.objects.filter(raw_material=material, method_name="Sliced").count(),
            1,
        )

    def test_seed_materials_reset_recreates_seeded_records(self):
        call_command("seed_materials")
        RawMaterial.objects.filter(name="Lean Pork").update(stock=Decimal("99.99"))

        call_command("seed_materials", "--reset")

        material = RawMaterial.objects.get(name="Lean Pork")
        self.assertEqual(material.stock, Decimal("18.50"))

    def test_seed_materials_delete_only_removes_seeded_records(self):
        call_command("seed_materials")

        call_command("seed_materials", "--delete-only")

        self.assertFalse(RawMaterial.objects.filter(name="Lean Pork").exists())
