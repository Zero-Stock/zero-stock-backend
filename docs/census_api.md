# Census API Documentation

## Overview

API endpoints for Daily Census (Headcount), supporting unified search, list with filtering, batch create/update, and summary aggregation.

> **Response Envelope**: All endpoints return `{"message": "...", "error": null|{type, details}, "results": ...}`.

---

## 1. Unified Search ⭐

**POST** `/api/census/search/`

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | No | Exact date filter (YYYY-MM-DD). Mutually exclusive with `start`/`end` |
| `start` | string (date) | No | Date range start (>=). Ignored if `date` is provided |
| `end` | string (date) | No | Date range end (<=). Ignored if `date` is provided |
| `region_id` | int | No | Filter by Region ID |
| `diet_category_id` | int | No | Filter by Diet Category ID |
| `ordering` | string | No | Ordering field. Options: `date`, `region_id`, `diet_category_id`. Prefix with `-` for descending. Default: `date` |
| `page` | int | No | Page number, default: 1 |
| `page_size` | int | No | Items per page, default: 20, max: 100 |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.total` | int | Total number of items matching the criteria |
| `results.page` | int | Current page number |
| `results.page_size` | int | Items per page |
| `results.results` | array | List of census records |
| `results.results[].id` | int | Census record ID |
| `results.results[].company` | int | Company ID |
| `results.results[].date` | string | Target date (YYYY-MM-DD) |
| `results.results[].region` | int | Region ID |
| `results.results[].region_name` | string | Region name |
| `results.results[].diet_category` | int | Diet Category ID |
| `results.results[].diet_category_name` | string | Diet Category name |
| `results.results[].count` | int | Headcount |

### Sample

**Request:**
```json
POST /api/census/search/
{
    "date": "2026-03-19",
    "region_id": 1,
    "ordering": "diet_category_id",
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
        "total": 3,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "id": 10,
                "company": 1,
                "date": "2026-03-19",
                "region": 1,
                "region_name": "East Wing",
                "diet_category": 1,
                "diet_category_name": "Standard A",
                "count": 85
            },
            {
                "id": 11,
                "company": 1,
                "date": "2026-03-19",
                "region": 1,
                "region_name": "East Wing",
                "diet_category": 2,
                "diet_category_name": "Diabetic",
                "count": 12
            }
        ]
    }
}
```

---

## 2. List Census Records

**GET** `/api/census/`

### Input Data (Query Params)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | No | Exact date filter (YYYY-MM-DD). Mutually exclusive with `start`/`end` |
| `start` | string (date) | No | Date range start (>=). Ignored if `date` is provided |
| `end` | string (date) | No | Date range end (<=). Ignored if `date` is provided |
| `region_id` | int | No | Filter by Region ID |
| `diet_category_id` | int | No | Filter by Diet Category ID |

### Output Data

Paginated list. Each item has the same structure as the `results.results[]` in the search endpoint. Records are ordered by `date`, then `region_id`, then `diet_category_id`.

### Sample

**Request:**
```
GET /api/census/?date=2026-03-19&region_id=1
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": [
        {
            "id": 10,
            "company": 1,
            "date": "2026-03-19",
            "region": 1,
            "region_name": "East Wing",
            "diet_category": 1,
            "diet_category_name": "Standard A",
            "count": 85
        }
    ]
}
```

---

## 3. Batch Create/Update Census

**POST** `/api/census/batch/`

> **Atomic**: All items are saved within a single transaction.

### Input Data

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | Yes | Target date (YYYY-MM-DD) |
| `items` | array | Yes | Census entries for this date |
| `items[].region_id` | int | Yes | Region ID |
| `items[].diet_category_id` | int | Yes | Diet Category ID |
| `items[].count` | int | Yes | Headcount (>= 0) |

> **Note**: Duplicate `(region_id, diet_category_id)` pairs within the same batch are rejected. If a record already exists for the given `(date, region_id, diet_category_id)`, it will be **updated**; otherwise a new record is **created**.

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Summary: "Created X, Updated Y" |
| `results.date` | string | The target date |
| `results.created` | int | Number of newly created records |
| `results.updated` | int | Number of updated records |

### Sample — Success

**Request:**
```json
POST /api/census/batch/
{
    "date": "2026-03-19",
    "items": [
        {"region_id": 1, "diet_category_id": 1, "count": 85},
        {"region_id": 1, "diet_category_id": 2, "count": 12},
        {"region_id": 2, "diet_category_id": 1, "count": 60}
    ]
}
```

**Response (200):**
```json
{
    "message": "Created 3, Updated 0",
    "error": null,
    "results": {
        "date": "2026-03-19",
        "created": 3,
        "updated": 0
    }
}
```

### Sample — Error (duplicate items in batch)

**Request:**
```json
POST /api/census/batch/
{
    "date": "2026-03-19",
    "items": [
        {"region_id": 1, "diet_category_id": 1, "count": 85},
        {"region_id": 1, "diet_category_id": 1, "count": 90}
    ]
}
```

**Response (400):**
```json
{
    "message": "Validation Error",
    "error": {
        "type": "VALIDATION_ERROR",
        "details": {
            "items": ["Duplicate (region_id, diet_category_id) found in items."]
        }
    },
    "results": null
}
```

---

## 4. Census Summary

**GET** `/api/census/summary/`

Returns aggregated headcount totals, broken down by diet category.

### Input Data (Query Params)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (date) | No | Exact date filter (YYYY-MM-DD). Mutually exclusive with `start`/`end` |
| `start` | string (date) | No | Date range start (>=). Ignored if `date` is provided |
| `end` | string (date) | No | Date range end (<=). Ignored if `date` is provided |

### Output Data

| Field | Type | Description |
|-------|------|-------------|
| `results.date` | string\|null | The exact date filter used (null if range query) |
| `results.start` | string\|null | Start date of range (null if exact date query) |
| `results.end` | string\|null | End date of range (null if exact date query) |
| `results.total` | int | Total headcount across all diet categories |
| `results.by_diet_category` | array | Breakdown by diet category |
| `results.by_diet_category[].diet_category_id` | int | Diet Category ID |
| `results.by_diet_category[].diet_category_name` | string | Diet Category name |
| `results.by_diet_category[].count` | int | Aggregated headcount for this category |

### Sample

**Request:**
```
GET /api/census/summary/?date=2026-03-19
```

**Response:**
```json
{
    "message": "OK",
    "error": null,
    "results": {
        "date": "2026-03-19",
        "start": null,
        "end": null,
        "total": 157,
        "by_diet_category": [
            {
                "diet_category_id": 1,
                "diet_category_name": "Standard A",
                "count": 145
            },
            {
                "diet_category_id": 2,
                "diet_category_name": "Diabetic",
                "count": 12
            }
        ]
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
