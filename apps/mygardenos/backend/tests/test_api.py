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

# ── Properties / maps / zones ─────────────────────────────────────────────────

def test_property_map_zone_and_dock_flow():
    _, headers = _auth_headers_for_user()
    property_res = client.post(
        "/properties",
        json={
            "name": "Backyard test site",
            "address": "123 Garden Road",
            "latitude": -36.8485,
            "longitude": 174.7633,
        },
        headers=headers,
    )
    assert property_res.status_code == 200
    garden_property = property_res.json()
    assert garden_property["name"] == "Backyard test site"
    assert garden_property["coordinate_system"] == "GOS-MAP-XY"

    map_res = client.post(
        f"/properties/{garden_property['id']}/maps",
        json={
            "map_type": "point_cloud_top_view",
            "image_url": "/maps/backyard-top-view.png",
            "coordinate_transform": {"scale": 0.05, "origin": {"x": 0, "y": 0}},
        },
        headers=headers,
    )
    assert map_res.status_code == 200
    garden_map = map_res.json()
    assert garden_map["property_id"] == garden_property["id"]
    assert garden_map["coordinate_transform"]["scale"] == 0.05

    zone_res = client.post(
        f"/maps/{garden_map['id']}/zones",
        json={
            "name": "Rear lawn",
            "zone_type": "WORK_AREA",
            "polygon_coordinates": [
                {"x": 0, "y": 0, "lat": -36.8485, "lng": 174.7633},
                {"x": 12, "y": 0},
                {"x": 12, "y": 8},
                {"x": 0, "y": 8},
            ],
            "metadata": {"mow_allowed": True, "rtk_required": True},
        },
        headers=headers,
    )
    assert zone_res.status_code == 200
    work_zone = zone_res.json()
    assert work_zone["zone_type"] == "WORK_AREA"
    assert len(work_zone["polygon_coordinates"]) == 4

    no_go_res = client.post(
        f"/maps/{garden_map['id']}/zones",
        json={
            "name": "Tree base",
            "zone_type": "NO_GO",
            "polygon_coordinates": [
                {"x": 4, "y": 3},
                {"x": 5, "y": 3},
                {"x": 5, "y": 4},
            ],
        },
        headers=headers,
    )
    assert no_go_res.status_code == 200

    dock_res = client.post(
        f"/maps/{garden_map['id']}/docks",
        json={
            "position": {"x": 1, "y": 1},
            "heading": 90,
            "related_zone_id": work_zone["id"],
            "network_available": True,
        },
        headers=headers,
    )
    assert dock_res.status_code == 200
    assert dock_res.json()["position"]["x"] == 1
    assert dock_res.json()["related_zone_id"] == work_zone["id"]

    path_res = client.post(
        f"/maps/{garden_map['id']}/paths/generate",
        json={
            "work_zone_id": work_zone["id"],
            "no_go_zone_ids": [no_go_res.json()["id"]],
            "dock_id": dock_res.json()["id"],
            "blade_width": 1.0,
            "overlap_ratio": 0.0,
            "path_angle": 0,
        },
        headers=headers,
    )
    assert path_res.status_code == 200
    path = path_res.json()
    assert path["map_id"] == garden_map["id"]
    assert path["work_zone_id"] == work_zone["id"]
    assert path["no_go_zone_ids"] == [no_go_res.json()["id"]]
    assert path["dock_id"] == dock_res.json()["id"]
    assert path["version"] == 1
    assert path["estimated_distance"] > 0
    assert len(path["path_points"]) > 2
    assert path["path_points"][0] == {"x": 1.0, "y": 1.0, "lat": None, "lng": None}
    assert path["path_points"][-1] == {"x": 1.0, "y": 1.0, "lat": None, "lng": None}

    task_res = client.post(
        f"/maps/{garden_map['id']}/tasks",
        json={"path_id": path["id"], "work_zone_id": work_zone["id"]},
        headers=headers,
    )
    assert task_res.status_code == 200
    task = task_res.json()
    assert task["status"] == "WAITING_CUSTOMER_CONFIRMATION"
    assert task["customer_confirmation_status"] == "pending"

    early_dispatch = client.post(f"/tasks/{task['id']}/dispatch", headers=headers)
    assert early_dispatch.status_code == 409

    confirm_res = client.post(
        f"/tasks/{task['id']}/customer-confirm",
        json={
            "yard_cleared": True,
            "allowed_start_time": "09:00",
            "allowed_end_time": "12:30",
        },
        headers=headers,
    )
    assert confirm_res.status_code == 200
    confirmed_task = confirm_res.json()
    assert confirmed_task["status"] == "SCHEDULED"
    assert confirmed_task["customer_confirmation_status"] == "confirmed"

    dispatch_res = client.post(f"/tasks/{task['id']}/dispatch", headers=headers)
    assert dispatch_res.status_code == 200
    assert dispatch_res.json()["status"] == "DISPATCHED"

    heartbeat_res = client.post(
        "/robots/SIM-MOWER-001/heartbeat",
        json={
            "task_id": task["id"],
            "position": {"x": 3, "y": 1},
            "battery_level": 86,
            "task_status": "RUNNING",
            "current_path_index": 3,
            "rtk_status": {
                "fix_type": "RTK_FIXED",
                "accuracy": 0.02,
                "is_reliable": True,
                "allowed_to_work": True,
            },
            "network_status": "online",
        },
        headers=headers,
    )
    assert heartbeat_res.status_code == 200
    assert heartbeat_res.json()["robot_identifier"] == "SIM-MOWER-001"
    assert heartbeat_res.json()["task_id"] == task["id"]

    rtk_lost_res = client.post(
        "/robots/SIM-MOWER-001/heartbeat",
        json={
            "task_id": task["id"],
            "position": {"x": 4, "y": 1},
            "battery_level": 84,
            "task_status": "RUNNING",
            "current_path_index": 4,
            "rtk_status": {
                "fix_type": "NONE",
                "accuracy": 99,
                "is_reliable": False,
                "allowed_to_work": False,
            },
            "network_status": "online",
        },
        headers=headers,
    )
    assert rtk_lost_res.status_code == 200

    task_after_heartbeat = client.get(f"/maps/{garden_map['id']}/tasks", headers=headers).json()[0]
    assert task_after_heartbeat["status"] == "PAUSED"
    assert task_after_heartbeat["current_path_index"] == 4
    assert task_after_heartbeat["progress_percent"] > 0

    telemetry_res = client.get("/robots/SIM-MOWER-001/telemetry", headers=headers)
    assert telemetry_res.status_code == 200
    assert len(telemetry_res.json()) == 2

    events_res = client.get(f"/tasks/{task['id']}/events", headers=headers)
    assert events_res.status_code == 200
    assert [event["event_type"] for event in events_res.json()] == [
        "TASK_CREATED",
        "CUSTOMER_CONFIRMED",
        "TASK_DISPATCHED",
        "ROBOT_RUNNING",
        "RTK_UNRELIABLE",
    ]

    assert len(client.get("/properties", headers=headers).json()) >= 1
    assert len(client.get(f"/properties/{garden_property['id']}/maps", headers=headers).json()) == 1
    assert len(client.get(f"/maps/{garden_map['id']}/zones", headers=headers).json()) == 2
    assert len(client.get(f"/maps/{garden_map['id']}/docks", headers=headers).json()) == 1
    assert len(client.get(f"/maps/{garden_map['id']}/paths", headers=headers).json()) == 1
    assert len(client.get(f"/maps/{garden_map['id']}/tasks", headers=headers).json()) == 1

