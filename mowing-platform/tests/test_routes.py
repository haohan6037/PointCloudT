"""FastAPI route integration tests / FastAPI 路由集成测试."""

from __future__ import annotations

import json
import urllib.parse


class TestDatabaseDsn:
    """Database DSN builder / 数据库连接串构建."""

    def test_build_dsn_uses_database_url_first(self, monkeypatch):
        from routes import _build_dsn

        monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
        monkeypatch.setenv("PGUSER", "ignored")

        assert _build_dsn() == "postgresql://example/db"

    def test_build_dsn_adds_rds_ssl_options(self, monkeypatch):
        from routes import _build_dsn

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("PGHOST", "mygardenostestdb.cno2oku4ynd8.ap-southeast-6.rds.amazonaws.com")
        monkeypatch.setenv("PGPORT", "5432")
        monkeypatch.setenv("PGDATABASE", "postgres")
        monkeypatch.setenv("PGUSER", "postgres")
        monkeypatch.setenv("PGPASSWORD", "secret with spaces")
        monkeypatch.setenv("PGSSLMODE", "verify-full")
        monkeypatch.setenv("PGSSLROOTCERT", "/app/certs/global-bundle.pem")

        dsn = _build_dsn()

        assert dsn is not None
        parsed = urllib.parse.urlparse(dsn)
        query = urllib.parse.parse_qs(parsed.query)
        assert parsed.hostname == "mygardenostestdb.cno2oku4ynd8.ap-southeast-6.rds.amazonaws.com"
        assert parsed.port == 5432
        assert parsed.username == "postgres"
        assert urllib.parse.unquote(parsed.password or "") == "secret with spaces"
        assert query["sslmode"] == ["verify-full"]
        assert query["sslrootcert"] == ["/app/certs/global-bundle.pem"]


class TestHealth:
    """Health check and bootstrap / 健康检查和数据加载."""

    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["mode"] in ("fallback", "postgres")

    def test_bootstrap_returns_orders_and_workers(self, client):
        resp = client.get("/api/bootstrap")
        assert resp.status_code == 200
        data = resp.json()
        assert "orders" in data
        assert "workers" in data
        assert "store" in data

    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_provider_returns_html(self, client):
        resp = client.get("/provider")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


