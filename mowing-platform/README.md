# 割草服务平台开发说明

## 当前阶段

当前目录承载割草服务平台第一期后台原型。阶段 1 聚焦平台运营后台，不做用户端、独立服务商端登录，也不接机器人远程控制。

当前主要入口：

- `app.py`
- `admin-prototype.html`

## 本地运行

推荐直接启动 FastAPI 开发服务：

```bash
python3 -m uvicorn app:app --app-dir mowing-platform --host 127.0.0.1 --port 8011
```

打开：

```text
http://127.0.0.1:8011/
```

如果只想查看静态页面，也可以从仓库根目录启动：

```bash
python3 -m http.server 8008
```

然后打开：

```text
http://localhost:8008/mowing-platform/admin-prototype.html
```

## 开发数据库

开发阶段使用本地 PostgreSQL：

```text
host: 127.0.0.1
port: 5433
database: MyGardenOSManagementSyetem
```

数据库名按本地现有拼写记录为 `MyGardenOSManagementSyetem`。如果后续确认这是拼写错误，再统一迁移或改名。

当前本机 `Postgres.app` 实例的本地认证配置是 `trust`，开发阶段通常不需要密码。如果未显式配置 `PGUSER`，应用会默认尝试使用当前 macOS 登录用户名连接 PostgreSQL。

环境变量模板见：

- `.env.example`

使用时复制为本地私有配置文件：

```bash
cp mowing-platform/.env.example mowing-platform/.env
```

不要把真实数据库用户名和密码提交到代码仓库。

## 阶段 1 数据接入原则

- 先保持静态原型可运行。
- 后续正式接入数据库时，优先落地订单、用户、服务地址、草坪服务商 4 个基础对象。
- 报价和派单先人工操作，不做自动报价或自动派单。
- 本阶段不接入机器人远程控制。

## 当前功能范围

- 订单管理：
  录入订单、时间控件录单、查看详情、保存报价、维护优先级和运营标签。
- 平台运营日报：
  首页查看紧急订单、逾期待处理、待派单、待结算，以及重点跟进订单。
- 派单看板：
  按状态、区域、日期、优先级、运营标签筛单，查看服务商日程和时间冲突提醒。
- 服务执行：
  订单可从已派单推进到已接单、服务中、已完成，并记录服务节点日志。
- 服务商管理：
  维护服务商资料、服务区域、联系电话、审核状态、可接单状态和备注。
- 服务商工作台：
  查看当天任务顺序，按待出发、服务中、待回传分组，并支持一键推进节点。
- 完成归档：
  补录实收金额、完成备注、平台分成、服务商应结、结算状态，支持 CSV 导出。
- 归档建议：
  自动生成分账建议，完工后可自动跳转到归档位并预填草稿。
- 阶段验收：
  汇总演示样本、主流程覆盖、服务记录和归档准备度，并提供一键跳转演示入口。

## 演示路径

推荐按下面顺序演示第一期能力：

1. 首页 `订单管理`
   看运营日报、重点跟进、紧急单和逾期待处理。
2. 选一张待处理订单
   展示报价、推荐服务商、运营标签、服务前 checklist。
3. 进入 `派单看板`
   展示区域筛选、时间冲突提醒和快速派单。
4. 进入 `服务商`
   展示当天任务顺序和一键推进 `已接单 / 服务中 / 已完成`。
5. 完工后自动跳到 `完成归档`
   展示实收金额、分账建议、完成备注模板和结算动作。
6. 在归档页演示
   已完成订单汇总、服务商排行、CSV 导出和批量标记已结算。
7. 最后进入 `阶段验收`
   展示阶段 1 是否具备汇报与内部试运营条件，以及推荐演示跳转入口。

## 当前开发进度记录

- 已完成 PostgreSQL 开发接入，后台当前直接读取和写入本地 `MyGardenOSManagementSyetem`。
- 已完成订单录入、报价、派单、服务商接单、服务中、已完成这条基础流转。
- 已完成首页运营日报，可汇总紧急订单、逾期待处理、待派单和待结算提醒。
- 已完成服务商资料管理，可维护接单状态、服务区域、联系电话和派单备注。
- 已完成派单看板，可按日期、区域、状态筛单，并查看服务商日程。
- 已完成同时间段冲突提醒，派单时会提示服务商是否已有重叠任务。
- 已完成服务记录节点，可记录上门前确认、到场签到、服务中记录和完工回传。
- 已完成服务商工作台，可按当天任务顺序查看订单，并支持一键推进状态。
- 已完成归档视图，可查看已完成订单、完成金额和服务商完成排行。
- 已完成归档补录，可录入实收金额、结算状态、完成备注，并按实收金额统计归档金额。
- 已完成订单优先级和运营标签管理，订单列表和详情页都能直接查看与维护。
- 已完成归档分账字段，可记录平台分成、服务商应结，并进入归档汇总与 CSV 导出。
- 已完成结算建议和完工自动跳转归档，归档页可自动预填金额拆分和备注模板。
- 已完成录单时间控件改造，新建订单时改用日期与时间控件，不再手动输入时间字符串。
- 已完成阶段 1 验收视图，可直接查看样本覆盖、主流程通过情况和推荐演示路径。
- 已修复用户端 `/customer` 路由加载问题，入口改为显式加载本地 `routes.py`，并补装 `python-multipart` 以支持用户端表单上传。
- 路由修复教训：以后不要再用 `from routes import app` 这种依赖同名模块解析的入口写法；用户端相关路由必须通过本地 `mowing-platform/routes.py` 显式加载，并确认 `python-multipart` 已安装，否则 `/customer` 会在启动时直接丢失。
- 已完成运营改派，订单详情中可选择新服务商改派，时间线记录改派前后服务商姓名。
- 已完成运营取消订单，非已完成和非已取消状态的订单都可取消，支持填写取消原因。
- 已完成服务商拒单，已派单或已接单状态可标记拒单，订单自动回到已报价待派单状态。
- 已完成地址自动补全，对接奥克兰市议会 ArcGIS 地址服务，输入 3 个字符即可搜索真实地址。
- 已完成智能派单推荐，后端通过地址→NZTM坐标转换计算各服务商距离，派单页和订单详情按距离排序显示推荐服务商。
- 已完成服务商经纬度管理，编辑服务商资料时可填写 lat/lng，用于距离计算。
- 已完成订单编辑，运营人员可在订单详情中修改客户姓名、电话、地址、服务类型、时间、草坪信息和备注。
- 已完成内部备注，运营人员可在每个订单上记录内部沟通内容，独立于客户备注，客户不可见。
- 已完成用户端页面（customer.html），支持在线下单、照片上传、报价确认/拒绝。
- 已完成客户 API（提交订单、查订单、确认/拒绝报价），新增 accepted_by_customer 状态。
- 已完成代码重构：Python 6 文件 + JS 6 文件 + 独立 CSS，注释统一双语风格。
- 已完成自动化测试（37 个用例）和 GitHub Actions CI/CD 流水线。
- 当前阶段 1 管理端已完整，阶段 2 用户端已起步，尚未覆盖服务商端独立登录、支付结算、机器人维护任务。

