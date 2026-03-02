# Dishes API Documentation

## Overview

API endpoints for Dishes (Recipes), supporting unified search, CRUD operations with nested ingredients, and print-friendly exports.

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
| `total` | int | Total number of items matching the criteria |
| `page` | int | Current page number |
| `page_size` | int | Items per page |
| `results` | array | List of dishes |
| `results[].id` | int | Dish ID |
| `results[].name` | string | Dish name |
| `results[].seasonings` | string | Seasonings list |
| `results[].cooking_method` | string | Cooking instructions |
| `results[].ingredients` | array | List of ingredients (recipe) |
| `results[].ingredients[].raw_material` | int | Raw Material ID |
| `results[].ingredients[].raw_material_name` | string | Raw Material name |
| `results[].ingredients[].processing` | int | Processing Spec ID (optional) |
| `results[].ingredients[].processing_name` | string | Processing method name |
| `results[].ingredients[].net_quantity` | decimal | Net weight per serving (kg) |

### Sample Input + Output

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

Standard Dish object (same structure as search results).

### Sample Input + Output

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
    "id": 42,
    "name": "Stir-fried Potato",
    "ingredients": [
        {
            "id": 505,
            "raw_material": 1,
            "raw_material_name": "Potato",
            "processing": 2,
            "processing_name": "Sliced",
            "net_quantity": "0.200"
        }
    ],
    ...
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
| `id` | int | Dish ID |
| `name` | string | Dish name |
| `ingredients_text` | string | Formatted ingredients string (e.g. "Beef[Diced]150g") |
| `seasonings` | string | Seasonings |
| `cooking_method` | string | Cooking instructions |

### Sample Input + Output

**Request:**
```
GET /api/dishes/print/
```

**Response:**
```json
[
    {
        "id": 5,
        "name": "Tomato Beef Stew",
        "ingredients_text": "Beef[Diced]150g、Tomato[Sliced]100g",
        "seasonings": "Salt, Soy Sauce",
        "cooking_method": "Slow cook"
    }
]
```

---

## 4. Delete Dish

**DELETE** `/api/dishes/{id}/`

### Input Data

Path parameter `{id}`: Dish ID

### Output Data

None (204 No Content)

### Sample Input + Output

```
DELETE /api/dishes/5/
-> 204 No Content
```
