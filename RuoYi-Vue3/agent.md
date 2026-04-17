# Agent.md — 青鸟集团管理系统 项目上下文说明

> 本文档供 AI 助手在对话开始时快速理解项目全貌。请优先阅读，再开始编码。

---

## 一、项目概述

| 项目 | 说明 |
|------|------|
| **名称** | 青鸟集团管理系统（Qingbird Management System） |
| **业务** | 电商客服外包公司的内部 ERP：管理分公司、员工、店铺、薪资、质检、结算、财务 |
| **前端仓库** | `d:\Tools\work_project\RuoYi-Vue3` |
| **后端仓库** | `d:\Tools\work_project\RuoYi-Vue`（Spring Boot，含 SQL） |
| **框架基础** | 若依（RuoYi）Vue3 全分离版，在其基础上叠加了完整的自定义业务层 |
| **前端语言** | Vue 3 (Composition API `<script setup>`) + Element Plus + SCSS |
| **后端语言** | Java / Spring Boot / MyBatis，API 前缀 `/qingbird/**` |
| **dev 地址** | `http://localhost:90`（`yarn dev` 启动，端口 90） |
| **后端代理** | Vite 将 `/dev-api/**` → `http://localhost:8080`，去掉前缀后透传 |

---

## 二、目录结构

```
RuoYi-Vue3/
├── src/
│   ├── api/
│   │   └── qingbird/            # 青鸟业务 API（全部走 /dev-api/qingbird/**）
│   │       ├── dashboard.js     # 控制台大屏
│   │       ├── branch.js        # 分公司管理
│   │       └── salary.js        # 薪资预览
│   ├── layout/
│   │   ├── index.vue            # 若依默认 Layout（系统管理等标准页用）
│   │   └── qingbird/
│   │       └── index.vue        # ★ 青鸟自定义 Layout（侧边栏+顶栏+内容区）
│   ├── router/index.js          # 路由配置（所有 /qingbird/* 使用 QingbirdLayout）
│   └── views/
│       └── qingbird/            # 青鸟所有业务页面
│           ├── components/
│           │   └── PlaceholderPage.vue   # 占位页（尚未开发的模块）
│           ├── center/          # 集团中心（已完成）
│           ├── dashboard/       # 控制台大屏（已完成）
│           ├── branch/          # ★ 分公司管理（已完成）
│           ├── docs/            # ★ 云文档/数字化资产库（已完成）
│           ├── salary/          # ★ 薪资预览/进度表（已完成）
│           ├── employee/        # 员工花名册（已完成）
│           ├── qcDetail/        # 质检明细（已完成）
│           ├── shop/            # 店铺管理（占位页）
│           ├── output/          # 产值管理（占位页）
│           ├── seat/            # 客服坐席（占位页）
│           ├── qc/              # 店铺质检（占位页）
│           ├── settlement/      # 结算管理（占位页）
│           ├── bonus/           # 绩费明细（占位页）
│           └── finance/         # 财务总览（占位页）
└── RuoYi-Vue/sql/
    ├── ry_20260321.sql          # 若依基础表（sys_user/sys_dept/sys_menu 等）
    ├── qingbird_schema.sql      # 青鸟业务表（biz_shop/biz_spider_data/biz_settlement_log）
    ├── biz_employee.sql         # 员工花名册表（biz_employee）
    └── quartz.sql               # 定时任务表
```

---

## 三、路由配置

所有青鸟页面统一挂在 `/qingbird` 路径下，使用 `QingbirdLayout`：

| 路由路径 | 组件 | 菜单名 | 状态 |
|----------|------|--------|------|
| `/qingbird/center` | center/index.vue | 集团中心 | ✅ 完成 |
| `/qingbird/dashboard` | dashboard/index.vue | 控制台 | ✅ 完成 |
| `/qingbird/branch` | branch/index.vue | 分公司管理 | ✅ 完成 |
| `/qingbird/docs` | docs/index.vue | 云文档 | ✅ 完成 |
| `/qingbird/employee` | employee/index.vue | 员工花名册 | ✅ 完成 |
| `/qingbird/salary` | salary/index.vue | 薪资预览 | ✅ 完成 |
| `/qingbird/qc-detail` | qcDetail/index.vue | 质检明细 | ✅ 完成 |
| `/qingbird/shop` | shop/index.vue | 店铺管理 | ✅ 完成 |
| `/qingbird/output` | output/index.vue | 产值管理 | ✅ 完成 |
| `/qingbird/seat` | seat/index.vue | 客服坐席 | ✅ 完成 |
| `/qingbird/qc` | qc/index.vue | 店铺质检 | 🚧 占位页 |
| `/qingbird/settlement` | settlement/index.vue | 结算管理 | 🚧 占位页 |
| `/qingbird/bonus` | bonus/index.vue | 绩费明细 | 🚧 占位页 |
| `/qingbird/finance` | finance/index.vue | 财务总览 | 🚧 占位页 |

