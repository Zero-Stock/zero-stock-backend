# Materials API Documentation

## Overview

API endpoints for Raw Materials, supporting unified search, CRUD operations, batch processing, processing specifications management, and yield rate configuration.

> **Response Envelope**: All endpoints return `{"message": "...", "error": null|{type, details}, "results": ...}`.

---

## 1. Unified Search ⭐

**POST** `/api/materials/search/`

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Fuzzy search for material name (contains match) |
| `category` | int | No | Filter by Category ID |
| `ordering` | string | No | Ordering field. Options: `id`, `name`, `category__name`. Prefix with `-` for descending. Default: `name` |
| `page` | int | No | Page number, default: 1 |
| `page_size` | int | No | Items per page, default: 20, max: 100 |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.total` | int | Total number of items matching the criteria |
| `results.page` | int | Current page number |
| `results.page_size` | int | Items per page |
| `results.results` | array | List of raw materials |
| `results.results[].id` | int | Material ID |
| `results.results[].name` | string | Material name |
| `results.results[].category` | int | Category ID |
| `results.results[].category_name` | string | Category name |
| `results.results[].specs` | array | List of processing specifications |
| `results.results[].specs[].id` | int | Spec ID |
| `results.results[].specs[].method_name` | string | Processing method name |
| `results.results[].current_yield_rate` | string | Currently effective yield rate |

### Sample

**Request:**
```json
POST /api/materials/search/
{
    "name": "Potato",
    "category": 1,
    "ordering": "-name",
    "page": 1,
    "page_size": 10
}
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "total": 2,
        "page": 1,
        "page_size": 10,
        "results": [
            {
                "id": 3,
                "name": "Potato",
                "category": 1,
                "category_name": "Fresh",
                "specs": [
                    {"id": 1, "method_name": "Peeled & Sliced"},
                    {"id": 2, "method_name": "Peeled & diced"}
                ],
                "current_yield_rate": "0.85"
            }
        ]
    }
}
```

---

## 2. List Raw Materials

**GET** `/api/materials/`

### Input Data (Query Params)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search` | string | No | Search by name |
| `category` | int | No | Filter by Category ID |
| `ordering` | string | No | Ordering: `id`, `name`, `category__name` |
| `group_by` | string | No | Group response by: `category` or `unit` |

### Output Data

Paginated list, structure same as the `results` in the search endpoint. When using `group_by`, returns an object keyed by the grouping criteria.

### Sample

**Request:**
```
GET /api/materials/?category=1&ordering=name
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "count": 15,
        "next": "http://localhost:8000/api/materials/?category=1&ordering=name&page=2",
        "previous": null,
        "results": [
            {
                "id": 3,
                "name": "Potato",
                "category": 1,
                "category_name": "Fresh",
                "specs": [{"id": 1, "method_name": "Peeled & Sliced"}],
                "current_yield_rate": "0.85"
            }
        ]
    }
}
```

---

## 3. Get Material Detail

**GET** `/api/materials/{id}/`

### Input Data

Path parameter `{id}`: Material ID

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | Material ID |
| `results.name` | string | Material name |
| `results.category` | int | Category ID |
| `results.category_name` | string | Category name |
| `results.specs` | array | List of processing specifications |
| `results.current_yield_rate` | string | Current yield rate |

### Sample

**Request:**
```
GET /api/materials/3/
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "id": 3,
        "name": "Potato",
        "category": 1,
        "category_name": "Fresh",
        "specs": [
            {"id": 1, "method_name": "Peeled & Sliced"},
            {"id": 2, "method_name": "Peeled & diced"}
        ],
        "current_yield_rate": "0.85"
    }
}
```

**Error (404):**
```json
{
    "message": "No RawMaterial matches the given query.",
    "error": {
        "type": "NOT_FOUND",
        "details": {"detail": "No RawMaterial matches the given query."}
    },
    "results": null
}
```

---

## 4. Batch Create/Update Materials

**POST** `/api/materials/batch/`

> **Atomic**: If any item fails validation, the entire batch is rejected — no partial writes.

