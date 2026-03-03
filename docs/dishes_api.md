# Dishes API Documentation

## Overview

API endpoints for Dishes (Recipes), supporting unified search, CRUD operations with nested ingredients, and print-friendly exports.

> **Response Envelope**: All endpoints return `{"message": "...", "error": null|{type, details}, "results": ...}`.

---

## 1. Unified Search ⭐

**POST** `/api/dishes/search/`

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Fuzzy search for dish name (contains match) |
| `ordering` | string | No | Ordering field. Options: `id`, `name`. Prefix with `-` for descending. Default: `name` |
| `page` | int | No | Page number, default: 1 |
| `page_size` | int | No | Items per page, default: 20, max: 100 |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.total` | int | Total number of items matching the criteria |
| `results.page` | int | Current page number |
| `results.page_size` | int | Items per page |
| `results.results` | array | List of dishes |
| `results.results[].id` | int | Dish ID |
| `results.results[].name` | string | Dish name |
| `results.results[].seasonings` | string | Seasonings list |
| `results.results[].cooking_method` | string | Cooking instructions |
| `results.results[].ingredients` | array | List of ingredients (recipe) |
| `results.results[].ingredients[].raw_material` | int | Raw Material ID |
| `results.results[].ingredients[].raw_material_name` | string | Raw Material name |
| `results.results[].ingredients[].processing` | int | Processing Spec ID (optional) |
| `results.results[].ingredients[].processing_name` | string | Processing method name |
| `results.results[].ingredients[].net_quantity` | decimal | Net weight per serving (kg) |

### Sample

**Request:**
```json
POST /api/dishes/search/
{
    "name": "Tomato",
    "ordering": "name",
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
        "total": 12,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "id": 5,
                "name": "Tomato Beef Stew",
                "seasonings": "Salt, Soy Sauce, Wine",
                "cooking_method": "Slow cook for 2 hours",
                "ingredients": [
                    {
                        "id": 101,
                        "raw_material": 3,
                        "raw_material_name": "Beef",
                        "processing": 5,
                        "processing_name": "Diced",
                        "net_quantity": "0.150"
                    }
                ]
            }
        ]
    }
}
```

---

## 2. Create/Update Dish

**POST** `/api/dishes/` (Create)
**PUT/PATCH** `/api/dishes/{id}/` (Update)

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Dish name |
| `seasonings` | string | No | List of seasonings |
| `cooking_method` | string | No | Cooking instructions |
| `ingredients_write` | array | No | Nested recipe ingredients |
| `ingredients_write[].raw_material` | int | Yes | Raw Material ID |
| `ingredients_write[].processing` | int | No | Processing Spec ID |
| `ingredients_write[].net_quantity` | decimal | Yes | Net weight per serving (kg) |

### Output Data

Standard Dish object (same structure as search `results.results[]`), wrapped in the envelope.

### Sample

**Request:**
```json
POST /api/dishes/
{
    "name": "Stir-fried Potato",
    "seasonings": "Salt, Vinegar",
    "cooking_method": "High heat stir fry",
    "ingredients_write": [
        {
            "raw_material": 1,
            "processing": 2,
            "net_quantity": "0.200"
        }
    ]
}
```

**Response (201 Created):**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "id": 42,
        "name": "Stir-fried Potato",
        "seasonings": "Salt, Vinegar",
        "cooking_method": "High heat stir fry",
        "ingredients": [
            {
                "id": 505,
                "raw_material": 1,
                "raw_material_name": "Potato",
                "processing": 2,
                "processing_name": "Sliced",
                "net_quantity": "0.200"
            }
        ]
    }
}
```

---

## 3. Print-friendly Export

**GET** `/api/dishes/print/`

### Input Data

None.

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | List of dishes in print format |
| `results[].id` | int | Dish ID |
| `results[].name` | string | Dish name |
| `results[].ingredients_text` | string | Formatted ingredients string (e.g. "Beef[Diced]150g") |
| `results[].seasonings` | string | Seasonings |
| `results[].cooking_method` | string | Cooking instructions |

### Sample

**Request:**
```
GET /api/dishes/print/
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": [
        {
            "id": 5,
            "name": "Tomato Beef Stew",
            "ingredients_text": "Beef[Diced]150g、Tomato[Sliced]100g",
            "seasonings": "Salt, Soy Sauce",
            "cooking_method": "Slow cook"
        }
    ]
}
```

---

## 4. Delete Dish

**DELETE** `/api/dishes/{id}/`

### Input Data

Path parameter `{id}`: Dish ID

### Output Data

None (204 No Content)

### Sample

```
DELETE /api/dishes/5/
-> 204 No Content
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
| 5xx | `SERVER_ERROR` | Internal server error |
