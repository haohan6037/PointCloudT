# 日报 — 2026-06-17（周三 · 新西兰时间 NZST）

> 项目：PointCloudTT / GardenOS 割草服务平台  
> 环境：本地 dev（127.0.0.1:8011，本地 PostgreSQL 5433）

---

## 今日目标

1. 修复管理员登录后被当作普通用户、无法稳定进入管理端的问题。
2. 在管理端新增用户管理模块，至少区分 `customer`、`admin`、`server` 三类角色。
3. 初始化 `haohan6037@gmail.com`、`kaiyu.yang@youngproperty.co.nz` 为管理员。
4. 管理员可在管理端、客户端、服务商端之间切换；非管理员越权时阻止或跳回对应端。
5. 修复本地 dev 环境连接 PostgreSQL，避免回退到演示数据。

---

## 完成事项

### 1. 角色体系与初始化管理员

**文件**：`mowing-platform/store.py`

- 新增统一角色规范：`admin`、`customer`、`server`。
- 保留旧值 `provider` 的兼容映射，后端读取或写入时统一转换为 `server`。
- 将以下账号作为默认管理员种子：
  - `haohan6037@gmail.com`
  - `kaiyu.yang@youngproperty.co.nz`
- 如果历史数据中这两个账号已经存在且角色为 `customer`，登录同步时会自动提升为 `admin`。

### 2. Clerk 登录后的多端路由守卫

**文件**：`mowing-platform/js/clerk-auth.js`

- `routeForRole()` 更新为：
  - `admin` → `/`
  - `server` → `/provider`
  - `customer` → `/customer`
- 管理员访问客户端或服务商端时不再被重定向回管理端。
- 普通用户、服务商访问不属于自己的端时，会被跳转回对应入口。

### 3. 管理端用户管理模块

**文件**：

- `mowing-platform/admin-prototype.html`
- `mowing-platform/js/utils.js`
- `mowing-platform/js/render.js`
- `mowing-platform/js/app.js`
- `mowing-platform/css/admin.css`

完成内容：

- 左侧菜单新增“用户管理”。
- 管理端顶部新增“服务商端入口”，管理员可从管理端进入服务商端。
- 用户管理页展示用户邮箱、显示名、角色、状态。
- 支持管理员修改用户角色与状态。
- 修复用户管理菜单挂错页面的问题：
  - 补充 `.workers-grid.hidden` 隐藏规则。
  - 用户管理内容只渲染到 `#userAdminList`，不再覆盖整个 `#usersView`。
- 管理端资源版本号更新为 `20260617-users-menu-fix`，避免浏览器继续使用旧缓存。

### 4. 用户管理 API 权限保护

**文件**：`mowing-platform/routes.py`

- `/api/users` 和 `/api/users/role` 增加管理员身份校验。
- 当前最小实现通过 `X-GardenOS-Actor-Email` 请求头识别操作者，并要求该账号在用户表中为启用状态的 `admin`。
- 无操作者或普通用户调用用户管理 API 时返回 `403 Admin permission required`。

> 备注：这是第一期本地可验证的最小权限保护。后续上线前建议升级为 Clerk JWT 服务端校验。

### 5. 服务商端角色命名调整

**文件**：`mowing-platform/provider.html`

- 服务商端守卫从旧 `provider` 改为 `server`。
- 文案调整为：服务商账号可停留在服务商端，管理员可从后台进入各端查看，普通用户回到客户端。

### 6. 本地 dev 数据库连接修复

**文件**：

- `start.sh`
- `mowing-platform/uv.lock`

问题：

- 本地 PostgreSQL 5433 正常运行，`.env` 也指向本地。
- 但 `start.sh` 原先使用系统 `python3`，系统 Python 缺少可用 `psycopg`，导致应用回退到 `fallback` 演示数据。

修复：

- `start.sh` 优先使用 `mowing-platform/.venv/bin/python`。
- 同步缺失依赖 `python-multipart` 到 `uv.lock`。

验证结果：

```text
GET /api/health
mode: postgres
databaseEnabled: true
error: null
```

当前本地 dev 访问地址：

```text
http://127.0.0.1:8011/
```

---

## 验证记录

### 自动化测试

```text
python3 -m pytest mowing-platform/tests -q
71 passed
```

```text
node --check mowing-platform/js/clerk-auth.js
node --check mowing-platform/js/render.js
node --check mowing-platform/js/app.js
通过
```

```text
python3 -m compileall -q mowing-platform/routes.py mowing-platform/store.py mowing-platform/models.py
通过
```

### 本地 HTTP 验证

```text
无 X-GardenOS-Actor-Email 请求头访问 /api/users → 403
普通用户访问 /api/users → 403
管理员访问 /api/users → 200
管理员设置用户为 server → 200
```

```text
GET /api/bootstrap
store.mode = postgres
orders = 25
workers = 4
```

---

## 涉及文件

| 文件 | 说明 |
|------|------|
| `mowing-platform/store.py` | 角色规范、默认管理员、provider 到 server 兼容 |
| `mowing-platform/routes.py` | 用户管理 API 管理员权限保护 |
| `mowing-platform/js/clerk-auth.js` | Clerk 登录后的角色路由与管理员跨端放行 |
| `mowing-platform/admin-prototype.html` | 用户管理菜单、服务商端入口、资源版本号 |
| `mowing-platform/js/utils.js` | 管理员邮箱状态、用户列表状态 |
| `mowing-platform/js/render.js` | 用户管理页渲染与保存逻辑 |
| `mowing-platform/js/app.js` | 服务商端入口点击跳转 |
| `mowing-platform/css/admin.css` | 用户管理样式、隐藏规则修复 |
| `mowing-platform/provider.html` | 服务商端角色改为 server |
| `mowing-platform/tests/test_routes.py` | 角色、管理员初始化、越权保护测试 |
| `start.sh` | 本地启动使用项目 venv |
| `mowing-platform/uv.lock` | 锁定 `python-multipart` |

---

## 注意事项

- 本地 dev 环境使用本地 PostgreSQL：`127.0.0.1:5433 / MyGardenOSManagementSyetem`。
- AWS test 环境仍应使用 AWS RDS 与 Secrets Manager，不应复用本地 `.env`。
- `.env`、API Key、数据库密码未提交。
- 当前用户管理 API 的管理员判断是本地最小实现，后续上线前建议接入服务端 Clerk token 校验。