### Input Data (JSON Array)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | int | No | If provided -> update by ID |
| `name` | string | Yes(for new) | Material name. If no ID but name matches existing -> update |
| `category` | int | Yes(for new) | Category ID |
| `yield_rate` | string | No | Yield rate (e.g. "0.85"), effective tomorrow |
| `specs` | array | No | List of processing specs `[{"method_name": "..."}]` |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Summary: "Created X, Updated Y" |
| `results.created` | array | List of newly created materials |
| `results.updated` | array | List of updated materials |

On error (400), the entire batch is rejected:

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | "Validation failed for N item(s), no changes applied." |
| `error.type` | string | `"VALIDATION_ERROR"` |
| `error.details` | array | List of `{index, detail}` per failed item |

### Sample — Success

**Request:**
```json
POST /api/materials/batch/
[
    {
        "name": "Potato",
        "category": 1,
        "yield_rate": "0.85",
        "specs": [
            {"method_name": "Peeled & Sliced"},
            {"method_name": "Peeled & diced"}
        ]
    },
    {
        "id": 5,
        "name": "Tomato",
        "category": 1
    }
]
```

**Response (200):**
```json
{
    "message": "Created 1, Updated 1",
    "error": null,
    "results": {
        "created": [
            {"id": 10, "name": "Potato", "category": 1, "category_name": "Fresh", "specs": [...], "current_yield_rate": "0.85"}
        ],
        "updated": [
            {"id": 5, "name": "Tomato", "category": 1, "category_name": "Fresh", "specs": [], "current_yield_rate": "1.00"}
        ]
    }
}
```

### Sample — Error (entire batch rejected)

**Request:**
```json
POST /api/materials/batch/
[
    {"name": "NewItem", "category": 999},
    {"name": "Potato"}
]
```

**Response (400):**
```json
{
    "message": "Validation failed for 1 item(s), no changes applied.",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": [
            {
                "index": 0,
                "detail": {
                    "category": ["Invalid pk \"999\" - object does not exist."]
                }
            }
        ]
    },
    "results": null
}
```

---

## 5. Add Processing Specification

**POST** `/api/materials/{id}/specs/`

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `method_name` | string | Yes | Name of the processing method (e.g. "Peeled & Sliced") |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.id` | int | New spec ID |
| `results.method_name` | string | Processing method name |

### Sample

**Request:**
```json
POST /api/materials/3/specs/
{
    "method_name": "Diced"
}
```

**Response (201 Created):**
```json
{
    "message": "Spec created",
    "error": null,
    "results": {
        "id": 5,
        "method_name": "Diced"
    }
}
```

---

## 6. Delete Material

**DELETE** `/api/materials/{id}/`

### Input Data

Path parameter `{id}`: Material ID

### Output Data

None (204 No Content)

### Sample

```
DELETE /api/materials/3/
-> 204 No Content
```

---

## 7. Update Yield Rate

**PUT** `/api/raw-materials/{id}/yield-rate/`

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `yield_rate` | string | Yes | Yield rate value (e.g. "0.85" = 85%), effective tomorrow |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.raw_material_id` | int | Material ID |
| `results.raw_material_name` | string | Material name |
| `results.yield_rate` | string | The set yield rate |
| `results.effective_date` | string | Date when it becomes effective |
| `results.created` | bool | Whether a new record was created |

### Sample

**Request:**
```json
PUT /api/raw-materials/3/yield-rate/
{
    "yield_rate": "0.85"
}
```

**Response (201):**
```json
{
    "message": "Yield rate updated",
    "error": null,
    "results": {
        "raw_material_id": 3,
        "raw_material_name": "Potato",
        "yield_rate": "0.85",
        "effective_date": "2026-03-03",
        "created": true
    }
}
```

---

## Error Type Reference

All error responses use the structure `{"type": "...", "details": ...}`:

| HTTP Status | error.type | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Field validation failures |
| 401 | `AUTHENTICATION_ERROR` | Not authenticated |
| 403 | `PERMISSION_DENIED` | Forbidden |
| 404 | `NOT_FOUND` | Resource not found |
| 405 | `METHOD_NOT_ALLOWED` | HTTP method not supported |
| 5xx | `SERVER_ERROR` | Internal server error |
