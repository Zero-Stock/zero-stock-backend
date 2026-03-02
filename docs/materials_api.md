# Materials API 文档

## 概览

食材（Raw Material）相关的 API 接口，支持食材的增删改查、批量操作、加工规格管理和出成率配置。

---

## 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/materials/search/` | **统一搜索**（筛选+排序+分页） |
| GET | `/api/materials/` | 获取食材列表 |
| GET | `/api/materials/{id}/` | 获取单个食材详情 |
| POST | `/api/materials/batch/` | 批量新增/修改食材 |
| POST | `/api/materials/{id}/specs/` | 添加加工规格 |
| DELETE | `/api/materials/{id}/` | 删除食材 |
| PUT | `/api/raw-materials/{id}/yield-rate/` | 更新出成率 |

---

## 1. 统一搜索 ⭐

**POST** `/api/materials/search/`

**请求体（所有字段均可选）：**

```json
{
    "name": "土豆",
    "category": 1,
    "ordering": "name",
    "page": 1,
    "page_size": 20
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | string | 模糊搜索食材名称（包含匹配） |
| `category` | int | 按分类 ID 精确筛选 |
| `ordering` | string | 排序字段，前加 `-` 倒序。可选值：`id`, `name`, `category__name` |
| `page` | int | 页码，默认 1 |
| `page_size` | int | 每页条数，默认 20，最大 100 |

**响应示例：**

```json
{
    "total": 42,
    "page": 1,
    "page_size": 20,
    "results": [
        {
            "id": 1,
            "name": "土豆",
            "category": 1,
            "category_name": "鲜品",
            "specs": [
                {"id": 1, "method_name": "去皮切丝"},
                {"id": 2, "method_name": "去皮切块"}
            ],
            "current_yield_rate": "0.85"
        }
    ]
}
```

**调用示例：**

```bash
# 搜索名称含"土豆"的食材
curl -X POST http://localhost:8000/api/materials/search/ \
  -H "Content-Type: application/json" \
  -d '{"name": "土豆"}'

# 筛选鲜品分类，按名称倒序，第2页
curl -X POST http://localhost:8000/api/materials/search/ \
  -H "Content-Type: application/json" \
  -d '{"category": 1, "ordering": "-name", "page": 2}'

# 无筛选条件，获取全部（分页）
curl -X POST http://localhost:8000/api/materials/search/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 2. 获取食材列表

**GET** `/api/materials/`

**查询参数（可选）：**

| 参数 | 说明 |
|------|------|
| `search` | 按名称搜索 |
| `category` | 按分类 ID 筛选 |
| `ordering` | 排序：`id`, `name`, `category__name` |
| `group_by` | 分组返回：`category` 或 `unit` |

**响应：** 分页列表，格式同搜索接口的 results 内容

---

## 3. 获取食材详情

**GET** `/api/materials/{id}/`

**响应示例：**

```json
{
    "id": 1,
    "name": "土豆",
    "category": 1,
    "category_name": "鲜品",
    "specs": [
        {"id": 1, "method_name": "去皮切丝"},
        {"id": 2, "method_name": "去皮切块"}
    ],
    "current_yield_rate": "0.85"
}
```

---

## 4. 批量新增/修改食材

**POST** `/api/materials/batch/`

**请求体（JSON 数组）：**

```json
[
    {
        "name": "土豆",
        "category": 1,
        "yield_rate": "0.85",
        "specs": [
            {"method_name": "去皮切丝"},
            {"method_name": "去皮切块"}
        ]
    },
    {
        "id": 5,
        "name": "番茄",
        "category": 1
    }
]
```

**规则：**
- 有 `id` → 按 ID 更新
- 无 `id` 但 `name` 匹配已有记录 → 按名称更新
- 无 `id` 且 `name` 不存在 → 新建

**响应示例：**

```json
{
    "message": "Created 1, Updated 1, Failed 0",
    "created": [...],
    "updated": [...],
    "errors": []
}
```

---

## 5. 添加加工规格

**POST** `/api/materials/{id}/specs/`

**请求体：**

```json
{
    "method_name": "去皮切块"
}
```

**响应：** 201 Created

---

## 6. 删除食材

**DELETE** `/api/materials/{id}/`

**响应：** 204 No Content

---

## 7. 更新出成率

**PUT** `/api/raw-materials/{id}/yield-rate/`

**请求体：**

```json
{
    "yield_rate": "0.85"
}
```

**说明：** 出成率次日生效（effective_date = 当天 + 1）

---

## 数据模型

### RawMaterial（食材）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `name` | string | 食材名称（唯一） |
| `category` | FK → MaterialCategory | 分类 |

### ProcessedMaterial（加工规格）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `raw_material` | FK → RawMaterial | 所属食材 |
| `method_name` | string | 加工方法名 |

### RawMaterialYieldRate（出成率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw_material` | FK → RawMaterial | 所属食材 |
| `yield_rate` | decimal | 出成率（1.00=100%） |
| `effective_date` | date | 生效日期 |
