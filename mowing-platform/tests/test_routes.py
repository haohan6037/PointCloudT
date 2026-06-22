"""FastAPI route integration tests / FastAPI 路由集成测试."""

from __future__ import annotations

import base64
import json
import time
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


class TestClerkAuthConfig:
    """Clerk auth runtime configuration."""

    def test_derives_issuer_from_publishable_key(self, monkeypatch):
        from auth_service import clerk_issuer_from_env

        host = "bright-marten-12.clerk.accounts.dev$"
        encoded = base64.urlsafe_b64encode(host.encode("utf-8")).decode("ascii").rstrip("=")

        monkeypatch.delenv("CLERK_ISSUER", raising=False)
        monkeypatch.setenv("Clerk_Public_Key", f"pk_test_{encoded}")

        assert clerk_issuer_from_env() == "https://bright-marten-12.clerk.accounts.dev"

    def test_explicit_issuer_wins_over_publishable_key(self, monkeypatch):
        from auth_service import clerk_issuer_from_env

        host = "bright-marten-12.clerk.accounts.dev$"
        encoded = base64.urlsafe_b64encode(host.encode("utf-8")).decode("ascii").rstrip("=")

        monkeypatch.setenv("CLERK_ISSUER", "https://clerk.example.com")
        monkeypatch.setenv("Clerk_Public_Key", f"pk_test_{encoded}")

        assert clerk_issuer_from_env() == "https://clerk.example.com"


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
            json={"email": "provider@example.com", "role": "server", "status": "active"},
            headers={"X-GardenOS-Actor-Email": "haohan6037@gmail.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "server"

        resp = client.get("/api/users/me", params={"email": "provider@example.com"})
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "server"

    def test_legacy_provider_role_is_normalized_to_server(self, client):
        resp = client.put(
            "/api/users/role",
            json={"email": "legacy.provider@example.com", "role": "provider", "status": "active"},
            headers={"X-GardenOS-Actor-Email": "haohan6037@gmail.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "server"

    def test_default_admin_emails_are_initialized_as_admin(self, client):
        for email in ("haohan6037@gmail.com", "kaiyu.yang@youngproperty.co.nz"):
            resp = client.post(
                "/api/session/sync",
                json={"email": email, "clerkUserId": f"user_{email}", "displayName": email},
            )
            assert resp.status_code == 200
            assert resp.json()["user"]["role"] == "admin"

    def test_user_management_requires_admin_actor(self, client):
        resp = client.get("/api/users")
        assert resp.status_code == 403

        client.post(
            "/api/session/sync",
            json={"email": "plain.customer@example.com", "clerkUserId": "user_customer", "displayName": "Customer"},
        )
        resp = client.get("/api/users", headers={"X-GardenOS-Actor-Email": "plain.customer@example.com"})
        assert resp.status_code == 403

    def test_admin_actor_can_list_and_update_users(self, client):
        resp = client.get("/api/users", headers={"X-GardenOS-Actor-Email": "kaiyu.yang@youngproperty.co.nz"})
        assert resp.status_code == 200
        assert "users" in resp.json()

        resp = client.put(
            "/api/users/role",
            json={"email": "new.server@example.com", "role": "server", "status": "active"},
            headers={"X-GardenOS-Actor-Email": "kaiyu.yang@youngproperty.co.nz"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "server"

    def test_admin_can_use_verified_clerk_token(self, client, monkeypatch):
        client.post(
            "/api/session/sync",
            json={
                "email": "haohan6037@gmail.com",
                "clerkUserId": "user_admin_token",
                "displayName": "Admin Token",
            },
        )
        monkeypatch.setattr("routes.verify_clerk_session_token", lambda authorization: {"sub": "user_admin_token"})

        resp = client.get("/api/users", headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        assert "users" in resp.json()

    def test_strict_auth_rejects_missing_clerk_token(self, client, monkeypatch):
        monkeypatch.setenv("CLERK_AUTH_STRICT", "1")

        resp = client.get("/api/users")

        assert resp.status_code == 401


class TestMqttMonitor:
    """MQTT monitoring and persistence / MQTT 监听与存储."""

    def test_mqtt_messages_require_admin_actor(self, client):
        resp = client.get("/api/mqtt/messages")
        assert resp.status_code == 403

    def test_admin_can_record_and_query_mqtt_messages(self, client):
        headers = {"X-GardenOS-Actor-Email": "haohan6037@gmail.com"}
        resp = client.post(
            "/api/mqtt/messages",
            headers=headers,
            json={
                "topic": "HeartBeat",
                "payload": json.dumps({"robotId": "TEST-MOWER", "power": 91}),
                "source": "test",
            },
        )
        assert resp.status_code == 200
        message = resp.json()["message"]
        assert message["topic"] == "HeartBeat"
        assert message["json"]["robotId"] == "TEST-MOWER"
        assert message["robotId"] == "TEST-MOWER"
        assert message["messageType"] == "HeartBeat"

        resp = client.get("/api/mqtt/messages", headers=headers, params={"topic": "HeartBeat", "q": "TEST-MOWER"})
        assert resp.status_code == 200
        messages = resp.json()["messages"]
        assert any(item["json"] and item["json"].get("robotId") == "TEST-MOWER" for item in messages)
        assert any(item["robotId"] == "TEST-MOWER" for item in messages)

    def test_admin_can_read_mqtt_status(self, client):
        resp = client.get("/api/mqtt/status", headers={"X-GardenOS-Actor-Email": "haohan6037@gmail.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert "topics" in data
        assert "started" in data
        assert "queueDepth" in data
        assert "rawLogDir" in data

    def test_monitor_requires_explicit_mqtt_host_and_port(self, monkeypatch):
        from mqtt_monitor import PlatformMqttMonitor

        class FakeService:
            store = None

        monkeypatch.delenv("MQTT_HOST", raising=False)
        monkeypatch.delenv("MQTT_PORT", raising=False)
        monkeypatch.setenv("MQTT_MONITOR_ENABLED", "1")

        monitor = PlatformMqttMonitor(FakeService())

        assert monitor.start() is False
        status = monitor.status()
        assert status["host"] == ""
        assert status["port"] is None
        assert "MQTT_HOST and MQTT_PORT" in status["lastError"]

    def test_monitor_writes_raw_ndjson_and_batches(self, tmp_path, monkeypatch):
        from mqtt_monitor import PlatformMqttMonitor

        class FakeStore:
            def __init__(self) -> None:
                self.messages = []

            def record_mqtt_messages(self, messages):
                self.messages.extend(messages)
                return messages

        class FakeService:
            def __init__(self) -> None:
                self.store = FakeStore()

        service = FakeService()
        monkeypatch.setenv("MQTT_RAW_LOG_DIR", str(tmp_path))
        monkeypatch.setenv("MQTT_BATCH_SIZE", "2")
        monkeypatch.setenv("MQTT_FLUSH_INTERVAL_SECONDS", "0.1")
        monitor = PlatformMqttMonitor(service)

        assert monitor.record_received_message("HeartBeat", json.dumps({"robotId": "QUEUE-MOWER"}), "test")
        assert monitor.record_received_message("ResponseCommand", json.dumps({"command": "$STATUS", "robotId": "QUEUE-MOWER"}), "test")

        deadline = time.time() + 2
        while time.time() < deadline and len(service.store.messages) < 2:
            time.sleep(0.02)
        monitor.stop()

        assert len(service.store.messages) == 2
        raw_files = list(tmp_path.glob("*/*.ndjson"))
        assert raw_files
        raw_text = "\n".join(path.read_text(encoding="utf-8") for path in raw_files)
        assert "HeartBeat" in raw_text
        assert "ResponseCommand" in raw_text


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

    def test_strict_customer_profile_and_orders_use_token_identity(self, client, monkeypatch):
        monkeypatch.setenv("CLERK_AUTH_STRICT", "1")
        client.post(
            "/api/session/sync",
            json={
                "email": "strict.customer@example.com",
                "clerkUserId": "user_customer_strict",
                "displayName": "Strict Customer",
            },
        )
        monkeypatch.setattr("routes.verify_clerk_session_token", lambda authorization: {"sub": "user_customer_strict"})
        headers = {"Authorization": "Bearer customer-token"}

        resp = client.put(
            "/api/customer/profile",
            params={"email": "other.customer@example.com"},
            headers=headers,
            json={
                "name": "Strict Customer",
                "phone": "021-777-0001",
                "whatsapp": "",
                "wechat": "",
                "address": "7 Strict Street, Auckland",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["profile"]["email"] == "strict.customer@example.com"

        resp = client.get("/api/customer/profile", params={"email": "other.customer@example.com"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["profile"]["email"] == "strict.customer@example.com"

        resp = client.post(
            "/api/customer/orders",
            headers=headers,
            data={
                "user": "Strict Customer",
                "phone": "021-777-0001",
                "address": "7 Strict Street, Auckland",
                "serviceType": "一次性割草",
                "requestedDate": "2026-06-25",
                "requestedTime": "09:00",
                "lawnSize": "120",
                "condition": "平整",
                "note": "",
            },
        )
        assert resp.status_code == 200
        order_id = resp.json()["order"]["id"]

        resp = client.get("/api/customer/orders", params={"phone": "021-000-0000"}, headers=headers)
        assert resp.status_code == 200
        orders = resp.json()["orders"]
        assert any(order["id"] == order_id for order in orders)
        assert all(order["phone"] == "021-777-0001" for order in orders)

    def test_strict_customer_cannot_confirm_another_customers_order(self, client, monkeypatch):
        monkeypatch.setenv("CLERK_AUTH_STRICT", "1")
        users = {
            "Bearer customer-one": "user_customer_one",
            "Bearer customer-two": "user_customer_two",
        }

        def fake_verify(authorization):
            return {"sub": users.get(authorization, "")}

        client.post(
            "/api/session/sync",
            json={"email": "one.customer@example.com", "clerkUserId": "user_customer_one", "displayName": "One"},
        )
        client.post(
            "/api/session/sync",
            json={"email": "two.customer@example.com", "clerkUserId": "user_customer_two", "displayName": "Two"},
        )
        monkeypatch.setattr("routes.verify_clerk_session_token", fake_verify)

        client.put(
            "/api/customer/profile",
            headers={"Authorization": "Bearer customer-one"},
            json={"name": "One", "phone": "021-777-1001", "address": "1 One Street, Auckland"},
        )
        client.put(
            "/api/customer/profile",
            headers={"Authorization": "Bearer customer-two"},
            json={"name": "Two", "phone": "021-777-2002", "address": "2 Two Street, Auckland"},
        )
        resp = client.post(
            "/api/customer/orders",
            headers={"Authorization": "Bearer customer-one"},
            data={
                "user": "One",
                "phone": "021-777-1001",
                "address": "1 One Street, Auckland",
                "serviceType": "一次性割草",
                "requestedDate": "2026-06-25",
                "requestedTime": "09:00",
                "lawnSize": "120",
                "condition": "平整",
                "note": "",
            },
        )
        assert resp.status_code == 200
        order_id = resp.json()["order"]["id"]
        client.post(f"/api/orders/{order_id}/quote", json={"price": "100"})

        resp = client.post(
            f"/api/customer/orders/{order_id}/confirm",
            headers={"Authorization": "Bearer customer-two"},
        )
        assert resp.status_code == 403

        resp = client.post(
            f"/api/customer/orders/{order_id}/confirm",
            headers={"Authorization": "Bearer customer-one"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "accepted_by_customer"


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

    def test_business_closure_customer_to_archive(self, client, monkeypatch):
        monkeypatch.setenv("CLERK_AUTH_STRICT", "1")
        users = {
            "Bearer closure-customer": "user_closure_customer",
            "Bearer closure-provider": "user_closure_provider",
        }

        def fake_verify(authorization):
            return {"sub": users.get(authorization, "")}

        client.post(
            "/api/session/sync",
            json={
                "email": "closure.customer@example.com",
                "clerkUserId": "user_closure_customer",
                "displayName": "Closure Customer",
            },
        )
        client.post(
            "/api/session/sync",
            json={
                "email": "zhang.worker@example.com",
                "clerkUserId": "user_closure_provider",
                "displayName": "张师傅",
            },
        )
        client.put(
            "/api/users/role",
            headers={"X-GardenOS-Actor-Email": "haohan6037@gmail.com"},
            json={"email": "zhang.worker@example.com", "role": "server", "status": "active"},
        )
        monkeypatch.setattr("routes.verify_clerk_session_token", fake_verify)

        customer_headers = {"Authorization": "Bearer closure-customer"}
        provider_headers = {"Authorization": "Bearer closure-provider"}

        resp = client.put(
            "/api/customer/profile",
            headers=customer_headers,
            json={
                "name": "Closure Customer",
                "phone": "021-777-3003",
                "address": "3 Closure Street, Auckland",
            },
        )
        assert resp.status_code == 200

        resp = client.post(
            "/api/customer/orders",
            headers=customer_headers,
            data={
                "user": "Closure Customer",
                "phone": "021-777-3003",
                "address": "3 Closure Street, Auckland",
                "serviceType": "一次性割草",
                "requestedDate": "2026-06-26",
                "requestedTime": "10:00",
                "lawnSize": "180",
                "condition": "边角较多",
                "note": "闭环验收订单",
            },
        )
        assert resp.status_code == 200
        order_id = resp.json()["order"]["id"]

        resp = client.post(f"/api/orders/{order_id}/quote", json={"price": "180", "priceNote": "闭环报价"})
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "quoted"

        resp = client.post(f"/api/customer/orders/{order_id}/confirm", headers=customer_headers)
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "accepted_by_customer"

        resp = client.post(f"/api/orders/{order_id}/assign", json={"workerId": "w-001"})
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "assigned"

        resp = client.post(
            f"/api/provider/orders/{order_id}/accept",
            headers=provider_headers,
            json={"email": "zhang.worker@example.com", "note": "可以服务"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "accepted_by_worker"

        resp = client.post(
            f"/api/provider/orders/{order_id}/arrival",
            headers=provider_headers,
            json={"email": "zhang.worker@example.com", "note": "已到场"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "in_service"

        resp = client.post(
            f"/api/provider/orders/{order_id}/evidence",
            headers=provider_headers,
            data={"email": "zhang.worker@example.com", "note": "完工照片"},
            files={"photos": ("closure-before.jpg", b"fake-image", "image/jpeg")},
        )
        assert resp.status_code == 200
        assert len(resp.json()["photos"]) == 1

        resp = client.post(
            f"/api/provider/orders/{order_id}/complete",
            headers=provider_headers,
            json={"email": "zhang.worker@example.com", "note": "已完工"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "pending_quality_review"

        resp = client.post(
            f"/api/orders/{order_id}/quality-review",
            json={"action": "approve", "note": "验收通过"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "completed"

        resp = client.post(
            f"/api/orders/{order_id}/completion",
            json={
                "actualAmount": "180",
                "paymentStatus": "paid",
                "paymentMethod": "manual",
                "paymentReceivedAt": "",
                "paymentNote": "闭环测试收款",
                "settlementStatus": "settled",
                "completionNote": "闭环验收归档",
                "platformShare": "54",
                "workerPayout": "126",
            },
        )
        assert resp.status_code == 200
        archived = resp.json()["order"]
        assert archived["status"] == "completed"
        assert archived["paymentStatus"] == "paid"
        assert archived["settlementStatus"] == "settled"

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


class TestProviderWorkbench:
    """Provider workbench route flow / 服务商工作台路由闭环."""

    def test_provider_can_advance_own_order(self, client, sample_order_data):
        resp = client.post("/api/orders", json=sample_order_data)
        assert resp.status_code == 200
        order_id = resp.json()["order"]["id"]
        client.post(f"/api/orders/{order_id}/quote", json={"price": "120", "priceNote": "测试报价"})
        client.post(f"/api/orders/{order_id}/assign", json={"workerId": "w-001"})

        email = "zhang.worker@example.com"
        resp = client.get("/api/provider/workbench", params={"email": email})
        assert resp.status_code == 200
        assert resp.json()["worker"]["id"] == "w-001"
        assert any(order["id"] == order_id for order in resp.json()["orders"])

        resp = client.post(
            f"/api/provider/orders/{order_id}/accept",
            json={"email": email, "note": "确认接单"},
        )
        assert resp.status_code == 200

        resp = client.post(
            f"/api/provider/orders/{order_id}/arrival",
            json={"email": email, "note": "已到场"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "in_service"

        resp = client.post(
            f"/api/provider/orders/{order_id}/evidence",
            data={"email": email, "note": "服务前照片"},
            files=[("photos", ("before.jpg", b"fake image bytes", "image/jpeg"))],
        )
        assert resp.status_code == 200
        evidence_order = resp.json()["order"]
        assert any("/mowing-platform/uploads/provider/" in item for item in evidence_order["photos"])

        resp = client.post(
            f"/api/provider/orders/{order_id}/complete",
            json={"email": email, "note": "服务完成，照片已回传"},
        )
        assert resp.status_code == 200
        assert resp.json()["order"]["status"] == "pending_quality_review"

    def test_provider_cannot_operate_other_worker_order(self, client):
        resp = client.post(
            "/api/provider/orders/MOW-1003/accept",
            json={"email": "li.worker@example.com", "note": "尝试越权接单"},
        )
        assert resp.status_code == 403

    def test_provider_can_use_verified_clerk_token(self, client, monkeypatch):
        client.post(
            "/api/session/sync",
            json={
                "email": "zhang.worker@example.com",
                "clerkUserId": "user_worker_token",
                "displayName": "张师傅",
            },
        )
        monkeypatch.setattr("routes.verify_clerk_session_token", lambda authorization: {"sub": "user_worker_token"})

        resp = client.get("/api/provider/workbench", headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        assert resp.json()["worker"]["id"] == "w-001"


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
