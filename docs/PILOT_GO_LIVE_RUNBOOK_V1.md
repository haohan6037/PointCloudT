# GardenOS Pilot Go-Live Runbook V1

## Scope

This runbook covers the remaining path from current local readiness to a real small pilot:

1. Deploy AWS Clerk strict auth.
2. Verify customer/admin/provider business closure on AWS.
3. Decide the minimum HTTPS/domain and S3 posture before inviting real external users.

Do not paste or commit real secrets, API keys, cookies, session tokens, private keys, or full Terraform `tfvars` values.

## Current Evidence

- Local customer token-backed identity is implemented for strict mode.
- Local business-closure test covers: customer booking, admin quote/assign, provider accept/arrival/evidence/complete, admin quality approval, settlement archive.
- Latest validated local command: `python3 -m pytest mowing-platform/tests -q` with 88 tests passing.
- AWS strict auth has not been deployed yet because local AWS control-plane calls to `sts.ap-southeast-6.amazonaws.com` are currently unreachable from this environment.

## AWS Strict Auth Deployment

Prerequisites:

- AWS CLI can call STS in `ap-southeast-6`.
- Terraform or OpenTofu is available.
- Current worktree changes are committed and pushed.
- The Clerk JWT public key PEM is available only as runtime input, not in Git.

Create or update the Clerk JWT key secret in Secrets Manager:

```bash
AWS_DEFAULT_REGION=ap-southeast-6 ./.awscli-venv/bin/aws secretsmanager create-secret \
  --name Clerk_JWT_Key \
  --description "GardenOS Clerk JWT public verification key" \
  --secret-string '{"CLERK_JWT_KEY":"PASTE_PUBLIC_KEY_PEM_WITH_ESCAPED_NEWLINES"}'
```

If the secret already exists, update it instead:

```bash
AWS_DEFAULT_REGION=ap-southeast-6 ./.awscli-venv/bin/aws secretsmanager put-secret-value \
  --secret-id Clerk_JWT_Key \
  --secret-string '{"CLERK_JWT_KEY":"PASTE_PUBLIC_KEY_PEM_WITH_ESCAPED_NEWLINES"}'
```

Then set these Terraform variables in local, untracked runtime config:

```text
clerk_auth_strict = "1"
clerk_jwt_key_secret_value_from = "arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Clerk_JWT_Key-xxxxxx:CLERK_JWT_KEY::"
clerk_jwt_key_secret_arn = "arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Clerk_JWT_Key-xxxxxx"
clerk_authorized_parties = "http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com"
```

`clerk_issuer` can stay blank unless the derived issuer fails verification or Clerk uses a custom Frontend API domain.

Apply infrastructure/task-definition config:

```bash
terraform -chdir=infra/aws/test init
terraform -chdir=infra/aws/test plan
terraform -chdir=infra/aws/test apply
```

If deployment is driven by GitHub Actions, push the committed changes and run `.github/workflows/deploy-aws-test.yml` for the `test` environment after Terraform has updated the service/task configuration.

## AWS Smoke Test

Expected app URL:

```text
http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com
```

Minimum checks:

```bash
curl -sS http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com/api/health
```

Expected:

```json
{"ok":true,"mode":"postgres","databaseEnabled":true,"error":null}
```

Strict-auth negative checks:

- `GET /api/users` without `Authorization` must return `401` or `403`.
- `GET /api/provider/workbench` without `Authorization` must return `401` or `403`.
- `GET /api/customer/orders?phone=<other-phone>` with a logged-in customer token must not return another customer's orders.

Runnable smoke script:

```bash
BASE_URL=http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com \
  scripts/aws_strict_auth_smoke.sh
```

Optional positive token checks:

```bash
BASE_URL=http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com \
ADMIN_TOKEN='<admin Clerk session token>' \
PROVIDER_TOKEN='<provider Clerk session token>' \
CUSTOMER_TOKEN='<customer Clerk session token>' \
  scripts/aws_strict_auth_smoke.sh
```

Do not paste these tokens into Git, logs, tickets, or documentation. Use them only in the shell session running the smoke test.

Manual portal checks:

- Admin `/`: sign in as an admin and confirm user management and order list load.
- Customer `/customer`: sign in, save profile, create booking, view only own orders.
- Provider `/provider`: sign in as the worker-linked provider, accept assigned work, upload evidence, submit completion.

## Business Closure Acceptance

The AWS pilot is ready only after one full AWS-hosted test order proves:

1. Customer creates a booking.
2. Admin quotes and assigns it.
3. Customer accepts the quote.
4. Provider accepts, marks arrival, uploads evidence, and submits completion.
5. Admin approves quality review.
6. Admin records payment/settlement metadata and archives completion.

Record the test order id and final status in the project handoff notes. Do not record real customer personal data.

## HTTPS And Domain Decision

Decision for small external pilot:

- Use a real domain plus HTTPS before inviting real customers or providers outside the owner/admin circle.
- The current ALB HTTP URL is acceptable only for internal smoke tests and owner-only demos.

Reason:

- Clerk, browser security expectations, customer trust, and copied booking links all work better with HTTPS.
- Strict auth protects APIs, but it does not make plain HTTP a good customer-facing launch surface.

Minimum path:

1. Register or choose a GardenOS test subdomain.
2. Add an ACM certificate in the AWS region used by the ALB.
3. Add an HTTPS listener on the ALB.
4. Redirect HTTP to HTTPS once verified.
5. Add the HTTPS origin to `CLERK_AUTHORIZED_PARTIES`.
6. Add the domain to Clerk allowed redirect/origin settings if required.

## S3 Decision

Decision for first very small pilot:

- Local ECS filesystem uploads are acceptable only for internal smoke tests.
- Before real providers upload real site photos, move evidence photos to S3 or another managed object store.

Reason:

- Fargate task filesystem is not durable across replacements.
- Evidence photos are part of business closure and dispute handling.
- S3 gives better lifecycle, access control, backup, and future scanning hooks.

Minimum S3 posture:

1. Private bucket in `ap-southeast-6`.
2. Object keys under `provider-evidence/<order-id>/...`.
3. Server-side encryption enabled.
4. Application stores URLs or object keys on the order.
5. File size/type validation before upload.
6. Later: signed download URLs or role-gated proxy endpoint.

## Current Go / No-Go

Internal local/demo: Go.

AWS owner-only smoke test: Go after strict auth deploy succeeds.

External small pilot with real customer/provider data: No-go until HTTPS/domain and managed evidence storage are in place.
