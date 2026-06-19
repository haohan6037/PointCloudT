# System Design — PointCloudTT / GardenOS

Date: 2026-06-19 NZST

---

## 1. System Overview

The current repository contains a web-based mowing service platform and a point-cloud lawn-recognition prototype.

The mowing platform is the active operational application. It is a monolithic FastAPI app with static HTML/CSS/JavaScript frontends. It supports local PostgreSQL persistence, fallback in-memory mode, and a documented AWS test deployment path.

The point-cloud workflow is currently a separate local tooling pipeline. It generates top-view imagery and lawn masks from LAS/LAZ input data.

---

## 2. Main Components

### 2.1 Backend Application

Path: `mowing-platform/`

| File | Responsibility |
| --- | --- |
| `app.py` | Stable app entrypoint. Explicitly loads local `routes.py` to avoid import-name ambiguity. |
| `routes.py` | FastAPI routes, HTML page serving, API endpoints, service locator. |
| `store.py` | `InMemoryStore` and `PostgresStore` implementations. |
| `models.py` | Pydantic request payloads and `StoreStatus`. |
| `address_service.py` | Address lookup, geocoding, reverse geocoding, and distance helpers. |
| `data.py` | Seed orders/workers and static defaults. |
| `schema.sql` | PostgreSQL table/index schema. |

### 2.2 Frontend Pages

| Route | File | User |
| --- | --- | --- |
| `/` | `admin-prototype.html` | Platform admin |
| `/customer` | `customer.html` | Customer |
| `/provider` | `provider.html` | Service provider |

### 2.3 Admin Frontend Modules

| Module | Responsibility |
| --- | --- |
| `js/constants.js` | Status labels and display constants. |
| `js/utils.js` | Shared state and helper functions. |
| `js/autocomplete.js` | Address autocomplete UI behavior. |
| `js/render.js` | Admin view rendering and hydration. |
| `js/api.js` | API action functions. |
| `js/app.js` | Event bindings and entry flow. |
| `css/admin.css` | Admin visual styles. |

### 2.4 Infrastructure

| Path | Responsibility |
| --- | --- |
| `start.sh` | Local dev startup. Loads `.env`, prefers project venv, starts app on 8011. |
| `mowing-platform/Dockerfile` | Container image for AWS test. |
| `infra/aws/test/` | Terraform scaffold for AWS test runtime. |
| `.github/workflows/` | CI/deployment workflows. |

---

## 3. Runtime Architecture

```text
Browser
  ├─ Admin portal (/)
  ├─ Customer portal (/customer)
  └─ Service-provider portal (/provider)
        │
        ▼
FastAPI app (mowing-platform/app.py -> routes.py)
        │
        ├─ PlatformService
        │    ├─ PostgresStore (preferred)
        │    └─ InMemoryStore (fallback)
        │
        ├─ AddressService
        └─ Static HTML/CSS/JS serving
```

Store selection:

1. Build PostgreSQL DSN from environment.
2. Try `PostgresStore(dsn).prepare()`.
3. On success, expose `mode = postgres`.
4. On failure, use `InMemoryStore` and expose fallback status.

---

## 4. Environment Design

### 4.1 Local Dev

Local dev must use local PostgreSQL:

```text
127.0.0.1:5433 / MyGardenOSManagementSyetem
```

Startup:

```bash
./start.sh
```

`start.sh` behavior:

1. Load `mowing-platform/.env` if present.
2. Set local PostgreSQL defaults.
3. Use `mowing-platform/.venv/bin/python` when available.
4. Start `uvicorn app:app --app-dir mowing-platform --host 127.0.0.1 --port 8011`.

### 4.2 AWS Test

AWS test is separate from local dev:

- Region: `ap-southeast-6`.
- Database: AWS RDS.
- Secrets: AWS Secrets Manager.
- Runtime: ECS/Fargate behind ALB.
- Deployment doc: `docs/AWS_TEST_DEPLOYMENT.md`.

AWS test should not reuse local `.env`.

---

## 5. Data Model

### 5.1 `mowing_orders`

Represents service orders.

Key fields:

- customer identity: `user_name`, `phone`
- site data: `address`, `service_type`, `requested_time`, `lawn_size`, `condition_note`
- operations: `status`, `priority_level`, `ops_tag`, `internal_note`
- pricing/dispatch: `quoted_price`, `price_note`, `assigned_worker_id`
- completion/settlement: `actual_amount`, `settlement_status`, `platform_share`, `worker_payout`, `settled_at`
- evidence and history: `photos_json`, `activity_json`

### 5.2 `mowing_workers`

Represents service providers / contractors.

Key fields:

- `id`, `name`, `area`, `phone`
- `approval_status`
- `service_note`
- `available`
- `lat`, `lng`

### 5.3 `app_users`

