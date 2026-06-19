# Project Summary — PointCloudTT / GardenOS

Date: 2026-06-19 NZST

---

## Executive Summary

PointCloudTT currently contains two related but distinct product tracks:

1. **GardenOS mowing service platform**
   - A web platform for connecting customers, platform administrators, and service providers.
   - The current implementation is a FastAPI + HTML/CSS/JavaScript application under `mowing-platform/`.
   - It supports local PostgreSQL development and has AWS test deployment documentation.

2. **Point-cloud / lawn recognition pipeline**
   - A prototype workflow for rendering LAS/LAZ point clouds into top-view imagery and extracting first-pass lawn boundaries.
   - It remains a separate research and tooling track.

The near-term product focus is the mowing service platform.

---

## Business Context

The platform is intended to support a hybrid lawn-care operating model:

- Customers request lawn/garden services.
- Platform admins manage orders, quotes, dispatch, service progress, and settlement.
- Service providers perform real-world lawn and garden work.
- Robots may be part of the operating model, but service providers still handle edge trimming, tree areas, complex terrain, and finishing work that robots cannot perform well.

Phase 1 focuses on operational flow and role separation, not full robot maintenance.

---

## Current System Capabilities

### Customer Portal

Path: `/customer`

Capabilities:

- Clerk login entry.
- First-login profile gate.
- Required profile basics: name, phone, default address.
- Customer address becomes the default booking address.
- Mobile-like tabs:
  - booking
  - my orders
  - my profile
- Customer can submit service requests and view order progress.

### Admin Portal

Path: `/`

Capabilities:

- Order management.
- Quote creation.
- Dispatch board.
- Worker/service-provider selection and conflict checks.
- Service logs.
- Exception handling.
- Quality review.
- Completion archive and settlement fields.
- CSV export.
- Stage acceptance view.
- User management:
  - list users
  - set role
  - set status

### Service-Provider Portal

Path: `/provider`

Current state:

- Role-gated service-provider entry.
- Account identity display.
- Workbench skeleton for future task list, service logs, and exception reporting.

This portal is not yet feature-equivalent to the admin operations view.

---

## Role Model

Canonical roles:

| Role | Chinese meaning | Default route |
| --- | --- | --- |
| `customer` | 普通用户 | `/customer` |
| `admin` | 管理员 | `/` |
| `server` | 服务商 | `/provider` |

Important rules:

- Admins can enter all three portals.
- Non-admin users should only have one portal role.
- Legacy `provider` values are normalized to `server`.
- Default admins are:
  - `haohan6037@gmail.com`
  - `kaiyu.yang@youngproperty.co.nz`

---

## Local Development State

Default local app URL:

```text
http://127.0.0.1:8011/
```

Local database:

```text
host: 127.0.0.1
port: 5433
database: MyGardenOSManagementSyetem
```

Startup:

```bash
./start.sh
```

Expected local health:

```json
{"ok": true, "mode": "postgres", "databaseEnabled": true, "error": null}
```

If the app reports fallback/demo data, check:

- Whether local PostgreSQL is listening on 5433.
- Whether `mowing-platform/.env` points to local dev, not AWS.
- Whether `start.sh` is using `mowing-platform/.venv/bin/python`.
- Whether `psycopg` and `python-multipart` are installed in the project venv.

---

## AWS Test State

AWS test environment is documented in:

```text
docs/AWS_TEST_DEPLOYMENT.md
```

Principles:

- AWS test uses AWS RDS and Secrets Manager.
- Runtime region should be New Zealand: `ap-southeast-6`.
- Local `.env` must not be copied to AWS.
- Secrets are referenced by secret names / environment variable names only.

---

## Point-Cloud / Lawn Recognition State

Main docs:

- `docs/LAS_TO_TOPVIEW_DESIGN.md`
- `docs/LAWN_RECOGNITION_DRAFT_V1.md`

Current pipeline:

1. Read LAS/LAZ source data.
2. Render top-view imagery from sampled point cloud data.
3. Generate enhanced top-view image and metadata.
4. Extract rule-based lawn mask.
5. Produce editable first-pass lawn polygon.

Known limitation:

- The lawn recognition output is a draft and requires human review before any operational use.

---

## Current Risks and Follow-Ups

1. **Authentication hardening**
   - Current user-management API guard uses `X-GardenOS-Actor-Email`.
   - Before production, replace with server-side Clerk JWT verification.

2. **Service-provider portal**
   - Needs real task list, accept/reject flow, service logs, photo upload, and earnings/settlement visibility.

3. **Address autocomplete**
   - Geoapify/live provider behavior may need re-verification depending on key restrictions.

4. **Environment separation**
   - Local dev must stay on local PostgreSQL.
   - AWS test must stay on AWS RDS/Secrets Manager.

5. **Point-cloud integration**
   - The point-cloud pipeline is not yet integrated into mowing order intake or quoting.

---

## Most Useful Next Steps

1. Add server-side Clerk token verification for protected admin APIs.
2. Expand the service-provider portal into a real daily task workflow.
3. Add role-aware API guards beyond the user-management API.
4. Re-check address autocomplete with the intended production provider key.
5. Decide how and when point-cloud lawn boundary output feeds into customer quoting or service planning.
