# -*- coding: utf-8 -*-
"""operations/tests/test_api.py"""
from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from core.models import ClientCompany, DietCategory, Dish, MaterialCategory, RawMaterial, UserProfile
from operations.models import ClientCompanyRegion, DailyCensus, WeeklyMenu, WeeklyMenuDish


class OpsAPITestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = ClientCompany.objects.create(name="Test Hospital", code="HOSP01")
        cls.user = User.objects.create_user(username="opsuser", password="testpass123")
        cls.profile = UserProfile.objects.create(user=cls.user, company=cls.company, role="RW")
        cls.category = MaterialCategory.objects.create(name="Fresh")
        cls.diet = DietCategory.objects.create(name="Standard A")
        cls.region = ClientCompanyRegion.objects.create(company=cls.company, name="East Wing")
        cls.dish1 = Dish.objects.create(name="Tomato Egg")
        cls.dish2 = Dish.objects.create(name="Pepper Pork")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class RegionAPITest(OpsAPITestBase):
    def test_list(self):
        r = self.client.get(f"/api/companies/{self.company.id}/regions/")
        self.assertEqual(r.status_code, 200)

    def test_create(self):
        r = self.client.post(f"/api/companies/{self.company.id}/regions/", {"name": "ICU"})
        self.assertEqual(r.status_code, 201)

    def test_create_duplicate_rejected(self):
        r = self.client.post(f"/api/companies/{self.company.id}/regions/", {"name": "East Wing"})
        self.assertEqual(r.status_code, 400)

    def test_access_other_company_denied(self):
        co2 = ClientCompany.objects.create(name="Other", code="OTHER01")
        r = self.client.get(f"/api/companies/{co2.id}/regions/")
        self.assertEqual(r.status_code, 403)

    def test_unauthenticated(self):
        client = APIClient()
        r = client.get(f"/api/companies/{self.company.id}/regions/")
        self.assertEqual(r.status_code, 401)


class WeeklyMenuAPITest(OpsAPITestBase):
    def test_list(self):
        r = self.client.get("/api/weekly-menus/")
        self.assertEqual(r.status_code, 200)

    def test_create(self):
        r = self.client.post("/api/weekly-menus/", {
            "company": self.company.id, "diet_category": self.diet.id,
            "day_of_week": 1, "meal_time": "L", "dishes": [self.dish1.id],
        }, format="json")
        self.assertEqual(r.status_code, 201)

    def test_filter_by_company(self):
        WeeklyMenu.objects.create(company=self.company, diet_category=self.diet, day_of_week=1, meal_time="L")
        r = self.client.get(f"/api/weekly-menus/?company={self.company.id}")
        self.assertEqual(r.status_code, 200)

    def test_batch_create(self):
        data = [
            {"company": self.company.id, "diet_category": self.diet.id,
             "day_of_week": 1, "meal_time": "B", "dishes": [self.dish1.id]},
            {"company": self.company.id, "diet_category": self.diet.id,
             "day_of_week": 1, "meal_time": "L",
             "dishes": [{"dish_id": self.dish1.id, "quantity": 2}]},
        ]
        r = self.client.post("/api/weekly-menus/batch/", data, format="json")
        self.assertEqual(r.status_code, 201)

    def test_update(self):
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet, day_of_week=5, meal_time="D")
        r = self.client.patch(f"/api/weekly-menus/{menu.id}/",
                              {"dishes": [self.dish2.id]}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_delete(self):
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet, day_of_week=7, meal_time="B")
        r = self.client.delete(f"/api/weekly-menus/{menu.id}/")
        self.assertEqual(r.status_code, 204)


