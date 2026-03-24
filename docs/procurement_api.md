# Procurement API Documentation

## Overview

API endpoints for generating, managing, and submitting daily procurement requests based on inventory stock and theoretical demand. Supports dual-unit display (kg + supplier unit), default supplier pre-filling, and a `CREATED` → `SUBMITTED` → `CONFIRMED` status lifecycle.

> **Response Envelope**: All endpoints return `{"message": "...", "error": null|{type, details}, "results": ...}`.

---

## 1. Unified Search ⭐

**POST** `/api/procurement/search/`

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | No | Exact target date (YYYY-MM-DD). Mutually exclusive with `start`/`end` |
| `start` | string (date) | No | Date range start (>=). Ignored if `date` is provided |
| `end` | string (date) | No | Date range end (<=). Ignored if `date` is provided |
| `status` | string | No | Filter by status: `CREATED`, `SUBMITTED`, `CONFIRMED` |
| `ordering` | string | No | Ordering field. Options: `target_date`, `id`. Prefix with `-` for descending. Default: `-target_date` |
| `page` | int | No | Page number, default: 1 |
| `page_size` | int | No | Items per page, default: 20, max: 100 |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.total` | int | Total number of items matching the criteria |
| `results.page` | int | Current page number |
| `results.page_size` | int | Items per page |
| `results.results` | array | List of procurement requests |
| `results.results[].id` | int | Procurement Request ID |
| `results.results[].company` | int | Company ID |
| `results.results[].target_date` | string | Target date (YYYY-MM-DD) |
| `results.results[].status` | string | Current status |
| `results.results[].created_at` | string | Creation timestamp |
| `results.results[].items` | array | Nested procurement items (see Section 4) |

### Sample

**Request:**
```json
POST /api/procurement/search/
{
    "date": "2026-03-20",
    "status": "CREATED",
    "ordering": "-target_date",
    "page": 1,
    "page_size": 20
}
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "total": 1,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "id": 5,
                "company": 1,
                "target_date": "2026-03-20",
                "status": "CREATED",
                "created_at": "2026-03-19T18:00:00Z",
                "items": [
                    {
                        "id": 10,
                        "raw_material": 3,
                        "raw_material_name": "Rice",
                        "category": "Grains",
                        "demand_quantity": "50.000",
                        "stock_quantity": "10.000",
                        "purchase_quantity": "40.000",
                        "demand_unit_qty": 2.5,
                        "stock_unit_qty": 0.5,
                        "purchase_unit_qty": 2,
                        "supplier": 1,
                        "supplier_name": "Supplier A",
                        "supplier_unit_name": "袋",
                        "supplier_kg_per_unit": "20.000",
                        "supplier_price": "150.00",
                        "notes": "..."
                    }
                ]
            }
        ]
    }
}
```

---

## 2. Generate Procurement

**POST** `/api/procurement/generate/`

Generates a new procurement request by computing theoretical demand from menus, census, and recipes, then subtracting current stock. Pre-fills `default_supplier` if one exists for each raw material.

> **Permission**: Requires `RW` role.

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | Yes | Target date for procurement (YYYY-MM-DD) |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | Procurement Request ID |
| `results.company` | int | Company ID |
| `results.target_date` | string | Target date (YYYY-MM-DD) |
| `results.status` | string | Always `CREATED` |
| `results.created_at` | string | Creation timestamp |
| `results.items` | array | Generated procurement items |

### Sample

**Request:**
```json
POST /api/procurement/generate/
{
    "date": "2026-03-20"
}
```

**Response (201):**
```json
{
    "message": "Procurement request generated",
    "error": null,
    "results": {
        "id": 5,
        "company": 1,
        "target_date": "2026-03-20",
        "status": "CREATED",
        "created_at": "2026-03-19T18:00:00Z",
        "items": [
            {
                "id": 10,
                "raw_material": 3,
                "raw_material_name": "Rice",
                "category": "Grains",
                "demand_quantity": "50.000",
                "stock_quantity": "10.000",
                "purchase_quantity": "40.000",
                "demand_unit_qty": 2.5,
                "stock_unit_qty": 0.5,
                "purchase_unit_qty": 2,
                "supplier": 1,
                "supplier_name": "Supplier A",
                "supplier_unit_name": "袋",
                "supplier_kg_per_unit": "20.000",
                "supplier_price": "150.00",
                "notes": "2026-03-20 L | diet=1 | ..."
            }
        ]
    }
}
```

### Sample — Error (no census data)

**Response (400):**
```json
{
    "message": "Error",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": {"date": ["No census found for this date."]}
    },
    "results": null
}
```

### Sample — Error (missing date)

**Response (400):**
```json
{
    "message": "Error",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": {"date": ["This field is required."]}
    },
    "results": null
}
```

### Sample — Error (invalid yield rate)

**Response (400):**
```json
{
    "message": "Error",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": {"detail": "Invalid yield_rate for Rice."}
    },
    "results": null
}
```

### Sample — Error (no items generated)

**Response (400):**
```json
{
    "message": "Error",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": {"detail": "No procurement items generated. Check menu/recipes."}
    },
    "results": null
}
```

### Sample — Error (already submitted)

**Response (400):**
```json
{
    "message": "Error",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": {"detail": "Procurement request already SUBMITTED. Cannot regenerate."}
    },
    "results": null
}
```

### Sample — Error (permission denied)

**Response (403):**
```json
{
    "message": "Error",
    "error": {
        "type": "PERMISSION_DENIED",
        "details": {"detail": "RW role required."}
    },
    "results": null
}
```

---

## 3. List Procurement Requests

**GET** `/api/procurement/`

Returns a paginated list of procurement requests for the current company, ordered by `target_date` descending.

### Output Data

Standard DRF paginated list. Each item has the same structure as `results.results[]` in the Search endpoint.

---

## 4. Procurement Detail

**GET** `/api/procurement/{id}/`

Returns a single procurement request with its nested items.

### Output Data

Same structure as a single `results.results[]` item from the Search endpoint.

### Sample

**Request:**
```
GET /api/procurement/5/
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "id": 5,
        "company": 1,
        "target_date": "2026-03-20",
        "status": "CREATED",
        "created_at": "2026-03-19T18:00:00Z",
        "items": [...]
    }
}
```

---

## 5. Procurement Items

**GET** `/api/procurement/{id}/items/`

Returns the line items of the procurement request. Supports optional grouping.

### Input Data (Query Params)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `group_by` | string | No | Group items by `supplier` or `category`. If omitted, returns flat item list |

### Output Data (Flat — No group_by)

| Field | Type | Description |
|-------|------|-------------|
| `results[].id` | int | ProcurementItem ID |
| `results[].raw_material` | int | Raw Material ID |
| `results[].raw_material_name` | string | Raw material name |
| `results[].category` | string | Material category name |
| `results[].demand_quantity` | string | Theoretical demand in kg |
| `results[].stock_quantity` | string | Stock snapshot in kg |
| `results[].purchase_quantity` | string | Purchase quantity in kg (`max(demand - stock, 0)`) |
| `results[].demand_unit_qty` | float\|null | Demand in supplier's unit |
| `results[].stock_unit_qty` | float\|null | Stock in supplier's unit |
| `results[].purchase_unit_qty` | int\|null | Purchase in supplier's unit (⌈ceiling⌉) |
| `results[].supplier` | int\|null | Supplier ID |
| `results[].supplier_name` | string\|null | Supplier name |
| `results[].supplier_unit_name` | string\|null | Supplier's commercial unit name (e.g. 箱, 袋) |
| `results[].supplier_kg_per_unit` | string\|null | Kg per supplier unit (conversion factor) |
| `results[].supplier_price` | string\|null | Unit price |
| `results[].notes` | string | Calculation breakdown notes |

### Output Data (group_by=supplier)

| Field | Type | Description |
|-------|------|-------------|
| `results[].supplier` | string | Supplier name (or `未分配`) |
| `results[].purchase_quantity` | string | Aggregated purchase quantity in kg |

### Output Data (group_by=category)

| Field | Type | Description |
|-------|------|-------------|
| `results[].category` | string | Material category name |
| `results[].purchase_quantity` | string | Aggregated purchase quantity in kg |

### Sample

**Request:**
```
GET /api/procurement/5/items/?group_by=supplier
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": [
        {"supplier": "Supplier A", "purchase_quantity": "40.000"},
        {"supplier": "未分配", "purchase_quantity": "15.000"}
    ]
}
```

---

## 6. Procurement Sheet (Dual Units)

**GET** `/api/procurement/{id}/sheet/`

Returns the formatted procurement order with dual-unit display. All weight-related fields include both kg values and the supplier's commercial unit. `purchase_unit_qty` is ceiling-rounded.

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | Procurement Request ID |
| `results.date` | string | Target date (YYYY-MM-DD) |
| `results.day_of_week` | string | Day name in Chinese (e.g. 周一) |
| `results.company` | string | Company name |
| `results.status` | string | Current status |
| `results.items` | array | Formatted item list |
| `results.items[].name` | string | Raw material name |
| `results.items[].category` | string | Material category |
| `results.items[].demand_kg` | float | Theoretical demand in kg |
| `results.items[].demand_unit_qty` | float\|null | Demand in supplier's unit |
| `results.items[].stock_kg` | float | Stock snapshot in kg |
| `results.items[].stock_unit_qty` | float\|null | Stock in supplier's unit |
| `results.items[].purchase_kg` | float | Purchase quantity in kg |
| `results.items[].purchase_unit_qty` | int\|null | Purchase in supplier's unit (⌈ceiling⌉) |
| `results.items[].supplier` | string\|null | Assigned supplier name |
| `results.items[].supplier_unit_name` | string\|null | Supplier's commercial unit (e.g. 箱, 袋) |
| `results.items[].supplier_kg_per_unit` | float\|null | Kg per unit conversion factor |
| `results.items[].supplier_price` | float\|null | Unit price |

### Sample

**Request:**
```
GET /api/procurement/5/sheet/
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "id": 5,
        "date": "2026-03-20",
        "day_of_week": "周五",
        "company": "Test Hospital",
        "status": "CREATED",
        "items": [
            {
                "name": "Rice",
                "category": "Grains",
                "demand_kg": 50.0,
                "demand_unit_qty": 2.5,
                "stock_kg": 10.0,
                "stock_unit_qty": 0.5,
                "purchase_kg": 40.0,
                "purchase_unit_qty": 2,
                "supplier": "Supplier A",
                "supplier_unit_name": "袋",
                "supplier_kg_per_unit": 20.0,
                "supplier_price": 150.0
            },
            {
                "name": "Pork",
                "category": "Meat",
                "demand_kg": 30.0,
                "demand_unit_qty": null,
                "stock_kg": 5.0,
                "stock_unit_qty": null,
                "purchase_kg": 25.0,
                "purchase_unit_qty": null,
                "supplier": null,
                "supplier_unit_name": null,
                "supplier_kg_per_unit": null,
                "supplier_price": null
            }
        ]
    }
}
```

---

## 7. Procurement Template

**GET** `/api/procurement/template/?date=YYYY-MM-DD`

Returns the procurement template with available suppliers for each material, enabling the user to assign or reassign suppliers before submission.

### Input Data (Query Params)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | Yes | Target date (YYYY-MM-DD) |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | Procurement Request ID |
| `results.date` | string | Target date |
| `results.status` | string | Current status |
| `results.items` | array | Template item list |
| `results.items[].item_id` | int | ProcurementItem ID |
| `results.items[].raw_material_id` | int | Raw Material ID |
| `results.items[].raw_material_name` | string | Material name |
| `results.items[].category` | string | Category name |
| `results.items[].demand_kg` | float | Demand in kg |
| `results.items[].stock_kg` | float | Stock in kg |
| `results.items[].purchase_kg` | float | Purchase in kg |
| `results.items[].current_supplier_id` | int\|null | Currently assigned Supplier ID |
| `results.items[].available_suppliers` | array | All suppliers offering this material |
| `results.items[].available_suppliers[].supplier_material_id` | int | SupplierMaterial ID |
| `results.items[].available_suppliers[].supplier_id` | int | Supplier ID |
| `results.items[].available_suppliers[].supplier_name` | string | Supplier name |
| `results.items[].available_suppliers[].unit_name` | string | Supplier's unit (e.g. 箱) |
| `results.items[].available_suppliers[].kg_per_unit` | float | Kg per unit |
| `results.items[].available_suppliers[].price` | float\|null | Unit price |

### Sample

**Request:**
```
GET /api/procurement/template/?date=2026-03-20
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "id": 5,
        "date": "2026-03-20",
        "status": "CREATED",
        "items": [
            {
                "item_id": 10,
                "raw_material_id": 3,
                "raw_material_name": "Rice",
                "category": "Grains",
                "demand_kg": 50.0,
                "stock_kg": 10.0,
                "purchase_kg": 40.0,
                "current_supplier_id": 1,
                "available_suppliers": [
                    {
                        "supplier_material_id": 5,
                        "supplier_id": 1,
                        "supplier_name": "Supplier A",
                        "unit_name": "袋",
                        "kg_per_unit": 20.0,
                        "price": 150.0
                    },
                    {
                        "supplier_material_id": 8,
                        "supplier_id": 2,
                        "supplier_name": "Supplier B",
                        "unit_name": "箱",
                        "kg_per_unit": 25.0,
                        "price": 180.0
                    }
                ]
            }
        ]
    }
}
```

---

## 8. Assign Suppliers

**POST** `/api/procurement/assign-suppliers/?date=YYYY-MM-DD`

Assigns or re-assigns suppliers to the raw material items in the procurement request. Only allowed when the request is in `CREATED` status. **Does not change the procurement status.**

> **Permission**: Requires `RW` role.

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` (query param) | string (date) | Yes | Target date (YYYY-MM-DD) |
| `assignments` | array | Yes | List of supplier assignments |
| `assignments[].item_id` | int | Yes | ProcurementItem ID |
| `assignments[].supplier_material_id` | int | Yes | SupplierMaterial relationship ID |

