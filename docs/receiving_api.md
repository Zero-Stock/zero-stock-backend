# Receiving API Documentation

## Overview

API endpoints for verifying and recording the delivery of materials ordered via a Procurement Request.

> **Response Envelope**: All endpoints return `{"message": "...", "error": null|{type, details}, "results": ...}`.

---

## 1. Get Receiving Template

**GET** `/api/receiving/{procurement_id}/template/`

Generates an empty receiving sheet scaffold based on the final expected quantities (purchase quantities) of the `SUBMITTED` procurement request.

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.procurement_id` | int | Procurement Request ID |
| `results.target_date` | string | Target delivery date |
| `results.status` | string | Procurement status |
| `results.items` | array | Expected items |
| `results.items[].raw_material_id` | int | Raw Material ID |
| `results.items[].raw_material_name` | string | Name of the material |
| `results.items[].expected_quantity` | float | Expected purchase quantity (in kg) |
| `results.items[].actual_quantity` | float | Always defaults to 0 |

---

## 2. Create Receiving Record

**POST** `/api/receiving/`

Submits the actual received quantities of the raw materials, completing the receiving cycle. This immediately updates inventory stock levels.

### Cutoff Deadline Rule
Receiving records *cannot* be created or updated past `23:59` of the target delivery date. Time-late submissions return a `400 Bad Request` with an explicit deadline error.

### Side Effects
On the first successful receiving event, the system automatically:
1. Marks the related Procurement Request state as `CONFIRMED`.
2. Memorizes the actively used suppliers by updating the `default_supplier` configuration on the `RawMaterial` model.

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `procurement_id` | int | Yes | Related Procurement Request ID |
| `notes` | string | No | Overall receiving notes |
| `items` | array | Yes | Actual received items |
| `items[].raw_material_id` | int | Yes | Raw Material ID |
| `items[].actual_quantity` | float | Yes | Actual quantity arrived (in kg) |
| `items[].notes` | string | No | Discrepancy or specific item notes |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | Receiving Record ID |
| `results.status` | string | Receiving status (e.g. `COMPLETED`) |

---

## 3. Get Receiving Detail

**GET** `/api/receiving/{id}/`

Retrieves the completed receiving record, detailing the `expected` vs `actual` quantities and any inventory discrepancy notes.
