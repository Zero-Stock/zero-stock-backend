# Materials API Documentation

## Overview

API endpoints for Raw Materials, supporting unified search, CRUD operations, batch processing, processing specifications management, and yield rate configuration.

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
| `total` | int | Total number of items matching the criteria |
| `page` | int | Current page number |
| `page_size` | int | Items per page |
| `results` | array | List of raw materials |
| `results[].id` | int | Material ID |
| `results[].name` | string | Material name |
| `results[].category` | int | Category ID |
| `results[].category_name` | string | Category name |
| `results[].specs` | array | List of processing specifications |
| `results[].specs[].id` | int | Spec ID |
| `results[].specs[].method_name` | string | Processing method name |
| `results[].current_yield_rate` | string | Currently effective yield rate |

### Sample Input + Output

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
        },
        {
            "id": 7,
            "name": "Small Potato",
            "category": 1,
            "category_name": "Fresh",
            "specs": [],
            "current_yield_rate": "1.00"
        }
    ]
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

### Sample Input + Output

**Request:**
```
GET /api/materials/?category=1&ordering=name
```

**Response:**
```json
{
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
```

---

## 3. Get Material Detail

**GET** `/api/materials/{id}/`

### Input Data

Path parameter `{id}`: Material ID

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Material ID |
| `name` | string | Material name |
| `category` | int | Category ID |
| `category_name` | string | Category name |
| `specs` | array | List of processing specifications |
| `current_yield_rate` | string | Current yield rate |

### Sample Input + Output

**Request:**
```
GET /api/materials/3/
```

**Response:**
```json
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
```

---

## 4. Batch Create/Update Materials

**POST** `/api/materials/batch/`

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
| `message` | string | Summary of the operation |
| `created` | array | List of newly created materials |
| `updated` | array | List of updated materials |
| `errors` | array | List of failed items |

### Sample Input + Output

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

**Response:**
```json
{
    "message": "Created 1, Updated 1, Failed 0",
    "created": [
        {"id": 10, "name": "Potato", "category": 1, "category_name": "Fresh", "specs": [...], "current_yield_rate": "0.85"}
    ],
    "updated": [
        {"id": 5, "name": "Tomato", "category": 1, "category_name": "Fresh", "specs": [], "current_yield_rate": "1.00"}
    ],
    "errors": []
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
| `id` | int | New spec ID |
| `method_name` | string | Processing method name |

### Sample Input + Output

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
    "id": 5,
    "method_name": "Diced"
}
```

---

## 6. Delete Material

**DELETE** `/api/materials/{id}/`

### Input Data

Path parameter `{id}`: Material ID

### Output Data

None (204 No Content)

### Sample Input + Output

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
| `raw_material_id` | int | Material ID |
| `yield_rate` | string | The set yield rate |
| `effective_date` | string | Date when it becomes effective |

### Sample Input + Output

**Request:**
```json
PUT /api/raw-materials/3/yield-rate/
{
    "yield_rate": "0.85"
}
```

**Response:**
```json
{
    "raw_material_id": 3,
    "yield_rate": "0.85",
    "effective_date": "2026-03-03"
}
```