class CensusAPITest(OpsAPITestBase):
    def test_list(self):
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 1),
            region=self.region, diet_category=self.diet, count=50)
        r = self.client.get("/api/census/?date=2026-03-01")
        self.assertEqual(r.status_code, 200)

    def test_batch_create(self):
        data = {"date": "2026-03-05", "items": [
            {"region_id": self.region.id, "diet_category_id": self.diet.id, "count": 50},
        ]}
        r = self.client.post("/api/census/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["created"], 1)

    def test_batch_update_existing(self):
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 10),
            region=self.region, diet_category=self.diet, count=50)
        data = {"date": "2026-03-10", "items": [
            {"region_id": self.region.id, "diet_category_id": self.diet.id, "count": 80},
        ]}
        r = self.client.post("/api/census/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["updated"], 1)
        dc = DailyCensus.objects.get(
            company=self.company, date=date(2026, 3, 10),
            region=self.region, diet_category=self.diet)
        self.assertEqual(dc.count, 80)

    def test_summary(self):
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 1),
            region=self.region, diet_category=self.diet, count=50)
        r = self.client.get("/api/census/summary/?date=2026-03-01")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["total"], 50)


# ---- Operations Search endpoints ----

class OpsSearchAPITest(OpsAPITestBase):
    def test_weekly_menu_search(self):
        WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet, day_of_week=1, meal_time="L")
        r = self.client.post("/api/weekly-menus/search/",
                             {"filters": {"company": self.company.id}}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_census_search(self):
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 1),
            region=self.region, diet_category=self.diet, count=50)
        r = self.client.post("/api/census/search/",
                             {"filters": {"date": "2026-03-01"}}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_procurement_search(self):
        from operations.models import ProcurementRequest
        ProcurementRequest.objects.create(company=self.company, target_date=date(2026, 3, 1))
        r = self.client.post("/api/procurement/search/",
                             {"filters": {"status": "CREATED"}}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_empty(self):
        r = self.client.post("/api/weekly-menus/search/", {}, format="json")
        self.assertEqual(r.status_code, 200)


# ---- Procurement API ----

class ProcurementAPITest(OpsAPITestBase):
    def _setup_full_menu(self, stock="0.00"):
        """Create a complete menu + census setup for procurement generation."""
        from core.models import DishIngredient, RawMaterial
        mat = RawMaterial.objects.create(name="ProcMat", category=self.category, stock=stock)
        self.dish1.allowed_diets.add(self.diet)
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.100")
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=date(2026, 3, 2).isoweekday(), meal_time="L")
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 2),
            region=self.region, diet_category=self.diet, count=100)
        return mat

    def test_generate(self):
        self._setup_full_menu()
        r = self.client.post("/api/procurement/generate/",
                             {"date": "2026-03-02"}, format="json")
        self.assertIn(r.status_code, [200, 201])
        # Status should be CREATED
        data = r.json()["results"]
        self.assertEqual(data["status"], "CREATED")

    def test_generate_no_date(self):
        r = self.client.post("/api/procurement/generate/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_generate_includes_stock(self):
        """Generated items should have demand, stock snapshot, and purchase = demand - stock."""
        from operations.models import ProcurementItem
        mat = self._setup_full_menu(stock="3.00")
        r = self.client.post("/api/procurement/generate/",
                             {"date": "2026-03-02"}, format="json")
        self.assertIn(r.status_code, [200, 201])
        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.stock_quantity, Decimal("3.00"))
        # demand = 100 * 0.1 / 1.0 = 10 kg
        self.assertEqual(item.demand_quantity, Decimal("10.00"))
        # purchase = 10 - 3 = 7 kg
        self.assertEqual(item.purchase_quantity, Decimal("7.00"))

    def test_generate_stock_exceeds_demand(self):
        """If stock >= demand, purchase_quantity should be 0."""
        from operations.models import ProcurementItem
        mat = self._setup_full_menu(stock="50.00")
        r = self.client.post("/api/procurement/generate/",
                             {"date": "2026-03-02"}, format="json")
        self.assertIn(r.status_code, [200, 201])
        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat).first()
        self.assertEqual(item.purchase_quantity, Decimal("0.00"))

    def test_list(self):
        from operations.models import ProcurementRequest
        ProcurementRequest.objects.create(company=self.company, target_date=date(2026, 3, 1))
        r = self.client.get("/api/procurement/")
        self.assertEqual(r.status_code, 200)

    def test_detail(self):
        from operations.models import ProcurementRequest
        pr = ProcurementRequest.objects.create(company=self.company, target_date=date(2026, 3, 1))
        r = self.client.get(f"/api/procurement/{pr.id}/")
        self.assertEqual(r.status_code, 200)

    def test_items(self):
        from operations.models import ProcurementRequest, ProcurementItem
        pr = ProcurementRequest.objects.create(company=self.company, target_date=date(2026, 3, 1))
        from core.models import RawMaterial
        mat = RawMaterial.objects.create(name="ProcItemMat", category=self.category)
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="12.50", stock_quantity="0", purchase_quantity="12.50")
        r = self.client.get(f"/api/procurement/{pr.id}/items/")
        self.assertEqual(r.status_code, 200)

    def test_submit(self):
        """CREATED -> SUBMITTED via submit endpoint."""
        from operations.models import ProcurementRequest
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1), status="CREATED")
        r = self.client.post(f"/api/procurement/{pr.id}/submit/")
        self.assertEqual(r.status_code, 200)
        pr.refresh_from_db()
        self.assertEqual(pr.status, "SUBMITTED")

    def test_submit_non_created_rejected(self):
        """Cannot submit if status is not CREATED."""
        from operations.models import ProcurementRequest
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1), status="SUBMITTED")
        r = self.client.post(f"/api/procurement/{pr.id}/submit/")
        pr.refresh_from_db()
        self.assertEqual(pr.status, "SUBMITTED")  # unchanged

    def test_sheet(self):
        from operations.models import ProcurementRequest
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1), status="SUBMITTED")
        r = self.client.get(f"/api/procurement/{pr.id}/sheet/")
        self.assertEqual(r.status_code, 200)

    def test_template(self):
        from operations.models import ProcurementRequest
        ProcurementRequest.objects.create(company=self.company, target_date=date(2026, 3, 1))
        r = self.client.get("/api/procurement/template/?date=2026-03-01")
        self.assertEqual(r.status_code, 200)

    def test_assign_suppliers(self):
        from operations.models import ProcurementRequest, ProcurementItem
        from core.models import RawMaterial, Supplier, SupplierMaterial
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1), status="CREATED")
        mat = RawMaterial.objects.create(name="AssignMat", category=self.category)
        item = ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="12.50", stock_quantity="0", purchase_quantity="12.50")
        supplier = Supplier.objects.create(name="AssignSupplier")
        sm = SupplierMaterial.objects.create(
            supplier=supplier, raw_material=mat,
            unit_name="box", kg_per_unit="5.00")
        r = self.client.post("/api/procurement/assign-suppliers/?date=2026-03-01",
                             {"assignments": [{"item_id": item.id, "supplier_material_id": sm.id}]},
                             format="json")
        self.assertEqual(r.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.supplier_kg_per_unit, Decimal("5.00"))
        # Status should still be CREATED (assign doesn't change status)
        pr.refresh_from_db()
        self.assertEqual(pr.status, "CREATED")

    def test_generate_prefills_default_supplier(self):
        """If RawMaterial has default_supplier, procurement should pre-fill it."""
        from operations.models import ProcurementItem
        from core.models import DishIngredient, RawMaterial, Supplier, SupplierMaterial

        supplier = Supplier.objects.create(name="DefaultSupp")
        mat = RawMaterial.objects.create(
            name="DefSuppMat", category=self.category, default_supplier=supplier)
        DishIngredient.objects.create(dish=self.dish1, raw_material=mat, net_quantity="0.100")
        SupplierMaterial.objects.create(
            supplier=supplier, raw_material=mat,
            unit_name="bag", kg_per_unit="2.00", price="15.00")

        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=date(2026, 3, 2).isoweekday(), meal_time="L")
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 2),
            region=self.region, diet_category=self.diet, count=50)

        r = self.client.post("/api/procurement/generate/",
                             {"date": "2026-03-02"}, format="json")
        self.assertIn(r.status_code, [200, 201])

        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.supplier_id, supplier.id)
        self.assertEqual(item.supplier_unit_name, "bag")
        self.assertEqual(item.supplier_kg_per_unit, Decimal("2.00"))
        self.assertEqual(item.supplier_price, Decimal("15.00"))

    def test_generate_no_default_supplier(self):
        """If no default_supplier, supplier fields should be null."""
        mat = self._setup_full_menu()

        r = self.client.post("/api/procurement/generate/",
                             {"date": "2026-03-02"}, format="json")
        self.assertIn(r.status_code, [200, 201])

        from operations.models import ProcurementItem
        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat).first()
        self.assertIsNotNone(item)
        self.assertIsNone(item.supplier_id)