> 根路径 `/` 和 `/index` 均重定向到 `/qingbird/dashboard`。

---

## 四、设计系统（CSS 变量）

所有青鸟页面共用统一 CSS 变量，定义在全局样式中（main.js 引入）：

```scss
--qb-primary:          #6C4EF2     // 主题紫色
--qb-primary-bg:       #F0EEFF     // 主题色浅背景
--qb-success:          #10B981     // 绿色
--qb-danger:           #EF4444     // 红色
--qb-info:             #3B82F6     // 蓝色
--qb-warning:          #F59E0B     // 橙色
--qb-text-primary:     #1A1A2E     // 主文字
--qb-text-secondary:   #4A4A6A     // 次要文字
--qb-text-muted:       #9CA3AF     // 灰色提示
--qb-border:           #E5E7EB     // 边框色
--qb-bg:               #F4F5F9     // 页面背景
--qb-card-bg:          #FFFFFF     // 卡片背景
--qb-dark-card-bg:     #1A1A2E     // 深色卡片背景（用于 KPI 大字卡）
--qb-sidebar-bg:       #FFFFFF     // 侧边栏背景
--qb-sidebar-width:    176px
--qb-topbar-height:    48px
--qb-radius:           12px
--qb-radius-sm:        8px
--qb-shadow-sm:        0 1px 3px rgba(0,0,0,.06)
--qb-shadow-md:        0 4px 12px rgba(0,0,0,.10)
```

**通用 CSS 类（所有页面可直接用）：**
```scss
.qb-page           // 页面外层容器（padding已含）
.qb-page-header    // 页面标题行（包含 h1.qb-page-title + p.qb-page-subtitle）
.qb-page-title     // 大标题
.qb-page-subtitle  // 副标题
.qb-card           // 卡片（白底+border+radius+shadow）
.qb-btn-primary    // 主色按钮（样式与 el-button 结合使用）
```

---

## 五、数据库表

### 已创建的业务表

| 表名 | 说明 | 所在 SQL 文件 |
|------|------|--------------|
| `biz_shop` | 店铺资产表（平台/分公司/登录账号/shop_key） | qingbird_schema.sql |
| `biz_spider_data` | 采集数据明细（咨询/接待/转化率/销售额 等） | qingbird_schema.sql |
| `biz_settlement_log` | 产值核算台账（月度结算总额） | qingbird_schema.sql |
| `biz_employee` | 员工花名册（岗位/薪资/合同/入职等） | biz_employee.sql |

### 关键关联关系
- `biz_shop.branch_id` → `sys_dept.dept_id`（分公司映射若依部门）
- `biz_shop.employee_id` → `sys_user.user_id`
- `biz_spider_data.shop_id` → `biz_shop.shop_id`
- `biz_employee.branch_code` = `'B-1773208272961'`（当前分公司硬编码）

---

## 六、API 规范

### 请求配置
- **baseURL**：`/dev-api`（开发环境），Vite proxy 去掉 `/dev-api` 后代理到 `localhost:8080`
- **Token**：Bearer Token 自动注入（via `Authorization` header）
- **Content-Type**：`application/json;charset=utf-8`

### hideErrorMsg —— 静默处理未实现接口

在 API 还未有后端实现时，请求配置加 `hideErrorMsg: true`，阻止拦截器弹出错误提示：

```js
// src/api/qingbird/xxx.js
export function getSomeData(params) {
  return request({
    url: '/qingbird/xxx/data',
    method: 'get',
    params,
    hideErrorMsg: true   // ← 后端未实现时静默，不弹错误弹窗
  })
}
```

> 已在 `dashboard.js`、`branch.js`、`salary.js` 全部加上，后续新增 API 文件时也要加。

### 统一响应格式
```json
{ "code": 200, "msg": "操作成功", "data": { ... } }
{ "code": 200, "msg": "操作成功", "rows": [...], "total": 100 }
```

