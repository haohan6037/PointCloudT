# MyGardenOS Project Context

Last updated: 2026-06-19

## Project

Workspace path:

```text
/Users/happyfamily/MyProject/PointCloudTT/apps/mygardenos
```

This project was migrated into the PointCloudTT monorepo from:

```text
/Users/happyfamily/MyProject/gardenos-mobile/MyGardenOS
```

It contains a React Native / Expo mobile app under `mobile/`, a FastAPI device backend under `backend/`, MQTT broker config under `mqtt/`, and BLE/MQTT integration tools under `tools/`.

From the PointCloudTT repository root, use:

```bash
cd apps/mygardenos
```

The mobile app should call the Railway backend directly. The current fallback API base is:

```text
https://mygardenos-mobile-backend-production.up.railway.app
```

Local Expo/Metro has previously been run with:

```bash
cd apps/mygardenos/mobile
npx expo start --ios --clear
```

Backend tests:

```bash
cd apps/mygardenos/backend
python3 -m pytest tests
```

Frontend typecheck:

```bash
cd apps/mygardenos/mobile
npm run typecheck
```

## Product Direction

The app is for managing MyGardenOS / Aitverse lawn mowing robots.

Current intended top-level app structure:

- Bottom tabs: `Device` and `Profile`.
- Users can browse the app before logging in.
- Login is required before managing account, families, and binding/managing devices.
- Device tab manages mower robots.
- Profile tab contains account, family, notification, general, help, and about areas.

## Implemented Recently

### Auth / Navigation

- App no longer forces login immediately on launch.
- Protected actions route to login when needed.
- Login debug code display was removed.

### Profile

- After login, Profile shows an avatar-style header similar to the provided screenshot.
- Profile shows username/email, Families/Devices quick buttons, and settings rows.
- Avatar can read from AsyncStorage key `avatar:${profile.id}` or `profile.avatar_url`.

### Add Device

- Add Device flow uses a radar-style scan animation.
- Radar sweep rotates and has trailing/fade effects.
- Default discovered Bluetooth device is shown as:
  - name: `Mower`
  - serial: `CD145B0AE7C1`
  - model: `NBMower`
  - RSSI: `-59 dBm`
- User selects the discovered device, then enters a password.
- Password input is empty by default and has placeholder `Default password: 1234`.
- Default accepted password is `1234`.
- The flow tries the platform Bluetooth pair endpoint first, then falls back to older bind behavior when the Railway backend is not yet updated.

### Device Page

- Device tab shows a mower card if a device is bound.
- Device card includes:
  - schedule time range pill
  - bluetooth/network icons
  - mower name, serial, model, user name placeholder
  - status pill
  - action buttons: Enter Device, Share, Start Task, Resume, Charging
- Bottom `Device` and `Profile` tabs were adjusted to sit at the bottom.

### Schedule Time Range

The current device page has a clickable working time range. It opens a modal where the user can set:

- start time
- end time

The schedule is now designed to persist to the platform backend, not just local app state.

Backend additions:

- `Device.schedule_start_time`
- `Device.schedule_end_time`
- response DTOs include both fields
- `PATCH /devices/{device_id}/schedule`
- startup helper adds schedule columns to existing DB tables if missing
- tests cover successful persistence and invalid time rejection

Frontend additions:

- `Device` type includes `schedule_start_time` / `schedule_end_time`
- `api.updateDeviceSchedule(id, body)`
- `Home` reads schedule from the device object and sends updates to the backend
- If Railway does not yet have the new endpoint deployed, the app shows `Schedule not saved`

Latest verification at time of writing:

```text
cd apps/mygardenos/mobile && npm run typecheck
passed

cd apps/mygardenos/backend && python3 -m pytest tests
27 passed, 6 warnings
```

## Protocol Notes

Protocol docs previously reviewed:

- `/Users/happyfamily/MyProject/Resource/Aitverse/协议/ymodem升级文档.md`
- `/Users/happyfamily/MyProject/Resource/Aitverse/协议/通讯协议精简版.md`

BLE/app-to-device command format appears to be JSON strings ending with `\r\n`.

Known commands from the protocol docs:

- unlock: `{"command":"$USER,2,admin,1234"}\r\n`
- get system info: `$SYSTEM`
- get status: `$STATUS`
- pause: `$ACTION,7`
- resume: `$ACTION,8`
- return to charge: `$ACTION,9`
- standby: `$ACTION,6`
- remote mode: `$ACTION,0`

Important gap:

- BLE service UUID and characteristic UUID are not documented yet.
- For real BLE integration, discover UUIDs from the physical device or firmware team.

## Backend API Direction

Device information that must survive logout/login or app reinstall should be saved to the backend.

Current device-related platform endpoints include or are being added:

- `GET /devices`
- `GET /devices/search`
- `GET /devices/bluetooth/scan`
- `POST /devices/bluetooth/pair`
- `GET /devices/{device_id}/status`
- `PATCH /devices/{device_id}/status`
- `PATCH /devices/{device_id}/schedule`

The Railway deployment must be updated after backend code changes before the mobile app can use new endpoints successfully.

## Monorepo Boundary

Within PointCloudTT, keep MyGardenOS as an independently runnable subproject:

- `apps/mygardenos/mobile`: mobile app.
- `apps/mygardenos/backend`: robot/device backend and MQTT monitor.
- `apps/mygardenos/tools`: BLE/MQTT/map-transfer tools.
- `apps/mygardenos/mqtt`: local broker config.

Do not fold these modules directly into `mowing-platform/` unless the integration is deliberately designed as an API boundary. The intended future split is a service-operations platform plus a separate robot/device service.

## Current Git State

At the time this context was written, these files had uncommitted changes:

```text
backend/app/main.py
backend/app/models/entities.py
backend/app/schemas/dto.py
backend/tests/test_api.py
mobile/App.tsx
mobile/src/screens/LoginScreen.tsx
mobile/src/services/api.ts
```

Before continuing development in a new Project session, run:

```bash
git status --short
```

Then inspect relevant diffs before editing further.

## Suggested Next Work

Continue one page/feature at a time.

Likely next steps:

1. Polish the working-time modal UI if needed.
2. Deploy backend changes to Railway and confirm `PATCH /devices/{id}/schedule` works from the simulator.
3. Start mapping device detail page data:
   - hardware/system info from `$SYSTEM`
   - live status from `$STATUS`
   - battery/status/task fields
4. Later, implement real BLE integration after service/characteristic UUIDs are confirmed.
