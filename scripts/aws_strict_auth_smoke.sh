#!/usr/bin/env bash
set -u

BASE_URL="${BASE_URL:-http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com}"
EXPECT_STRICT="${EXPECT_STRICT:-1}"

BASE_URL="${BASE_URL%/}"
failures=0
body_file="$(mktemp -t gardenos-smoke.XXXXXX)"

cleanup() {
  rm -f "$body_file"
}
trap cleanup EXIT

log() {
  printf '%s\n' "$*"
}

record_failure() {
  failures=$((failures + 1))
  log "FAIL: $*"
  if [ -s "$body_file" ]; then
    log "Response body:"
    head -c 800 "$body_file"
    printf '\n'
  fi
}

expect_status() {
  local label="$1"
  local expected="$2"
  shift 2

  : > "$body_file"
  local code
  code="$(curl -sS -o "$body_file" -w '%{http_code}' "$@")"
  local curl_status=$?
  if [ "$curl_status" -ne 0 ]; then
    record_failure "$label -> curl failed with exit $curl_status"
    return
  fi

  case " $expected " in
    *" $code "*)
      log "PASS: $label -> HTTP $code"
      ;;
    *)
      record_failure "$label -> expected HTTP {$expected}, got $code"
      ;;
  esac
}

expect_body_contains() {
  local label="$1"
  local needle="$2"
  if grep -Fq "$needle" "$body_file"; then
    log "PASS: $label contains $needle"
  else
    record_failure "$label missing $needle"
  fi
}

log "GardenOS AWS strict-auth smoke"
log "BASE_URL=$BASE_URL"
log "EXPECT_STRICT=$EXPECT_STRICT"

expect_status "health" "200" "$BASE_URL/api/health"
expect_body_contains "health" '"ok":true'
expect_body_contains "health" '"databaseEnabled":true'

expect_status "admin page" "200" "$BASE_URL/"
expect_status "customer page" "200" "$BASE_URL/customer"
expect_status "provider page" "200" "$BASE_URL/provider"

if [ "$EXPECT_STRICT" = "1" ]; then
  expect_status "admin users without token rejected" "401 403" "$BASE_URL/api/users"
  expect_status "provider workbench without token rejected" "401 403" "$BASE_URL/api/provider/workbench"
  expect_status "customer orders without token rejected" "401 403" "$BASE_URL/api/customer/orders?phone=021-000-0000"
else
  log "SKIP: strict negative checks disabled"
fi

if [ "${ADMIN_TOKEN:-}" != "" ]; then
  expect_status "admin users with token" "200" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "$BASE_URL/api/users"
else
  log "SKIP: ADMIN_TOKEN not set"
fi

if [ "${PROVIDER_TOKEN:-}" != "" ]; then
  expect_status "provider workbench with token" "200" \
    -H "Authorization: Bearer ${PROVIDER_TOKEN}" \
    "$BASE_URL/api/provider/workbench"
else
  log "SKIP: PROVIDER_TOKEN not set"
fi

if [ "${CUSTOMER_TOKEN:-}" != "" ]; then
  expect_status "customer profile with token" "200" \
    -H "Authorization: Bearer ${CUSTOMER_TOKEN}" \
    "$BASE_URL/api/customer/profile"
  expect_status "customer orders with token" "200" \
    -H "Authorization: Bearer ${CUSTOMER_TOKEN}" \
    "$BASE_URL/api/customer/orders"
else
  log "SKIP: CUSTOMER_TOKEN not set"
fi

if [ "$failures" -gt 0 ]; then
  log "Smoke test failed: $failures check(s)"
  exit 1
fi

log "Smoke test passed"
