# Procurement API Documentation

## Overview

API endpoints for generating, managing, and submitting daily procurement requests based on inventory stock and theoretical demand.

> **Response Envelope**: All endpoints return `{"message": "...", "error": null|{type, details}, "results": ...}`.

---

## 1. Generate Procurement

**POST** `/api/procurement/generate/`

Generates a new procurement request by comparing the theoretical demand for a target date against the current stock baseline. Also automatically pre-fills the `default_supplier` if one exists for each raw material.

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | Yes | Target date for procurement (YYYY-MM-DD) |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | Procurement Request ID |
| `results.target_date` | string | Target date (YYYY-MM-DD) |
| `results.status` | string | New status, always `CREATED` |

---

## 2. Procurement List & Search

**GET** `/api/procurement/`
**POST** `/api/procurement/search/`

Lists historical procurement requests. Search supports pagination and filtering.

### Input Data (For Search)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | No | Exact target date |
| `status` | string | No | Filter by status (`CREATED`, `SUBMITTED`, `CONFIRMED`) |
| `page`, `page_size` | int | No | Pagination parameters |

---

## 3. Procurement Detail & Items

**GET** `/api/procurement/{id}/`
Returns the metadata for a specific procurement request.

**GET** `/api/procurement/{id}/items/`
Returns the raw line items of the procurement request exactly as stored in the database.

---

## 4. Get Procurement Sheet (Dual Units)

**GET** `/api/procurement/{id}/sheet/`

Returns the formatted procurement order, showing the calculated demand, stock, and purchasing quantity in both `kg` and the supplier's specific commercial unit. Quantities are ceiling-rounded to guarantee that sufficient whole units are purchased.

### Output Data

Items array containing:
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Raw material name |
| `category` | string | Material category |
| `demand_kg` | float | Theoretical demand in kg |
| `demand_unit_qty` | float | Theoretical demand in supplier's unit |
| `stock_kg` | float | Current stock snapshot in kg |
| `stock_unit_qty` | float | Current stock snapshot in supplier's unit |
| `purchase_kg` | float | Quantity to purchase in kg (`max(demand - stock, 0)`) |
| `purchase_unit_qty` | int | Final purchase quantity in supplier's unit (Ceiling rounded) |
| `supplier` | string | Pre-filled assigned supplier name |
| `supplier_unit_name` | string | Supplier's commercial unit name (e.g.箱, 袋) |

---

## 5. Assign Suppliers

**POST** `/api/procurement/assign-suppliers/`

Assigns or re-assigns suppliers to the raw material items in the procurement request. Operations are only allowed when the request is in the `CREATED` state. *Note: this action does not change the status of the procurement.*

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `assignments` | array | Yes | List of supplier assignments |
| `assignments[].item_id` | int | Yes | ProcurementItem ID |
| `assignments[].supplier_material_id` | int | No | SupplierMaterial relationship ID. Null to unassign. |

---

## 6. Submit Procurement

**POST** `/api/procurement/{id}/submit/`

Submits the drafted procurement request, pushing it to the next step of the pipeline for receiving.

### Rules
- Only allowed when the procurement is in `CREATED` status.
- Procurement Status changes `CREATED` → `SUBMITTED`.
