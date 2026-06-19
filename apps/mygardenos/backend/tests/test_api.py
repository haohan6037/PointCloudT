import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.entities import Device, User

client = TestClient(app)


def _auth_headers_for_user():
    email = f"profile-{int(time.time() * 1000)}@example.com"
    send_res = client.post("/auth/email/request-code", json={"email": email})
    assert send_res.status_code == 200
    code = send_res.json()["debug_code"]

    verify_res = client.post("/auth/email/verify-code", json={"email": email, "code": code})
    assert verify_res.status_code == 200
    verify_token = verify_res.json()["verify_token"]

    set_res = client.post(
        "/auth/password/set",
        json={"verify_token": verify_token, "password": "MyPass123"},
    )
    assert set_res.status_code == 200
    token = set_res.json()["access_token"]
    return email, {"Authorization": f"Bearer {token}"}

# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "MyGardenOS API"

# ── Auth / Dev user ───────────────────────────────────────────────────────────

def test_dev_user():
    res = client.get("/auth/dev-user")
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "demo@example.com"
    assert "id" in data

# ── Profile ───────────────────────────────────────────────────────────────────

def test_get_profile():
    email, headers = _auth_headers_for_user()
    res = client.get("/profile", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == email

def test_update_profile():
    _, headers = _auth_headers_for_user()
    res = client.patch("/profile", json={"username": "TestUser", "gender": "Female"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "TestUser"
    assert data["gender"] == "Female"

# ── Families ──────────────────────────────────────────────────────────────────

def test_list_families():
    _, headers = _auth_headers_for_user()
    res = client.get("/families", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_create_and_dissolve_family():
    _, headers = _auth_headers_for_user()
    res = client.post("/families", json={"name": "Test Family", "address": "123 Test St"}, headers=headers)
    assert res.status_code == 200
    fam = res.json()
    assert fam["name"] == "Test Family"
    fam_id = fam["id"]

    # dissolve
    del_res = client.delete(f"/families/{fam_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "dissolved"

def test_update_family():
    _, headers = _auth_headers_for_user()
    res = client.post("/families", json={"name": "Edit Family"}, headers=headers)
    assert res.status_code == 200
    fam_id = res.json()["id"]

    patch_res = client.patch(f"/families/{fam_id}", json={"address": "456 New Ave"}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["address"] == "456 New Ave"

    client.delete(f"/families/{fam_id}", headers=headers)

def test_update_nonexistent_family():
    _, headers = _auth_headers_for_user()
    res = client.patch("/families/999999", json={"name": "Ghost"}, headers=headers)
    assert res.status_code == 404

def test_dissolve_nonexistent_family():
    _, headers = _auth_headers_for_user()
    res = client.delete("/families/999999", headers=headers)
    assert res.status_code == 404

# ── Devices ───────────────────────────────────────────────────────────────────

def test_search_devices():
    _, headers = _auth_headers_for_user()
    res = client.get("/devices/search", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_list_devices():
    _, headers = _auth_headers_for_user()
    res = client.get("/devices", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_bind_device():
    _, headers = _auth_headers_for_user()
    available = client.get("/devices/search", headers=headers).json()
    assert len(available) > 0, "No unbound devices available for binding test"
    serial = available[0]["serial"]

    res = client.post("/devices/bind", json={"serial": serial}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["serial"] == serial
    assert data["status"] == "online"

def test_bind_nonexistent_device():
    _, headers = _auth_headers_for_user()
    res = client.post("/devices/bind", json={"serial": "DOES-NOT-EXIST-0000"}, headers=headers)
    assert res.status_code == 404

def test_bluetooth_scan_pair_and_status_flow():
    _, headers = _auth_headers_for_user()
    scan_res = client.get("/devices/bluetooth/scan", headers=headers)
    assert scan_res.status_code == 200
    assert isinstance(scan_res.json(), list)

    serial = f"BT-MOWER-{int(time.time() * 1000)}"
    pair_res = client.post(
        "/devices/bluetooth/pair",
        json={
            "serial": serial,
            "peripheral_id": f"BLE-{serial}",
            "name": "Backyard Mower",
            "model": "AN-1600",
        },
        headers=headers,
    )
    assert pair_res.status_code == 200
    paired = pair_res.json()
    assert paired["serial"] == serial
    assert paired["name"] == "Backyard Mower"
    assert paired["status"] == "online"

    status_res = client.get(f"/devices/{paired['id']}/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["serial"] == serial

    patch_res = client.patch(
        f"/devices/{paired['id']}/status",
        json={"status": "mowing", "battery_percent": 87},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "mowing"
    assert patch_res.json()["battery_percent"] == 87

def test_update_device_schedule_persists_for_user_device():
    _, headers = _auth_headers_for_user()
    serial = f"BT-SCHEDULE-{int(time.time() * 1000)}"
    pair_res = client.post(
        "/devices/bluetooth/pair",
        json={"serial": serial, "name": "Schedule Mower", "model": "NBMower"},
        headers=headers,
    )
    assert pair_res.status_code == 200
    device_id = pair_res.json()["id"]

    schedule_res = client.patch(
        f"/devices/{device_id}/schedule",
        json={"schedule_start_time": "09:15", "schedule_end_time": "17:45"},
        headers=headers,
    )
    assert schedule_res.status_code == 200
    assert schedule_res.json()["schedule_start_time"] == "09:15"
    assert schedule_res.json()["schedule_end_time"] == "17:45"

    list_res = client.get("/devices", headers=headers)
    assert list_res.status_code == 200
    saved = next(device for device in list_res.json() if device["id"] == device_id)
    assert saved["schedule_start_time"] == "09:15"
    assert saved["schedule_end_time"] == "17:45"

def test_update_device_schedule_rejects_invalid_time():
    _, headers = _auth_headers_for_user()
    pair_res = client.post(
        "/devices/bluetooth/pair",
        json={"serial": f"BT-BAD-SCHEDULE-{int(time.time() * 1000)}"},
        headers=headers,
    )
    device_id = pair_res.json()["id"]
    res = client.patch(
        f"/devices/{device_id}/schedule",
        json={"schedule_start_time": "25:00", "schedule_end_time": "17:45"},
        headers=headers,
    )
    assert res.status_code == 400

def test_pair_device_rejects_family_user_does_not_belong_to():
    _, owner_headers = _auth_headers_for_user()
    family_res = client.post("/families", json={"name": "Owner Family"}, headers=owner_headers)
    assert family_res.status_code == 200
    family_id = family_res.json()["id"]

    _, other_headers = _auth_headers_for_user()
    res = client.post(
        "/devices/bluetooth/pair",
        json={"serial": f"BT-FORBIDDEN-{int(time.time() * 1000)}", "family_id": family_id},
        headers=other_headers,
    )
    assert res.status_code == 403

def test_pair_device_can_reclaim_legacy_demo_binding():
    _, headers = _auth_headers_for_user()
    serial = f"BT-DEMO-RECLAIM-{int(time.time() * 1000)}"
    override = app.dependency_overrides[get_db]
    db_gen = override()
    db = next(db_gen)
    try:
        demo = db.query(User).filter(User.email == "demo@example.com").first()
        assert demo is not None
        device = Device(serial=serial, name="Legacy Demo Mower", model="NBMower", owner_id=demo.id)
        db.add(device)
        db.commit()
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    pair_res = client.post(
        "/devices/bluetooth/pair",
        json={"serial": serial, "name": "Recovered Mower", "model": "NBMower"},
        headers=headers,
    )
    assert pair_res.status_code == 200
    assert pair_res.json()["serial"] == serial

    list_res = client.get("/devices", headers=headers)
    assert list_res.status_code == 200
    assert any(device["serial"] == serial for device in list_res.json())

# ── Notifications ─────────────────────────────────────────────────────────────

def test_notifications_device():
    res = client.get("/notifications?kind=device")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_notifications_system():
    res = client.get("/notifications?kind=system")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_notifications_read_filter():
    res = client.get("/notifications?kind=device&read=false")
    assert res.status_code == 200

# ── Settings ──────────────────────────────────────────────────────────────────

def test_get_settings():
    res = client.get("/settings")
    assert res.status_code == 200
    data = res.json()
    assert "language" in data
    assert "device_notifications" in data

def test_update_settings():
    res = client.patch("/settings", json={"language": "Chinese", "device_notifications": False})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "Chinese"
    assert data["device_notifications"] is False
    # restore
    client.patch("/settings", json={"language": "English", "device_notifications": True})

# ── Help articles ─────────────────────────────────────────────────────────────

def test_list_help_articles():
    res = client.get("/help/articles")
    assert res.status_code == 200
    articles = res.json()
    assert isinstance(articles, list)
    assert len(articles) > 0

def test_get_help_article_by_slug():
    articles = client.get("/help/articles").json()
    slug = articles[0]["slug"]

    res = client.get(f"/help/articles/{slug}")
    assert res.status_code == 200
    assert res.json()["slug"] == slug

def test_get_nonexistent_article():
    res = client.get("/help/articles/not-a-real-slug")
    assert res.status_code == 404

# ── About ─────────────────────────────────────────────────────────────────────

def test_about():
    res = client.get("/about")
    assert res.status_code == 200
    data = res.json()
    assert data["product"] == "MyGardenOS"
    assert "version" in data
    assert "privacy_policy" in data
    assert "user_agreement" in data


# ── Real auth flow ────────────────────────────────────────────────────────────

def test_email_code_password_auth_flow():
    email = f"authflow-{int(time.time() * 1000)}@example.com"

    # 1) Request code and verify email; first login requires setting password.
    send_res = client.post("/auth/email/request-code", json={"email": email})
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["status"] in {"sent", "debug_only"}
    assert send_data.get("debug_code")

    verify_res = client.post(
        "/auth/email/verify-code",
        json={"email": email, "code": send_data["debug_code"]},
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["verified"] is True
    assert verify_data["next_step"] == "set_password"

    set_res = client.post(
        "/auth/password/set",
        json={"verify_token": verify_data["verify_token"], "password": "MyPass123"},
    )
    assert set_res.status_code == 200
    set_data = set_res.json()
    assert set_data["access_token"]
    assert set_data["user"]["email"] == email

    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {set_data['access_token']}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == email

    # 2) Next login via email+code should require password verification.
    send2_res = client.post("/auth/email/request-code", json={"email": email})
    assert send2_res.status_code == 200
    code2 = send2_res.json()["debug_code"]

    verify2_res = client.post("/auth/email/verify-code", json={"email": email, "code": code2})
    assert verify2_res.status_code == 200
    verify2_data = verify2_res.json()
    assert verify2_data["next_step"] == "verify_password"

    wrong_pw = client.post(
        "/auth/password/verify",
        json={"verify_token": verify2_data["verify_token"], "password": "WrongPass"},
    )
    assert wrong_pw.status_code == 401

    verify_pw = client.post(
        "/auth/password/verify",
        json={"verify_token": verify2_data["verify_token"], "password": "MyPass123"},
    )
    assert verify_pw.status_code == 200
    assert verify_pw.json()["user"]["email"] == email