class TestUserRoles:
    """App user session and roles / 平台用户会话与角色."""

    def test_session_sync_creates_customer_user(self, client):
        resp = client.post(
            "/api/session/sync",
            json={
                "email": "new.customer@example.com",
                "clerkUserId": "user_123",
                "displayName": "New Customer",
            },
        )
        assert resp.status_code == 200
        user = resp.json()["user"]
        assert user["email"] == "new.customer@example.com"
        assert user["role"] == "customer"
        assert user["clerkUserId"] == "user_123"

    def test_role_update_changes_route_role(self, client):
        client.post(
            "/api/session/sync",
            json={"email": "provider@example.com", "clerkUserId": "user_provider", "displayName": "Provider"},
        )
        resp = client.put(
            "/api/users/role",
            json={"email": "provider@example.com", "role": "provider", "status": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "provider"

        resp = client.get("/api/users/me", params={"email": "provider@example.com"})
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "provider"


class TestCustomerAuth:
    """Customer email-code login / 用户邮箱验证码登录."""

    def test_email_code_profile_roundtrip(self, client):
        email = "helen.chen@example.com"

        resp = client.post("/api/customer/auth/send-code", json={"email": email})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        from auth_service import _pending_codes

        code = next(key for key, value in _pending_codes.items() if value["email"] == email)
        resp = client.post("/api/customer/auth/verify", json={"email": email, "code": code})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["email"] == email

        resp = client.get("/api/customer/profile", params={"email": email})
        assert resp.status_code == 200
        assert resp.json()["profile"]["email"] == email

        resp = client.put(
            "/api/customer/profile",
            params={"email": email},
            json={
                "name": "Helen Updated",
                "phone": "021-555-0101",
                "whatsapp": "+64 21 555 0101",
                "wechat": "helen-updated",
                "address": "99 Test Street, Auckland",
            },
        )
        assert resp.status_code == 200
        updated = resp.json()["profile"]
        assert updated["name"] == "Helen Updated"
        assert updated["phone"] == "021-555-0101"

    def test_verify_rejects_invalid_code(self, client):
        resp = client.post(
            "/api/customer/auth/verify",
            json={"email": "helen.chen@example.com", "code": "000000"},
        )
        assert resp.status_code == 400


class TestOrderLifecycle:
    """Full order lifecycle via HTTP / 完整订单生命周期 HTTP 测试."""

    def test_create_and_quote_and_assign(self, client, sample_order_data):
        # Create
        resp = client.post("/api/orders", json=sample_order_data)
        assert resp.status_code == 200
        order_id = resp.json()["order"]["id"]
        assert order_id.startswith("MOW-")

        # Quote
        resp = client.post(
            f"/api/orders/{order_id}/quote",
            json={"price": "150", "priceNote": "标准"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "quoted"

        # Assign
        resp = client.post(
            f"/api/orders/{order_id}/assign",
            json={"workerId": "w-001"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "assigned"

        # Accept
        resp = client.post(f"/api/orders/{order_id}/accept")
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "accepted_by_worker"

    def test_reassign(self, client):
        # Find a quoted order
        resp = client.get("/api/bootstrap")
        orders = resp.json()["orders"]
        quoted = next((o for o in orders if o["status"] == "quoted"), None)
        if not quoted:
            # Create and quote one
            client.post("/api/orders", json={
                "user": "Test", "phone": "021", "address": "A",
                "serviceType": "一次性割草", "requestedTime": "2026-06-10",
                "lawnSize": "100", "condition": "flat",
            })
            resp = client.get("/api/bootstrap")
            quoted = next(o for o in resp.json()["orders"] if o["status"] == "pending_review")
            client.post(f"/api/orders/{quoted['id']}/quote", json={"price": "100"})
            client.post(f"/api/orders/{quoted['id']}/assign", json={"workerId": "w-001"})
            resp = client.get("/api/bootstrap")
            quoted = next(o for o in resp.json()["orders"] if o["status"] == "assigned")

        # Reassign
        resp = client.post(
            f"/api/orders/{quoted['id']}/reassign",
            json={"workerId": "w-002"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["assignedWorkerId"] == "w-002"

    def test_cancel(self, client):
        resp = client.post(
            "/api/orders",
            json={
                "user": "Cancel Test",
                "phone": "021-000-0000",
                "address": "1 Cancel Street, Auckland",
                "serviceType": "一次性割草",
                "requestedTime": "2026-06-20 09:00-12:00",
                "lawnSize": "约 120 平方米",
                "condition": "平整草坪",
                "note": "用于取消测试",
            },
        )
        assert resp.status_code == 200
        pending_id = resp.json()["order"]["id"]

        resp = client.post(
            f"/api/orders/{pending_id}/cancel",
            json={"note": "测试取消"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "cancelled"


class TestWorkerRoutes:
    """Worker management routes / 服务商管理路由."""

    def test_worker_availability_toggle(self, client):
        resp = client.post(
            "/api/workers/w-001/availability",
            json={"available": False},
        )
        assert resp.status_code == 200
        assert resp.json()["worker"]["available"] is False

    def test_worker_profile_update(self, client):
        resp = client.post(
            "/api/workers/w-002/profile",
            json={
                "name": "李师傅更新", "phone": "021-888",
                "area": "Mt Eden", "approvalStatus": "approved",
                "serviceNote": "更新备注", "lat": -36.87, "lng": 174.76,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["worker"]["name"] == "李师傅更新"


class TestAddressRoutes:
    """Address autocomplete, geocode, reverse-geocode and suggest / 地址服务路由."""

    # ── Geoapify unit tests / Geoapify 单元测试 ──

    def test_autocomplete_missing_key_returns_empty(self, monkeypatch):
        """autocomplete returns [] when GEOAPIFY_API_KEY is unset."""
        from address_service import AddressService

        monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
        result = AddressService.autocomplete("16 Pounamu Place")
        assert result == []

    def test_reverse_geocode_missing_key_returns_none(self, monkeypatch):
        """reverse_geocode returns None when GEOAPIFY_API_KEY is unset."""
        from address_service import AddressService

        monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
        result = AddressService.reverse_geocode(-36.85, 174.76)
        assert result is None

    def test_autocomplete_calls_geoapify_with_correct_params(self, monkeypatch):
        """autocomplete constructs a Geoapify autocomplete request with NZ bias."""
        from address_service import AddressService

        monkeypatch.setenv("GEOAPIFY_API_KEY", "test-key-123")

        captured = {}

        class DummyResponse:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return b'{"results":[]}'

        def fake_urlopen(url, timeout=0):
            captured["url"] = url
            captured["timeout"] = timeout
            return DummyResponse()

        monkeypatch.setattr("address_service.urllib.request.urlopen", fake_urlopen)

        AddressService.autocomplete("16 Pounamu Place")
        parsed = urllib.parse.urlparse(captured["url"])
        qs = urllib.parse.parse_qs(parsed.query)

        assert parsed.hostname == "api.geoapify.com"
        assert "/v1/geocode/autocomplete" in parsed.path
        assert qs["text"][0] == "16 Pounamu Place"
        assert qs["apiKey"][0] == "test-key-123"
        assert qs["filter"][0] == "countrycode:nz"

    def test_autocomplete_parses_geoapify_response(self, monkeypatch):
        """autocomplete extracts address + lat/lon from Geoapify response."""
        from address_service import AddressService

        monkeypatch.setenv("GEOAPIFY_API_KEY", "test-key-123")

        class DummyResponse:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return json.dumps({
                    "results": [
                        {"formatted": "16 Pounamu Place, Auckland", "lat": -36.85, "lon": 174.76},
                        {"formatted": "", "lat": 0, "lon": 0},
                    ]
                }).encode("utf-8")

        monkeypatch.setattr("address_service.urllib.request.urlopen", lambda u, timeout=0: DummyResponse())

        results = AddressService.autocomplete("16 Pounamu")
        assert len(results) == 1  # empty formatted is skipped
        assert results[0]["address"] == "16 Pounamu Place, Auckland"
        assert results[0]["lat"] == -36.85
        assert results[0]["lng"] == 174.76

    def test_reverse_geocode_calls_geoapify_with_correct_params(self, monkeypatch):
        """reverse_geocode constructs a Geoapify reverse request."""
        from address_service import AddressService

        monkeypatch.setenv("GEOAPIFY_API_KEY", "test-key-456")

        captured = {}

        class DummyResponse:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return json.dumps({
                    "results": [{"formatted": "1 Queen St, Auckland", "lat": -36.8485, "lon": 174.7633, "distance": 15}]
                }).encode("utf-8")

        def fake_urlopen(url, timeout=0):
            captured["url"] = url
            captured["timeout"] = timeout
            return DummyResponse()

        monkeypatch.setattr("address_service.urllib.request.urlopen", fake_urlopen)

        result = AddressService.reverse_geocode(-36.8485, 174.7633)
        parsed = urllib.parse.urlparse(captured["url"])
        qs = urllib.parse.parse_qs(parsed.query)

        assert parsed.hostname == "api.geoapify.com"
        assert "/v1/geocode/reverse" in parsed.path
        assert qs["lat"][0] == "-36.8485"
        assert qs["lon"][0] == "174.7633"
        assert qs["apiKey"][0] == "test-key-456"
        assert result["address"] == "1 Queen St, Auckland"

    def test_reverse_geocode_handles_geoapify_network_error(self, monkeypatch):
        """reverse_geocode returns None on network failure."""
        from address_service import AddressService

        monkeypatch.setenv("GEOAPIFY_API_KEY", "test-key")

        monkeypatch.setattr(
            "address_service.urllib.request.urlopen",
            lambda u, timeout=0: (_ for _ in ()).throw(OSError("network down")),
        )
        result = AddressService.reverse_geocode(-36.85, 174.76)
        assert result is None

    def test_autocomplete_short_query_returns_empty(self, client):
        resp = client.post("/api/address/autocomplete", json={"q": "XX"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_geocode_not_found(self, client):
        """Geocode returns 404 for nonsense address / 无效地址返回 404."""
        resp = client.post("/api/address/geocode", json={"q": "ZZZZZZZ_NO_SUCH_ADDRESS"})
        assert resp.status_code == 404

    def test_reverse_geocode_with_valid_coords(self, client, monkeypatch):
        """Reverse geocode with coordinates near central Auckland / 奥克兰中心附近坐标."""
        from address_service import AddressService

        monkeypatch.setattr(
            AddressService,
            "reverse_geocode",
            staticmethod(lambda lat, lng, max_radius_m=200: {"address": "62A Victoria Street West, Auckland", "lat": lat, "lng": lng}),
        )
        resp = client.get("/api/address/reverse-geocode", params={"lat": -36.85, "lng": 174.76})
        assert resp.status_code == 200
        assert resp.json()["address"].startswith("62A Victoria")

    def test_reverse_geocode_remote_location(self, client, monkeypatch):
        """Remote location returns 404 gracefully / 偏远位置应返回 404."""
        from address_service import AddressService

        monkeypatch.setattr(AddressService, "reverse_geocode", staticmethod(lambda lat, lng, max_radius_m=200: None))
        resp = client.get("/api/address/reverse-geocode", params={"lat": -40.0, "lng": 170.0})
        assert resp.status_code == 404

    def test_reverse_geocode_missing_params(self, client):
        """Missing lat/lng returns 422 / 缺少参数返回 422."""
        resp = client.get("/api/address/reverse-geocode")
        assert resp.status_code == 422

    def test_reverse_geocode_invalid_params(self, client):
        """Non-numeric lat/lng returns 422 / 非法参数返回 422."""
        resp = client.get("/api/address/reverse-geocode", params={"lat": "abc", "lng": "xyz"})
        assert resp.status_code == 422

    def test_worker_suggest(self, client, monkeypatch):
        from address_service import AddressService

        monkeypatch.setattr(
            AddressService,
            "geocode",
            staticmethod(lambda q: {"address": "16 Pounamu Place, Auckland", "lat": -36.85, "lng": 174.76, "nztm_x": None, "nztm_y": None}),
        )
        resp = client.post("/api/workers/suggest", json={"q": "16 Pounamu Place"})
        assert resp.status_code == 200
        data = resp.json()
        assert "workers" in data
        assert len(data["workers"]) >= 4


class TestEdgeCases:
    """Error handling / 错误处理."""

    def test_order_not_found(self, client):
        resp = client.post("/api/orders/MOW-9999/quote", json={"price": "100"})
        assert resp.status_code == 404

    def test_quote_empty_price(self, client):
        resp = client.post("/api/orders/MOW-1001/quote", json={"price": ""})
        assert resp.status_code == 422  # validation error

    def test_reset_demo(self, client):
        resp = client.post("/api/orders/reset-demo")
        # May be 200 (fallback mode) or 400 (postgres mode)
        assert resp.status_code in (200, 400)
