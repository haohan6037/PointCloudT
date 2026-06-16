# 日报 — 2026-06-15（周一 · 新西兰时间 NZST）

> 项目：PointCloudTT / GardenOS 割草服务平台  
> 作者：CodeWhale (deepseek-v4-pro)

---

## 任务目标

1. 页面数据保存到本地 PostgreSQL（不再仅依赖内存存储）
2. 用户 Clerk 登录成功后自动从后端拉取数据
3. 提供一键启动脚本，替代手动 uvicorn 命令

---

## 完成事项

### 1. 项目依赖规范化

**文件**: `mowing-platform/pyproject.toml`

新增 `[project]` 段，声明四项核心依赖：

| 包名 | 版本 | 用途 |
|------|------|------|
| `fastapi` | >=0.115.0 | Web 框架 |
| `uvicorn[standard]` | >=0.30.0 | ASGI 服务器 |
| `psycopg[binary]` | >=3.2.0 | PostgreSQL 驱动 |
| `python-dotenv` | >=1.0.0 | .env 环境变量加载 |

通过 `uv add` 安装并锁定在 `uv.lock`（577 行）。

### 2. PostgreSQL 连接配置对齐

**文件**: `mowing-platform/store.py`（第 1709–1711 行）

默认连接参数与 `.env` 保持一致：

```python
port = os.getenv("PGPORT", "5433")
database = os.getenv("PGDATABASE", "MyGardenOSManagementSyetem")
```

启动时 `data.py` 自动加载 `mowing-platform/.env`，`PlatformService` 优先尝试 `PostgresStore`，连接失败则回退 `InMemoryStore`。

**文件**: `mowing-platform/.env.example`

创建环境配置模板，数据库段与用户实际 `.env` 对齐（PGPORT=5433, PGDATABASE=MyGardenOSManagementSyetem, PGUSER=happyfamily, DATABASE_URL）。

### 3. 一键启动脚本

**文件**: `start.sh`（项目根目录，已 `chmod +x`）

流程：
1. 加载 `mowing-platform/.env`（存在时）或项目根 `.env`
2. 设置 PostgreSQL 默认环境变量（PGHOST/PGPORT/PGDATABASE/PGUSER）
3. 检查 PostgreSQL 连接可达性（通过 `psql`）
4. 若无 `.venv` 且 `uv` 可用，执行 `uv sync` 安装依赖
5. 启动 uvicorn，监听 `127.0.0.1:8011`

用法：`./start.sh`

### 4. 登录后自动拉取数据

**问题**：原先 `bootstrap()` 在 `js/app.js` 末尾无条件执行，与 Clerk 登录流程脱节。用户未登录时也会发起 `/api/bootstrap` 请求（虽然 UI 隐藏），登录成功后不会重新拉取最新数据。

**修改**：

| 文件 | 改动 |
|------|------|
| `mowing-platform/admin-prototype.html` | `onAuthorized` 回调中新增 `bootstrap()` 调用，失败时更新状态栏 |
| `mowing-platform/js/app.js` | 移除底部无条件 `bootstrap()` 调用（第 110–114 行），改为注释说明 |
| `mowing-platform/provider.html` | `onAuthorized` 回调中新增 `typeof bootstrap === "function"` 守卫调用 |

**效果**：
- 管理员登录 → `onAuthorized` → `bootstrap()` → `/api/bootstrap` → `hydrate()` → 页面渲染
- 服务商登录 → 同上（`provider.html` 当前未加载 `render.js`，守卫安全跳过）
- 用户端 `customer.html` 原本已在 `onAuthorized` 中调用 `fetchCustomerProfile()`，无需改动

---

## 数据流总览

```
./start.sh
  └─ 加载 .env → DATABASE_URL
       └─ uvicorn 启动
            └─ PlatformService.__init__()
                 ├─ PostgresStore(dsn).prepare()  ← 建表 + seed
                 │    └─ 成功 → store = PostgresStore, mode = "postgres"
                 └─ 失败 → store = InMemoryStore, mode = "fallback"

浏览器 → Clerk 登录
  └─ onAuthorized 回调
       └─ bootstrap()
            └─ GET /api/bootstrap
                 └─ store.bootstrap()
                      ├─ Postgres: SELECT from mowing_orders + mowing_workers
                      └─ InMemory: 返回 SEED_ORDERS + WORKERS 深拷贝
            └─ hydrate(payload) → render()
```

---

## 涉及文件

| 文件 | 操作 | 说明 |
|------|:---:|------|
| `mowing-platform/pyproject.toml` | 修改 | 新增 [project] 依赖声明 |
| `mowing-platform/uv.lock` | 自动更新 | uv 锁定全部依赖 |
| `mowing-platform/store.py` | 修改 | 默认 DSN 参数对齐 .env |
| `mowing-platform/.env.example` | 新建 | 环境配置模板 |
| `start.sh` | 新建 | 一键启动脚本 |
| `mowing-platform/admin-prototype.html` | 修改 | onAuthorized → bootstrap() |
| `mowing-platform/js/app.js` | 修改 | 移除无条件 bootstrap() |
| `mowing-platform/provider.html` | 修改 | onAuthorized → bootstrap() 守卫 |

---

## 备注

- 后端 `PostgresStore` 此前已实现完整的订单/服务商/用户/客户资料 CRUD（约 1200 行），本次主要是打通连接链路和启动流程
- `.env` 由用户自行维护（含 Clerk Publishable Key 和 Geoapify API Key），未纳入版本控制
- `mowing-platform/admin-app.js`（3009 行）为独立完整版本，当前 admin-prototype.html 加载的是 `js/` 下的模块化版本，两者未统一——后续可考虑合并