# ---- Receiving API ----

class ReceivingAPITest(OpsAPITestBase):
    def _create_procurement(self, target_date=None, status="SUBMITTED"):
        from operations.models import ProcurementRequest, ProcurementItem
        from core.models import RawMaterial, Supplier, SupplierMaterial
        td = target_date or date.today()
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=td, status=status)
        mat = RawMaterial.objects.create(name=f"RecvMat{td}", category=self.category)
        supplier = Supplier.objects.create(name=f"RecvSupp{td}")
        SupplierMaterial.objects.create(
            supplier=supplier, raw_material=mat,
            unit_name="box", kg_per_unit="5.00", price="10.00")
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="12.50", stock_quantity="0", purchase_quantity="12.50",
            supplier=supplier, supplier_unit_name="box",
            supplier_kg_per_unit="5.00", supplier_price="10.00")
        return pr, mat, supplier

    def test_template(self):
        pr, mat, _ = self._create_procurement()
        r = self.client.get(f"/api/receiving/{pr.id}/template/")
        self.assertEqual(r.status_code, 200)
        items = r.json()["results"]["items"]
        self.assertEqual(len(items), 1)

    def test_template_not_found(self):
        r = self.client.get("/api/receiving/99999/template/")
        self.assertEqual(r.status_code, 404)

    def test_create_confirms_procurement(self):
        """First receiving should set procurement status to CONFIRMED."""
        from operations.models import ProcurementRequest
        pr, mat, _ = self._create_procurement()
        data = {
            "procurement_id": pr.id,
            "notes": "All good",
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 12.0, "notes": ""},
            ]
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 201)
        pr.refresh_from_db()
        self.assertEqual(pr.status, "CONFIRMED")

    def test_receiving_updates_default_supplier(self):
        """Receiving should update RawMaterial.default_supplier."""
        from core.models import RawMaterial
        pr, mat, supplier = self._create_procurement()
        data = {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 12.0},
            ]
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 201)
        mat.refresh_from_db()
        self.assertEqual(mat.default_supplier_id, supplier.id)

    def test_create_not_found_procurement(self):
        data = {"procurement_id": 99999, "items": []}
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 404)

    def test_detail(self):
        from operations.models import ReceivingRecord, ProcurementRequest
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1))
        rr = ReceivingRecord.objects.create(procurement=pr, company=self.company)
        r = self.client.get(f"/api/receiving/{rr.id}/")
        self.assertEqual(r.status_code, 200)

    def test_detail_not_found(self):
        r = self.client.get("/api/receiving/99999/")
        self.assertEqual(r.status_code, 404)


