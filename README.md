# PointCloudTT / GardenOS Workspace

This repository is now the combined workspace for the GardenOS mowing-service platform, point-cloud lawn-recognition tools, and the MyGardenOS robot/mobile exploration project.

## Project Layout

| Path | Purpose |
| --- | --- |
| `mowing-platform/` | Active GardenOS service platform: FastAPI backend plus admin/customer/service-provider HTML portals. |
| `apps/mygardenos/` | MyGardenOS robot/mobile project migrated from the former standalone `gardenos-mobile/MyGardenOS` checkout. Contains the Expo app, device backend, MQTT broker config, and BLE/MQTT tools. |
| `scripts/` | Local point-cloud and lawn-recognition tooling. |
| `docs/` | Product, architecture, deployment, and long-term memory docs for the combined workspace. |
| `infra/aws/test/` | AWS test-environment scaffold for the service platform. |

## Run The Current Service Platform

```bash
./start.sh
```

Default local URL:

```text
http://127.0.0.1:8011/
```

## Work On MyGardenOS

From the repository root:

```bash
cd apps/mygardenos
```

Backend:

```bash
cd apps/mygardenos/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Mobile:

```bash
cd apps/mygardenos/mobile
npm install
npm run typecheck
npm run start
```

BLE/MQTT web tool:

```bash
cd apps/mygardenos/tools/ble-mqtt-config
python3 -m http.server 4173
```

Open `http://localhost:4173`.

## Architecture Direction

Keep each product/service boundary explicit:

- `mowing-platform/` remains the service-operations platform.
- `apps/mygardenos/backend` remains the robot/device API and MQTT monitor service.
- `apps/mygardenos/mobile` remains the mobile app.
- `apps/mygardenos/tools` remains device-integration tooling.
- `scripts/` remains local lawn-recognition research tooling.

This gives one-person workspace convenience now while preserving a clean path to split these pieces into independent services later.
