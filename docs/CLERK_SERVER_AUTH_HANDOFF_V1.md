# Clerk Server Auth Handoff V1

## Purpose

GardenOS now supports a safer admin/provider API path:

- Frontend pages request a Clerk session token from ClerkJS.
- API requests send the token in `Authorization: Bearer <token>`.
- Backend code verifies the token when `CLERK_JWT_KEY` is configured.
- Verified token claim `sub` is matched to local `app_users.clerk_user_id`.
- Role checks then use the local `app_users` row, not a client-supplied email.

This keeps the app usable in local/dev mode while creating a strict production switch.

## Runtime Modes

### Local / Demo Mode

```text
CLERK_AUTH_STRICT=0
```

Behavior:

- Bearer tokens are used if present and `CLERK_JWT_KEY` is configured.
- If no token/key is configured, legacy email/header fallback still works.
- This mode is useful for local demos and tests.

### Production / Strict Mode

```text
CLERK_AUTH_STRICT=1
CLERK_JWT_KEY=...
CLERK_AUTHORIZED_PARTIES=...
```

Behavior:

- Admin and provider protected APIs require a valid Clerk session token.
- Client-supplied emails and `X-GardenOS-Actor-Email` are not accepted as proof of identity.
- If `CLERK_JWT_KEY` is missing, protected API calls fail.

## Environment Variables

Required for strict production:

```text
CLERK_AUTH_STRICT=1
CLERK_JWT_KEY=<Clerk JWT public key PEM>
CLERK_AUTHORIZED_PARTIES=<allowed frontend origins, comma-separated>
```

Optional:

```text
CLERK_ISSUER=<expected Clerk issuer>
CLERK_AUDIENCE=<expected JWT audience, comma-separated>
```

Do not commit real secrets or private keys. `CLERK_JWT_KEY` is a public verification key, but it should still be managed through environment/runtime config rather than hard-coded in source.

## Clerk Dashboard Values Needed

Ask the project owner for:

1. Clerk publishable key for frontend login.
2. Clerk JWT public key in PEM format.
3. Clerk issuer / Frontend API URL.
4. Allowed frontend origins for `CLERK_AUTHORIZED_PARTIES`.
5. Production domain once available.

## Current Protected APIs

Admin:

- `GET /api/users`
- `PUT /api/users/role`
- `GET /api/mqtt/status`
- `GET /api/mqtt/messages`
- `POST /api/mqtt/messages`

Provider:

- `GET /api/provider/workbench`
- `POST /api/provider/orders/{order_id}/accept`
- `POST /api/provider/orders/{order_id}/reject`
- `POST /api/provider/orders/{order_id}/arrival`
- `POST /api/provider/orders/{order_id}/service-log`
- `POST /api/provider/orders/{order_id}/complete`
- `POST /api/provider/orders/{order_id}/evidence`
- `POST /api/provider/orders/{order_id}/exception`

## Remaining Auth Hardening

Still needed before public production:

- Apply token-backed customer identity to customer profile/order APIs.
- Remove phone-only customer order lookup or restrict it to verified customer identity.
- Add managed upload scanning and file-size limits for evidence photos.
- Move uploads to managed object storage before production scale.
- Add audit log fields for actor id, role, and action on admin/provider operations.
