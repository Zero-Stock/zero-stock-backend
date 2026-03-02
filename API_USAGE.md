# 食堂管理系统 API 使用文档

本文档介绍如何使用已实现的 RESTful APIs。

## 目录

1. [认证 APIs](#认证-apis)
2. [公司与区域 APIs](#公司与区域-apis)
3. [基础数据 APIs](#基础数据-apis)
4. [菜品与配方 APIs](#菜品与配方-apis)
5. [周菜单配置 APIs](#周菜单配置-apis)
6. [住院人数统计 APIs](#住院人数统计-apis)
7. [采购清单 APIs](#采购清单-apis)
8. [收货清单 APIs](#收货清单-apis)
9. [加工需求清单 APIs](#加工需求清单-apis)
10. [菜品制作（配方查看）APIs](#菜品制作配方查看-apis)
11. [送餐需求表 APIs](#送餐需求表-apis)
12. [供应商管理 APIs](#供应商管理-apis)
13. [常见问题](#常见问题)

---

## 认证 APIs

> 本系统使用 JWT (JSON Web Token) 认证。登录后获取 `access` 和 `refresh` token。
> 需要认证的接口请在请求头中添加：`Authorization: Bearer <access_token>`

### 1. 用户登录

**POST** `/api/auth/login/`

**请求体：**
```json
{
    "username": "admin",
    "password": "your_password"
}
```

**响应示例：**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": "RW",
        "company": {
            "id": 1,
            "name": "XX医院",
            "code": "HOSP01"
        }
    }
}
```

---

### 2. 获取当前用户信息 🔒

**GET** `/api/auth/me/`

**响应示例：**
```json
{
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "RW",
    "company": {
        "id": 1,
        "name": "XX医院",
        "code": "HOSP01"
    }
}
```

---

### 3. 用户登出 🔒

**POST** `/api/auth/logout/`

**请求体：**
```json
{
    "refresh": "<refresh_token>"
}
```

**响应：** `{"detail": "Logged out."}`

---

## 公司与区域 APIs

### 4. 获取公司列表 🔒

**GET** `/api/companies/`

返回当前用户所属公司信息。

**响应示例：**
```json
[
    {"id": 1, "name": "XX医院", "code": "HOSP01"}
]
```

---

### 5. 管理公司区域/病区 🔒

#### 5.1 获取区域列表

**GET** `/api/companies/{company_id}/regions/`

**响应示例：**
```json
[
    {"id": 1, "name": "东区", "company": 1},
    {"id": 2, "name": "ICU", "company": 1}
]
```

#### 5.2 创建区域

**POST** `/api/companies/{company_id}/regions/`

**请求体：**
```json
{
    "name": "VIP楼"
}
```

**响应：** 201 Created

---

## 基础数据 APIs

### 6. 原料分类管理

#### 6.1 获取分类列表

**GET** `/api/material-categories/`

**响应示例：**
```json
[
    {"id": 1, "name": "鲜品"},
    {"id": 2, "name": "冻品"},
    {"id": 3, "name": "粮油"}
]
```

#### 6.2 创建/修改/删除分类

**POST** `/api/material-categories/`

```json
{"name": "调味品"}
```

**PUT/PATCH** `/api/material-categories/{id}/`

**DELETE** `/api/material-categories/{id}/`

---

### 7. 餐食类型（套餐）管理

#### 7.1 获取套餐列表

**GET** `/api/diets/`

**响应示例：**
```json
[
    {"id": 1, "name": "标准套餐A"},
    {"id": 2, "name": "糖尿病餐"},
    {"id": 3, "name": "软食"}
]
```

#### 7.2 创建/修改套餐

**POST** `/api/diets/`

```json
{"name": "新套餐类型"}
```

**PUT/PATCH** `/api/diets/{id}/`

#### 7.3 获取套餐下的菜品

**GET** `/api/diets/{id}/dishes/`

#### 7.4 批量为套餐分配菜品

**POST** `/api/diets/{id}/dishes/`

**请求体：**
```json
{
    "dish_ids": [1, 2, 3]
}
```

---

### 8. 食材管理

#### 8.1 食材列表（支持搜索、筛选、排序、分组）

**GET** `/api/materials/`

**查询参数：**
- `search`: 按名称搜索，例如 `?search=土豆`
- `category`: 按分类ID筛选，例如 `?category=1`
- `ordering`: 排序（支持 `id`、`name`），前加 `-` 倒序，例如 `?ordering=-name`
- `group_by`: 分组返回（支持 `category`），例如 `?group_by=category`

**响应示例：**
```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "土豆",
            "category": 1,
            "category_name": "鲜品",
            "specs": [
                {
                    "id": 1,
                    "method_name": "去皮切块",
                    "yield_rate": "0.80"
                }
            ]
        }
    ]
}
```

**说明：**
- `category` 为原料分类的 ID（关联 MaterialCategory 表）
- `category_name` 为分类名称（只读）
- `specs` 为该食材的加工规格列表

---

#### 8.2 获取单个食材详情

**GET** `/api/materials/{id}/`

返回与列表相同结构的单个食材对象。

---

#### 8.3 删除食材

**DELETE** `/api/materials/{id}/`

**响应：** 204 No Content

---

#### 8.4 批量添加/修改食材

**POST** `/api/materials/batch/`

**请求体（JSON 数组）：**
```json
[
    {"name": "带鱼", "category": 2},
    {"name": "大米", "category": 3},
    {"id": 1, "name": "番茄（更新）", "category": 1}
]
```

**规则：**
- 有 `id` → 更新已有记录
- 无 `id` → 创建新记录
- `category` 为 MaterialCategory 的 ID

**响应示例：**
```json
{
    "message": "创建 2 条，更新 1 条，失败 0 条",
    "created": [...],
    "updated": [...],
    "errors": []
}
```

---

#### 8.5 为食材添加加工规格

**POST** `/api/materials/{id}/specs/`

**请求体：**
```json
{
    "method_name": "切丝",
    "yield_rate": "0.85"
}
```

**响应：** 201 Created

**说明：**
- `yield_rate`：出成率，0.80 表示 80%（即 1kg 原料加工后得到 0.8kg）
- 同一食材不能有重复的加工方法名称

---

## 菜品与配方 APIs

### 9. 菜品列表（支持搜索）

**GET** `/api/dishes/`

**查询参数：**
- `search`: 按菜品名称搜索，例如 `?search=牛肉`

**响应示例：**
```json
{
    "count": 1,
    "results": [
        {
            "id": 1,
            "name": "番茄牛腩",
            "seasonings": "盐、酱油、料酒",
            "cooking_method": "先炒后炖，大火收汁",
            "ingredients": [
                {
                    "id": 1,
                    "raw_material": 1,
                    "raw_material_name": "牛肉",
                    "processing": 1,
                    "processing_name": "切块",
                    "yield_rate": 0.95,
                    "net_quantity": "0.150"
                },
                {
                    "id": 2,
                    "raw_material": 2,
                    "raw_material_name": "番茄",
                    "processing": 2,
                    "processing_name": "切块",
                    "yield_rate": 0.90,
                    "net_quantity": "0.100"
                }
            ]
        }
    ]
}
```

**说明：**
- `raw_material` 字段是 `RawMaterial` 的 ID
- `processing` 字段是 `ProcessedMaterial` 的 ID（可选，为 null 表示无加工）
- `processing_name` 显示加工方法名称
- `yield_rate` 显示该加工方法的出成率
- `seasonings` 调料信息
- `cooking_method` 制作工艺
- `ingredients` 为只读字段

---

### 10. 创建菜品及配方（嵌套创建）

**POST** `/api/dishes/`

**请求体：**
```json
{
    "name": "番茄牛腩",
    "seasonings": "盐、酱油、料酒",
    "cooking_method": "先炒后炖，大火收汁",
    "ingredients_write": [
        {
            "raw_material": 1,
            "processing": 1,
            "net_quantity": "0.150"
        },
        {
            "raw_material": 2,
            "processing": 2,
            "net_quantity": "0.100"
        }
    ]
}
```

**说明：**
- `raw_material`: RawMaterial 的 ID
- `processing`: ProcessedMaterial 的 ID（可选，可为 null）
- `net_quantity`: 每份菜品需要的净重量（kg）
- `ingredients_write`: 只写字段，用于创建/更新配方
- `seasonings`: 调料说明（可选）
- `cooking_method`: 制作工艺说明（可选）

**响应：** 201 Created，返回创建的菜品及配方详情

---

### 11. 获取菜品详情

**GET** `/api/dishes/{id}/`

返回菜品完整信息，包含所有配方详情。

---

### 12. 更新菜品及配方

**PUT/PATCH** `/api/dishes/{id}/`

**请求体示例（更新配方）：**
```json
{
    "name": "番茄牛腩（改良版）",
    "seasonings": "盐、酱油、料酒、白糖",
    "ingredients_write": [
        {
            "raw_material": 1,
            "processing": 1,
            "net_quantity": "0.200"
        },
        {
            "raw_material": 2,
            "processing": 2,
            "net_quantity": "0.120"
        }
    ]
}
```

**说明：**
- 如果提供 `ingredients_write`，会删除旧配方并创建新配方
- 如果不提供 `ingredients_write`，只更新菜品基本信息

---

### 13. 删除菜品

**DELETE** `/api/dishes/{id}/`

**响应：** 204 No Content

---

### 14. 获取菜品打印格式 ⭐

**GET** `/api/dishes/print/`

获取所有菜品的打印友好格式，适合导出菜谱。

**响应示例：**
```json
[
    {
        "id": 1,
        "name": "番茄牛腩",
        "ingredients_text": "牛肉[切块]150g、番茄[切块]100g",
        "seasonings": "盐、酱油、料酒",
        "cooking_method": "先炒后炖，大火收汁"
    }
]
```

**说明：**
- `ingredients_text`：将配方格式化为字符串，格式为 `原料名[加工方法]克重`

---

## 周菜单配置 APIs

### 15. 查询周菜单

**GET** `/api/weekly-menus/`

**查询参数：**
- `company`: 公司 ID，例如 `?company=1`
- `diet_category`: 餐食类型 ID，例如 `?diet_category=1`
- `day_of_week`: 星期几（1-7），例如 `?day_of_week=1`
- `meal_time`: 用餐时间（B/L/D），例如 `?meal_time=L`

**响应示例：**
```json
{
    "count": 2,
    "results": [
        {
            "id": 1,
            "company": 1,
            "company_name": "XX医院",
            "diet_category": 1,
            "diet_category_name": "标准套餐A",
            "day_of_week": 5,
            "day_display": "Friday",
            "meal_time": "L",
            "meal_display": "Lunch",
            "dishes": [1, 2, 3],
            "dish_names": ["番茄炒蛋", "土豆丝", "米饭"],
            "dishes_detail": [
                {"dish_id": 1, "dish_name": "番茄炒蛋", "quantity": 2},
                {"dish_id": 2, "dish_name": "土豆丝", "quantity": 3},
                {"dish_id": 3, "dish_name": "米饭", "quantity": 1}
            ]
        }
    ]
}
```

**说明：**
- `day_display`: 英文星期名
- `meal_display`: 英文餐次名
- `dish_names`: 菜品名称列表（仅名称字符串）
- `dishes_detail`: 菜品详情列表，包含每道菜的 `dish_id`、`dish_name` 和 `quantity`（份数/盘数）
- `quantity`：该菜品在本餐次的数量，默认为 1。例如 `quantity: 2` 表示该菜做两盘

---

### 16. 创建单个菜单配置

**POST** `/api/weekly-menus/`

**请求体（方式一：纯 ID 列表，quantity 默认为 1）：**
```json
{
    "company": 1,
    "diet_category": 1,
    "day_of_week": 1,
    "meal_time": "L",
    "dishes": [1, 2, 3]
}
```

**请求体（方式二：指定每道菜的数量）：**
```json
{
    "company": 1,
    "diet_category": 1,
    "day_of_week": 5,
    "meal_time": "L",
    "dishes": [
        {"dish_id": 1, "quantity": 2},
        {"dish_id": 2, "quantity": 3},
        {"dish_id": 3, "quantity": 1}
    ]
}
```

**响应：** 201 Created

**说明：**
- `dishes` 支持两种格式：纯菜品 ID 列表（向后兼容，数量默认 1）或对象列表（可指定 quantity）

---

### 17. 批量创建/更新周菜单 ⭐

**POST** `/api/weekly-menus/batch/`

**请求体（JSON 数组，注意外层无需包裹）：**
```json
[
    {
        "company": 1,
        "diet_category": 1,
        "day_of_week": 1,
        "meal_time": "L",
        "dishes": [1, 2, 3]
    },
    {
        "company": 1,
        "diet_category": 1,
        "day_of_week": 5,
        "meal_time": "L",
        "dishes": [
            {"dish_id": 1, "quantity": 2},
            {"dish_id": 2, "quantity": 3}
        ]
    }
]
```

**响应示例：**
```json
{
    "message": "成功处理 2 条菜单配置",
    "data": [...]
}
```

**说明：**
- 如果指定的组合（公司+餐食类型+星期+用餐时间）已存在，则更新菜品列表
- 如果不存在，则创建新配置
- 适合前端一次性提交整周的菜单安排
- `dishes` 支持纯 ID 列表（quantity 默认 1）和对象列表（可指定 quantity）

---

### 18. 更新/删除单个菜单配置

**PUT/PATCH** `/api/weekly-menus/{id}/`

**请求体示例（纯 ID 列表）：**
```json
{
    "dishes": [10, 11, 12]
}
```

**请求体示例（带数量）：**
```json
{
    "dishes": [
        {"dish_id": 10, "quantity": 2},
        {"dish_id": 11, "quantity": 1}
    ]
}
```

**DELETE** `/api/weekly-menus/{id}/`

---

## 住院人数统计 APIs

> 以下接口均需要认证 🔒，数据自动按用户所属公司隔离。

### 19. 获取每日人数统计 🔒

**GET** `/api/census/`

**查询参数：**
- `date`: 精确日期，例如 `?date=2026-02-25`
- `start` / `end`: 日期范围，例如 `?start=2026-02-01&end=2026-02-28`
- `region_id`: 区域 ID，例如 `?region_id=1`
- `diet_category_id`: 套餐类型 ID，例如 `?diet_category_id=1`

**响应示例：**
```json
[
    {
        "id": 1,
        "company": 1,
        "date": "2026-02-25",
        "region": 1,
        "region_name": "东区",
        "diet_category": 1,
        "diet_category_name": "标准套餐A",
        "count": 120
    }
]
```

---

### 20. 批量录入每日人数 🔒

**POST** `/api/census/batch/`

**请求体：**
```json
{
    "date": "2026-02-25",
    "items": [
        {"region_id": 1, "diet_category_id": 1, "count": 120},
        {"region_id": 1, "diet_category_id": 2, "count": 15},
        {"region_id": 2, "diet_category_id": 1, "count": 85}
    ]
}
```

**说明：**
- 如果相同（日期+区域+套餐类型）已存在，则更新人数
- `company` 从用户 Token 中自动获取

**响应示例：**
```json
{
    "date": "2026-02-25",
    "created": 2,
    "updated": 1
}
```

---

### 21. 按日期汇总统计 🔒

**GET** `/api/census/summary/`

**查询参数：**
- `date`: 精确日期
- `start` / `end`: 日期范围

**响应示例：**
```json
{
    "date": "2026-02-25",
    "start": null,
    "end": null,
    "total": 220,
    "by_diet_category": [
        {
            "diet_category_id": 1,
            "diet_category_name": "标准套餐A",
            "count": 205
        },
        {
            "diet_category_id": 2,
            "diet_category_name": "糖尿病餐",
            "count": 15
        }
    ]
}
```

---

## 采购清单 APIs

> 以下接口均需要认证 🔒，数据自动按用户所属公司隔离。
> 生成和确认操作需要 RW（Read/Write）权限。
>
> **两步式采购流程：**
> 1. **生成采购量**（`generate`）：根据人数+菜单自动计算公斤级采购量，状态变为 `PENDING`
> 2. **分配供应商**（`template` + `assign-suppliers`）：查看可选供应商，分配后自动计算供应商单位数量并确认

### 22. 生成采购单 🔒🔑RW

**POST** `/api/procurement/generate/`

**请求体：**
```json
{
    "date": "2026-02-25"
}
```

**说明：**
- 根据日期查找 Census（人数） + WeeklyMenu/DailyMenu（菜单） + 配方自动计算采购量
- 自动拆分 AM（早餐+午餐）和 PM（晚餐）用量
- 如果该日期已有非 CONFIRMED 采购单则重新生成覆盖
- CONFIRMED 状态不可重新生成
- 生成后状态为 `PENDING`（等待分配供应商）

**响应：** 201 Created，返回采购单详情

---

### 23. 获取采购单列表 🔒

**GET** `/api/procurement/`

返回当前公司的采购单列表，按日期倒序。

**响应中每个采购单包含：**
- `id`, `company`, `target_date`, `status`, `created_at`
- `items`: 采购明细列表

**采购单状态说明：**
- `DRAFT`: 草稿（计算中）
- `PENDING`: 等待供应商选择
- `CONFIRMED`: 已确认（已发送）

---

### 24. 查看采购单详情 🔒

**GET** `/api/procurement/{id}/`

---

### 25. 获取采购明细 🔒

**GET** `/api/procurement/{id}/items/`

**查询参数（可选）：**
- `group_by=supplier`: 按供应商分组汇总
- `group_by=category`: 按品类分组汇总

**明细字段说明：**
```json
{
    "id": 1,
    "raw_material": 1,
    "raw_material_name": "土豆",
    "category": "鲜品",
    "total_gross_quantity": "17.50",
    "am_quantity": "12.50",
    "pm_quantity": "5.00",
    "supplier": null,
    "supplier_name": null,
    "supplier_unit_name": "",
    "supplier_unit_qty": null,
    "supplier_price": null,
    "notes": "..."
}
```

---

### 26. 获取采购模板（第一步：查看可选供应商） ⭐🔒

**GET** `/api/procurement/template/?date=2026-02-27`

用于查看每种原料的公斤级采购量及可分配的供应商列表。

**响应示例：**
```json
{
    "id": 1,
    "date": "2026-02-27",
    "status": "PENDING",
    "items": [
        {
            "item_id": 101,
            "raw_material_id": 1,
            "raw_material_name": "土豆",
            "category": "鲜品",
            "total_kg": 17.5,
            "am_kg": 12.5,
            "pm_kg": 5.0,
            "current_supplier_id": null,
            "available_suppliers": [
                {
                    "supplier_material_id": 10,
                    "supplier_id": 1,
                    "supplier_name": "张三蔬菜",
                    "unit_name": "箱",
                    "kg_per_unit": 10.0,
                    "price": 35.0
                },
                {
                    "supplier_material_id": 11,
                    "supplier_id": 2,
                    "supplier_name": "李四农产",
                    "unit_name": "kg",
                    "kg_per_unit": 1.0,
                    "price": 3.5
                }
            ]
        }
    ]
}
```

---

### 27. 分配供应商（第二步：分配并确认） ⭐🔒🔑RW

**POST** `/api/procurement/assign-suppliers/?date=2026-02-27`

为采购项分配供应商，系统自动计算供应商单位数量（如 17.5kg ÷ 10kg/箱 = 1.75 箱），分配完成后状态自动变为 `CONFIRMED`。

**请求体：**
```json
{
    "assignments": [
        {"item_id": 101, "supplier_material_id": 10},
        {"item_id": 102, "supplier_material_id": 15}
    ]
}
```

**说明：**
- `item_id`: ProcurementItem 的 ID
- `supplier_material_id`: SupplierMaterial 的 ID（从 template 接口获取）
- 系统自动计算 `supplier_unit_qty = total_kg / kg_per_unit`
- 分配成功后采购单状态自动变为 `CONFIRMED`

**响应：** 返回更新后的完整采购单

---

### 28. 获取采购单打印表格数据 ⭐🔒

**GET** `/api/procurement/{id}/sheet/`

用于前端渲染含供应商单位信息的最终采购申请表格。

**响应示例：**
```json
{
    "id": 1,
    "date": "2026-02-25",
    "day_of_week": "周三",
    "company": "XX医院",
    "status": "CONFIRMED",
    "items": [
        {
            "name": "土豆",
            "category": "鲜品",
            "total_kg": 17.5,
            "am_kg": 12.5,
            "pm_kg": 5.0,
            "supplier": "张三蔬菜",
            "supplier_unit_name": "箱",
            "supplier_unit_qty": 1.75,
            "supplier_price": 35.0
        },
        {
            "name": "猪肉",
            "category": "冻品",
            "total_kg": 8.0,
            "am_kg": 8.0,
            "pm_kg": 0.0,
            "supplier": null,
            "supplier_unit_name": null,
            "supplier_unit_qty": null,
            "supplier_price": null
        }
    ]
}
```

**说明：**
- 数据已经按照原料维度汇总，并按分类+名称排序
- `total_kg`/`am_kg`/`pm_kg` 为公斤级重量
- `supplier*` 字段在分配供应商之前为 null
- 分配供应商后显示供应商名称、单位名、换算后的数量和单价

---

### 29. 确认采购单 🔒🔑RW

**POST** `/api/procurement/{id}/confirm/`

将采购单状态改为 CONFIRMED（也可通过 `assign-suppliers` 自动确认）。

**响应示例：**
```json
{
    "id": 1,
    "status": "CONFIRMED"
}
```

---

## 收货清单 APIs

### 30. 获取收货验收模板

**GET** `/api/receiving/{procurement_id}/template/`

根据采购单生成收货模板（含应收量），用于填写实收量。

**响应示例：**
```json
{
    "procurement_id": 1,
    "target_date": "2026-02-25",
    "company": "XX医院",
    "status": "CONFIRMED",
    "items": [
        {
            "raw_material_id": 1,
            "raw_material_name": "土豆",
            "expected_quantity": 17.5,
            "category": "鲜品",
            "actual_quantity": 0
        }
    ]
}
```

---

### 31. 录入实际收货记录

**POST** `/api/receiving/`

**请求体：**
```json
{
    "procurement_id": 1,
    "notes": "部分短缺",
    "items": [
        {"raw_material_id": 1, "actual_quantity": 17.0, "notes": ""},
        {"raw_material_id": 2, "actual_quantity": 7.5, "notes": "缺0.5kg"}
    ]
}
```

**响应：** 201 Created，返回收货记录详情（含实收 vs 应收对比）

---

### 32. 查看收货详情

**GET** `/api/receiving/{id}/`

**响应中每条明细包含：**
- `expected_quantity`: 应收量
- `actual_quantity`: 实收量
- `difference`: 差异量（actual - expected）

---

## 加工需求清单 APIs

### 33. 生成加工清单

**POST** `/api/processing/generate/`

**请求体：**
```json
{
    "date": "2026-02-25"
}
```

根据当日周菜单 + 人数自动计算加工需求。

**响应：** 201 Created，返回加工清单详情

---

### 34. 查看加工清单详情

**GET** `/api/processing/{id}/`

---

### 35. 按原料维度查看

**GET** `/api/processing/{id}/by-material/`

**响应示例：**
```json
[
    {
        "material": "土豆",
        "methods": [
            {
                "method": "切丝",
                "total_quantity": 30.0,
                "dishes": [
                    {"dish": "酸辣土豆丝", "net_qty": 16.0, "gross_qty": 20.0},
                    {"dish": "土豆丝炒肉", "net_qty": 8.0, "gross_qty": 10.0}
                ]
            },
            {
                "method": "切块",
                "total_quantity": 20.0,
                "dishes": [
                    {"dish": "红烧土豆", "net_qty": 16.0, "gross_qty": 20.0}
                ]
            }
        ]
    }
]
```

---

### 36. 按菜品维度查看

**GET** `/api/processing/{id}/by-dish/`

**响应示例：**
```json
[
    {
        "dish": "酸辣土豆丝",
        "ingredients": [
            {
                "material": "土豆",
                "method": "切丝",
                "net_quantity": 16.0,
                "gross_quantity": 20.0
            }
        ]
    }
]
```

---

### 37. 按车间/类别分组

**GET** `/api/processing/{id}/by-workshop/`

**响应示例：**
```json
[
    {
        "workshop": "鲜品",
        "items": [
            {
                "dish": "酸辣土豆丝",
                "material": "土豆",
                "method": "切丝",
                "net_quantity": 16.0,
                "gross_quantity": 20.0
            }
        ]
    }
]
```

---

## 菜品制作（配方查看）APIs

### 38. 获取当日制作任务

**GET** `/api/cooking/today/`

**查询参数：**
- `meal_time`: 筛选餐次，例如 `?meal_time=L`
- `company`: 筛选公司 ID，例如 `?company=1`

根据当天星期自动匹配周菜单，并按人数计算用量。

**响应示例：**
```json
[
    {
        "company": "XX医院",
        "diet_category": "标准套餐A",
        "meal_time": "Lunch",
        "headcount": 120,
        "dishes": [
            {
                "dish_id": 1,
                "dish_name": "番茄牛腩",
                "ingredients": [
                    {
                        "material": "牛肉",
                        "method": "切块",
                        "net_per_serving": 0.15,
                        "net_total": 18.0,
                        "gross_total": 18.95
                    }
                ]
            }
        ]
    }
]
```

---

### 39. 查看单道菜的完整配方

**GET** `/api/cooking/recipe/{dish_id}/`

**查询参数：**
- `count`: 按人数计算用量，例如 `?count=100`（默认为 1）

**响应示例：**
```json
{
    "dish_id": 1,
    "dish_name": "番茄牛腩",
    "count": 100,
    "ingredients": [
        {
            "material": "牛肉",
            "method": "切块",
            "yield_rate": 0.95,
            "net_per_serving": 0.15,
            "net_total": 15.0,
            "gross_total": 15.79,
            "unit": "kg"
        },
        {
            "material": "番茄",
            "method": "切块",
            "yield_rate": 0.9,
            "net_per_serving": 0.1,
            "net_total": 10.0,
            "gross_total": 11.11,
            "unit": "kg"
        }
    ]
}
```

---

## 送餐需求表 APIs

### 40. 生成送餐分派表

**POST** `/api/delivery/generate/`

**请求体：**
```json
{
    "date": "2026-02-25",
    "meal_time": "L"
}
```

根据日期 + 餐次自动从 Census 数据生成送餐分派表。

**响应：** 201 Created，返回送餐单详情列表

---

### 41. 查看送餐需求详情

**GET** `/api/delivery/{id}/`

---

### 42. 按区域分组视图

**GET** `/api/delivery/{id}/by-region/`

**响应示例：**
```json
[
    {
        "region": "东区",
        "items": [
            {"diet_category": "标准套餐A", "count": 120},
            {"diet_category": "糖尿病餐", "count": 15}
        ],
        "total": 135
    }
]
```

---

### 43. 获取送餐打单数据 ⭐

**GET** `/api/delivery/{id}/export/`

获取完整、层次化的 JSON 送餐打单数据结构（前端表格渲染、打印用）。

**响应示例：**
```json
{
    "title": "Delivery Demand Form",
    "company": "XX医院",
    "date": "2026-02-25",
    "meal_time": "Lunch",
    "regions": [
        {
            "region": "东区",
            "diets": [
                {"diet_category": "标准套餐A", "count": 120},
                {"diet_category": "糖尿病餐", "count": 15}
            ],
            "total_count": 135
        },
        {
            "region": "研发楼B",
            "diets": [
                {"diet_category": "标准套餐A", "count": 85}
            ],
            "total_count": 85
        }
    ],
    "grand_total": 220
}
```

---

## 供应商管理 APIs

### 44. 供应商列表与创建

**GET** `/api/suppliers/`

**查询参数：**
- `search`: 按名称搜索，例如 `?search=张三`

**响应示例：**
```json
[
    {
        "id": 1,
        "name": "张三蔬菜批发",
        "contact_person": "张三",
        "phone": "13800138000",
        "address": "某某路123号",
        "materials": [
            {
                "id": 1,
                "raw_material": 1,
                "raw_material_name": "土豆",
                "unit_name": "箱",
                "kg_per_unit": "10.00",
                "price": "35.00",
                "notes": "优质供应"
            }
        ]
    }
]
```

**POST** `/api/suppliers/`

**请求体：**
```json
{
    "name": "张三蔬菜批发",
    "contact_person": "张三",
    "phone": "13800138000",
    "address": "某某路123号"
}
```

---

### 45. 修改供应商

**PUT/PATCH** `/api/suppliers/{id}/`

---

### 46. 管理供应商可供应的原材料

#### 获取供应商原材料列表

**GET** `/api/suppliers/{id}/materials/`

**响应示例：**
```json
[
    {
        "id": 1,
        "raw_material": 1,
        "raw_material_name": "土豆",
        "unit_name": "箱",
        "kg_per_unit": "10.00",
        "price": "35.00",
        "notes": "优质供应"
    }
]
```

#### 为供应商添加原材料

**POST** `/api/suppliers/{id}/materials/`

**请求体：**
```json
{
    "raw_material": 1,
    "unit_name": "箱",
    "kg_per_unit": "10.00",
    "price": "35.00",
    "notes": "优质供应"
}
```

**说明：**
- `unit_name`: 供应商的销售单位（如 箱、袋、盒、kg）
- `kg_per_unit`: 每个销售单位对应的公斤数（如 1箱=10kg 就填 10）
- `price`: 每个销售单位的单价
- 同一供应商不能重复添加同一原料

---

## 常见问题

### Q1: ProcessedMaterial 和 RawMaterial 的区别？

- **RawMaterial（原料）**：从供应商采购的原始食材，如"土豆"。内部计量统一使用公斤（kg）。
- **ProcessedMaterial（加工规格）**：原料的加工方式及出成率，如"土豆-去皮切块-80%"

配方中使用的是 RawMaterial + ProcessedMaterial 的组合，因为需要知道加工损耗。

### Q2: 为什么创建菜品时使用 `ingredients_write` 而不是 `ingredients`？

- `ingredients`：只读字段，用于显示完整的配方详情
- `ingredients_write`：只写字段，用于创建/更新时接收配方数据

这样设计是为了区分读取和写入的数据格式。

### Q3: 如何实现多租户数据隔离？

需要认证的接口（标记 🔒 的）会自动通过 JWT Token 获取用户所属公司，仅返回该公司数据。
部分基础数据接口（食材、菜品、周菜单等）目前允许所有访问。

### Q4: day_of_week 的值是什么？

- 1 = 周一 (Monday)
- 2 = 周二 (Tuesday)
- 3 = 周三 (Wednesday)
- 4 = 周四 (Thursday)
- 5 = 周五 (Friday)
- 6 = 周六 (Saturday)
- 7 = 周日 (Sunday)

### Q5: meal_time 的值是什么？

- `B` = 早餐 (Breakfast)
- `L` = 午餐 (Lunch)
- `D` = 晚餐 (Dinner)

### Q6: 哪些接口需要认证？

文档中标记 🔒 的接口需要在请求头中携带 JWT Token。标记 🔑RW 的接口还需要用户角色为 RW（管理员）。

### Q7: 采购流程的三个状态是什么？

- `DRAFT`: 草稿状态（计算中）
- `PENDING`: 采购量已生成，等待分配供应商
- `CONFIRMED`: 已确认（已分配供应商或手动确认）

典型流程：`generate` → PENDING → `template`查看 → `assign-suppliers`确认 → CONFIRMED

### Q8: 供应商单位换算怎么工作？

供应商有自己的销售单位（如 箱、袋），通过 `kg_per_unit` 字段定义换算关系。
例如：土豆供应商按"箱"销售，1箱=10kg，采购需要 17.5kg，则自动计算为 1.75 箱。

---

## 下一步

建议使用 Django REST Framework 的可浏览 API 进行测试：
1. 启动服务器：`python manage.py runserver`
2. 在浏览器访问：`http://localhost:8000/api/`
3. 可以可视化浏览所有接口并进行测试

或使用 Postman/curl 进行 API 测试。
