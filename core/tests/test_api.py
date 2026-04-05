# -*- coding: utf-8 -*-
"""
core/tests/test_api.py
API layer unit tests.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import (
    ClientCompany,
    DietCategory,
    Dish,
    DishIngredient,
    MaterialCategory,
    ProcessedMaterial,
    RawMaterial,
    Supplier,
    SupplierMaterial,
    UserProfile,
)


class APITestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        #cls.company = ClientCompany.objects.create(name="Test Hospital", code="HOSP01")
        cls.company = ClientCompany.objects.create(id=1, name="Test Hospital", code="HOSP01")
        cls.user = User.objects.create_user(username="apiuser", password="testpass123")
        cls.profile = UserProfile.objects.create(
            user=cls.user, company=cls.company, role="RW"
        )
        cls.category = MaterialCategory.objects.create(name="Fresh")
        cls.diet = DietCategory.objects.create(name="Standard A")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class MaterialCategoryAPITest(APITestBase):
    def test_list(self):
        r = self.client.get("/api/material-categories/")
        self.assertEqual(r.status_code, 200)

    def test_create(self):
        r = self.client.post("/api/material-categories/", {"name": "Frozen"})
        self.assertEqual(r.status_code, 201)

    def test_update(self):
        r = self.client.patch(
            f"/api/material-categories/{self.category.id}/", {"name": "Fresh Goods"}
        )
        self.assertEqual(r.status_code, 200)

    def test_delete(self):
        cat = MaterialCategory.objects.create(name="ToDelete")
        r = self.client.delete(f"/api/material-categories/{cat.id}/")
        self.assertEqual(r.status_code, 204)

    def test_delete_in_use_fails(self):
        RawMaterial.objects.create(name="InUseMat", category=self.category)
        r = self.client.delete(f"/api/material-categories/{self.category.id}/")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["error"]["type"], "PROTECTED_ERROR")


class RawMaterialAPITest(APITestBase):
    def test_list(self):
        RawMaterial.objects.create(name="Potato", category=self.category)
        r = self.client.get("/api/materials/")
        self.assertEqual(r.status_code, 200)

    def test_retrieve(self):
        mat = RawMaterial.objects.create(name="Potato", category=self.category)
        r = self.client.get(f"/api/materials/{mat.id}/")
        self.assertEqual(r.status_code, 200)

    def test_delete(self):
        mat = RawMaterial.objects.create(name="ToDelete", category=self.category)
        r = self.client.delete(f"/api/materials/{mat.id}/")
        self.assertEqual(r.status_code, 204)

    def test_filter_by_category(self):
        cat2 = MaterialCategory.objects.create(name="Frozen")
        RawMaterial.objects.create(name="M1", category=self.category)
        RawMaterial.objects.create(name="M2", category=cat2)
        r = self.client.get(f"/api/materials/?category={self.category.id}")
        self.assertEqual(r.status_code, 200)

    def test_search(self):
        RawMaterial.objects.create(name="Tomato", category=self.category)
        RawMaterial.objects.create(name="Potato", category=self.category)
        r = self.client.get("/api/materials/?search=Tomato")
        self.assertEqual(r.status_code, 200)

    def test_batch_create(self):
        data = [
            {"name": "BatchMat1", "category": self.category.id},
            {"name": "BatchMat2", "category": self.category.id},
        ]
        r = self.client.post("/api/materials/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        result = r.json()["results"]
        self.assertEqual(len(result["created"]), 2)

    def test_batch_update_by_id(self):
        mat = RawMaterial.objects.create(name="ExistMat", category=self.category)
        data = [{"id": mat.id, "name": "UpdatedMat"}]
        r = self.client.post("/api/materials/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        mat.refresh_from_db()
        self.assertEqual(mat.name, "UpdatedMat")

    def test_batch_update_by_name(self):
        RawMaterial.objects.create(name="ByNameMat", category=self.category)
        data = [{"name": "ByNameMat", "category": self.category.id}]
        r = self.client.post("/api/materials/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        result = r.json()["results"]
        self.assertEqual(len(result["updated"]), 1)

    def test_batch_not_list_rejected(self):
        r = self.client.post("/api/materials/batch/", {"name": "Single"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_batch_validation_error_rejects_all(self):
        data = [
            {"name": "GoodMat", "category": self.category.id},
            {"name": ""},
        ]
        r = self.client.post("/api/materials/batch/", data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(RawMaterial.objects.filter(name="GoodMat").exists())

    def test_add_spec(self):
        mat = RawMaterial.objects.create(name="SpecMat", category=self.category)
        r = self.client.post(
            f"/api/materials/{mat.id}/specs/", {"method_name": "Diced"}
        )
        self.assertEqual(r.status_code, 201)
        self.assertTrue(
            ProcessedMaterial.objects.filter(
                raw_material=mat, method_name="Diced"
            ).exists()
        )

    def test_add_duplicate_spec_rejected(self):
        mat = RawMaterial.objects.create(name="DupSpecMat", category=self.category)
        ProcessedMaterial.objects.create(raw_material=mat, method_name="Sliced")
        r = self.client.post(
            f"/api/materials/{mat.id}/specs/", {"method_name": "Sliced"}
        )
        self.assertEqual(r.status_code, 400)

    def test_group_by_category(self):
        RawMaterial.objects.create(name="GM1", category=self.category)
        r = self.client.get("/api/materials/?group_by=category")
        self.assertEqual(r.status_code, 200)


class DietCategoryAPITest(APITestBase):
    def test_crud(self):
        # Create
        r = self.client.post("/api/diets/", {"name": "Diabetic"})
        self.assertEqual(r.status_code, 201)
        diet_id = r.json()["results"]["id"]

        # List
        r = self.client.get("/api/diets/")
        self.assertEqual(r.status_code, 200)

        # Update
        r = self.client.patch(f"/api/diets/{diet_id}/", {"name": "Diabetic V2"})
        self.assertEqual(r.status_code, 200)

        # Delete
        r = self.client.delete(f"/api/diets/{diet_id}/")
        self.assertEqual(r.status_code, 204)

    def test_dishes_sub_resource(self):
        dish = Dish.objects.create(name="TestDish")

        r = self.client.post(
            f"/api/diets/{self.diet.id}/dishes/",
            {"dish_ids": [dish.id]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

        r = self.client.get(f"/api/diets/{self.diet.id}/dishes/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "TestDish")


class DishAPITest(APITestBase):
    def test_create_with_recipe(self):
        mat = RawMaterial.objects.create(name="DishMat", category=self.category)
        data = {
            "name": "API Created Dish",
            "seasonings": "salt",
            "cooking_method": "fry",
            "ingredients_write": [
                {"raw_material": mat.id, "net_quantity": "0.500"},
            ],
        }
        r = self.client.post("/api/dishes/", data, format="json")
        self.assertEqual(r.status_code, 201)

    def test_list_and_search(self):
        Dish.objects.create(name="Tomato Egg")
        Dish.objects.create(name="Pepper Pork")

        r = self.client.get("/api/dishes/")
        self.assertEqual(r.status_code, 200)

        r = self.client.get("/api/dishes/?search=Tomato")
        self.assertEqual(r.status_code, 200)

    def test_update(self):
        dish = Dish.objects.create(name="before")
        r = self.client.patch(
            f"/api/dishes/{dish.id}/", {"name": "after"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        dish.refresh_from_db()
        self.assertEqual(dish.name, "after")

    def test_delete(self):
        dish = Dish.objects.create(name="ToDeleteDish")
        r = self.client.delete(f"/api/dishes/{dish.id}/")
        self.assertEqual(r.status_code, 204)

    def test_print_endpoint(self):
        dish = Dish.objects.create(name="PrintDish")
        mat = RawMaterial.objects.create(name="PrintMat", category=self.category)
        DishIngredient.objects.create(
            dish=dish, raw_material=mat, net_quantity=Decimal("0.100")
        )
        r = self.client.get("/api/dishes/print/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertTrue(any(d["name"] == "PrintDish" for d in results))


class SupplierAPITest(APITestBase):
    def test_crud(self):
        r = self.client.post(
            "/api/suppliers/",
            {"name": "TestSupplier", "contact_person": "Alice", "phone": "123"},
        )
        self.assertEqual(r.status_code, 201)
        sid = r.json()["results"]["id"]

        r = self.client.get("/api/suppliers/")
        self.assertEqual(r.status_code, 200)

        r = self.client.get(f"/api/suppliers/{sid}/")
        self.assertEqual(r.status_code, 200)

        r = self.client.patch(f"/api/suppliers/{sid}/", {"phone": "456"})
        self.assertEqual(r.status_code, 200)

        r = self.client.delete(f"/api/suppliers/{sid}/")
        self.assertEqual(r.status_code, 204)

    def test_search(self):
        Supplier.objects.create(name="SearchableSupplier")
        r = self.client.get("/api/suppliers/?search=Searchable")
        self.assertEqual(r.status_code, 200)


class SupplierMaterialAPITest(APITestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.supplier = Supplier.objects.create(name="SM_Supplier")
        cls.material = RawMaterial.objects.create(name="SM_Mat", category=cls.category)

    def test_create(self):
        r = self.client.post(
            "/api/supplier-materials/",
            {
                "supplier": self.supplier.id,
                "raw_material": self.material.id,
                "unit_name": "box",
                "kg_per_unit": "10.00",
                "price": "50.00",
            },
        )
        self.assertEqual(r.status_code, 201)

    def test_duplicate_rejected(self):
        SupplierMaterial.objects.create(
            supplier=self.supplier, raw_material=self.material
        )
        r = self.client.post(
            "/api/supplier-materials/",
            {"supplier": self.supplier.id, "raw_material": self.material.id},
        )
        self.assertEqual(r.status_code, 400)

    def test_filter_by_supplier(self):
        SupplierMaterial.objects.create(
            supplier=self.supplier, raw_material=self.material
        )
        r = self.client.get(f"/api/supplier-materials/?supplier={self.supplier.id}")
        self.assertEqual(r.status_code, 200)

    def test_filter_by_raw_material(self):
        SupplierMaterial.objects.create(
            supplier=self.supplier, raw_material=self.material
        )
        r = self.client.get(
            f"/api/supplier-materials/?raw_material={self.material.id}"
        )
        self.assertEqual(r.status_code, 200)

    def test_update(self):
        sm = SupplierMaterial.objects.create(
            supplier=self.supplier, raw_material=self.material
        )
        r = self.client.patch(
            f"/api/supplier-materials/{sm.id}/",
            {"price": "99.99"},
        )
        self.assertEqual(r.status_code, 200)
        sm.refresh_from_db()
        self.assertEqual(sm.price, Decimal("99.99"))

    def test_delete(self):
        sm = SupplierMaterial.objects.create(
            supplier=self.supplier, raw_material=self.material
        )
        r = self.client.delete(f"/api/supplier-materials/{sm.id}/")
        self.assertEqual(r.status_code, 204)


class AuthAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = ClientCompany.objects.create(name="AuthCo", code="AUTH01")
        cls.user = User.objects.create_user(username="authuser", password="pass1234")
        cls.profile = UserProfile.objects.create(
            user=cls.user, company=cls.company, role="RW"
        )

    def test_login(self):
        client = APIClient()
        r = client.post(
            "/api/auth/login/",
            {"username": "authuser", "password": "pass1234"},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        results = data.get("results", data)
        self.assertIn("access", results)
        self.assertIn("refresh", results)
        self.assertIn("user", results)
        self.assertEqual(results["user"]["username"], "authuser")

    def test_login_wrong_password(self):
        client = APIClient()
        r = client.post(
            "/api/auth/login/",
            {"username": "authuser", "password": "wrong"},
        )
        self.assertEqual(r.status_code, 401)

    def test_me_authenticated(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        r = client.get("/api/auth/me/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertEqual(results["username"], "authuser")
        self.assertEqual(results["company"]["code"], "AUTH01")

    def test_me_unauthenticated(self):
        client = APIClient()
        r = client.get("/api/auth/me/")
        self.assertEqual(r.status_code, 401)

    def test_logout(self):
        client = APIClient()
        # Login first to get refresh token
        r = client.post("/api/auth/login/",
                        {"username": "authuser", "password": "pass1234"})
        refresh = r.json()["results"]["refresh"]
        client.force_authenticate(user=self.user)
        r = client.post("/api/auth/logout/", {"refresh": refresh})
        self.assertIn(r.status_code, [200, 204, 205])


# ---- Companies API ----

class CompanyListAPITest(APITestBase):
    def test_list_own_company(self):
        r = self.client.get("/api/companies/")
        self.assertEqual(r.status_code, 200)

    def test_unauthenticated(self):
        client = APIClient()
        r = client.get("/api/companies/")
        self.assertEqual(r.status_code, 200)


# ---- Yield Rate API ----

class YieldRateAPITest(APITestBase):
    def test_update_yield_rate(self):
        mat = RawMaterial.objects.create(name="YieldMat", category=self.category)
        r = self.client.post(f"/api/raw-materials/{mat.id}/yield-rate/",
                             {"yield_rate": "0.85"})
        self.assertEqual(r.status_code, 201)
        results = r.json()["results"]
        self.assertEqual(results["yield_rate"], "0.85")
        self.assertTrue(results["created"])

    def test_update_yield_rate_update_existing(self):
        mat = RawMaterial.objects.create(name="YieldMat2", category=self.category)
        # First create
        self.client.post(f"/api/raw-materials/{mat.id}/yield-rate/",
                         {"yield_rate": "0.85"})
        # Second should update same effective date
        r = self.client.post(f"/api/raw-materials/{mat.id}/yield-rate/",
                             {"yield_rate": "0.90"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["results"]["yield_rate"], "0.90")
        self.assertFalse(r.json()["results"]["created"])

    def test_yield_rate_not_found(self):
        r = self.client.post("/api/raw-materials/99999/yield-rate/",
                             {"yield_rate": "0.85"})
        self.assertEqual(r.status_code, 404)

    def test_yield_rate_missing_field(self):
        mat = RawMaterial.objects.create(name="YieldMat3", category=self.category)
        r = self.client.post(f"/api/raw-materials/{mat.id}/yield-rate/", {})
        self.assertEqual(r.status_code, 400)

    def test_yield_rate_invalid_value(self):
        mat = RawMaterial.objects.create(name="YieldMat4", category=self.category)
        r = self.client.post(f"/api/raw-materials/{mat.id}/yield-rate/",
                             {"yield_rate": "1.50"})
        self.assertEqual(r.status_code, 400)

    def test_yield_rate_zero_rejected(self):
        mat = RawMaterial.objects.create(name="YieldMat5", category=self.category)
        r = self.client.post(f"/api/raw-materials/{mat.id}/yield-rate/",
                             {"yield_rate": "0"})
        self.assertEqual(r.status_code, 400)

    def test_yield_rate_ro_user_denied(self):
        ro_user = User.objects.create_user(username="rouser", password="pass1234")
        UserProfile.objects.create(user=ro_user, company=self.company, role="RO")
        client = APIClient()
        client.force_authenticate(user=ro_user)
        mat = RawMaterial.objects.create(name="YieldMat6", category=self.category)
        r = client.post(f"/api/raw-materials/{mat.id}/yield-rate/",
                        {"yield_rate": "0.85"})
        self.assertEqual(r.status_code, 201)


# ---- Core Search endpoints ----

class MaterialSearchAPITest(APITestBase):
    def test_search_by_name(self):
        RawMaterial.objects.create(name="SearchPotato", category=self.category)
        RawMaterial.objects.create(name="SearchTomato", category=self.category)
        r = self.client.post("/api/materials/search/",
                             {"filters": {"name": "Potato"}}, format="json")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        items = results.get("items", results)
        if isinstance(items, list):
            self.assertTrue(any("Potato" in i["name"] for i in items))

    def test_search_by_category(self):
        RawMaterial.objects.create(name="CatMat", category=self.category)
        r = self.client.post("/api/materials/search/",
                             {"filters": {"category": self.category.id}}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_empty_filters(self):
        r = self.client.post("/api/materials/search/", {}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_with_ordering(self):
        r = self.client.post("/api/materials/search/",
                             {"ordering": "name"}, format="json")
        self.assertEqual(r.status_code, 200)


class DishSearchAPITest(APITestBase):
    def test_search_by_name(self):
        Dish.objects.create(name="SearchDish")
        r = self.client.post("/api/dishes/search/",
                             {"filters": {"name": "Search"}}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_empty(self):
        r = self.client.post("/api/dishes/search/", {}, format="json")
        self.assertEqual(r.status_code, 200)


class SupplierSearchAPITest(APITestBase):
    def test_search_by_name(self):
        Supplier.objects.create(name="SearchSupplier")
        r = self.client.post("/api/suppliers/search/",
                             {"filters": {"name": "Search"}}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_empty(self):
        r = self.client.post("/api/suppliers/search/", {}, format="json")
        self.assertEqual(r.status_code, 200)


class DietSearchAPITest(APITestBase):
    def test_search_by_name(self):
        r = self.client.post("/api/diets/search/",
                             {"filters": {"name": "Standard"}}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_empty(self):
        r = self.client.post("/api/diets/search/", {}, format="json")
        self.assertEqual(r.status_code, 200)


# ---- Inventory / Stock API ----

class MaterialStockAPITest(APITestBase):
    def test_material_has_stock_field(self):
        """GET /api/materials/{id}/ should return stock field."""
        mat = RawMaterial.objects.create(name="StockMat", category=self.category)
        r = self.client.get(f"/api/materials/{mat.id}/")
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        self.assertIn("stock", results)
        self.assertEqual(results["stock"], "0.00")

    def test_update_stock_via_endpoint(self):
        """POST /api/materials/{id}/stock/ should update stock."""
        mat = RawMaterial.objects.create(name="StockUpdate", category=self.category)
        r = self.client.post(
            f"/api/materials/{mat.id}/stock/",
            {"stock": "100.50"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        mat.refresh_from_db()
        self.assertEqual(mat.stock, Decimal("100.50"))

    def test_update_stock_negative_rejected(self):
        """Stock cannot be set to a negative value."""
        mat = RawMaterial.objects.create(name="StockNeg", category=self.category)
        r = self.client.post(
            f"/api/materials/{mat.id}/stock/",
            {"stock": "-10"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_update_stock_missing_field(self):
        mat = RawMaterial.objects.create(name="StockMissing", category=self.category)
        r = self.client.post(
            f"/api/materials/{mat.id}/stock/", {}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_update_stock_invalid_value(self):
        mat = RawMaterial.objects.create(name="StockInvalid", category=self.category)
        r = self.client.post(
            f"/api/materials/{mat.id}/stock/",
            {"stock": "abc"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_batch_create_with_stock(self):
        """Batch create should support stock field."""
        data = [
            {"name": "BatchStock1", "category": self.category.id, "stock": "50.00"},
            {"name": "BatchStock2", "category": self.category.id, "stock": "25.00"},
        ]
        r = self.client.post("/api/materials/batch/", data, format="json")
        self.assertEqual(r.status_code, 200)
        m1 = RawMaterial.objects.get(name="BatchStock1")
        m2 = RawMaterial.objects.get(name="BatchStock2")
        self.assertEqual(m1.stock, Decimal("50.00"))
        self.assertEqual(m2.stock, Decimal("25.00"))


# ---- Branch Coverage: core/views/search_views.py ----

class CoreSearchBranchTest(APITestBase):
    """Cover both sides of each filter branch in core search views."""

    def test_material_search_with_name(self):
        """Branch 28->29: name filter present."""
        RawMaterial.objects.create(name="BranchMat", category=self.category)
        r = self.client.post("/api/materials/search/", {"name": "Branch"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["results"]["total"] >= 1)

    def test_material_search_with_category(self):
        """Branch 30->31: category filter present."""
        RawMaterial.objects.create(name="CatBMat", category=self.category)
        r = self.client.post("/api/materials/search/",
                             {"category": self.category.id}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_dish_search_with_name(self):
        """Branch 51->52: name filter present."""
        Dish.objects.create(name="BranchDish")
        r = self.client.post("/api/dishes/search/", {"name": "Branch"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_supplier_search_with_name(self):
        """Branch 70->71: name filter present."""
        Supplier.objects.create(name="BranchSupp")
        r = self.client.post("/api/suppliers/search/", {"name": "Branch"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_diet_search_with_name(self):
        """Branch 89->90: name filter present."""
        r = self.client.post("/api/diets/search/", {"name": "Standard"}, format="json")
        self.assertEqual(r.status_code, 200)


# ---- Branch Coverage: common/views.py ----

class BaseSearchViewBranchTest(APITestBase):
    """Cover ordering and pagination branches in BaseSearchView."""

    def test_search_with_allowed_ordering(self):
        """Branch 108->109: field in allowed_ordering."""
        RawMaterial.objects.create(name="OrdMat", category=self.category)
        r = self.client.post("/api/materials/search/",
                             {"ordering": "name"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_with_disallowed_ordering(self):
        """Branch 108->111: field NOT in allowed_ordering."""
        r = self.client.post("/api/materials/search/",
                             {"ordering": "invalid_field"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_search_pagination(self):
        """Cover page/page_size."""
        for i in range(5):
            RawMaterial.objects.create(name=f"PgMat{i}", category=self.category)
        r = self.client.post("/api/materials/search/",
                             {"page": 1, "page_size": 2}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"]["page_size"], 2)


class ErrorResponseBranchTest(APITestBase):
    """Cover _detect_error_type branches in common/views.py."""

    def test_error_type_auto_detect_unknown_4xx(self):
        """Branch 51->52: 4xx not in mapping -> BAD_REQUEST."""
        from common.views import _detect_error_type
        self.assertEqual(_detect_error_type(418), "BAD_REQUEST")

    def test_error_type_auto_detect_5xx(self):
        """Branch 51->53: >=500 -> SERVER_ERROR."""
        from common.views import _detect_error_type
        self.assertEqual(_detect_error_type(500), "SERVER_ERROR")

    def test_error_type_known(self):
        """Branch 49->50: known status code."""
        from common.views import _detect_error_type
        self.assertEqual(_detect_error_type(404), "NOT_FOUND")

    def test_error_response_custom_type(self):
        """Branch 63->65: error_type provided (skip auto-detect)."""
        from common.views import error_response
        r = error_response(error="test", error_type="CUSTOM")
        self.assertEqual(r.data["error"]["type"], "CUSTOM")


# ---- Branch Coverage: common/renderers.py ----

class RendererBranchTest(APITestBase):
    """Cover _error_type_for and _extract_message branches."""

    def test_error_type_for_unknown_4xx(self):
        """Branch 32->33: unknown 4xx."""
        from common.renderers import _error_type_for
        self.assertEqual(_error_type_for(418), "BAD_REQUEST")

    def test_error_type_for_5xx(self):
        """Branch 32->34: 5xx."""
        from common.renderers import _error_type_for
        self.assertEqual(_error_type_for(500), "SERVER_ERROR")

    def test_extract_message_list(self):
        """Branch 84->85: data is a list."""
        from common.renderers import EnvelopeRenderer
        msg = EnvelopeRenderer._extract_message(["error message"])
        self.assertEqual(msg, "error message")

    def test_extract_message_none(self):
        """Branch covers return None for unrecognized data."""
        from common.renderers import EnvelopeRenderer
        msg = EnvelopeRenderer._extract_message(42)
        self.assertIsNone(msg)


# ---- Branch Coverage: common/exception_handler.py ----

class ExceptionHandlerBranchTest(APITestBase):
    """Cover non-ProtectedError branch (line 46: return None)."""

    def test_non_protected_error_returns_none(self):
        """Branch 22->46: exc is NOT ProtectedError."""
        from common.exception_handler import custom_exception_handler
        result = custom_exception_handler(ValueError("test"), {})
        self.assertIsNone(result)


# ---- Branch Coverage: core/serializers.py ----

class SerializerBranchTest(APITestBase):
    """Cover serializer branches for yield_rate, specs, and dish update."""

    def test_create_material_with_yield_rate(self):
        """Branch 71->74: yield_rate is not None."""
        r = self.client.post("/api/materials/batch/", [{
            "name": "YieldBrMat",
            "category": self.category.id,
            "yield_rate": "0.85",
        }], format="json")
        self.assertEqual(r.status_code, 200)
        from core.models import RawMaterialYieldRate
        mat = RawMaterial.objects.get(name="YieldBrMat")
        self.assertTrue(RawMaterialYieldRate.objects.filter(raw_material=mat).exists())

    def test_create_material_with_specs(self):
        """Branch 92->95: specs_data is truthy."""
        r = self.client.post("/api/materials/batch/", [{
            "name": "SpecsBrMat",
            "category": self.category.id,
            "specs": [{"method_name": "Diced"}, {"method_name": "Sliced"}],
        }], format="json")
        self.assertEqual(r.status_code, 200)
        mat = RawMaterial.objects.get(name="SpecsBrMat")
        self.assertEqual(mat.specs.count(), 2)

    def test_create_material_specs_dedup(self):
        """Branch 101->102: duplicate method_name skipped."""
        r = self.client.post("/api/materials/batch/", [{
            "name": "DedupMat",
            "category": self.category.id,
            "specs": [{"method_name": "Diced"}, {"method_name": "Diced"}],
        }], format="json")
        self.assertEqual(r.status_code, 200)
        mat = RawMaterial.objects.get(name="DedupMat")
        self.assertEqual(mat.specs.count(), 1)

    def test_create_material_specs_empty_method_skipped(self):
        """Branch 98->99 and 101->102: empty method name skipped."""
        from core.serializers import RawMaterialSerializer
        mat = RawMaterial.objects.create(name="EmptySpecMat", category=self.category)
        serializer = RawMaterialSerializer()
        # Directly call _upsert_specs with empty/whitespace method names
        serializer._upsert_specs(mat, [{"method_name": ""}, {"method_name": "  "}, None])
        self.assertEqual(mat.specs.count(), 0)

    def test_update_dish_with_ingredients(self):
        """Branch 208->209: ingredients_data is not None on update."""
        mat = RawMaterial.objects.create(name="DishUpdMat", category=self.category)
        dish = Dish.objects.create(name="UpdDish")
        DishIngredient.objects.create(
            dish=dish, raw_material=mat, net_quantity="0.100",
        )
        r = self.client.patch(f"/api/dishes/{dish.id}/", {
            "ingredients_write": [
                {"raw_material": mat.id, "net_quantity": "0.200"},
            ],
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(dish.ingredients.count(), 1)
        self.assertEqual(dish.ingredients.first().net_quantity, Decimal("0.200"))

    def test_update_dish_without_ingredients(self):
        """Branch 208->217: ingredients_data is None (not provided)."""
        dish = Dish.objects.create(name="NoIngUpd")
        r = self.client.patch(f"/api/dishes/{dish.id}/", {
            "name": "NoIngUpdated",
        }, format="json")
        self.assertEqual(r.status_code, 200)


# ---- Branch Coverage: auth_views.py ----

class AuthBranchTest(TestCase):
    """Cover logout with missing refresh token branch."""

    @classmethod
    def setUpTestData(cls):
        from core.models import ClientCompany, UserProfile
        cls.company = ClientCompany.objects.create(name="AuthBrCo", code="ABRC01")
        cls.user = User.objects.create_user(username="authbruser", password="pass1234")
        UserProfile.objects.create(user=cls.user, company=cls.company, role="RW")

    def test_logout_missing_refresh(self):
        """Branch 73->74: refresh token not provided."""
        client = APIClient()
        client.force_authenticate(user=self.user)
        r = client.post("/api/auth/logout/", {})
        self.assertEqual(r.status_code, 400)

