# Project Long-Term Memory

Last updated: 2026-06-19 NZST

This file is the durable project memory for future agents. Update it after every task that changes product scope, architecture, database/environment behavior, authentication/authorization, deployment, validation, or next-step priorities.

Do not store secrets, API keys, passwords, cookies, tokens, private keys, or full private connection strings here.

---

## Project Identity

- Repository: `https://github.com/haohan6037/PointCloudT.git`
- Main local path: `/Users/happyfamily/MyProject/PointCloudTT`
- Current primary product: GardenOS mowing service platform.
- Secondary research/product line: point-cloud to lawn/map extraction pipeline.
- Robot/mobile product line: MyGardenOS robot app and device integration tooling under `apps/mygardenos/`.
- Main active app path: `mowing-platform/`
- Root `index.html` is the point-cloud/lawn-boundary workspace prototype.

---

## Current Product Scope

### GardenOS Mowing Service Platform

The mowing platform connects three operational parties:

- `customer`: end customer using the mobile-like customer portal.
- `admin`: platform operator/admin using the management portal.
- `server`: service provider / mowing contractor using the service-provider portal.

Business direction:

- The robot is not the contractor's main responsibility in phase 1.
- The service provider's core work is lawn edge work, under-tree/complex areas, trimming, garden work, and practical site service.
- Robot maintenance can appear in platform records, but blade replacement and deeper maintenance workflows are later-phase work.

### Point-Cloud / Lawn Recognition

The point-cloud side remains a separate product line:

- Generate top-view imagery from LAS/LAZ source data.
- Extract first-pass lawn masks and editable lawn polygons.
- Keep the output human-reviewable and editable before any mower-control use.

Keep the mowing platform docs and the point-cloud/lawn-recognition docs separate.

### MyGardenOS Robot / Mobile Project

MyGardenOS now lives inside this repository at:

```text
apps/mygardenos/
```

It was migrated from `/Users/happyfamily/MyProject/gardenos-mobile/MyGardenOS` to make related GardenOS work easier to manage in one workspace.

Scope:

- `apps/mygardenos/mobile`: React Native / Expo mobile app.
- `apps/mygardenos/backend`: FastAPI device/backend service with auth, profiles, families, devices, schedule, MQTT monitor, and robot command endpoints.
- `apps/mygardenos/tools`: browser BLE/MQTT/map-transfer tools.
- `apps/mygardenos/mqtt`: local Mosquitto config.

Boundary rule:

- Keep MyGardenOS independently runnable. Do not merge its backend into `mowing-platform/` by default.
- Future integration should happen through explicit API contracts so the robot/device service can later be split out as a microservice.

---

## Current Architecture

### Mowing Platform Runtime

- Backend: FastAPI.
- Entry point: `mowing-platform/app.py`.
- Route module: `mowing-platform/routes.py`.
- Store layer: `mowing-platform/store.py`.
- Data model payloads: `mowing-platform/models.py`.
- Address and distance logic: `mowing-platform/address_service.py`.
- PostgreSQL schema: `mowing-platform/schema.sql`.
- Local startup script: `start.sh`.

### MyGardenOS Runtime

- App root: `apps/mygardenos/`.
- Backend: `apps/mygardenos/backend/app/main.py`.
- Mobile app: `apps/mygardenos/mobile/App.tsx`.
- BLE/MQTT web tool: `apps/mygardenos/tools/ble-mqtt-config/index.html`.
- Local Docker/PostGIS/MQTT compose file: `apps/mygardenos/docker-compose.yml`.

### Frontend Entrypoints

- Admin portal: `/` -> `mowing-platform/admin-prototype.html`.
- Customer portal: `/customer` -> `mowing-platform/customer.html`.
- Service-provider portal: `/provider` -> `mowing-platform/provider.html`.

Admin frontend modules:

- `mowing-platform/js/constants.js`
- `mowing-platform/js/utils.js`
- `mowing-platform/js/autocomplete.js`
- `mowing-platform/js/render.js`
- `mowing-platform/js/api.js`
- `mowing-platform/js/app.js`
- `mowing-platform/css/admin.css`

Legacy reference:

- `mowing-platform/admin-app.js` is the older monolithic JS reference. The active admin page uses the modular `js/` files.

---

## Environment Rules

### Local Dev

Local dev must use local PostgreSQL:

- Host: `127.0.0.1`
- Port: `5433`
- Database: `MyGardenOSManagementSyetem`
- Default local URL: `http://127.0.0.1:8011/`

Use:

```bash
./start.sh
```

Important startup detail:

- `start.sh` must use `mowing-platform/.venv/bin/python` when available.
- System Python may miss `psycopg` or libpq support and cause fallback demo mode.
- Healthy local dev should show `/api/health` with `mode: postgres`, `databaseEnabled: true`, `error: null`.

Do not commit `mowing-platform/.env`.

### AWS Test

AWS test is separate from local dev:

- Region: `ap-southeast-6` New Zealand.
- App URL currently documented in `docs/AWS_TEST_DEPLOYMENT.md`.
- Runtime should use AWS RDS and Secrets Manager.
- Existing RDS and secrets are reused; do not copy local `.env` into AWS.

Secrets may be referenced by secret name or environment key only. Do not record secret values.

---

## Current Role and Permission Rules

Canonical roles:

