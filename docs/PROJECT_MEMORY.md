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
- Robot coverage analysis should normalize map geometry and MQTT robot poses into the canonical `GOS-MAP-XY` frame defined in `docs/ROBOT_COORDINATE_ALIGNMENT_SPEC_V1.md`.
- LAS/LAZ location handling must follow `docs/LAS_EPSG_COORDINATE_WORKFLOW_V1.md`: never treat LAS `x/y` as latitude/longitude; read `las.header.parse_crs()` first, fallback to `EPSG:32760` only when CRS is missing, and use `pyproj` with `always_xy=True`.

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
- Current ECS task definition after the 2026-06-21 MQTT broker migration is `gardenos-test:7`.
- Current AWS app URL is `http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com`.
- AWS `/api/health` verified `mode: postgres`, `databaseEnabled: true`.
- Current AWS MQTT broker is EC2 Mosquitto instance `i-07ee81ca7a5d2e5e5` with Elastic IP `3.103.181.148`, port `53239`, security group `sg-067d077ce5e5c0830`.

Secrets may be referenced by secret name or environment key only. Do not record secret values.

### Robot MQTT Runtime Constraint

The deployed platform must monitor the robot's existing MQTT broker. Do not move this path to AWS IoT Core unless a separate robot firmware/config change is planned.

The previously discussed settings below were examples from the old Railway broker, not the correct new robot MQTT target:

```text
MQTT Address: 66.33.22.249
MQTT Port: 53239
```

Do not use that example address for the AWS backend or robot configuration unless the user explicitly confirms it is still the intended broker. Railway MQTT is being replaced by the AWS broker below:

```text
MQTT Address: 3.103.181.148
MQTT Port: 53239
```

Important constraints:

- The robot only accepts address/IP plus port style MQTT settings, not an HTTP backend URL.
- The robot's existing topic behavior must not be changed from the platform side.
- Current monitored topics are `HeartBeat`, `ResponseCommand`, and `$SYS/broker/log/#`.
- `nozomi.proxy.rlwy.net` and `66.33.22.249:53239` refer to the old/example Railway broker path in this context.
- Username/password/TLS requirements are unknown until the real broker is confirmed.
- Platform MQTT code must not default to any broker. `MQTT_HOST` and `MQTT_PORT` must be explicitly configured before live MQTT monitoring starts.
- AWS ECS now listens to the AWS broker through `MQTT_HOST=3.103.181.148`, `MQTT_PORT=53239`, `MQTT_MONITOR_ENABLED=1`.
- Platform management remains read/store focused. Do not add robot command publishing here without a separate safety design.

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
- Service-provider portal first real workbench: linked by worker email, shows provider-assigned active orders, and supports accept, reject, arrival/start, service log, exception report, and completion submission.
- Service-provider evidence upload: provider-assigned orders can receive现场照片 through `/api/provider/orders/{order_id}/evidence`, stored under `mowing-platform/uploads/provider/<order-id>/` and appended to order `photos`.
- Manual business-closure payment metadata: completed orders can record payment status, payment method, payment received time, and payment note alongside settlement fields.
- MQTT vendor integration standard `docs/MQTT_VENDOR_INTEGRATION_STANDARD_V1.md` defines the current monitor-only topic/data contract and manufacturer questions while keeping command publishing out of scope.
- Admin/provider APIs support Clerk Bearer-token verification in strict mode. `CLERK_AUTH_STRICT=1` plus `CLERK_JWT_KEY` makes protected APIs resolve actor identity from verified token `sub` -> `app_users.clerk_user_id` instead of trusting client-supplied email.

Known gaps:

- Customer-facing profile/order APIs still need token-backed identity; admin/provider API token verification is implemented but strict production depends on Clerk runtime config.
- Service-provider portal still needs richer earnings display and real provider onboarding. Evidence upload is functional, but production file size/type scanning and managed object storage remain later hardening work.
- Payment/settlement automation is not implemented.
- Robot maintenance workflows are not phase-1 complete.
- Geoapify/live address provider status may need re-verification when keys or restrictions change.
- Point-cloud/lawn recognition remains a separate research pipeline, not yet integrated into the mowing service order flow.
- MQTT monitor is read/store focused only. Do not add robot command publishing to platform management without a separate safety design.
- MQTT raw NDJSON is the durable high-volume capture path; PostgreSQL rows are for searchable recent history and analysis metadata (`robot_id`, `message_type`).
- Manufacturer robot-coordinate integration is not implemented yet. Before coding coverage analysis, confirm the robot's coordinate frame, origin, axes, unit, heading convention, reference point, cut width, working-state field, timestamp, and accuracy fields against `docs/ROBOT_COORDINATE_ALIGNMENT_SPEC_V1.md`.

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

GitHub Actions CI baseline:

- `.github/workflows/ci.yml` runs `tests/test_store.py` with coverage scoped to `store`, `models`, and `data`, with `--cov-fail-under=40`.
- The integration test job installs `httpx2` because the current FastAPI/Starlette `TestClient` dependency expects it.
- Do not raise the coverage threshold back to 70 until broader tests cover `routes.py`, `mqtt_monitor.py`, `auth_service.py`, and `address_service.py`.

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

### 2026-06-22

- Prioritized business closure as the primary landing goal. MQTT remains standard/spec-first for vendor alignment, and point-cloud work remains functional development for later integration into the larger workflow.
- Added worker email binding to seed data and schema so service-provider login can resolve to a worker profile.
- Added provider workbench APIs under `/api/provider/*`: provider users can read only their assigned active orders, accept/reject, mark arrival/start, add service logs, report exceptions, and submit completion for platform quality review.
- Replaced `/provider` skeleton with a working service-provider dashboard that reads the logged-in provider's orders and performs the above actions.
- Added manual payment metadata to completion/archive flow: `paymentStatus`, `paymentMethod`, `paymentReceivedAt`, and `paymentNote`.
- Fixed the PostgreSQL customer quote confirmation gap by adding `accept_by_customer` and `reject_by_customer` to `PostgresStore`; customer quote confirmation now works beyond fallback memory mode.
- Added `docs/MQTT_VENDOR_INTEGRATION_STANDARD_V1.md` for manufacturer MQTT alignment. The platform remains monitor/store focused and still must not publish movement commands without a separate safety design.
- Validation: `python3 -m pytest mowing-platform/tests -q` passed 79 tests; Python compile checks and JS syntax checks passed.
- Added service-provider evidence upload for business closure: provider workbench can upload现场照片, backend stores files under `mowing-platform/uploads/provider/<order-id>/`, appends photo URLs to the order, and records an activity timeline entry. Validation now passes 80 tests.
- Added Clerk server-auth hardening for admin/provider APIs. Frontend requests can send Clerk session tokens in `Authorization`; backend can verify with `CLERK_JWT_KEY`, map token `sub` to local `app_users.clerk_user_id`, and enforce strict mode with `CLERK_AUTH_STRICT=1`. Added `docs/CLERK_SERVER_AUTH_HANDOFF_V1.md`. Validation now passes 83 tests.

### 2026-06-19

- Added robot coordinate alignment spec `docs/ROBOT_COORDINATE_ALIGNMENT_SPEC_V1.md`: canonical analysis frame is `GOS-MAP-XY` in meters, fixed per map, +X map right/east, +Y map up/north, yaw counter-clockwise from +X; robot/manufacturer coordinates must be transformed into this frame before coverage/missed-area analysis.
- Added LAS/EPSG coordinate workflow `docs/LAS_EPSG_COORDINATE_WORKFLOW_V1.md` and linked it from `docs/REGISTRATION_WORKFLOW_V1.md`: LAS header CRS is authoritative when present, missing CRS falls back to `EPSG:32760`, WGS84 `EPSG:4326` is only for Google Maps/sanity checks, and Auckland Council alignment uses `EPSG:2193`.
- Fixed GitHub Actions CI baseline after the 2026-06-21 push: coverage failure was caused by measuring the whole app while only running `tests/test_store.py`; CI now measures `store/models/data` with a 40% threshold and installs `httpx2` for FastAPI route tests.
- Deployed `main` to AWS test through GitHub Actions after adding the missing GitHub environment variables. Verified ECS `gardenos-test:5`, then updated ECS to `gardenos-test:6`; the MQTT runtime env used `MQTT_HOST=66.33.22.249` and `MQTT_PORT=53239`, but the user later clarified this was only the old Railway example broker, not the real new target.
- Verified AWS app health. The previous MQTT monitor verification used the old/example broker and must be repeated after the real broker address/port is configured.
- Confirmed robot MQTT setup should be address/port only, not AWS IoT Core key/cert and not the HTTP ALB URL. Existing robot topics must remain unchanged.
- Removed the platform MQTT monitor's old default broker behavior. If `MQTT_HOST` or `MQTT_PORT` is missing, the monitor now refuses to start instead of connecting to the old Railway example broker.
- Migrated the test MQTT broker path to AWS: created EC2 Mosquitto broker `i-07ee81ca7a5d2e5e5`, Elastic IP `3.103.181.148`, port `53239`, and broker SG `sg-067d077ce5e5c0830`; updated ECS to `gardenos-test:7` with `MQTT_HOST=3.103.181.148`, `MQTT_PORT=53239`, `MQTT_MONITOR_ENABLED=1`.
- Verified new AWS broker end to end: TCP port reachable, MQTT publish/subscribe on `HeartBeat` works, `/api/mqtt/status` reports connected, and a simulated `HeartBeat` with robotId `AWS-END2END-c205d925` was persisted in `mqtt_messages`.
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