## 工作总结（2026-06-09 ~ 2026-06-10）

### 代码重构
- **Python 拆分**：`app.py`（1921 行）→ `data.py` + `models.py` + `address_service.py` + `store.py` + `routes.py` + `app.py`（7 行入口）。
- **JS 拆分**：`admin-app.js`（3009 行）→ `js/constants.js` + `utils.js` + `autocomplete.js` + `render.js` + `api.js` + `app.js`，通过 `<script>` 标签按顺序加载。
- **CSS 提取**：`admin-prototype.html` 内嵌 1380 行样式 → `css/admin.css`，HTML 从 1808 行缩减到 390 行。
- **注释规范**：全部统一为双语 `# EN / 中文` 或 `// EN / 中文`。

### 自动化测试与 CI/CD
- `tests/test_store.py`：24 个单元测试，覆盖 InMemoryStore 全部核心方法。
- `tests/test_routes.py`：13 个集成测试，覆盖全部 API 端点与生命周期。
- `tests/conftest.py`：共享夹具（`store` / `client` / `sample_order_data`）。
- `.github/workflows/ci.yml`：push/PR 自动运行 pytest + ruff lint，覆盖率要求 ≥70%。
- `pyproject.toml`：pytest + ruff 配置。
- Python 3.9 兼容性修复（`str | None` → `Optional[str]`）。

### 用户端（阶段 2 起步）
- 新增 `customer.html`（416 行）：服务类型选择、地址自动补全、照片拖拽上传、订单提交。
- 订单跟踪：输入手机号查看历史订单，`quoted` 状态下可「接受报价」或「拒绝」。
- 新增 `accepted_by_customer` 订单状态，完整流程：`pending_review → quoted → accepted_by_customer → assigned → …`。
- 新增 5 个客户 API：
  - `POST /api/customer/orders` — 提交订单（Form + 文件上传）
  - `GET /api/customer/orders?phone=` — 按手机号查订单
  - `POST /api/customer/orders/{id}/confirm` — 确认报价
  - `POST /api/customer/orders/{id}/reject` — 拒绝报价
  - `GET /customer` — 用户端页面
- 管理端同步适配：筛选器加入「客户已确认」状态，新增 CSS 样式。

### 订单列表 CSV 导出
- 订单管理页顶部新增「导出 CSV」按钮，按当前筛选条件导出 21 列完整数据。
- 提取公用 `downloadCsv()` 函数，归档导出同步简化。

## 当前项目结构

```
mowing-platform/
├── app.py                    # 7 行入口
├── data.py                   # 种子数据（WORKERS, SEED_ORDERS）
├── models.py                 # Pydantic 模型（16 个类）
├── address_service.py        # 奥克兰地址服务 + haversine
├── store.py                  # InMemoryStore + PostgresStore
├── routes.py                 # FastAPI 路由 + PlatformService
├── schema.sql                # PostgreSQL 建表
├── customer.html             # 用户端页面
├── admin-prototype.html      # 管理端页面（390 行纯标记）
├── admin-app.js              # 原始 JS（保留参考，已拆分为 js/）
├── css/admin.css             # 管理端样式
├── js/
│   ├── constants.js          # 状态标签常量
│   ├── utils.js              # 工具函数 + 共享状态
│   ├── autocomplete.js       # 地址自动补全组件
│   ├── render.js             # 所有渲染函数
│   ├── api.js                # API 请求函数
│   └── app.js                # 事件绑定 + bootstrap
├── tests/
│   ├── conftest.py           # 测试夹具
│   ├── test_store.py         # 24 个 Store 单元测试
│   └── test_routes.py        # 13 个路由集成测试
├── uploads/                  # 用户上传照片
└── pyproject.toml            # pytest + ruff 配置
```

## 下一步安排

1. 用户端完善：用户注册/登录（短信验证）、服务进度实时查看、评价系统。
2. 服务商端：独立登录、今日任务、到场打卡、服务前后照片上传、收入查看。
3. 支付与结算：对接 Stripe/PoliPay，自动分账。
4. 产品线 A（点云→2D 地图）：管理端稳定后恢复官方边界裁切开发。
