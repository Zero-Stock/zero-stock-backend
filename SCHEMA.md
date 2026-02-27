# 食堂管理系统数据库架构 (Database Schema)

## 1. 用户与租户管理 (User & Tenant Management)

核心模块，处理多租户隔离和用户权限。所有业务数据均隔离至特定公司 ID 下。

### `ClientCompany` (客户公司)
代表租户实体（如医院A、康复中心B）。
- `id`: PK
- `name`: 公司名称
- `code`: 唯一标识符 (如 HOSP01)
- `created_at`: 创建时间

### `UserProfile` (用户配置)
扩展 Django内置 User 模型，添加租户关联角色。
- `user_id`: FK (1:1) 关联 Django `auth_user`
- `company_id`: FK 关联 `ClientCompany` (数据访问范围)
- `role`: 权限等级 ('RW' 管理员或 'RO' 只读者)

---

## 2. 基础数据：食材与配方 (Master Data: Ingredients & Recipes)

存储用于运算逻辑的标准化数据。

### `MaterialCategory` (原料分类)
食材的分类（如鲜品、冻品、粮油）。
- `id`: PK
- `name`: 分类名称 (唯一)

### `RawMaterial` (原材料)
从供应商采购的原始食材（毛料），系统内部计量单位统一为 `kg`。
- `id`: PK
- `name`: 食材名称 (唯一)
- `category_id`: FK 关联 `MaterialCategory`

### `ProcessedMaterial` (加工规格)
定义原料的加工方式和出成率。
公式: 毛重 = 净重 / 出成率
- `id`: PK
- `raw_material_id`: FK 关联 `RawMaterial`
- `method_name`: 加工方法 (如 "去皮切块")
- `yield_rate`: 出成率 (如 0.80 = 80%)

### `DietCategory` (套餐类型)
提供的套餐分类。
- `id`: PK
- `name`: 名称 (如 "标准餐", "糖尿病餐")

### `Dish` (菜品)
代表一道具体的菜。
- `id`: PK
- `name`: 菜名
- `seasonings`: 调料描述
- `cooking_method`: 制作工艺
- `allowed_diets`: M2M 关联 `DietCategory` (该菜品适用的套餐)

### `DishIngredient` (菜品配方/配料)
菜品的BOM。每种配料直接关联原料和可选的加工方式。
- `id`: PK
- `dish_id`: FK 关联 `Dish`
- `raw_material_id`: FK 关联 `RawMaterial` (直接关联原料)
- `processing_id`: FK 关联 `ProcessedMaterial` (可选的加工方法)
- `net_quantity`: 每份净重 (kg)

---

## 3. 运营管理 (Operations)

### `ClientCompanyRegion` (公司区域/病区)
物理区域，用于配送目的地和人数统计。
- `id`: PK
- `company_id`: FK 关联 `ClientCompany`
- `name`: 区域名称 (如 "东区", "ICU")

### `WeeklyMenu` (周菜单配置)
标准化的周循环菜单。用户一次性配置，系统自动循环应用。
- `id`: PK
- `company_id`: FK
- `diet_category_id`: FK 关联 `DietCategory`
- `day_of_week`: 星期 (1-7)
- `meal_time`: 餐次 (B/L/D)
- `dishes`: M2M 关联 `Dish` 

### `DailyMenu` (日菜单)
特定日期、特定套餐、特定餐次的具体菜品。覆盖周菜单的特定场景。
- `date`: 服务日期
- `diet_id`: FK 关联 `DietCategory`
- `meal_type`: 餐次 (B/L/D)
- `dishes`: M2M 关联 `Dish`

### `DailyCensus` (每日统计/住院人数)
记录每日各区域各类套餐的人数。
- `id`: PK
- `company_id`: FK
- `date`: 目标日期
- `region_id`: FK 关联 `ClientCompanyRegion`
- `diet_category_id`: FK 关联 `DietCategory`
- `count`: 人数 (Headcount) - 与菜单配方相乘以计算采购量

### `StapleDemand` (主食需求)
主食（米饭、面条）的具体数量需求。
- `date`: 日期
- `diet_id`: FK
- `meal_type`: 餐次 (B/L/D)
- `staple_type`: 类型 (RICE/NOODLE)
- `quantity`: 需求数量 
- `unit`: 单位

---

## 4. 供应商管理 (Suppliers)

### `Supplier` (供应商)
供应商的基本信息。
- `name`: 名称
- `contact_person`: 联系人
- `phone`: 电话
- `address`: 地址

### `SupplierMaterial` (供应商供货规格)
定义哪个供应商以何种规格跟单价提供哪种原料。
- `supplier_id`: FK 关联 `Supplier`
- `raw_material_id`: FK 关联 `RawMaterial`
- `unit_name`: 销售单位 (如 "箱", "袋")
- `kg_per_unit`: 每单位kg数 (换算比率，如1箱=10kg则填10)
- `price`: 单价

---

## 5. 输出单据 (Output Orders)

根据基础数据和运营输入（人数+菜单）自动生成的各环节单据。

### `ProcurementRequest` & `ProcurementItem` (采购清单)
- **Request**: 采购申请单头 (包含 `target_date`, `status` [DRAFT/PENDING/CONFIRMED])
- **Item**: 采购明细，记录计算出的毛重 (`total_gross_quantity`)、早晚时段拆分 (`am_quantity`, `pm_quantity`)。分配后记录供应商及供应商单位数量 (`supplier_unit_qty`)。

### `ReceivingRecord` & `ReceivingItem` (收货验收单)
- **Record**: 关联到 ProcurementRequest 的收货动作。
- **Item**: 记录每种原料的应收量 (`expected_quantity`) 与实收量 (`actual_quantity`)。

### `ProcessingOrder` & `ProcessingItem` (加工需求单)
- **Order**: 加工单头 (按日期)。
- **Item**: 记录哪种原料需要何种加工（结合 `raw_material` 和 `processed_material`），供哪道菜使用 (`dish_id`)，以及所需的总重量。

### `DeliveryOrder` & `DeliveryItem` (送餐分派单)
- **Order**: 送餐单头 (按日期和餐次)。
- **Item**: 记录某区域 (`region_id`) 需要某餐饮类型 (`diet_category_id`) 多少份 (`count`)。
