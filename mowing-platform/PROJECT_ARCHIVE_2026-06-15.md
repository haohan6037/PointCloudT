# Mowing Platform Archive - 2026-06-15

## Completed This Round

- Customer route and role-based flow remain in place for `admin / customer / provider`.
- Customer page keeps the first-login profile gate for name, phone, and default address.
- Customer tabs were stabilized into a consistent top tab bar.
- Address input now has:
  - manual typing with dropdown suggestions
  - current-location button
  - backend-compatible autocomplete / geocode / reverse-geocode endpoints
- Address provider backend has been refactored toward Geoapify integration with environment-variable-based key loading.
- Tests around address services were expanded to cover request construction and safe fallback behavior.

## Current Known Issue

- The provided Geoapify key currently returns `401 Unauthorized` against the live Geoapify API.
- Because of that, the production-like address autocomplete / reverse-geocode flow still cannot succeed with live data, even though the integration path and tests are in place.

## Local Secret Handling

- Real provider keys must stay in local private config only:
  - `mowing-platform/.env`
- Tracked files contain placeholders only:
  - `mowing-platform/.env.example`

## Recommended Next Step

1. Verify or replace the Geoapify key in the provider console.
2. Re-run live address lookup against `/api/address/autocomplete`.
3. If Geoapify remains blocked, switch the provider implementation cleanly to another managed autocomplete source without changing the frontend API contract.
