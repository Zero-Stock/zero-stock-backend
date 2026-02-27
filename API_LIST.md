# 食堂管理系统 API 清单

### 一、原材料管理

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/materials/` | GET | 获取原材料列表（支持搜索、排序、分类筛选、分组） |
| `/api/materials/{id}/` | GET | 获取单个原材料详情（含加工规格） |
| `/api/materials/{id}/` | DELETE | 删除原材料 |
| `/api/materials/batch/` | POST | 批量添加/修改原材料（有id更新，无id新建） |
| `/api/materials/{id}/specs/` | POST | 为原材料添加加工规格（加工方法+出成率） |

### 二、套餐管理

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/diets/` | GET | 获取所有套餐类型列表 |
| `/api/diets/` | POST | 新增套餐类型 |
| `/api/diets/{id}/` | PUT/PATCH | 修改套餐类型 |
| `/api/diets/{id}/dishes/` | GET | 获取该套餐下的所有菜品 |
| `/api/diets/{id}/dishes/` | POST | 批量设置该套餐的菜品（传菜品ID列表） |

### 三、菜品与配方

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/dishes/` | GET | 获取菜品列表（支持搜索） |
| `/api/dishes/` | POST | 创建菜品及其配方（嵌套创建） |
| `/api/dishes/{id}/` | GET | 获取菜品详情（含完整配方） |
| `/api/dishes/{id}/` | PUT/PATCH | 修改菜品及配方 |
| `/api/dishes/{id}/` | DELETE | 删除菜品 |

### 四、周菜单配置

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/weekly-menus/` | GET | 获取周菜单列表（支持按公司/餐类/星期/餐次筛选） |
| `/api/weekly-menus/` | POST | 创建单个菜单配置 |
| `/api/weekly-menus/{id}/` | PUT/PATCH | 修改单个菜单配置 |
| `/api/weekly-menus/batch/` | POST | 批量创建/更新一周菜单 |


### 五、用户与租户管理

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/auth/login/` | POST | 用户登录（获取 Token） |
| `/api/auth/logout/` | POST | 用户登出 |
| `/api/auth/me/` | GET | 获取当前用户信息 |
| `/api/companies/` | GET | 获取公司列表 |
| `/api/companies/{id}/regions/` | GET/POST | 管理公司下的区域/病区 |

### 六、住院情况（每日人数统计）

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/census/` | GET | 获取每日人数统计（支持按日期/区域/套餐类型筛选） |
| `/api/census/batch/` | POST | 批量录入某日各区域各套餐人数 |
| `/api/census/summary/` | GET | 按日期汇总统计（总人数、各套餐人数） |

### 七、采购清单

> 按"供应商/品类"的要货汇总单，包含毛重、规格、单位。
> **附带早晚（AM/PM）时段重量拆分以适配采购表格需求。**

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/procurement/generate/` | POST | 根据日期+人数自动计算采购量（含 AM/PM 拆分） |
| `/api/procurement/` | GET | 获取采购单列表 |
| `/api/procurement/{id}/` | GET | 查看采购单详情（含明细行） |
| `/api/procurement/{id}/items/` | GET | 获取明细（原料名、毛重、规格、单位） |
| `/api/procurement/{id}/items/?group_by=supplier` | GET | 按供应商分组的要货汇总 |
| `/api/procurement/{id}/items/?group_by=category` | GET | 按品类分组的要货汇总 |
| **`/api/procurement/{id}/sheet/`** | **GET** | **获取专用于打单渲染的层次化分好类的采购单表结构（核心渲染接口）** |
| `/api/procurement/{id}/confirm/` | POST | 确认采购单 |

### 八、收货清单

> 预计到货验收模板：用于实际收货时核对（毛重、规格、单位）

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/receiving/{procurement_id}/template/` | GET | 生成收货验收模板（可导出打印） |
| `/api/receiving/` | POST | 录入实际收货记录 |
| `/api/receiving/{id}/` | GET | 查看收货详情（实收 vs 应收对比） |

### 九、加工需求清单

> 按原料维度汇总 + 按菜品维度细分  
> 示例：土豆 → 切丝 30kg（酸辣土豆丝 20kg + 土豆丝炒肉 10kg）；切块 20kg  
> 按菜品类别分发到对应炒制车间

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/processing/generate/` | POST | 根据当日菜单+人数生成加工清单 |
| `/api/processing/{id}/` | GET | 查看加工清单详情 |
| `/api/processing/{id}/by-material/` | GET | 按原料维度（土豆：切丝30kg、切块20kg） |
| `/api/processing/{id}/by-dish/` | GET | 按菜品维度（酸辣土豆丝：土豆切丝20kg…） |
| `/api/processing/{id}/by-workshop/` | GET | 按炒制车间/菜品类别分组 |

### 十、菜品制作（配方查看）

> 周期菜单（周/天/餐次） + 套餐类型 + 每道菜的配方（原材料+净菜克重）

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/cooking/today/` | GET | 获取当日制作任务（根据周菜单自动匹配） |
| `/api/cooking/today/?meal_time=L` | GET | 筛选某餐次的制作任务 |
| `/api/cooking/recipe/{dish_id}/` | GET | 查看单道菜的完整配方（原料+净重+毛重） |
| `/api/cooking/recipe/{dish_id}/?count=100` | GET | 按人数计算用量（100人份的配方量） |

### 十一、送餐需求表

> x区需要A餐x份、餐具x份，生成可打印的实体单子。

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/delivery/generate/` | POST | 根据日期+餐次自动计算并生成送餐分派表 |
| `/api/delivery/{id}/` | GET | 查看送餐需求基础详情 |
| `/api/delivery/{id}/by-region/` | GET | 按区域分组汇总视图（前端界面展示用） |
| **`/api/delivery/{id}/export/`** | **GET** | **获取完整、层次化的 JSON 送餐打单数据结构（前端表格渲染、打印用）** |

### 十二、供应商管理

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/suppliers/` | GET/POST | 供应商列表 / 添加供应商 |
| `/api/suppliers/{id}/` | PUT/PATCH | 修改供应商信息 |
| `/api/suppliers/{id}/materials/` | GET/POST | 管理该供应商可供应的原材料 |