# ---- Processing API ----

class ProcessingAPITest(OpsAPITestBase):
    def _setup_processing(self):
        """Create menu + census so processing can be generated."""
        from core.models import DishIngredient, RawMaterial, ProcessedMaterial
        mat = RawMaterial.objects.create(name="ProcMatX", category=self.category)
        pm = ProcessedMaterial.objects.create(raw_material=mat, method_name="Diced")
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, processing=pm, net_quantity="0.200")
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=date(2026, 3, 3).isoweekday(), meal_time="L")
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 3),
            region=self.region, diet_category=self.diet, count=50)
        return mat, pm

    def test_generate(self):
        self._setup_processing()
        r = self.client.post("/api/processing/generate/",
                             {"date": "2026-03-03"}, format="json")
        self.assertIn(r.status_code, [200, 201])

    def test_generate_no_date(self):
        r = self.client.post("/api/processing/generate/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_detail(self):
        from operations.models import ProcessingOrder
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1))
        r = self.client.get(f"/api/processing/{po.id}/")
        self.assertEqual(r.status_code, 200)

    def test_detail_not_found(self):
        r = self.client.get("/api/processing/99999/")
        self.assertEqual(r.status_code, 404)

    def test_by_material(self):
        from operations.models import ProcessingOrder, ProcessingItem
        from core.models import RawMaterial
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1))
        mat = RawMaterial.objects.create(name="ByMatMat", category=self.category)
        ProcessingItem.objects.create(
            order=po, raw_material=mat, dish=self.dish1,
            net_quantity="5.00", gross_quantity="6.25")
        r = self.client.get(f"/api/processing/{po.id}/by-material/")
        self.assertEqual(r.status_code, 200)

    def test_by_dish(self):
        from operations.models import ProcessingOrder, ProcessingItem
        from core.models import RawMaterial
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1))
        mat = RawMaterial.objects.create(name="ByDishMat", category=self.category)
        ProcessingItem.objects.create(
            order=po, raw_material=mat, dish=self.dish1,
            net_quantity="5.00", gross_quantity="6.25")
        r = self.client.get(f"/api/processing/{po.id}/by-dish/")
        self.assertEqual(r.status_code, 200)

    def test_by_workshop(self):
        from operations.models import ProcessingOrder, ProcessingItem
        from core.models import RawMaterial
        po = ProcessingOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1))
        mat = RawMaterial.objects.create(name="ByWorkMat", category=self.category)
        ProcessingItem.objects.create(
            order=po, raw_material=mat, dish=self.dish1,
            net_quantity="5.00", gross_quantity="6.25")
        r = self.client.get(f"/api/processing/{po.id}/by-workshop/")
        self.assertEqual(r.status_code, 200)


