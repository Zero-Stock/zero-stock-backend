# Test Coverage Report

> Generated: 2026-04-05 | Framework: `coverage.py` + `django.test` | **258 tests, all passing** ✅

## Overview

| Metric | Value |
|--------|-------|
| Total Statements | 2,226 |
| Total Branches | 536 |
| Line Coverage | **95.4%** |
| Branch Coverage | **80.8%** |

> Note: Metrics above exclude test files, migrations, `__init__.py`, and seed scripts to reflect **production code only**.

---

## Common Module

| File | Stmts | Miss | Line% | Branch | BrMiss | Branch% |
|------|------:|-----:|------:|-------:|-------:|--------:|
| `exception_handler.py` | 15 | 0 | **100.0%** | 6 | 0 | **100.0%** |
| `renderers.py` | 31 | 0 | **100.0%** | 20 | 0 | **100.0%** |
| `views.py` | 40 | 2 | **95.8%** | 8 | 0 | **100.0%** |

## Core Module

| File | Stmts | Miss | Line% | Branch | BrMiss | Branch% |
|------|------:|-----:|------:|-------:|-------:|--------:|
| `admin.py` | 33 | 2 | **93.9%** | — | — | — |
| `models.py` | 98 | 10 | **89.8%** | — | — | — |
| `serializers.py` | 132 | 0 | **100.0%** | 20 | 0 | **100.0%** |
| `urls.py` | 13 | 0 | **100.0%** | — | — | — |
| `viewsets.py` | 170 | 11 | **91.9%** | 52 | 7 | **86.5%** |

### Core Views

| File | Stmts | Miss | Line% | Branch | BrMiss | Branch% |
|------|------:|-----:|------:|-------:|-------:|--------:|
| `auth_views.py` | 34 | 0 | **100.0%** | 2 | 0 | **100.0%** |
| `company_views.py` | 11 | 0 | **100.0%** | — | — | — |
| `diet_views.py` | 10 | 0 | **100.0%** | — | — | — |
| `search_views.py` | 45 | 0 | **100.0%** | 10 | 0 | **100.0%** |
| `yield_views.py` | 36 | 2 | **95.2%** | 6 | 0 | **100.0%** |

## Operations Module

| File | Stmts | Miss | Line% | Branch | BrMiss | Branch% |
|------|------:|-----:|------:|-------:|-------:|--------:|
| `inventory_service.py` | 72 | 4 | **92.0%** | 28 | 4 | **85.7%** |
| `models.py` | 156 | 0 | **100.0%** | — | — | — |
| `serializers.py` | 194 | 3 | **97.0%** | 38 | 4 | **89.5%** |
| `urls.py` | 8 | 0 | **100.0%** | — | — | — |
| `viewsets.py` | 56 | 1 | **97.4%** | 20 | 1 | **95.0%** |

### Operations Views

| File | Stmts | Miss | Line% | Branch | BrMiss | Branch% |
|------|------:|-----:|------:|-------:|-------:|--------:|
| `census_views.py` | 77 | 2 | **97.9%** | 18 | 0 | **100.0%** |
| `cooking_views.py` | 55 | 0 | **100.0%** | 12 | 0 | **100.0%** |
| `delivery_views.py` | 90 | 2 | **94.9%** | 28 | 4 | **85.7%** |
| `processing_views.py` | 85 | 6 | **91.2%** | 28 | 4 | **85.7%** |
| `procurement_views.py` | 229 | 4 | **96.7%** | 72 | 6 | **91.7%** |
| `receiving_views.py` | 79 | 1 | **97.2%** | 30 | 2 | **93.3%** |
| `region_views.py` | 32 | 2 | **94.1%** | 2 | 0 | **100.0%** |
| `search_views.py` | 157 | 6 | **94.1%** | 64 | 7 | **89.1%** |

---

## Excluded Files

The following are intentionally excluded from coverage targets:

- `core/management/commands/seed_materials.py` — Data seed script
- `core/management/commands/seed_menu_demo.py` — Demo data script
- All `__init__.py`, migration files, and test files
