# Railway Backend Deployment Runbook

This guide is the production-ready, repeatable process to deploy the MyGardenOS backend to Railway.

## Scope

- Deploys the FastAPI backend in `apps/mygardenos/backend/`
- Uses Docker build from `apps/mygardenos/backend/Dockerfile`
- Publishes a public Railway URL
- Configures required runtime environment variables
- Verifies API health and auth email endpoints

## Prerequisites

- GitHub repo is up to date
- Railway account access
- Node.js and npm installed locally (for Railway CLI install)
- Access to backend secrets:
  - `DATABASE_URL`
  - `RESEND_API_KEY`
  - `AUTH_SECRET`

## Required backend files

These files must exist in the repo for stable Railway deployment:

- `apps/mygardenos/backend/Dockerfile`
- `apps/mygardenos/backend/requirements.txt`
- `apps/mygardenos/backend/Procfile`
- `apps/mygardenos/backend/runtime.txt`

Current expected values:

### apps/mygardenos/backend/Procfile

```procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### apps/mygardenos/backend/runtime.txt

```text
python-3.11.9
```

### apps/mygardenos/backend/Dockerfile (important CMD)

Use a dynamic port from Railway:

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## One-time setup

1. Install Railway CLI:

```bash
npm install -g @railway/cli
```

2. Login (browserless flow):

```bash
railway login --browserless
```

3. Open the activation URL shown in terminal and enter the code.

## Create or link Railway project

From repo backend folder:

```bash
cd apps/mygardenos/backend
railway init --name MyGardenOS-Mobile-Backend --json
```

If project already exists, link it:

```bash
railway link
railway service link MyGardenOS-Mobile-Backend
```

## Configure environment variables

Set all required vars on the backend service:

```bash
railway variable set \
  DATABASE_URL='YOUR_DATABASE_URL' \
  RESEND_API_KEY='YOUR_RESEND_API_KEY' \
  AUTH_SECRET='YOUR_AUTH_SECRET' \
  AUTH_CODE_TTL_MINUTES='10' \
  AUTH_VERIFY_TOKEN_TTL_MINUTES='15' \
  AUTH_SESSION_TTL_DAYS='30' \
  AUTH_DEBUG_CODES='1' \
  --service MyGardenOS-Mobile-Backend --json
```

Recommended for real email-only behavior in staging/production:

```bash
railway variable set AUTH_DEBUG_CODES='0' --service MyGardenOS-Mobile-Backend --json
```

## Deploy

```bash
railway up --detach
```

Check status:

```bash
railway service status --service MyGardenOS-Mobile-Backend --json
```

Check logs:

```bash
railway logs --latest --service MyGardenOS-Mobile-Backend --lines 200
railway logs --build --latest --service MyGardenOS-Mobile-Backend --lines 200
```

## Create public domain

```bash
railway domain --service MyGardenOS-Mobile-Backend --json
```

Example generated URL:

```text
https://mygardenos-mobile-backend-production.up.railway.app
```

## Verification checklist

1. Health endpoint:

```bash
curl -s -w "\nHTTP %{http_code}\n" https://YOUR_RAILWAY_URL/health
```

Expected: HTTP 200 and `{"status":"ok","service":"MyGardenOS API"}`.

2. Email code endpoint:

```bash
curl -s -X POST https://YOUR_RAILWAY_URL/auth/email/request-code \
  -H 'Content-Type: application/json' \
  -d '{"email":"your-email@example.com"}' | jq .
```

Interpretation:

- `status: "sent"` and `delivered: true`: provider accepted send request.
- `status: "debug_only"` and `delivered: false`: email provider call failed; use `delivery_error` for root cause.

## Mobile app integration

Set mobile API URL to Railway in env files:

- `apps/mygardenos/mobile/.env`
- `apps/mygardenos/mobile/.env.development`
- `apps/mygardenos/mobile/.env.staging`

Value format:

```text
EXPO_PUBLIC_API_URL=https://YOUR_RAILWAY_URL
```

Restart Expo after env changes:

```bash
cd apps/mygardenos/mobile
npx expo start --ios --clear
```

## Troubleshooting

### Build fails with resend version error

Symptom:

- `No matching distribution found for resend==3.7.0`

Fix:

- Use a valid version in `backend/requirements.txt` (current working value: `resend==2.30.1`).

### Service starts but Railway returns 502

Symptom:

- `Application failed to respond`

Fix:

- Ensure app binds Railway `PORT` dynamically in Docker `CMD`.

### API says sent but inbox empty

Use endpoint response fields:

- `delivered`
- `delivery_error`

If `delivered=false`, resolve provider/config issue first.

### delivery_error = resend_sdk_not_installed

Cause:

- SDK import/call mismatch.

Fix already applied:

- Backend now uses `resend` 2.x style (`resend.api_key` + `resend.Emails.send`).

## Security notes

- Never commit real secrets to git.
- Rotate any token exposed in terminal/chat history.
- Prefer Railway dashboard secret management for all production values.