# ---- Cooking API ----

class CookingAPITest(OpsAPITestBase):
    def test_today(self):
        r = self.client.get("/api/cooking/today/")
        self.assertEqual(r.status_code, 200)

    def test_today_with_filters(self):
        r = self.client.get(f"/api/cooking/today/?meal_time=L&company={self.company.id}")
        self.assertEqual(r.status_code, 200)

    def test_recipe(self):
        from core.models import DishIngredient, RawMaterial
        mat = RawMaterial.objects.create(name="RecipeMat", category=self.category)
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.300")
        r = self.client.get(f"/api/cooking/recipe/{self.dish1.id}/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(results["dish_name"], "Tomato Egg")
        self.assertEqual(len(results["ingredients"]), 1)

    def test_recipe_with_count(self):
        from core.models import DishIngredient, RawMaterial
        mat = RawMaterial.objects.create(name="RecipeMatScale", category=self.category)
        DishIngredient.objects.create(
            dish=self.dish2, raw_material=mat, net_quantity="0.100")
        r = self.client.get(f"/api/cooking/recipe/{self.dish2.id}/?count=10")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(results["count"], 10)
        self.assertAlmostEqual(results["ingredients"][0]["net_total"], 1.0)

    def test_recipe_not_found(self):
        r = self.client.get("/api/cooking/recipe/99999/")
        self.assertEqual(r.status_code, 404)


# ---- Delivery API ----

class DeliveryAPITest(OpsAPITestBase):
    def test_generate(self):
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 4),
            region=self.region, diet_category=self.diet, count=50)
        r = self.client.post("/api/delivery/generate/",
                             {"date": "2026-03-04", "meal_time": "L"}, format="json")
        self.assertIn(r.status_code, [200, 201])

    def test_generate_invalid(self):
        r = self.client.post("/api/delivery/generate/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_detail(self):
        from operations.models import DeliveryOrder
        do = DeliveryOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1), meal_time="L")
        r = self.client.get(f"/api/delivery/{do.id}/")
        self.assertEqual(r.status_code, 200)

    def test_detail_not_found(self):
        r = self.client.get("/api/delivery/99999/")
        self.assertEqual(r.status_code, 404)

    def test_by_region(self):
        from operations.models import DeliveryOrder, DeliveryItem
        do = DeliveryOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1), meal_time="L")
        DeliveryItem.objects.create(
            delivery=do, region=self.region, diet_category=self.diet, count=30)
        r = self.client.get(f"/api/delivery/{do.id}/by-region/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["region"], "East Wing")
        self.assertEqual(results[0]["total"], 30)

    def test_by_region_not_found(self):
        r = self.client.get("/api/delivery/99999/by-region/")
        self.assertEqual(r.status_code, 404)

    def test_export(self):
        from operations.models import DeliveryOrder, DeliveryItem
        do = DeliveryOrder.objects.create(
            company=self.company, target_date=date(2026, 3, 1), meal_time="L")
        DeliveryItem.objects.create(
            delivery=do, region=self.region, diet_category=self.diet, count=20)
        r = self.client.get(f"/api/delivery/{do.id}/export/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(results["company"], "Test Hospital")
        self.assertEqual(results["grand_total"], 20)

    def test_export_not_found(self):
        r = self.client.get("/api/delivery/99999/export/")
        self.assertEqual(r.status_code, 404)


# ---- Inventory Update on Receiving ----

class InventoryOnReceivingTest(OpsAPITestBase):
    """Tests for auto-updating material stock when a receiving record is created."""

    def _setup_full_scenario(self, initial_stock="0.00", actual_qty=12.0):
        """
        Create a full procurement + census + menu + recipe scenario.
        Returns (procurement, material).
        """
        from decimal import Decimal
        from core.models import DishIngredient, RawMaterial
        from operations.models import ProcurementRequest, ProcurementItem

        mat = RawMaterial.objects.create(
            name="InvMat", category=self.category, stock=Decimal(initial_stock)
        )
        # Recipe: dish1 uses 0.100 kg per serving of this material
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.100"
        )
        # Weekly menu for Monday (2030-01-07 is Monday, isoweekday=1)
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=1, meal_time="L"
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)

        # Census: 100 people
        DailyCensus.objects.create(
            company=self.company, date="2030-01-07",
            region=self.region, diet_category=self.diet, count=100
        )
        # Theoretical usage = 100 * 0.1 / 1.0 (yield=1) = 10 kg

        # Procurement order for that date
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date="2030-01-07", status="SUBMITTED"
        )
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="10.00", stock_quantity="0.00", purchase_quantity="10.00"
        )
        return pr, mat

    def test_receiving_updates_inventory(self):
        """Stock should increase by actual_received - theoretical_usage."""
        from decimal import Decimal
        pr, mat = self._setup_full_scenario(initial_stock="20.00")
        # actual_received = 15 kg, theoretical_usage = 10 kg
        # new_stock = 20 + 15 - 10 = 25
        data = {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 15.0},
            ],
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 201)
        mat.refresh_from_db()
        self.assertEqual(mat.stock, Decimal("25.00"))

    def test_inventory_floor_at_zero(self):
        """If new_stock < 0, set to 0 and include warning in message."""
        from decimal import Decimal
        pr, mat = self._setup_full_scenario(initial_stock="0.00")
        # actual_received = 5 kg, theoretical_usage = 10 kg
        # new_stock = 0 + 5 - 10 = -5 => floor to 0
        data = {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 5.0},
            ],
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 201)
        mat.refresh_from_db()
        self.assertEqual(mat.stock, Decimal("0"))
        # Should have a warning in the message
        self.assertIn("库存警告", r.json()["message"])

    def test_receiving_with_no_menu_only_adds_stock(self):
        """If no menu/census data, usage is 0, stock only increases."""
        from decimal import Decimal
        from core.models import RawMaterial
        from operations.models import ProcurementRequest, ProcurementItem

        mat = RawMaterial.objects.create(
            name="InvMatNoMenu", category=self.category, stock=Decimal("10.00")
        )
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date="2030-06-03", status="SUBMITTED"
        )
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="20.00", stock_quantity="10.00", purchase_quantity="10.00"
        )
        data = {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 20.0},
            ],
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 201)
        mat.refresh_from_db()
        # no usage, so: 10 + 20 - 0 = 30
        self.assertEqual(mat.stock, Decimal("30.00"))