---

## 七、已完成页面说明

### 1. 控制台大屏 (`/qingbird/dashboard`)
- **功能**：集团整体 KPI 看板，含深色 banner + 业务规模 + 合规预警 + 近7天趋势
- **API**：`GET /qingbird/dashboard/overview`
- **状态**：前端完成，后端 API 待实现

### 2. 分公司管理 (`/qingbird/branch`)
- **功能**：当前分公司运营指挥仪表板，含 8 格 KPI 卡、资金储备进度条、近期店铺数据表
- **API**：`GET /qingbird/branch/overview?branchCode=B-1773208272961`
- **Mock 数据**：API 404 时自动使用默认数据（branchName='Q43-锦鲤电商' 等）

### 3. 云文档 (`/qingbird/docs`)
- **功能**：数字化资产库，左侧目录树 + 右侧文件网格/列表，支持上传模拟
- **数据**：纯前端 Mock，无后端 API（文件数据硬编码在组件内）
- **文件类型**：image/excel/doc/pdf，支持网格/列表切换

### 4. 员工花名册 (`/qingbird/employee`)
- **功能**：分公司员工 CRUD，含搜索/分页/导出
- **API**：`GET /qingbird/employee/list`、`POST /qingbird/employee`、`PUT`、`DELETE`
- **数据库**：`biz_employee`（`branch_code='B-1773208272961'` 隔离）

### 5. 薪资预览 (`/qingbird/salary`)
- **功能**：我的薪资进度表，含 4 KPI 卡（月度总量/档位/奖金/扣款）+ 核算大表 + 政策说明弹窗
- **API**：`GET /qingbird/salary/preview?month=YYYY-MM`
- **Mock 数据**：API 不通时展示演示数据

### 6. 店铺管理 (`/qingbird/shop`)
- **功能**：店铺列表管理，含 4 个 KPI 卡、搜索/筛选、表格（平台/负责客服/子账号/近 30 天客询/到期状态）、录入帖编辑 Dialog
- **API**：`GET /qingbird/shop/list`、`POST /qingbird/shop`、`PUT /qingbird/shop`
- **Mock 数据**：4 家示例店铺（Q43-锦鲤电商），店铺表 `biz_shop` 已建

### 7. 产值管理 (`/qingbird/output`)
- **功能**：产值效能管理中心，支持两种视图切换：《个人产値明细》和《2 人小组看板》
- **个人视图**：按分公司分组展示员工卡片，含店铺数、累计接待产値
- **小组视图**：显示 2 人小组，含 6 格指标、KPI 座和共同管理资产清单，支持输入目标金额
- **API**：`GET /qingbird/output/overview`
- **Mock 数据**：多名员工和小组演示数据

---

## 八、开发惯例与注意事项

### 命名惯例
- 组件 `name` 属性统一用 `QingbirdXxx` 格式（如 `QingbirdBranch`）
- API 文件统一放 `src/api/qingbird/`，接口路径以 `/qingbird/` 开头

### 分公司编号
当前系统硬编码分公司编号为：
```
B-1773208272961
```
多处使用（layout/branch/employee），后期应从用户信息中动态读取（`userStore.deptCode`）。

### 尚未实现的模块（占位页）
以下路由已存在但页面仍为 `PlaceholderPage`：
- `/qingbird/qc` — 店铺质检
- `/qingbird/settlement` — 结算管理
- `/qingbird/bonus` — 绩费明细
- `/qingbird/finance` — 财务总览

### 环境启动
```bash
# 前端（端口90）
cd d:\Tools\work_project\RuoYi-Vue3
yarn dev

# 后端 Spring Boot（端口8080）
# 需单独启动 RuoYi-Vue 后端项目
```

---

## 九、下次开发建议

优先级高的待开发模块：

1. **客服坐席** (`/qingbird/seat`)：`biz_spider_data` 采集数据的主要展示入口
2. **店铺质检** (`/qingbird/qc`)：结合采集数据异常检测
3. **结算管理** (`/qingbird/settlement`)：`biz_settlement_log` 月度台账录入与展示
4. **薪资计算后端**：`/qingbird/salary/preview` API 待实现
5. **分公司概览后端**：`/qingbird/branch/overview` API 待实现
6. **店铺/产値后端**：`/qingbird/shop/list` 和 `/qingbird/output/overview` API 待实现
