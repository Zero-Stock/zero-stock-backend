from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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
)
from operations.models import WeeklyMenu, WeeklyMenuDish

SEED_COMPANY = {
    "name": "Demo General Hospital",
    "code": "DEMO01",
}

SEED_DIET = "Standard Menu"

SEED_SUPPLIERS = [
    {
        "name": "North Farm Produce",
        "contact_person": "Emma Clark",
        "phone": "555-0101",
        "address": "12 Orchard Road",
    },
    {
        "name": "Prime Protein Supply",
        "contact_person": "Liam Turner",
        "phone": "555-0102",
        "address": "88 Market Street",
    },
    {
        "name": "Pantry Depot",
        "contact_person": "Olivia Baker",
        "phone": "555-0103",
        "address": "41 Harbor Avenue",
    },
]

SEED_MATERIALS = [
    {
        "name": "Rolled Oats",
        "category": "fresh",
        "stock": Decimal("30.00"),
        "yield_rate": Decimal("1.00"),
        "specs": ["Cooked"],
        "supplier": "Pantry Depot",
        "unit_name": "bag",
        "kg_per_unit": Decimal("10.00"),
        "price": Decimal("28.00"),
    },
    {
        "name": "Egg",
        "category": "fresh",
        "stock": Decimal("18.00"),
        "yield_rate": Decimal("0.98"),
        "specs": ["Beaten", "Scrambled"],
        "supplier": "Prime Protein Supply",
        "unit_name": "tray",
        "kg_per_unit": Decimal("12.00"),
        "price": Decimal("46.00"),
    },
    {
        "name": "Chicken Breast",
        "category": "fresh",
        "stock": Decimal("25.00"),
        "yield_rate": Decimal("0.92"),
        "specs": ["Diced", "Sliced", "Shredded"],
        "supplier": "Prime Protein Supply",
        "unit_name": "case",
        "kg_per_unit": Decimal("15.00"),
        "price": Decimal("96.00"),
    },
    {
        "name": "Ground Beef",
        "category": "fresh",
        "stock": Decimal("20.00"),
        "yield_rate": Decimal("0.90"),
        "specs": ["Marinated", "Cooked"],
        "supplier": "Prime Protein Supply",
        "unit_name": "case",
        "kg_per_unit": Decimal("12.00"),
        "price": Decimal("118.00"),
    },
    {
        "name": "Shrimp",
        "category": "frozen",
        "stock": Decimal("12.00"),
        "yield_rate": Decimal("0.88"),
        "specs": ["Thawed", "Peeled"],
        "supplier": "Prime Protein Supply",
        "unit_name": "box",
        "kg_per_unit": Decimal("8.00"),
        "price": Decimal("104.00"),
    },
    {
        "name": "Tomato",
        "category": "fresh",
        "stock": Decimal("22.00"),
        "yield_rate": Decimal("0.97"),
        "specs": ["Diced", "Roasted"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("10.00"),
        "price": Decimal("32.00"),
    },
    {
        "name": "Cucumber",
        "category": "fresh",
        "stock": Decimal("14.00"),
        "yield_rate": Decimal("0.98"),
        "specs": ["Sliced"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("8.00"),
        "price": Decimal("26.00"),
    },
    {
        "name": "Bok Choy",
        "category": "fresh",
        "stock": Decimal("16.00"),
        "yield_rate": Decimal("0.94"),
        "specs": ["Chopped"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("9.00"),
        "price": Decimal("30.00"),
    },
    {
        "name": "Garlic",
        "category": "fresh",
        "stock": Decimal("5.00"),
        "yield_rate": Decimal("0.96"),
        "specs": ["Minced", "Sliced"],
        "supplier": "North Farm Produce",
        "unit_name": "bag",
        "kg_per_unit": Decimal("5.00"),
        "price": Decimal("20.00"),
    },
    {
        "name": "Mushroom",
        "category": "fresh",
        "stock": Decimal("11.00"),
        "yield_rate": Decimal("0.95"),
        "specs": ["Sliced"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("6.00"),
        "price": Decimal("27.00"),
    },
    {
        "name": "Tofu",
        "category": "fresh",
        "stock": Decimal("13.00"),
        "yield_rate": Decimal("0.99"),
        "specs": ["Cubed", "Steamed"],
        "supplier": "Pantry Depot",
        "unit_name": "case",
        "kg_per_unit": Decimal("10.00"),
        "price": Decimal("36.00"),
    },
    {
        "name": "Rice",
        "category": "fresh",
        "stock": Decimal("40.00"),
        "yield_rate": Decimal("1.00"),
        "specs": ["Cooked"],
        "supplier": "Pantry Depot",
        "unit_name": "bag",
        "kg_per_unit": Decimal("20.00"),
        "price": Decimal("48.00"),
    },
    {
        "name": "Onion",
        "category": "fresh",
        "stock": Decimal("10.00"),
        "yield_rate": Decimal("0.95"),
        "specs": ["Diced", "Sliced"],
        "supplier": "North Farm Produce",
        "unit_name": "bag",
        "kg_per_unit": Decimal("8.00"),
        "price": Decimal("22.00"),
    },
    {
        "name": "Carrot",
        "category": "fresh",
        "stock": Decimal("18.00"),
        "yield_rate": Decimal("0.96"),
        "specs": ["Diced", "Sliced", "Julienned"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("10.00"),
        "price": Decimal("24.00"),
    },
    {
        "name": "Potato",
        "category": "fresh",
        "stock": Decimal("28.00"),
        "yield_rate": Decimal("0.90"),
        "specs": ["Cubed", "Mashed", "Roasted"],
        "supplier": "North Farm Produce",
        "unit_name": "bag",
        "kg_per_unit": Decimal("15.00"),
        "price": Decimal("29.00"),
    },
    {
        "name": "Broccoli",
        "category": "fresh",
        "stock": Decimal("12.00"),
        "yield_rate": Decimal("0.92"),
        "specs": ["Florets", "Steamed"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("7.00"),
        "price": Decimal("31.00"),
    },
    {
        "name": "Bell Pepper",
        "category": "fresh",
        "stock": Decimal("9.00"),
        "yield_rate": Decimal("0.94"),
        "specs": ["Diced", "Sliced"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("6.00"),
        "price": Decimal("33.00"),
    },
    {
        "name": "Spinach",
        "category": "fresh",
        "stock": Decimal("10.00"),
        "yield_rate": Decimal("0.91"),
        "specs": ["Chopped", "Sauteed"],
        "supplier": "North Farm Produce",
        "unit_name": "crate",
        "kg_per_unit": Decimal("5.00"),
        "price": Decimal("26.00"),
    },
    {
        "name": "Pasta",
        "category": "fresh",
        "stock": Decimal("16.00"),
        "yield_rate": Decimal("1.00"),
        "specs": ["Boiled"],
        "supplier": "Pantry Depot",
        "unit_name": "box",
        "kg_per_unit": Decimal("8.00"),
        "price": Decimal("34.00"),
    },
    {
        "name": "Salmon",
        "category": "frozen",
        "stock": Decimal("14.00"),
        "yield_rate": Decimal("0.89"),
        "specs": ["Thawed", "Portioned", "Baked"],
        "supplier": "Prime Protein Supply",
        "unit_name": "box",
        "kg_per_unit": Decimal("10.00"),
        "price": Decimal("128.00"),
    },
    {
        "name": "Green Peas",
        "category": "frozen",
        "stock": Decimal("11.00"),
        "yield_rate": Decimal("0.99"),
        "specs": ["Thawed"],
        "supplier": "Pantry Depot",
        "unit_name": "bag",
        "kg_per_unit": Decimal("6.00"),
        "price": Decimal("25.00"),
    },
    {
        "name": "Corn",
        "category": "frozen",
        "stock": Decimal("11.00"),
        "yield_rate": Decimal("0.99"),
        "specs": ["Thawed"],
        "supplier": "Pantry Depot",
        "unit_name": "bag",
        "kg_per_unit": Decimal("6.00"),
        "price": Decimal("24.00"),
    },
]

SEED_DISHES = [
    {
        "name": "Savory Oatmeal Bowl",
        "seasonings": "Salt, black pepper",
        "cooking_method": "Cook oats until creamy, then finish with scrambled egg and minced garlic.",
        "ingredients": [
            {"material": "Rolled Oats", "processing": "Cooked", "net_quantity": Decimal("0.080")},
            {"material": "Egg", "processing": "Scrambled", "net_quantity": Decimal("0.060")},
            {"material": "Garlic", "processing": "Minced", "net_quantity": Decimal("0.005")},
        ],
    },
    {
        "name": "Scrambled Eggs and Tomato",
        "seasonings": "Salt, olive oil",
        "cooking_method": "Scramble eggs, fold in diced tomatoes, and cook until glossy.",
        "ingredients": [
            {"material": "Egg", "processing": "Beaten", "net_quantity": Decimal("0.090")},
            {"material": "Tomato", "processing": "Diced", "net_quantity": Decimal("0.080")},
            {"material": "Garlic", "processing": "Minced", "net_quantity": Decimal("0.004")},
        ],
    },
    {
        "name": "Herb Chicken Rice",
        "seasonings": "Salt, parsley, light soy sauce",
        "cooking_method": "Pan-sear diced chicken, season lightly, and serve over steamed rice.",
        "ingredients": [
            {"material": "Chicken Breast", "processing": "Diced", "net_quantity": Decimal("0.120")},
            {"material": "Rice", "processing": "Cooked", "net_quantity": Decimal("0.150")},
            {"material": "Onion", "processing": "Diced", "net_quantity": Decimal("0.030")},
        ],
    },
    {
        "name": "Tomato Tofu Soup",
        "seasonings": "Salt, white pepper",
        "cooking_method": "Simmer tomatoes and tofu in a light broth until the flavors blend.",
        "ingredients": [
            {"material": "Tomato", "processing": "Diced", "net_quantity": Decimal("0.100")},
            {"material": "Tofu", "processing": "Cubed", "net_quantity": Decimal("0.120")},
            {"material": "Onion", "processing": "Diced", "net_quantity": Decimal("0.020")},
        ],
    },
    {
        "name": "Ginger Beef Stir Fry",
        "seasonings": "Salt, ginger, soy sauce",
        "cooking_method": "Quickly stir-fry marinated beef with onion and garlic over high heat.",
        "ingredients": [
            {"material": "Ground Beef", "processing": "Marinated", "net_quantity": Decimal("0.130")},
            {"material": "Onion", "processing": "Sliced", "net_quantity": Decimal("0.040")},
            {"material": "Garlic", "processing": "Sliced", "net_quantity": Decimal("0.005")},
        ],
    },
    {
        "name": "Garlic Bok Choy",
        "seasonings": "Salt, sesame oil",
        "cooking_method": "Saute chopped bok choy with garlic until just tender.",
        "ingredients": [
            {"material": "Bok Choy", "processing": "Chopped", "net_quantity": Decimal("0.140")},
            {"material": "Garlic", "processing": "Minced", "net_quantity": Decimal("0.005")},
        ],
    },
    {
        "name": "Mushroom Chicken Rice Bowl",
        "seasonings": "Salt, thyme",
        "cooking_method": "Cook sliced mushrooms with chicken, then plate over rice.",
        "ingredients": [
            {"material": "Chicken Breast", "processing": "Sliced", "net_quantity": Decimal("0.110")},
            {"material": "Mushroom", "processing": "Sliced", "net_quantity": Decimal("0.060")},
            {"material": "Rice", "processing": "Cooked", "net_quantity": Decimal("0.140")},
        ],
    },
    {
        "name": "Cucumber Salad",
        "seasonings": "Salt, vinegar, dill",
        "cooking_method": "Toss sliced cucumber with a light dressing and chill before serving.",
        "ingredients": [
            {"material": "Cucumber", "processing": "Sliced", "net_quantity": Decimal("0.120")},
            {"material": "Onion", "processing": "Sliced", "net_quantity": Decimal("0.015")},
        ],
    },
    {
        "name": "Shrimp Fried Rice",
        "seasonings": "Salt, white pepper, light soy sauce",
        "cooking_method": "Stir-fry thawed shrimp with rice, egg, and diced vegetables.",
        "ingredients": [
            {"material": "Shrimp", "processing": "Thawed", "net_quantity": Decimal("0.110")},
            {"material": "Rice", "processing": "Cooked", "net_quantity": Decimal("0.150")},
            {"material": "Egg", "processing": "Beaten", "net_quantity": Decimal("0.040")},
            {"material": "Onion", "processing": "Diced", "net_quantity": Decimal("0.020")},
        ],
    },
    {
        "name": "Steamed Tofu Bowl",
        "seasonings": "Salt, scallion oil",
        "cooking_method": "Steam tofu until warm, then top with roasted tomatoes and garlic.",
        "ingredients": [
            {"material": "Tofu", "processing": "Steamed", "net_quantity": Decimal("0.140")},
            {"material": "Tomato", "processing": "Roasted", "net_quantity": Decimal("0.070")},
            {"material": "Garlic", "processing": "Minced", "net_quantity": Decimal("0.004")},
        ],
    },
    {
        "name": "Chicken and Broccoli",
        "seasonings": "Salt, garlic, light soy sauce",
        "cooking_method": "Stir-fry diced chicken with broccoli florets and finish with a light glaze.",
        "ingredients": [
            {"material": "Chicken Breast", "processing": "Diced", "net_quantity": Decimal("0.120")},
            {"material": "Broccoli", "processing": "Florets", "net_quantity": Decimal("0.090")},
            {"material": "Garlic", "processing": "Minced", "net_quantity": Decimal("0.004")},
        ],
    },
    {
        "name": "Roasted Potato Hash",
        "seasonings": "Salt, paprika, black pepper",
        "cooking_method": "Roast cubed potatoes with onion and bell pepper until crisp and golden.",
        "ingredients": [
            {"material": "Potato", "processing": "Roasted", "net_quantity": Decimal("0.160")},
            {"material": "Onion", "processing": "Diced", "net_quantity": Decimal("0.030")},
            {"material": "Bell Pepper", "processing": "Diced", "net_quantity": Decimal("0.040")},
        ],
    },
    {
        "name": "Salmon Rice Plate",
        "seasonings": "Salt, dill, lemon pepper",
        "cooking_method": "Bake salmon portions and serve with warm rice and a side of broccoli.",
        "ingredients": [
            {"material": "Salmon", "processing": "Baked", "net_quantity": Decimal("0.130")},
            {"material": "Rice", "processing": "Cooked", "net_quantity": Decimal("0.140")},
            {"material": "Broccoli", "processing": "Steamed", "net_quantity": Decimal("0.070")},
        ],
    },
    {
        "name": "Vegetable Fried Rice",
        "seasonings": "Salt, white pepper, soy sauce",
        "cooking_method": "Stir-fry rice with egg, peas, corn, and diced carrots.",
        "ingredients": [
            {"material": "Rice", "processing": "Cooked", "net_quantity": Decimal("0.150")},
            {"material": "Egg", "processing": "Beaten", "net_quantity": Decimal("0.040")},
            {"material": "Green Peas", "processing": "Thawed", "net_quantity": Decimal("0.030")},
            {"material": "Corn", "processing": "Thawed", "net_quantity": Decimal("0.030")},
            {"material": "Carrot", "processing": "Diced", "net_quantity": Decimal("0.030")},
        ],
    },
    {
        "name": "Spinach Egg Soup",
        "seasonings": "Salt, white pepper, sesame oil",
        "cooking_method": "Simmer chopped spinach and drizzle in beaten egg for a light soup.",
        "ingredients": [
            {"material": "Spinach", "processing": "Chopped", "net_quantity": Decimal("0.080")},
            {"material": "Egg", "processing": "Beaten", "net_quantity": Decimal("0.040")},
            {"material": "Garlic", "processing": "Minced", "net_quantity": Decimal("0.003")},
        ],
    },
    {
        "name": "Creamy Mushroom Pasta",
        "seasonings": "Salt, black pepper, parsley",
        "cooking_method": "Boil pasta, then toss with sliced mushrooms and a light creamy sauce.",
        "ingredients": [
            {"material": "Pasta", "processing": "Boiled", "net_quantity": Decimal("0.140")},
            {"material": "Mushroom", "processing": "Sliced", "net_quantity": Decimal("0.070")},
            {"material": "Onion", "processing": "Diced", "net_quantity": Decimal("0.025")},
        ],
    },
    {
        "name": "Tofu Vegetable Bowl",
        "seasonings": "Salt, ginger, sesame oil",
        "cooking_method": "Saute tofu with bok choy, carrot, and bell pepper for a colorful bowl.",
        "ingredients": [
            {"material": "Tofu", "processing": "Cubed", "net_quantity": Decimal("0.130")},
            {"material": "Bok Choy", "processing": "Chopped", "net_quantity": Decimal("0.060")},
            {"material": "Carrot", "processing": "Julienned", "net_quantity": Decimal("0.030")},
            {"material": "Bell Pepper", "processing": "Sliced", "net_quantity": Decimal("0.040")},
        ],
    },
    {
        "name": "Beef and Potato Stew",
        "seasonings": "Salt, thyme, black pepper",
        "cooking_method": "Slow simmer beef with potatoes, carrots, and onion until tender.",
        "ingredients": [
            {"material": "Ground Beef", "processing": "Cooked", "net_quantity": Decimal("0.130")},
            {"material": "Potato", "processing": "Cubed", "net_quantity": Decimal("0.120")},
            {"material": "Carrot", "processing": "Sliced", "net_quantity": Decimal("0.040")},
            {"material": "Onion", "processing": "Diced", "net_quantity": Decimal("0.025")},
        ],
    },
]

SEED_MEAL_PLANS = [
    {
        "day_of_week": 1,
        "meal_time": "B",
        "dishes": [
            {"name": "Savory Oatmeal Bowl", "quantity": 1},
            {"name": "Scrambled Eggs and Tomato", "quantity": 1},
        ],
    },
    {
        "day_of_week": 1,
        "meal_time": "L",
        "dishes": [
            {"name": "Herb Chicken Rice", "quantity": 1},
            {"name": "Tomato Tofu Soup", "quantity": 1},
        ],
    },
    {
        "day_of_week": 1,
        "meal_time": "D",
        "dishes": [
            {"name": "Ginger Beef Stir Fry", "quantity": 1},
            {"name": "Garlic Bok Choy", "quantity": 1},
        ],
    },
    {
        "day_of_week": 2,
        "meal_time": "B",
        "dishes": [
            {"name": "Roasted Potato Hash", "quantity": 1},
            {"name": "Spinach Egg Soup", "quantity": 1},
        ],
    },
    {
        "day_of_week": 2,
        "meal_time": "L",
        "dishes": [
            {"name": "Mushroom Chicken Rice Bowl", "quantity": 1},
            {"name": "Cucumber Salad", "quantity": 1},
        ],
    },
    {
        "day_of_week": 2,
        "meal_time": "D",
        "dishes": [
            {"name": "Shrimp Fried Rice", "quantity": 1},
            {"name": "Steamed Tofu Bowl", "quantity": 1},
        ],
    },
    {
        "day_of_week": 3,
        "meal_time": "B",
        "dishes": [
            {"name": "Savory Oatmeal Bowl", "quantity": 1},
            {"name": "Cucumber Salad", "quantity": 1},
        ],
    },
    {
        "day_of_week": 3,
        "meal_time": "L",
        "dishes": [
            {"name": "Chicken and Broccoli", "quantity": 1},
            {"name": "Tomato Tofu Soup", "quantity": 1},
        ],
    },
    {
        "day_of_week": 3,
        "meal_time": "D",
        "dishes": [
            {"name": "Beef and Potato Stew", "quantity": 1},
            {"name": "Garlic Bok Choy", "quantity": 1},
        ],
    },
    {
        "day_of_week": 4,
        "meal_time": "B",
        "dishes": [
            {"name": "Scrambled Eggs and Tomato", "quantity": 1},
            {"name": "Roasted Potato Hash", "quantity": 1},
        ],
    },
    {
        "day_of_week": 4,
        "meal_time": "L",
        "dishes": [
            {"name": "Salmon Rice Plate", "quantity": 1},
            {"name": "Spinach Egg Soup", "quantity": 1},
        ],
    },
    {
        "day_of_week": 4,
        "meal_time": "D",
        "dishes": [
            {"name": "Creamy Mushroom Pasta", "quantity": 1},
            {"name": "Tofu Vegetable Bowl", "quantity": 1},
        ],
    },
    {
        "day_of_week": 5,
        "meal_time": "B",
        "dishes": [
            {"name": "Savory Oatmeal Bowl", "quantity": 1},
            {"name": "Spinach Egg Soup", "quantity": 1},
        ],
    },
    {
        "day_of_week": 5,
        "meal_time": "L",
        "dishes": [
            {"name": "Vegetable Fried Rice", "quantity": 1},
            {"name": "Chicken and Broccoli", "quantity": 1},
        ],
    },
    {
        "day_of_week": 5,
        "meal_time": "D",
        "dishes": [
            {"name": "Beef and Potato Stew", "quantity": 1},
            {"name": "Steamed Tofu Bowl", "quantity": 1},
        ],
    },
    {
        "day_of_week": 6,
        "meal_time": "B",
        "dishes": [
            {"name": "Scrambled Eggs and Tomato", "quantity": 1},
            {"name": "Cucumber Salad", "quantity": 1},
        ],
    },
    {
        "day_of_week": 6,
        "meal_time": "L",
        "dishes": [
            {"name": "Herb Chicken Rice", "quantity": 1},
            {"name": "Tofu Vegetable Bowl", "quantity": 1},
        ],
    },
    {
        "day_of_week": 6,
        "meal_time": "D",
        "dishes": [
            {"name": "Salmon Rice Plate", "quantity": 1},
            {"name": "Garlic Bok Choy", "quantity": 1},
        ],
    },
    {
        "day_of_week": 7,
        "meal_time": "B",
        "dishes": [
            {"name": "Roasted Potato Hash", "quantity": 1},
            {"name": "Savory Oatmeal Bowl", "quantity": 1},
        ],
    },
    {
        "day_of_week": 7,
        "meal_time": "L",
        "dishes": [
            {"name": "Shrimp Fried Rice", "quantity": 1},
            {"name": "Spinach Egg Soup", "quantity": 1},
        ],
    },
    {
        "day_of_week": 7,
        "meal_time": "D",
        "dishes": [
            {"name": "Creamy Mushroom Pasta", "quantity": 1},
            {"name": "Tomato Tofu Soup", "quantity": 1},
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seed demo data for materials, suppliers, dishes, and meal plans. "
        "Safe to rerun and reset by seeded identifiers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the seeded demo records first, then recreate them.",
        )
        parser.add_argument(
            "--delete-only",
            action="store_true",
            help="Delete the seeded demo records without recreating them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options["reset"]
        delete_only = options["delete_only"]

        if reset and delete_only:
            raise ValueError("Use either --reset or --delete-only, not both.")

        if reset or delete_only:
            self._reset_seed_data()
            if delete_only:
                self.stdout.write(
                    self.style.SUCCESS("Deleted seeded demo data.")
                )
                return

        company, _ = ClientCompany.objects.update_or_create(
            code=SEED_COMPANY["code"],
            defaults={"name": SEED_COMPANY["name"]},
        )
        diet, _ = DietCategory.objects.get_or_create(name=SEED_DIET)
        suppliers = self._seed_suppliers()
        materials = self._seed_materials(suppliers)
        dishes = self._seed_dishes(materials, diet)
        menus_created = self._seed_meal_plans(company, diet, dishes)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo data: {len(suppliers)} suppliers, "
                f"{len(materials)} materials, {len(dishes)} dishes, "
                f"and {menus_created} meal plans."
            )
        )

    def _seed_suppliers(self):
        suppliers = {}
        for item in SEED_SUPPLIERS:
            supplier, _ = Supplier.objects.update_or_create(
                name=item["name"],
                defaults={
                    "contact_person": item["contact_person"],
                    "phone": item["phone"],
                    "address": item["address"],
                },
            )
            suppliers[item["name"]] = supplier
        return suppliers

    def _seed_materials(self, suppliers):
        categories = {}
        materials = {}
        effective_date = timezone.localdate()

        for item in SEED_MATERIALS:
            category = categories.get(item["category"])
            if not category:
                category, _ = MaterialCategory.objects.get_or_create(name=item["category"])
                categories[item["category"]] = category

            supplier = suppliers[item["supplier"]]
            material, _ = RawMaterial.objects.update_or_create(
                name=item["name"],
                defaults={
                    "category": category,
                    "stock": item["stock"],
                    "default_supplier": supplier,
                },
            )
            materials[item["name"]] = material

            self._replace_specs(material, item["specs"])
            RawMaterialYieldRate.objects.update_or_create(
                raw_material=material,
                effective_date=effective_date,
                defaults={"yield_rate": item["yield_rate"]},
            )
            SupplierMaterial.objects.update_or_create(
                supplier=supplier,
                raw_material=material,
                defaults={
                    "unit_name": item["unit_name"],
                    "kg_per_unit": item["kg_per_unit"],
                    "price": item["price"],
                    "notes": "Seeded demo supplier mapping",
                },
            )

        return materials

    def _seed_dishes(self, materials, diet):
        dishes = {}
        for item in SEED_DISHES:
            dish, _ = Dish.objects.update_or_create(
                name=item["name"],
                defaults={
                    "seasonings": item["seasonings"],
                    "cooking_method": item["cooking_method"],
                },
            )
            DishIngredient.objects.filter(dish=dish).delete()

            for ingredient in item["ingredients"]:
                raw_material = materials[ingredient["material"]]
                processing = None
                processing_name = ingredient.get("processing")
                if processing_name:
                    processing = ProcessedMaterial.objects.get(
                        raw_material=raw_material,
                        method_name=processing_name,
                    )

                DishIngredient.objects.create(
                    dish=dish,
                    raw_material=raw_material,
                    processing=processing,
                    net_quantity=ingredient["net_quantity"],
                )

            dish.allowed_diets.set([diet])
            dishes[item["name"]] = dish
        return dishes

    def _seed_meal_plans(self, company, diet, dishes):
        for item in SEED_MEAL_PLANS:
            menu, _ = WeeklyMenu.objects.update_or_create(
                company=company,
                diet_category=diet,
                day_of_week=item["day_of_week"],
                meal_time=item["meal_time"],
            )
            WeeklyMenuDish.objects.filter(menu=menu).delete()
            for entry in item["dishes"]:
                WeeklyMenuDish.objects.create(
                    menu=menu,
                    dish=dishes[entry["name"]],
                    quantity=entry["quantity"],
                )
        return len(SEED_MEAL_PLANS)

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

    def _reset_seed_data(self):
        menu_day_pairs = [
            (item["day_of_week"], item["meal_time"])
            for item in SEED_MEAL_PLANS
        ]
        for day_of_week, meal_time in menu_day_pairs:
            WeeklyMenu.objects.filter(
                company__code=SEED_COMPANY["code"],
                diet_category__name=SEED_DIET,
                day_of_week=day_of_week,
                meal_time=meal_time,
            ).delete()

        dish_names = [item["name"] for item in SEED_DISHES]
        Dish.objects.filter(name__in=dish_names).delete()

        supplier_names = [item["name"] for item in SEED_SUPPLIERS]
        Supplier.objects.filter(name__in=supplier_names).delete()

        material_names = [item["name"] for item in SEED_MATERIALS]
        RawMaterial.objects.filter(name__in=material_names).delete()

        category_names = sorted({item["category"] for item in SEED_MATERIALS})
        MaterialCategory.objects.filter(name__in=category_names, rawmaterial__isnull=True).delete()

        DietCategory.objects.filter(name=SEED_DIET).delete()
        ClientCompany.objects.filter(code=SEED_COMPANY["code"]).delete()
