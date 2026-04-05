# -*- coding: utf-8 -*-
"""operations/tests/test_api.py"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import (
    ClientCompany,
    DietCategory,
    Dish,
    MaterialCategory,
    RawMaterial,
    UserProfile,
)
from operations.models import (
    ClientCompanyRegion,
    DailyCensus,
    ProcurementItem,
    ProcurementRequest,
    WeeklyMenu,
    WeeklyMenuDish,
)


class OpsAPITestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = ClientCompany.objects.create(
            id=1, name="Test Hospital", code="HOSP01"
        )
        cls.user = User.objects.create_user(
            username="opsuser", password="testpass123"
        )
        cls.profile = UserProfile.objects.create(
            user=cls.user, company=cls.company, role="RW"
        )
        cls.category = MaterialCategory.objects.create(name="Fresh")
        cls.diet = DietCategory.objects.create(name="Standard A")
        cls.region = ClientCompanyRegion.objects.create(
            company=cls.company, name="East Wing"
        )
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
        r = self.client.post(
            f"/api/companies/{self.company.id}/regions/", {"name": "ICU"}
        )
        self.assertEqual(r.status_code, 201)

    def test_create_duplicate_rejected(self):
        r = self.client.post(
            f"/api/companies/{self.company.id}/regions/", {"name": "East Wing"}
        )
        self.assertEqual(r.status_code, 400)

    def test_access_other_company_denied(self):
        co2 = ClientCompany.objects.create(name="Other", code="OTHER01")
        r = self.client.get(f"/api/companies/{co2.id}/regions/")
        self.assertEqual(r.status_code, 403)

    def test_unauthenticated(self):
        client = APIClient()
        r = client.get(f"/api/companies/{self.company.id}/regions/")
        self.assertEqual(r.status_code, 200)


class WeeklyMenuAPITest(OpsAPITestBase):
    def test_list(self):
        r = self.client.get("/api/weekly-menus/")
        self.assertEqual(r.status_code, 200)

    def test_create(self):
        r = self.client.post(
            "/api/weekly-menus/",
            {
                "company": self.company.id,
                "diet_category": self.diet.id,
                "day_of_week": 1,
                "meal_time": "L",
                "dishes": [self.dish1.id],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)

    def test_filter_by_company(self):
        WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="L",
        )
        r = self.client.get(f"/api/weekly-menus/?company={self.company.id}")
        self.assertEqual(r.status_code, 200)

    def test_batch_create(self):
        data = [
            {
                "company": self.company.id,
                "diet_category": self.diet.id,
                "day_of_week": 1,
                "meal_time": "B",
                "dishes": [self.dish1.id],
            },
            {
                "company": self.company.id,
                "diet_category": self.diet.id,
                "day_of_week": 1,
                "meal_time": "L",
                "dishes": [{"dish_id": self.dish1.id, "quantity": 2}],
            },
        ]
        r = self.client.post("/api/weekly-menus/batch/", data, format="json")
        self.assertEqual(r.status_code, 201)

    def test_update(self):
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=5,
            meal_time="D",
        )
        r = self.client.patch(
            f"/api/weekly-menus/{menu.id}/",
            {"dishes": [self.dish2.id]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_delete(self):
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=7,
            meal_time="B",
        )
        r = self.client.delete(f"/api/weekly-menus/{menu.id}/")
        self.assertEqual(r.status_code, 204)


class CensusAPITest(OpsAPITestBase):
    def test_list(self):
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        r = self.client.get("/api/census/?date=2026-03-01")
        self.assertEqual(r.status_code, 200)

    def test_batch_create(self):
        data = {
            "date": "2026-03-05",
            "items": [
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": 50,
                },
            ],
        }
        r = self.client.post("/api/census/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["created"], 1)

    def test_batch_update_existing(self):
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 10),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        data = {
            "date": "2026-03-10",
            "items": [
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": 80,
                },
            ],
        }
        r = self.client.post("/api/census/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["updated"], 1)
        dc = DailyCensus.objects.get(
            company=self.company,
            date=date(2026, 3, 10),
            region=self.region,
            diet_category=self.diet,
        )
        self.assertEqual(dc.count, 80)

    def test_summary(self):
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        r = self.client.get("/api/census/summary/?date=2026-03-01")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["total"], 50)

    def test_summary_does_not_include_other_company(self):
        co2 = ClientCompany.objects.create(name="Other", code="OTHER01")
        region2 = ClientCompanyRegion.objects.create(company=co2, name="Other Wing")

        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        DailyCensus.objects.create(
            company=co2,
            date=date(2026, 3, 1),
            region=region2,
            diet_category=self.diet,
            count=999,
        )

        r = self.client.get("/api/census/summary/?date=2026-03-01")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["total"], 50)

    def test_unauthenticated_access_allowed(self):
        self.client.logout()  # ensure no credentials

        r1 = self.client.get("/api/census/?date=2026-03-01")
        self.assertEqual(r1.status_code, 200)

        data = {
            "date": "2026-03-05",
            "items": [
                {
                    "region_id": self.region.id,
                    "diet_category_id": self.diet.id,
                    "count": 50,
                }
            ],
        }
        r2 = self.client.post("/api/census/batch/", data, format="json")
        self.assertEqual(r2.status_code, 200)


class OpsSearchAPITest(OpsAPITestBase):
    def test_weekly_menu_search(self):
        WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="L",
        )
        r = self.client.post(
            "/api/weekly-menus/search/",
            {"filters": {"company": self.company.id}},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_census_search(self):
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 1),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        r = self.client.post(
            "/api/census/search/",
            {"filters": {"date": "2026-03-01"}},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_procurement_search(self):
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        r = self.client.post(
            "/api/procurement/search/",
            {"filters": {"status": "CREATED"}},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_search_empty(self):
        r = self.client.post("/api/weekly-menus/search/", {}, format="json")
        self.assertEqual(r.status_code, 200)


class ProcurementAPITest(OpsAPITestBase):
    def _setup_full_menu(self, stock="0.00"):
        from core.models import DishIngredient

        mat = RawMaterial.objects.create(
            name="ProcMat", category=self.category, stock=stock
        )
        self.dish1.allowed_diets.add(self.diet)
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.100"
        )
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=date(2026, 3, 2).isoweekday(),
            meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 2),
            region=self.region,
            diet_category=self.diet,
            count=100,
        )
        return mat

    def test_generate(self):
        self._setup_full_menu()
        r = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])
        self.assertEqual(r.json()["results"]["status"], "CREATED")

    def test_generate_no_date(self):
        r = self.client.post("/api/procurement/generate/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_generate_includes_stock(self):
        mat = self._setup_full_menu(stock="3.00")
        r = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat
        ).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.stock_quantity, Decimal("3.00"))
        self.assertEqual(item.demand_quantity, Decimal("10.00"))
        self.assertEqual(item.purchase_quantity, Decimal("7.00"))

    def test_generate_stock_exceeds_demand(self):
        mat = self._setup_full_menu(stock="50.00")
        r = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat
        ).first()
        self.assertEqual(item.purchase_quantity, Decimal("0.00"))

    def test_generate_same_date_twice(self):
        self._setup_full_menu()

        r1 = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertIn(r1.status_code, [200, 201])

        r2 = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertIn(r2.status_code, [200, 201])

        self.assertEqual(
            ProcurementRequest.objects.filter(
                company=self.company,
                target_date=date(2026, 3, 2),
            ).count(),
            1,
        )

    def test_list(self):
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        r = self.client.get("/api/procurement/")
        self.assertEqual(r.status_code, 200)

    def test_detail(self):
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        r = self.client.get(f"/api/procurement/{pr.id}/")
        self.assertEqual(r.status_code, 200)

    def test_items(self):
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        mat = RawMaterial.objects.create(name="ProcItemMat", category=self.category)
        ProcurementItem.objects.create(
            request=pr,
            raw_material=mat,
            demand_quantity="12.50",
            stock_quantity="0",
            purchase_quantity="12.50",
        )
        r = self.client.get(f"/api/procurement/{pr.id}/items/")
        self.assertEqual(r.status_code, 200)

    def test_submit(self):
        pr = ProcurementRequest.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            status="CREATED",
        )
        r = self.client.post(f"/api/procurement/{pr.id}/submit/")
        self.assertEqual(r.status_code, 200)
        pr.refresh_from_db()
        self.assertEqual(pr.status, "SUBMITTED")

    def test_submit_non_created_rejected(self):
        pr = ProcurementRequest.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            status="SUBMITTED",
        )
        self.client.post(f"/api/procurement/{pr.id}/submit/")
        pr.refresh_from_db()
        self.assertEqual(pr.status, "SUBMITTED")

    def test_sheet(self):
        pr = ProcurementRequest.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            status="SUBMITTED",
        )
        r = self.client.get(f"/api/procurement/{pr.id}/sheet/")
        self.assertEqual(r.status_code, 200)

    def test_template(self):
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        r = self.client.get("/api/procurement/template/?date=2026-03-01")
        self.assertEqual(r.status_code, 200)

    def test_assign_suppliers(self):
        from core.models import Supplier, SupplierMaterial

        pr = ProcurementRequest.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            status="CREATED",
        )
        mat = RawMaterial.objects.create(name="AssignMat", category=self.category)
        item = ProcurementItem.objects.create(
            request=pr,
            raw_material=mat,
            demand_quantity="12.50",
            stock_quantity="0",
            purchase_quantity="12.50",
        )
        supplier = Supplier.objects.create(name="AssignSupplier")
        sm = SupplierMaterial.objects.create(
            supplier=supplier,
            raw_material=mat,
            unit_name="box",
            kg_per_unit="5.00",
        )
        r = self.client.post(
            "/api/procurement/assign-suppliers/?date=2026-03-01",
            {"assignments": [{"item_id": item.id, "supplier_material_id": sm.id}]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.supplier_kg_per_unit, Decimal("5.00"))
        pr.refresh_from_db()
        self.assertEqual(pr.status, "CREATED")

    def test_generate_prefills_default_supplier(self):
        from core.models import DishIngredient, Supplier, SupplierMaterial

        supplier = Supplier.objects.create(name="DefaultSupp")
        mat = RawMaterial.objects.create(
            name="DefSuppMat",
            category=self.category,
            default_supplier=supplier,
        )
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.100"
        )
        SupplierMaterial.objects.create(
            supplier=supplier,
            raw_material=mat,
            unit_name="bag",
            kg_per_unit="2.00",
            price="15.00",
        )

        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=date(2026, 3, 2).isoweekday(),
            meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 2),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )

        r = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat
        ).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.supplier_id, supplier.id)
        self.assertEqual(item.supplier_unit_name, "bag")
        self.assertEqual(item.supplier_kg_per_unit, Decimal("2.00"))
        self.assertEqual(item.supplier_price, Decimal("15.00"))

    def test_generate_no_default_supplier(self):
        mat = self._setup_full_menu()
        r = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

        item = ProcurementItem.objects.filter(
            request__target_date=date(2026, 3, 2), raw_material=mat
        ).first()
        self.assertIsNotNone(item)
        self.assertIsNone(item.supplier_id)


class ReceivingAPITest(OpsAPITestBase):
    def _create_procurement(self, target_date=None, status="SUBMITTED"):
        from datetime import timedelta
        from core.models import Supplier, SupplierMaterial

        td = target_date or (date.today() + timedelta(days=1))
        pr = ProcurementRequest.objects.create(
            company=self.company,
            target_date=td,
            status=status,
        )
        mat = RawMaterial.objects.create(name=f"RecvMat{td}", category=self.category)
        supplier = Supplier.objects.create(name=f"RecvSupp{td}")
        SupplierMaterial.objects.create(
            supplier=supplier,
            raw_material=mat,
            unit_name="box",
            kg_per_unit="5.00",
            price="10.00",
        )
        ProcurementItem.objects.create(
            request=pr,
            raw_material=mat,
            demand_quantity="12.50",
            stock_quantity="0",
            purchase_quantity="12.50",
            supplier=supplier,
            supplier_unit_name="box",
            supplier_kg_per_unit="5.00",
            supplier_price="10.00",
        )
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
        pr, mat, _ = self._create_procurement()
        data = {
            "procurement_id": pr.id,
            "notes": "All good",
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 12.0, "notes": ""},
            ],
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 201)
        pr.refresh_from_db()
        self.assertEqual(pr.status, "CONFIRMED")

    def test_receiving_updates_default_supplier(self):
        pr, mat, supplier = self._create_procurement()
        data = {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 12.0},
            ],
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 201)
        mat.refresh_from_db()
        self.assertEqual(mat.default_supplier_id, supplier.id)

    def test_create_not_found_procurement(self):
        data = {"procurement_id": 99999, "items": []}
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 404)

    def test_create_rejects_negative_actual_quantity(self):
        pr, mat, _ = self._create_procurement()
        data = {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": -1},
            ],
        }
        r = self.client.post("/api/receiving/", data, format="json")
        self.assertEqual(r.status_code, 400)

    def test_detail(self):
        from operations.models import ReceivingRecord

        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 1)
        )
        rr = ReceivingRecord.objects.create(procurement=pr, company=self.company)
        r = self.client.get(f"/api/receiving/{rr.id}/")
        self.assertEqual(r.status_code, 200)

    def test_detail_not_found(self):
        r = self.client.get("/api/receiving/99999/")
        self.assertEqual(r.status_code, 404)


class ProcessingAPITest(OpsAPITestBase):
    def _setup_processing(self):
        from core.models import DishIngredient, ProcessedMaterial

        mat = RawMaterial.objects.create(name="ProcMatX", category=self.category)
        pm = ProcessedMaterial.objects.create(raw_material=mat, method_name="Diced")
        DishIngredient.objects.create(
            dish=self.dish1,
            raw_material=mat,
            processing=pm,
            net_quantity="0.200",
        )
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=date(2026, 3, 3).isoweekday(),
            meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 3),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        return mat, pm

    def test_generate(self):
        self._setup_processing()
        r = self.client.post(
            "/api/processing/generate/",
            {"date": "2026-03-03"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

    def test_generate_no_date(self):
        r = self.client.post("/api/processing/generate/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_generate_creates_processing_items(self):
        self._setup_processing()
        r = self.client.post(
            "/api/processing/generate/",
            {"date": "2026-03-03"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

        from operations.models import ProcessingItem, ProcessingOrder

        order = ProcessingOrder.objects.filter(
            company=self.company,
            target_date=date(2026, 3, 3),
        ).first()
        self.assertIsNotNone(order)
        self.assertTrue(ProcessingItem.objects.filter(order=order).exists())
    
    def test_search(self):
        self._setup_processing()
        self.client.post(
            "/api/processing/generate/",
            {"date": "2026-03-03"},
            format="json",
        )

        r = self.client.post(
            "/api/processing/search/",
            {"date": "2026-03-03"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(len(r.json()["results"]) > 0)


    def test_search_by_material(self):
        mat, _ = self._setup_processing()
        self.client.post(
            "/api/processing/generate/",
            {"date": "2026-03-03"},
            format="json",
        )

        r = self.client.post(
            "/api/processing/search/",
            {"date": "2026-03-03", "material_id": mat.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertTrue(all(row["material_id"] == mat.id for row in results))

  
class CookingAPITest(OpsAPITestBase):
    def test_today(self):
        r = self.client.get("/api/cooking/today/")
        self.assertEqual(r.status_code, 200)

    def test_today_with_filters(self):
        r = self.client.get(
            f"/api/cooking/today/?meal_time=L&company={self.company.id}"
        )
        self.assertEqual(r.status_code, 200)

    def test_recipe(self):
        from core.models import DishIngredient

        mat = RawMaterial.objects.create(name="RecipeMat", category=self.category)
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.300"
        )
        r = self.client.get(f"/api/cooking/recipe/{self.dish1.id}/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(results["dish_name"], "Tomato Egg")
        self.assertEqual(len(results["ingredients"]), 1)

    def test_recipe_with_count(self):
        from core.models import DishIngredient

        mat = RawMaterial.objects.create(name="RecipeMatScale", category=self.category)
        DishIngredient.objects.create(
            dish=self.dish2, raw_material=mat, net_quantity="0.100"
        )
        r = self.client.get(f"/api/cooking/recipe/{self.dish2.id}/?count=10")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(results["count"], 10)
        self.assertAlmostEqual(results["ingredients"][0]["net_total"], 1.0)

    def test_recipe_not_found(self):
        r = self.client.get("/api/cooking/recipe/99999/")
        self.assertEqual(r.status_code, 404)


class DeliveryAPITest(OpsAPITestBase):
    def test_generate(self):
        DailyCensus.objects.create(
            company=self.company,
            date=date(2026, 3, 4),
            region=self.region,
            diet_category=self.diet,
            count=50,
        )
        r = self.client.post(
            "/api/delivery/generate/",
            {"date": "2026-03-04", "meal_time": "L"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

    def test_generate_invalid(self):
        r = self.client.post("/api/delivery/generate/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_detail(self):
        from operations.models import DeliveryOrder

        do = DeliveryOrder.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            meal_time="L",
        )
        r = self.client.get(f"/api/delivery/{do.id}/")
        self.assertEqual(r.status_code, 200)

    def test_detail_not_found(self):
        r = self.client.get("/api/delivery/99999/")
        self.assertEqual(r.status_code, 404)

    def test_by_region(self):
        from operations.models import DeliveryItem, DeliveryOrder

        do = DeliveryOrder.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            meal_time="L",
        )
        DeliveryItem.objects.create(
            delivery=do,
            region=self.region,
            diet_category=self.diet,
            count=30,
        )
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
        from operations.models import DeliveryItem, DeliveryOrder

        do = DeliveryOrder.objects.create(
            company=self.company,
            target_date=date(2026, 3, 1),
            meal_time="L",
        )
        DeliveryItem.objects.create(
            delivery=do,
            region=self.region,
            diet_category=self.diet,
            count=20,
        )
        r = self.client.get(f"/api/delivery/{do.id}/export/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(results["company"], "Test Hospital")
        self.assertEqual(results["grand_total"], 20)

    def test_export_not_found(self):
        r = self.client.get("/api/delivery/99999/export/")
        self.assertEqual(r.status_code, 404)


class InventoryOnReceivingTest(OpsAPITestBase):
    def _setup_full_scenario(self, initial_stock="0.00"):
        from core.models import DishIngredient

        mat = RawMaterial.objects.create(
            name="InvMat",
            category=self.category,
            stock=Decimal(initial_stock),
        )
        DishIngredient.objects.create(
            dish=self.dish1,
            raw_material=mat,
            net_quantity="0.100",
        )
        menu = WeeklyMenu.objects.create(
            company=self.company,
            diet_category=self.diet,
            day_of_week=1,
            meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)

        DailyCensus.objects.create(
            company=self.company,
            date="2030-01-07",
            region=self.region,
            diet_category=self.diet,
            count=100,
        )

        pr = ProcurementRequest.objects.create(
            company=self.company,
            target_date="2030-01-07",
            status="SUBMITTED",
        )
        ProcurementItem.objects.create(
            request=pr,
            raw_material=mat,
            demand_quantity="10.00",
            stock_quantity="0.00",
            purchase_quantity="10.00",
        )
        return pr, mat

    def test_receiving_updates_inventory(self):
        pr, mat = self._setup_full_scenario(initial_stock="20.00")
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
        pr, mat = self._setup_full_scenario(initial_stock="0.00")
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
        self.assertIn("Inventory warnings", r.json()["message"])

    def test_receiving_with_no_menu_only_adds_stock(self):
        mat = RawMaterial.objects.create(
            name="InvMatNoMenu",
            category=self.category,
            stock=Decimal("10.00"),
        )
        pr = ProcurementRequest.objects.create(
            company=self.company,
            target_date="2030-06-03",
            status="SUBMITTED",
        )
        ProcurementItem.objects.create(
            request=pr,
            raw_material=mat,
            demand_quantity="20.00",
            stock_quantity="10.00",
            purchase_quantity="10.00",
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
        self.assertEqual(mat.stock, Decimal("30.00"))


# ---- Coverage boost: Search Views ----

class SearchViewsCoverageTest(OpsAPITestBase):
    """Tests to cover all filter branches in search_views.py."""

    def test_weekly_menu_search_all_filters(self):
        """Cover lines 31, 33, 35, 37 in WeeklyMenuSearchView.apply_filters."""
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=2, meal_time="L",
        )
        r = self.client.post(
            "/api/weekly-menus/search/",
            {
                "company": self.company.id,
                "diet_category": self.diet.id,
                "day_of_week": 2,
                "meal_time": "L",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_census_search_with_date_padding(self):
        """Cover the padded-results branch (lines 82-182) in CensusSearchView.post."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=10,
        )
        r = self.client.post(
            "/api/census/search/",
            {"date": "2026-04-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertGreaterEqual(results["total"], 1)

    def test_census_search_date_range(self):
        """Cover start/end range branch (lines 98-109)."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=5,
        )
        r = self.client.post(
            "/api/census/search/",
            {"start": "2026-04-01", "end": "2026-04-02"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()["results"]["total"], 1)

    def test_census_search_ordering_reverse(self):
        """Cover ordering branch (lines 153-166)."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=5,
        )
        r = self.client.post(
            "/api/census/search/",
            {"date": "2026-04-01", "ordering": "-date"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_census_search_pagination(self):
        """Cover pagination branch (lines 169-173)."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=5,
        )
        r = self.client.post(
            "/api/census/search/",
            {"date": "2026-04-01", "page": 1, "page_size": 5},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["page_size"], 5)

    def test_census_search_with_region_filter(self):
        """Cover region_id filter (line 68, 115-116)."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=5,
        )
        r = self.client.post(
            "/api/census/search/",
            {"date": "2026-04-01", "region_id": self.region.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_census_search_with_diet_filter(self):
        """Cover diet_category_id filter (line 70, 119-120)."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=5,
        )
        r = self.client.post(
            "/api/census/search/",
            {"date": "2026-04-01", "diet_category_id": self.diet.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_census_search_no_date_params(self):
        """Cover the fallback super().post() path (line 80)."""
        r = self.client.post(
            "/api/census/search/",
            {},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_procurement_search_with_date_range(self):
        """Cover start/end filter in ProcurementSearchView (lines 202-209)."""
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 1),
        )
        r = self.client.post(
            "/api/procurement/search/",
            {"start": "2026-04-01", "end": "2026-04-30"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_procurement_search_with_exact_date(self):
        """Cover date filter (line 204)."""
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 1),
        )
        r = self.client.post(
            "/api/procurement/search/",
            {"date": "2026-04-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_receiving_search(self):
        """Cover ReceivingSearchView (lines 222-241)."""
        from operations.models import ReceivingRecord
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 1),
        )
        ReceivingRecord.objects.create(procurement=pr, company=self.company)
        r = self.client.post(
            "/api/receiving/search/",
            {"date": "2026-04-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_receiving_search_status_and_range(self):
        """Cover status + start/end filters."""
        from operations.models import ReceivingRecord
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 1),
        )
        ReceivingRecord.objects.create(
            procurement=pr, company=self.company, status="PENDING",
        )
        r = self.client.post(
            "/api/receiving/search/",
            {"status": "PENDING", "start": "2026-03-01", "end": "2026-05-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_delivery_search(self):
        """Cover DeliverySearchView (lines 254-273)."""
        from operations.models import DeliveryOrder
        DeliveryOrder.objects.create(
            company=self.company, target_date=date(2026, 4, 1), meal_time="L",
        )
        r = self.client.post(
            "/api/delivery/search/",
            {"meal_time": "L", "date": "2026-04-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_delivery_search_range(self):
        """Cover start/end filters (lines 268-271)."""
        from operations.models import DeliveryOrder
        DeliveryOrder.objects.create(
            company=self.company, target_date=date(2026, 4, 1), meal_time="L",
        )
        r = self.client.post(
            "/api/delivery/search/",
            {"start": "2026-04-01", "end": "2026-04-30"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)


# ---- Coverage boost: Cooking Views ----

class CookingViewsCoverageTest(OpsAPITestBase):
    """Tests to cover CookingTodayView with actual menu/census data."""

    def test_today_with_data(self):
        """Cover lines 48-95 in CookingTodayView (menu iteration, headcount,
        dishes_data, ingredients loop)."""
        from core.models import DishIngredient, ProcessedMaterial

        today = date.today()
        day_of_week = today.isoweekday()

        mat = RawMaterial.objects.create(name="CookMat", category=self.category)
        pm = ProcessedMaterial.objects.create(raw_material=mat, method_name="Sliced")

        # Ingredient with processing
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, processing=pm, net_quantity="0.200",
        )
        # Ingredient without processing
        mat2 = RawMaterial.objects.create(name="CookMat2", category=self.category)
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat2, net_quantity="0.050",
        )

        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=day_of_week, meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=2)

        DailyCensus.objects.create(
            company=self.company, date=today,
            region=self.region, diet_category=self.diet, count=50,
        )

        r = self.client.get("/api/cooking/today/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertTrue(len(results) >= 1)
        first = results[0]
        self.assertEqual(first["headcount"], 50)
        self.assertTrue(len(first["dishes"]) >= 1)
        dish_data = first["dishes"][0]
        self.assertEqual(dish_data["quantity"], 2)
        self.assertTrue(len(dish_data["ingredients"]) >= 2)

        # Check one ingredient has method, one doesn't
        methods = [i["method"] for i in dish_data["ingredients"]]
        self.assertIn("Sliced", methods)
        self.assertIn(None, methods)


# ---- Coverage boost: Delivery Views ----

class DeliveryViewsCoverageTest(OpsAPITestBase):
    """Tests to cover DeliveryDetailView.patch and regeneration."""

    def test_generate_regenerates_existing(self):
        """Cover lines 57-58 (not created => delete items)."""
        from operations.models import DeliveryItem, DeliveryOrder

        DailyCensus.objects.create(
            company=self.company, date=date(2026, 5, 1),
            region=self.region, diet_category=self.diet, count=30,
        )
        # First generate
        r1 = self.client.post(
            "/api/delivery/generate/",
            {"date": "2026-05-01", "meal_time": "L"},
            format="json",
        )
        self.assertIn(r1.status_code, [200, 201])
        # Second generate (regenerate)
        r2 = self.client.post(
            "/api/delivery/generate/",
            {"date": "2026-05-01", "meal_time": "L"},
            format="json",
        )
        self.assertIn(r2.status_code, [200, 201])
        # Should still have only one order
        self.assertEqual(
            DeliveryOrder.objects.filter(
                company=self.company, target_date=date(2026, 5, 1), meal_time="L",
            ).count(), 1
        )

    def test_generate_skips_zero_count(self):
        """Cover line 61 (count > 0 check) and 48 (no census)."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 5, 2),
            region=self.region, diet_category=self.diet, count=0,
        )
        r = self.client.post(
            "/api/delivery/generate/",
            {"date": "2026-05-02", "meal_time": "L"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

    def test_patch_delivery_detail(self):
        """Cover lines 97-154 in DeliveryDetailView.patch."""
        from operations.models import DeliveryItem, DeliveryOrder
        from datetime import timedelta

        future_date = date.today() + timedelta(days=5)
        do = DeliveryOrder.objects.create(
            company=self.company, target_date=future_date, meal_time="L",
        )
        item = DeliveryItem.objects.create(
            delivery=do, region=self.region, diet_category=self.diet, count=30,
        )
        r = self.client.patch(
            "/api/delivery/%d/" % do.id,
            {"items": [{"id": item.id, "count": 50}]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.count, 50)

    def test_patch_delivery_invalid_item_id(self):
        """Cover lines 135-141 (invalid item IDs)."""
        from operations.models import DeliveryOrder
        from datetime import timedelta

        future_date = date.today() + timedelta(days=5)
        do = DeliveryOrder.objects.create(
            company=self.company, target_date=future_date, meal_time="L",
        )
        r = self.client.patch(
            "/api/delivery/%d/" % do.id,
            {"items": [{"id": 99999, "count": 10}]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_patch_delivery_not_found(self):
        """Cover line 114-119 (order not found)."""
        r = self.client.patch(
            "/api/delivery/99999/",
            {"items": [{"id": 1, "count": 10}]},
            format="json",
        )
        self.assertEqual(r.status_code, 404)

    def test_patch_delivery_validation_error(self):
        """Cover lines 98-104 (invalid body)."""
        from operations.models import DeliveryOrder
        from datetime import timedelta

        future_date = date.today() + timedelta(days=5)
        do = DeliveryOrder.objects.create(
            company=self.company, target_date=future_date, meal_time="L",
        )
        r = self.client.patch(
            "/api/delivery/%d/" % do.id,
            {"bad_field": "xxx"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)


# ---- Coverage boost: Census Views ----

class CensusViewsCoverageTest(OpsAPITestBase):
    """Tests to cover date range filtering in census list and summary."""

    def test_list_start_end(self):
        """Cover lines 39-42 in DailyCensusListView."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=50,
        )
        r = self.client.get("/api/census/?start=2026-04-01&end=2026-04-30")
        self.assertEqual(r.status_code, 200)

    def test_list_region_and_diet_filter(self):
        """Cover lines 45, 47 filters."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 2),
            region=self.region, diet_category=self.diet, count=20,
        )
        r = self.client.get(
            "/api/census/?date=2026-04-02&region_id=%d&diet_category_id=%d"
            % (self.region.id, self.diet.id)
        )
        self.assertEqual(r.status_code, 200)

    def test_summary_start_end(self):
        """Cover lines 111-114 in DailyCensusSummaryView."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 4, 1),
            region=self.region, diet_category=self.diet, count=50,
        )
        r = self.client.get("/api/census/summary/?start=2026-04-01&end=2026-04-30")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["total"], 50)

    def test_batch_create_multiple_items(self):
        """Cover the batch loop with multiple items to verify correct counts."""
        region2 = ClientCompanyRegion.objects.create(company=self.company, name="West Wing")
        data = {
            "date": "2026-04-01",
            "items": [
                {"region_id": self.region.id, "diet_category_id": self.diet.id, "count": 10},
                {"region_id": region2.id, "diet_category_id": self.diet.id, "count": 20},
            ],
        }
        r = self.client.post("/api/census/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["created"], 2)


# ---- Coverage boost: Procurement Views ----

class ProcurementViewsCoverageTest(OpsAPITestBase):
    """Tests to cover edge cases in procurement_views.py."""

    def test_detail_not_found(self):
        """Cover line 63 (NotFound)."""
        r = self.client.get("/api/procurement/99999/")
        self.assertEqual(r.status_code, 404)

    def test_items_not_found(self):
        """Cover line 75 (NotFound)."""
        r = self.client.get("/api/procurement/99999/items/")
        self.assertEqual(r.status_code, 404)

    def test_items_group_by_supplier(self):
        """Cover lines 83-95 (group_by=supplier)."""
        from core.models import Supplier
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 1),
        )
        mat = RawMaterial.objects.create(name="GBSMat", category=self.category)
        supplier = Supplier.objects.create(name="GBSSupp")
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="10", stock_quantity="0", purchase_quantity="10",
            supplier=supplier,
        )
        r = self.client.get("/api/procurement/%d/items/?group_by=supplier" % pr.id)
        self.assertEqual(r.status_code, 200)

    def test_items_group_by_category(self):
        """Cover lines 97-109 (group_by=category)."""
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 2),
        )
        mat = RawMaterial.objects.create(name="GBCMat", category=self.category)
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="10", stock_quantity="0", purchase_quantity="10",
        )
        r = self.client.get("/api/procurement/%d/items/?group_by=category" % pr.id)
        self.assertEqual(r.status_code, 200)

    def test_items_group_by_invalid(self):
        """Cover line 111 (invalid group_by)."""
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 3),
        )
        r = self.client.get("/api/procurement/%d/items/?group_by=invalid" % pr.id)
        self.assertEqual(r.status_code, 400)

    def test_submit_not_found(self):
        """Cover line 128 (NotFound)."""
        r = self.client.post("/api/procurement/99999/submit/")
        self.assertEqual(r.status_code, 404)

    def test_generate_no_census(self):
        """Cover line 174 (no census)."""
        r = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-12-25"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_generate_submitted_rejected(self):
        """Cover lines 252-255 (SUBMITTED status rejection)."""
        from core.models import DishIngredient
        mat = RawMaterial.objects.create(name="SubRejMat", category=self.category)
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.100",
        )
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=date(2026, 3, 2).isoweekday(), meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 3, 2),
            region=self.region, diet_category=self.diet, count=100,
        )
        # Create existing SUBMITTED procurement
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 3, 2), status="SUBMITTED",
        )
        r = self.client.post(
            "/api/procurement/generate/",
            {"date": "2026-03-02"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_sheet_not_found(self):
        """Cover line 326 (NotFound)."""
        r = self.client.get("/api/procurement/99999/sheet/")
        self.assertEqual(r.status_code, 404)

    def test_sheet_with_supplier_data(self):
        """Cover lines 334-368 (sheet with supplier unit conversion)."""
        from core.models import Supplier

        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 10), status="CREATED",
        )
        mat = RawMaterial.objects.create(name="SheetMat", category=self.category)
        supplier = Supplier.objects.create(name="SheetSupp")
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="20.00", stock_quantity="5.00", purchase_quantity="15.00",
            supplier=supplier, supplier_unit_name="box",
            supplier_kg_per_unit="5.00", supplier_price="25.00",
        )
        r = self.client.get("/api/procurement/%d/sheet/" % pr.id)
        self.assertEqual(r.status_code, 200)
        items = r.json()["results"]["items"]
        self.assertEqual(len(items), 1)
        self.assertIsNotNone(items[0]["demand_unit_qty"])
        self.assertIsNotNone(items[0]["purchase_unit_qty"])
        self.assertEqual(items[0]["supplier"], "SheetSupp")

    def test_template_no_date(self):
        """Cover line 384 (missing date param)."""
        r = self.client.get("/api/procurement/template/")
        self.assertEqual(r.status_code, 400)

    def test_template_not_found(self):
        """Cover line 390 (no procurement for date)."""
        r = self.client.get("/api/procurement/template/?date=2099-01-01")
        self.assertEqual(r.status_code, 404)

    def test_template_with_supplier_materials(self):
        """Cover lines 396-432 (template with available suppliers)."""
        from core.models import Supplier, SupplierMaterial

        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 15),
        )
        mat = RawMaterial.objects.create(name="TplMat", category=self.category)
        supplier = Supplier.objects.create(name="TplSupp")
        SupplierMaterial.objects.create(
            supplier=supplier, raw_material=mat,
            unit_name="bag", kg_per_unit="2.00", price="10.00",
        )
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="10", stock_quantity="0", purchase_quantity="10",
        )
        r = self.client.get("/api/procurement/template/?date=2026-04-15")
        self.assertEqual(r.status_code, 200)
        items = r.json()["results"]["items"]
        self.assertEqual(len(items), 1)
        self.assertTrue(len(items[0]["available_suppliers"]) >= 1)

    def test_assign_suppliers_no_date(self):
        """Cover line 458 (missing date)."""
        r = self.client.post(
            "/api/procurement/assign-suppliers/",
            {"assignments": []},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_assign_suppliers_not_found(self):
        """Cover line 464 (no procurement for date)."""
        r = self.client.post(
            "/api/procurement/assign-suppliers/?date=2099-01-01",
            {"assignments": [{"item_id": 1, "supplier_material_id": 1}]},
            format="json",
        )
        self.assertEqual(r.status_code, 404)

    def test_assign_suppliers_wrong_status(self):
        """Cover line 467 (status not CREATED)."""
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 20), status="SUBMITTED",
        )
        r = self.client.post(
            "/api/procurement/assign-suppliers/?date=2026-04-20",
            {"assignments": [{"item_id": 1, "supplier_material_id": 1}]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_assign_suppliers_empty_list(self):
        """Cover line 471 (empty assignments)."""
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 21), status="CREATED",
        )
        r = self.client.post(
            "/api/procurement/assign-suppliers/?date=2026-04-21",
            {"assignments": []},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_assign_suppliers_invalid_item(self):
        """Cover line 481-484 (invalid item_id)."""
        ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 22), status="CREATED",
        )
        r = self.client.post(
            "/api/procurement/assign-suppliers/?date=2026-04-22",
            {"assignments": [{"item_id": 99999, "supplier_material_id": 1}]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_assign_suppliers_invalid_sm(self):
        """Cover lines 490-491 (invalid supplier_material_id)."""
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 4, 23), status="CREATED",
        )
        mat = RawMaterial.objects.create(name="ASInvMat", category=self.category)
        item = ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="10", stock_quantity="0", purchase_quantity="10",
        )
        r = self.client.post(
            "/api/procurement/assign-suppliers/?date=2026-04-23",
            {"assignments": [{"item_id": item.id, "supplier_material_id": 99999}]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)


# ---- Branch Coverage: operations/viewsets.py ----

class ViewSetBranchTest(OpsAPITestBase):
    """Cover filter branches in WeeklyMenuViewSet.get_queryset and _set_dishes."""

    def test_filter_by_diet_category(self):
        """Branch 47->48: diet_category filter."""
        WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=1, meal_time="L",
        )
        r = self.client.get("/api/weekly-menus/?diet_category=%d" % self.diet.id)
        self.assertEqual(r.status_code, 200)

    def test_filter_by_day_of_week(self):
        """Branch 51->52: day_of_week filter."""
        r = self.client.get("/api/weekly-menus/?day_of_week=1")
        self.assertEqual(r.status_code, 200)

    def test_filter_by_meal_time(self):
        """Branch 55->56: meal_time filter."""
        r = self.client.get("/api/weekly-menus/?meal_time=L")
        self.assertEqual(r.status_code, 200)

    def test_set_dishes_none(self):
        """Branch 66->67: dishes_data is None."""
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=self.diet,
            day_of_week=3, meal_time="D",
        )
        # PATCH without dishes key
        r = self.client.patch(
            "/api/weekly-menus/%d/" % menu.id,
            {"meal_time": "D"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_set_dishes_dict_format(self):
        """Branch 69->70: dish as dict with dish_id and quantity."""
        r = self.client.post(
            "/api/weekly-menus/",
            {
                "company": self.company.id,
                "diet_category": self.diet.id,
                "day_of_week": 4,
                "meal_time": "B",
                "dishes": [{"dish_id": self.dish1.id, "quantity": 3}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)

    def test_batch_create_validation_error(self):
        """Branch 119->128: serializer invalid."""
        r = self.client.post(
            "/api/weekly-menus/batch/",
            [{"invalid": "data"}],
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_update_with_empty_dishes(self):
        """Branch 82->83 false: no dishes_data on create."""
        r = self.client.post(
            "/api/weekly-menus/",
            {
                "company": self.company.id,
                "diet_category": self.diet.id,
                "day_of_week": 6,
                "meal_time": "D",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)


# ---- Branch Coverage: operations/views/processing_views.py ----

class ProcessingBranchTest(OpsAPITestBase):
    """Cover edge case branches in processing views."""

    def test_generate_no_menu(self):
        """Branch 88->89: no menus found."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 6, 1),
            region=self.region, diet_category=self.diet, count=50,
        )
        r = self.client.post(
            "/api/processing/generate/",
            {"date": "2026-06-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 404)

    def test_generate_no_census(self):
        """Branch 76->77: no census found."""
        r = self.client.post(
            "/api/processing/generate/",
            {"date": "2026-12-25"},
            format="json",
        )
        self.assertEqual(r.status_code, 404)

    def test_generate_headcount_zero_skipped(self):
        """Branch 117->118: headcount=0 skipped."""
        from core.models import DishIngredient

        diet2 = DietCategory.objects.create(name="Zero Diet")
        mat = RawMaterial.objects.create(name="ProcBrMat", category=self.category)
        DishIngredient.objects.create(
            dish=self.dish1, raw_material=mat, net_quantity="0.100",
        )
        menu = WeeklyMenu.objects.create(
            company=self.company, diet_category=diet2,
            day_of_week=date(2026, 6, 2).isoweekday(), meal_time="L",
        )
        WeeklyMenuDish.objects.create(menu=menu, dish=self.dish1, quantity=1)
        # Census for a different diet with 0 count
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 6, 2),
            region=self.region, diet_category=diet2, count=0,
        )
        # Need at least one non-zero to avoid "no census" error
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 6, 2),
            region=self.region, diet_category=self.diet, count=10,
        )
        r = self.client.post(
            "/api/processing/generate/",
            {"date": "2026-06-02"},
            format="json",
        )
        self.assertIn(r.status_code, [200, 201])

    def test_search_no_order(self):
        """Branch 198->199: no processing order found."""
        r = self.client.post(
            "/api/processing/search/",
            {"date": "2099-01-01"},
            format="json",
        )
        self.assertEqual(r.status_code, 404)


# ---- Branch Coverage: operations/views/receiving_views.py ----

class ReceivingBranchTest(OpsAPITestBase):
    """Cover receiving edge case branches."""

    def test_template_non_submitted(self):
        """Branch 44->45: procurement not SUBMITTED."""
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 7, 1),
            status="CREATED",
        )
        r = self.client.get("/api/receiving/%d/template/" % pr.id)
        self.assertEqual(r.status_code, 400)

    def test_create_non_submitted_procurement(self):
        """Branch 121->122: procurement status != SUBMITTED."""
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=date(2026, 7, 2),
            status="CREATED",
        )
        r = self.client.post("/api/receiving/", {
            "procurement_id": pr.id,
            "items": [],
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_create_invalid_raw_material(self):
        """Branch 147->148: invalid raw_material_id not in procurement."""
        from datetime import timedelta
        future = date.today() + timedelta(days=30)
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=future, status="SUBMITTED",
        )
        mat = RawMaterial.objects.create(name="RecvBrMat", category=self.category)
        ProcurementItem.objects.create(
            request=pr, raw_material=mat,
            demand_quantity="10", stock_quantity="0", purchase_quantity="10",
        )
        # Send a raw_material_id that doesn't belong to this procurement
        mat2 = RawMaterial.objects.create(name="RecvBrMat2", category=self.category)
        r = self.client.post("/api/receiving/", {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat.id, "actual_quantity": 10},
                {"raw_material_id": mat2.id, "actual_quantity": 5},
            ],
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_create_with_missing_items_defaults_to_zero(self):
        """Branch 170->174: item not in incoming_items_map."""
        from datetime import timedelta
        future = date.today() + timedelta(days=30)
        pr = ProcurementRequest.objects.create(
            company=self.company, target_date=future, status="SUBMITTED",
        )
        mat1 = RawMaterial.objects.create(name="RecvMiss1", category=self.category)
        mat2 = RawMaterial.objects.create(name="RecvMiss2", category=self.category)
        ProcurementItem.objects.create(
            request=pr, raw_material=mat1,
            demand_quantity="10", stock_quantity="0", purchase_quantity="10",
        )
        ProcurementItem.objects.create(
            request=pr, raw_material=mat2,
            demand_quantity="5", stock_quantity="0", purchase_quantity="5",
        )
        # Only send one of the two materials
        r = self.client.post("/api/receiving/", {
            "procurement_id": pr.id,
            "items": [
                {"raw_material_id": mat1.id, "actual_quantity": 10},
            ],
        }, format="json")
        self.assertEqual(r.status_code, 201)
        # Check the result has warnings about missing items
        results = r.json()["results"]
        self.assertIn("warnings", results)


# ---- Branch Coverage: operations/views/census_views.py ----

class CensusViewBranchTest(OpsAPITestBase):
    """Cover start-only and end-only filter branches."""

    def test_list_start_only(self):
        """Branch 39->41 true, 41->44 false: only start param."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 5, 1),
            region=self.region, diet_category=self.diet, count=10,
        )
        r = self.client.get("/api/census/?start=2026-05-01")
        self.assertEqual(r.status_code, 200)

    def test_list_end_only(self):
        """Branch 39->41 false, 41->44 true: only end param."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 5, 1),
            region=self.region, diet_category=self.diet, count=10,
        )
        r = self.client.get("/api/census/?end=2026-05-31")
        self.assertEqual(r.status_code, 200)

    def test_summary_start_only(self):
        """Branch 111->113 true, 113->116 false."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 5, 1),
            region=self.region, diet_category=self.diet, count=10,
        )
        r = self.client.get("/api/census/summary/?start=2026-05-01")
        self.assertEqual(r.status_code, 200)

    def test_summary_end_only(self):
        """Branch 111->113 false, 113->116 true."""
        DailyCensus.objects.create(
            company=self.company, date=date(2026, 5, 1),
            region=self.region, diet_category=self.diet, count=10,
        )
        r = self.client.get("/api/census/summary/?end=2026-05-31")
        self.assertEqual(r.status_code, 200)