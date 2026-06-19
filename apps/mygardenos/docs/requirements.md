# Screenshot Requirement Mapping

## Mobile UI

1. **Device home**: top Help, notification, add controls; empty Add Device art; Device/Profile tabs; bound mock device card after binding.
2. **Add Device**: radar scan artwork, `Search in Devices`, Bluetooth guidance, `Select Device`, mock selectable devices, bind flow via API.
3. **Account**: profile photo placeholder, account/email, username, gender, address, password, deactivate, logout; editable fields call `/profile`.
4. **Families**: list shows `happy family(1)` and member card; plus action sheet with Creating/Binding familie/Cancel; details show code/name/address/dissolve; address modal.
5. **Notifications**: Device/System tabs, Unread/Read filters, empty `No news at this time`, settings page with two switches.
6. **Help**: Advice and feedback, expandable Contact Us details, Operation Help list and PDF-like article detail.
7. **About**: product placeholder, MyGardenOS version metadata, check updates, privacy, user agreement.
8. **General Settings**: Language, Region Auto, Clear Cache, English/Cancel action sheet.

## Backend

- Dev auth/profile: `/auth/dev-user`, `/profile`
- Families/members: `/families`
- Devices: `/devices`, `/devices/search`, `/devices/bind`
- Notifications/settings: `/notifications`, `/settings`
- Help/about: `/help/articles`, `/about`
- Health/docs: `/health`, `/docs`

## PostGIS readiness

`users` and `families` currently include latitude/longitude fields for portable dev/test execution. Docker Compose uses `postgis/postgis`; a production Alembic migration can add `geography(Point,4326)` columns and backfill from latitude/longitude.