- `customer`
- `admin`
- `server`

Legacy role compatibility:

- Old `provider` values are normalized to `server`.

Default admin emails:

- `haohan6037@gmail.com`
- `kaiyu.yang@youngproperty.co.nz`

Routing:

- `admin` default route: `/`
- `customer` route: `/customer`
- `server` route: `/provider`
- Admin can enter all three portals.
- Non-admin users should have one role only and should be redirected or blocked when accessing the wrong portal.

User management API:

- `/api/users`
- `/api/users/role`

Current minimum backend guard:

- Requires `X-GardenOS-Actor-Email`.
- Actor must be an active `admin` in `app_users`.

Known security follow-up:

- Before production, replace the email-header admin check with server-side Clerk JWT verification.

---

## Database and Store Notes

Store implementations:

- `InMemoryStore`: fallback/demo/test-compatible store.
- `PostgresStore`: local/AWS persistent store.

Core tables:

- `mowing_workers`
- `mowing_orders`
- `app_users`
- `customer_profiles`
- `mqtt_messages`

Important behavior:

- `PlatformService` attempts PostgreSQL first.
- If PostgreSQL preparation fails, it falls back to in-memory mode.
- The UI status strip should show whether data is `postgres` or fallback.

---

## Current Feature Status

Completed or mostly functional:

- Admin order management.
- Quote, assign, reassign, cancel, reject, accept, status progression.
- Service logs, exception handling, quality review, completion/settlement fields.
- Dispatch board, worker availability/profile, worker distance suggestions.
- Archive and CSV export workflows.
- Stage acceptance view.
- Customer portal with Clerk login, profile gate, default address, booking, and order tracking.
- Address autocomplete/reverse geocode API path, with provider-specific key handled by environment variable.
- User management module in admin portal.
- Role split across customer/admin/server.
- Local dev PostgreSQL startup via `start.sh`.
- AWS test deployment documentation and Terraform scaffold.
- Admin MQTT monitor view for robot/broker messages. MQTT callback records to a bounded in-memory queue; a background writer appends raw hourly NDJSON under `mowing-platform/data/mqtt-raw/` and batch-inserts analysis rows into `mqtt_messages`.

Known gaps:

- Production-grade Clerk token verification is not implemented server-side.
- Service-provider portal is still a skeleton compared with admin/customer flows.
- Payment/settlement automation is not implemented.
- Robot maintenance workflows are not phase-1 complete.
- Geoapify/live address provider status may need re-verification when keys or restrictions change.
- Point-cloud/lawn recognition remains a separate research pipeline, not yet integrated into the mowing service order flow.
- MQTT monitor is read/store focused only. Do not add robot command publishing to platform management without a separate safety design.
- MQTT raw NDJSON is the durable high-volume capture path; PostgreSQL rows are for searchable recent history and analysis metadata (`robot_id`, `message_type`).

---

## Validation Commands

Common backend/frontend validation:

```bash
python3 -m pytest mowing-platform/tests -q
node --check mowing-platform/js/clerk-auth.js
node --check mowing-platform/js/render.js
node --check mowing-platform/js/app.js
python3 -m compileall -q mowing-platform/routes.py mowing-platform/store.py mowing-platform/models.py
python3 -m compileall -q mowing-platform/mqtt_monitor.py
git diff --check
```

MyGardenOS validation:

```bash
cd apps/mygardenos/backend && python3 -m pytest tests
cd apps/mygardenos/mobile && npm run typecheck
cd apps/mygardenos/tools/ble-mqtt-config && python3 -m http.server 4173
```

Local runtime verification:

```bash
./start.sh
curl -sS http://127.0.0.1:8011/api/health
curl -sS http://127.0.0.1:8011/api/bootstrap
```

Expected local `/api/health` when PostgreSQL is connected:

```json
{"ok": true, "mode": "postgres", "databaseEnabled": true, "error": null}
```

---

## Latest Progress Log

### 2026-06-19

- Added platform admin MQTT monitoring/storage direction: admin can view MQTT messages and the platform stores them through queue -> raw NDJSON -> batched PostgreSQL rows for later analysis; command publishing remains outside the admin platform by default.
- Migrated the standalone MyGardenOS project into `apps/mygardenos/` as an independently runnable subproject.
- Preserved service boundaries for future microservice extraction: service platform, robot/device backend, mobile app, BLE/MQTT tools, and point-cloud tooling remain separate.
- Added this long-term memory file.
- Added rule to `AGENTS.md`: every task that changes meaningful project state must update this memory.
- Prepared project summary and system design documentation for current repository state.

### 2026-06-17

- Added admin/user/server role split and user management module.
- Initialized `haohan6037@gmail.com` and `kaiyu.yang@youngproperty.co.nz` as admins.
- Allowed admins to enter admin, customer, and service-provider portals.
- Added minimum backend guard for user-management APIs.
- Fixed user management menu view mounting.
- Fixed local dev startup to use project venv and local PostgreSQL.
- Pushed commit `03116db Add role management and local dev startup fixes`.

### 2026-06-16

- AWS test deployment resources and documentation were prepared.
- AWS runtime is intended for `ap-southeast-6` using AWS RDS and Secrets Manager.

### 2026-06-15

- Address integration and local PostgreSQL connection work continued.
- Live Geoapify behavior required follow-up verification.