### Output Data

Returns the full `ProcurementRequest` object with updated items (same structure as Section 4).

### Sample

**Request:**
```json
POST /api/procurement/assign-suppliers/?date=2026-03-20
{
    "assignments": [
        {"item_id": 10, "supplier_material_id": 5},
        {"item_id": 11, "supplier_material_id": 8}
    ]
}
```

**Response:**
```json
{
    "message": "Suppliers assigned",
    "error": null,
    "results": {
        "id": 5,
        "company": 1,
        "target_date": "2026-03-20",
        "status": "CREATED",
        "created_at": "2026-03-19T18:00:00Z",
        "items": [...]
    }
}
```

### Sample — Error (wrong status)

**Response (400):**
```json
{
    "message": "Error",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": {"detail": "Cannot reassign: status is SUBMITTED."}
    },
    "results": null
}
```

---

## 9. Submit Procurement

**POST** `/api/procurement/{id}/submit/`

Submits a drafted procurement request, transitioning it from `CREATED` → `SUBMITTED`.

> **Permission**: Requires `RW` role.

### Rules
- Only allowed when the procurement is in `CREATED` status.
- If not in `CREATED` status, returns `200` with a message explaining it cannot be submitted.

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | Procurement Request ID |
| `results.status` | string | New status (`SUBMITTED`) |

### Sample

**Request:**
```json
POST /api/procurement/5/submit/
```

**Response:**
```json
{
    "message": "Submitted",
    "error": null,
    "results": {
        "id": 5,
        "status": "SUBMITTED"
    }
}
```

---

## Status Lifecycle

```
CREATED ──submit──▶ SUBMITTED ──first receiving──▶ CONFIRMED
```

| Trigger | Status | Description |
|---------|--------|-------------|
| Generate | `CREATED` | 采购单生成，供应商已预填 |
| User submit | `SUBMITTED` | 用户确认/修改后提交 |
| First receiving | `CONFIRMED` | 收货单提交，更新默认供应商 |

---

## Error Type Reference

All error responses use the structure `{"type": "...", "details": ...}`:

| HTTP Status | error.type | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Field validation failures |
| 401 | `AUTHENTICATION_ERROR` | Not authenticated |
| 403 | `PERMISSION_DENIED` | Forbidden / RW role required |
| 404 | `NOT_FOUND` | Resource not found |
| 405 | `METHOD_NOT_ALLOWED` | HTTP method not supported |
| 5xx | `SERVER_ERROR` | Internal server error |
