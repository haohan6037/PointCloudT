# Clerk Server Auth Handoff V1

## Purpose

GardenOS now supports a safer protected API path:

- Frontend pages request a Clerk session token from ClerkJS.
- API requests send the token in `Authorization: Bearer <token>`.
- Backend code verifies the token when `CLERK_JWT_KEY` is configured.
- Verified token claim `sub` is matched to local `app_users.clerk_user_id`.
- Role checks then use the local `app_users` row, not a client-supplied email.
- Customer profile/order APIs also use the verified token in strict mode. Customer order access is restricted through the signed-in user's local customer profile phone.

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

- Admin, provider, and customer protected APIs require a valid Clerk session token.
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

If `CLERK_ISSUER` is not set, the backend derives it from `Clerk_Public_Key`, `CLERK_PUBLISHABLE_KEY`, or `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` when possible.

Do not commit real secrets or private keys. `CLERK_JWT_KEY` is a public verification key, but it should still be managed through environment/runtime config rather than hard-coded in source.

## Clerk Dashboard Values Needed

Ask the project owner for:

1. Clerk publishable key for frontend login.
2. Clerk JWT public key in PEM format.
3. Allowed frontend origins for `CLERK_AUTHORIZED_PARTIES`.
4. Production domain once available.

The Clerk issuer / Frontend API URL can usually be derived from the publishable key. Configure `CLERK_ISSUER` explicitly only when using a custom Clerk domain or when runtime verification shows the derived value does not match the token `iss`.

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

Customer:

- `GET /api/customer/profile`
- `PUT /api/customer/profile`
- `POST /api/customer/orders`
- `GET /api/customer/orders`
- `POST /api/customer/orders/{order_id}/confirm`
- `POST /api/customer/orders/{order_id}/reject`

## Remaining Auth Hardening

Still needed before public production:

- AWS test must be deployed with `CLERK_AUTH_STRICT=1` and `CLERK_JWT_KEY`.
- Consider adding a durable `customer_email` / `customer_user_id` owner field on orders. The current strict path uses the signed-in customer's profile phone as the order ownership boundary to avoid a database migration.
- Add managed upload scanning and file-size limits for evidence photos.
- Move uploads to managed object storage before production scale.
- Add audit log fields for actor id, role, and action on admin/provider operations.
