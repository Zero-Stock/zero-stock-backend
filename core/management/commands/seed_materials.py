from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    MaterialCategory,
    ProcessedMaterial,
    RawMaterial,
    RawMaterialYieldRate,
)

SEED_MATERIALS = [
    {
        "name": "Lean Pork",
        "category": "Protein",
        "stock": Decimal("18.50"),
        "yield_rate": Decimal("0.95"),
        "specs": ["Sliced", "Shredded", "Diced"],
    },
    {
        "name": "Chicken Breast",
        "category": "Protein",
        "stock": Decimal("15.00"),
        "yield_rate": Decimal("0.92"),
        "specs": ["Diced", "Strips", "Skinless"],
    },
    {
        "name": "Tomato",
        "category": "Produce",
        "stock": Decimal("24.00"),
        "yield_rate": Decimal("0.98"),
        "specs": ["Diced", "Peeled", "Crushed"],
    },
    {
        "name": "Cucumber",
        "category": "Produce",
        "stock": Decimal("12.00"),
        "yield_rate": Decimal("0.97"),
        "specs": ["Sliced", "Shredded"],
    },
    {
        "name": "Black Fungus",
        "category": "Dry Goods",
        "stock": Decimal("6.50"),
        "yield_rate": Decimal("0.88"),
        "specs": ["Soaked", "Shredded"],
    },
    {
        "name": "Dried Shiitake",
        "category": "Dry Goods",
        "stock": Decimal("5.00"),
        "yield_rate": Decimal("0.85"),
        "specs": ["Soaked", "Sliced"],
    },
    {
        "name": "Shrimp",
        "category": "Frozen",
        "stock": Decimal("8.00"),
        "yield_rate": Decimal("0.90"),
        "specs": ["Thawed", "Butterflied"],
    },
    {
        "name": "Bok Choy",
        "category": "Produce",
        "stock": Decimal("14.50"),
        "yield_rate": Decimal("0.93"),
        "specs": ["Washed", "Cut Sections"],
    },
    {
        "name": "Garlic",
        "category": "Produce",
        "stock": Decimal("4.20"),
        "yield_rate": Decimal("0.96"),
        "specs": ["Minced", "Sliced"],
    },
    {
        "name": "Tofu",
        "category": "Protein",
        "stock": Decimal("10.00"),
        "yield_rate": Decimal("0.99"),
        "specs": ["Cubed", "Blanched"],
    },
]


class Command(BaseCommand):
    help = "Seed demo data for the materials module. Safe to rerun."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the seeded materials first, then recreate them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options["reset"]
        material_names = [item["name"] for item in SEED_MATERIALS]

        if reset:
            deleted_count, _ = RawMaterial.objects.filter(name__in=material_names).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Deleted existing seeded material records: {deleted_count}"
                )
            )

        categories = self._ensure_categories()
        created_count = 0
        updated_count = 0
        effective_date = timezone.localdate()

        for item in SEED_MATERIALS:
            material, created = RawMaterial.objects.update_or_create(
                name=item["name"],
                defaults={
                    "category": categories[item["category"]],
                    "stock": item["stock"],
                },
            )
            created_count += int(created)
            updated_count += int(not created)

            self._replace_specs(material, item["specs"])
            RawMaterialYieldRate.objects.update_or_create(
                raw_material=material,
                effective_date=effective_date,
                defaults={"yield_rate": item["yield_rate"]},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(SEED_MATERIALS)} materials "
                f"({created_count} created, {updated_count} updated)."
            )
        )

    def _ensure_categories(self):
        category_names = sorted({item["category"] for item in SEED_MATERIALS})
        categories = {}
        for name in category_names:
            category, _ = MaterialCategory.objects.get_or_create(name=name)
            categories[name] = category
        return categories

    def _replace_specs(self, material, specs):
        desired = {name.strip() for name in specs if name and name.strip()}
        existing = {
            spec.method_name: spec
            for spec in ProcessedMaterial.objects.filter(raw_material=material)
        }

        for method_name, spec in existing.items():
            if method_name not in desired:
                spec.delete()

        for method_name in sorted(desired):
            ProcessedMaterial.objects.get_or_create(
                raw_material=material,
                method_name=method_name,
            )