Represents platform login users synced from Clerk.

Key fields:

- `email`
- `clerk_user_id`
- `display_name`
- `role`
- `status`

Canonical roles:

- `customer`
- `admin`
- `server`

Legacy compatibility:

- `provider` is normalized to `server`.

### 5.4 `customer_profiles`

Represents customer profile data.

Key fields:

- `email`
- `name`
- `phone`
- `whatsapp`
- `wechat`
- `address`

---

## 6. Authentication and Authorization

### 6.1 Clerk Frontend Login

`js/clerk-auth.js` loads Clerk and synchronizes the signed-in user to the backend through:

```text
POST /api/session/sync
```

The backend creates or updates `app_users`.

### 6.2 Role Routing

`routeForRole()` maps:

```text
admin    -> /
customer -> /customer
server   -> /provider
```

Admin can access all portals. Non-admin users are redirected to their own role portal.

### 6.3 Current API Guard

User-management APIs:

```text
GET /api/users
PUT /api/users/role
```

Current minimum guard:

- Requires `X-GardenOS-Actor-Email`.
- Actor must be active `admin`.

Design limitation:

- This is not production-grade token verification.
- Production should verify Clerk JWT server-side and derive the actor from the token, not from a client-provided email header.

---

## 7. Main Workflows

### 7.1 Customer Booking

```text
Customer logs in
  -> profile gate checks name / phone / address
  -> customer enters service details
  -> POST /api/customer/orders
  -> order enters pending_review
```

### 7.2 Admin Quote and Dispatch

```text
Admin reviews pending order
  -> saves quote
  -> customer accepts quote
  -> admin selects service provider
  -> order becomes assigned
```

### 7.3 Service Progress

```text
assigned
  -> accepted_by_worker
  -> in_service
  -> pending_quality_review
  -> completed
```

Additional paths:

- service provider reject
- admin cancel
- exception open/close
- quality review rework

### 7.4 Completion and Archive

```text
completed order
  -> actual amount and completion note
  -> platform share / worker payout
  -> settlement status
  -> CSV export / archive reporting
```

### 7.5 User Management

```text
Admin opens user management
  -> GET /api/users with admin actor header
  -> change role/status
  -> PUT /api/users/role with admin actor header
```

Non-admin access returns 403.

---

## 8. Address and Dispatch Design

Address features:

- Autocomplete endpoint:
  - `POST /api/address/autocomplete`
- Geocode endpoint:
  - `POST /api/address/geocode`
- Reverse geocode endpoint:
  - `GET /api/address/reverse-geocode`
- Worker suggestion endpoint:
  - `POST /api/workers/suggest`

Dispatch distance uses worker latitude/longitude and site geocoding when available.

Provider keys must live in local `.env` or AWS Secrets Manager, not tracked files.

---

## 9. Point-Cloud / Lawn Recognition Design

The point-cloud workflow is local tooling rather than part of the live mowing platform runtime.

Primary flow:

```text
LAS / LAZ
  -> render_topview.py
  -> topview image + metadata
  -> extract_lawn_mask.py
  -> mask / overlay / editable polygon draft
```

Key documents:

- `docs/LAS_TO_TOPVIEW_DESIGN.md`
- `docs/LAWN_RECOGNITION_DRAFT_V1.md`

Design stance:

- Generated boundaries are drafts.
- Human review is required before operational or mower-control use.

---

## 10. Validation Strategy

Recommended default validation:

```bash
python3 -m pytest mowing-platform/tests -q
node --check mowing-platform/js/clerk-auth.js
node --check mowing-platform/js/render.js
node --check mowing-platform/js/app.js
python3 -m compileall -q mowing-platform/routes.py mowing-platform/store.py mowing-platform/models.py
git diff --check
```

Runtime validation:

```bash
./start.sh
curl -sS http://127.0.0.1:8011/api/health
```

Expected local PostgreSQL health:

```json
{"ok": true, "mode": "postgres", "databaseEnabled": true, "error": null}
```

---

## 11. Current Known Limitations

1. API authorization is not yet fully token-based.
2. Service-provider portal is still a skeleton.
3. Payment and automated settlement are not implemented.
4. Robot maintenance workflows are future-phase.
5. Address provider behavior depends on environment keys and provider restrictions.
6. Point-cloud outputs are not yet integrated into customer quote or service planning workflows.

---

## 12. Recommended Architecture Next Steps

1. Add server-side Clerk JWT verification middleware/dependency.
2. Apply role-aware API guards to order/admin/provider endpoints.
3. Expand service-provider portal into a real daily task workflow.
4. Add a formal migration strategy for PostgreSQL schema changes.
5. Define how point-cloud lawn boundary outputs attach to customer properties and orders.
6. Separate app runtime config into explicit `dev`, `test`, and future `prod` profiles.
