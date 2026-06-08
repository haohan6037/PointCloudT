# 割草服务平台开发说明

## 当前阶段

当前目录用于承载割草服务平台第一期开发。阶段 1 先做平台后台和订单基础，当前已有静态后台原型：

- `admin-prototype.html`

## 本地预览

从仓库根目录启动静态服务：

```bash
python3 -m http.server 8008
```

打开：

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
- 后续正式接入数据库时，优先落地订单、用户、服务地址、割草工 4 个基础对象。
- 报价和派单先人工操作，不做自动报价或自动派单。
- 本阶段不接入机器人远程控制。