def test_zone_requires_three_polygon_points():
    _, headers = _auth_headers_for_user()
    property_res = client.post("/properties", json={"name": "Invalid zone site"}, headers=headers)
    garden_property = property_res.json()
    map_res = client.post(f"/properties/{garden_property['id']}/maps", json={}, headers=headers)
    garden_map = map_res.json()

    res = client.post(
        f"/maps/{garden_map['id']}/zones",
        json={
            "name": "Bad zone",
            "zone_type": "WORK_AREA",
            "polygon_coordinates": [{"x": 0, "y": 0}, {"x": 1, "y": 1}],
        },
        headers=headers,
    )
    assert res.status_code == 400

def test_path_generation_validates_work_zone_type():
    _, headers = _auth_headers_for_user()
    property_res = client.post("/properties", json={"name": "Path validation site"}, headers=headers)
    garden_property = property_res.json()
    map_res = client.post(f"/properties/{garden_property['id']}/maps", json={}, headers=headers)
    garden_map = map_res.json()
    no_go_res = client.post(
        f"/maps/{garden_map['id']}/zones",
        json={
            "name": "Cannot mow here",
            "zone_type": "NO_GO",
            "polygon_coordinates": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}],
        },
        headers=headers,
    )
    assert no_go_res.status_code == 200

    res = client.post(
        f"/maps/{garden_map['id']}/paths/generate",
        json={"work_zone_id": no_go_res.json()["id"]},
        headers=headers,
    )
    assert res.status_code == 400

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
