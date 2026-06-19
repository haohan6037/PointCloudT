import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Optional

from app.database import SessionLocal
from app.models.entities import Device

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

logger = logging.getLogger(__name__)

_messages: deque[dict[str, Any]] = deque(maxlen=80)
_client: Optional["mqtt.Client"] = None
_started = False
_lock = threading.Lock()


def mqtt_settings() -> dict[str, Any]:
    return {
        "enabled": os.getenv("MQTT_MONITOR_ENABLED", "1") == "1",
        "host": os.getenv("MQTT_HOST", "nozomi.proxy.rlwy.net"),
        "port": int(os.getenv("MQTT_PORT", "53239")),
        "username": os.getenv("MQTT_USERNAME", ""),
        "topics": ["HeartBeat", "ResponseCommand", "$SYS/broker/log/#"],
    }


def recent_messages() -> list[dict[str, Any]]:
    with _lock:
        return list(_messages)


def clear_recent_messages() -> dict[str, int]:
    with _lock:
        count = len(_messages)
        _messages.clear()
    return {"cleared": count}


def record_message(topic: str, payload: str, source: str = "mqtt") -> dict[str, Any]:
    parsed: Any = None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        parsed = None

    message = {
        "topic": topic,
        "payload": payload,
        "json": parsed,
        "source": source,
        "received_at": datetime.utcnow().isoformat() + "Z",
    }
    with _lock:
        _messages.appendleft(message)

    if topic == "HeartBeat" and isinstance(parsed, dict):
        _update_device_from_heartbeat(parsed)

    return message


def publish_test_heartbeat(robot_id: str = "LOCAL-TEST") -> dict[str, Any]:
    payload = json.dumps(
        {
            "robotId": robot_id,
            "ip": "127.0.0.1",
            "system": 1,
            "checkState": 1,
            "unlock": 1,
            "mode": 0,
            "pause": 0,
            "error": 0,
            "power": 88,
            "productModel": "NBMower",
        },
        separators=(",", ":"),
    )
    if _client is not None:
        try:
            _client.publish("HeartBeat", payload)
            return {"published": True, "message": record_message("HeartBeat", payload, "local-test")}
        except Exception as exc:
            logger.warning("Failed to publish test heartbeat: %s", exc)
    return {"published": False, "message": record_message("HeartBeat", payload, "local-test")}


def publish_robot_command(robot_id: str, command: str) -> dict[str, Any]:
    robot_id = robot_id.strip()
    command = command.strip()
    if not robot_id:
        raise ValueError("robot_id is required")
    if not command:
        raise ValueError("command is required")

    command_code = str(int(time.time() * 1000))
    topic = f"RobotCommand/{robot_id}"
    payload = json.dumps(
        {
            "robotId": robot_id,
            "commandCode": command_code,
            "command": command,
        },
        separators=(",", ":"),
    )
    if _client is not None:
        try:
            info = _client.publish(topic, payload)
            info.wait_for_publish(timeout=3)
            return {
                "published": info.is_published(),
                "topic": topic,
                "payload": payload,
                "commandCode": command_code,
                "message": record_message(topic, payload, "local-command"),
            }
        except Exception as exc:
            logger.warning("Failed to publish robot command: %s", exc)

    return {
        "published": False,
        "topic": topic,
        "payload": payload,
        "commandCode": command_code,
        "message": record_message(topic, payload, "local-command"),
    }


def start_mqtt_monitor() -> bool:
    global _client, _started
    settings = mqtt_settings()
    if not settings["enabled"]:
        return False
    if mqtt is None:
        logger.warning("paho-mqtt is not installed; MQTT monitor is disabled")
        return False
    if _started:
        return True

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mygardenos-backend-monitor")
    if settings["username"]:
        client.username_pw_set(settings["username"], os.getenv("MQTT_PASSWORD", ""))

    def on_connect(client, userdata, flags, reason_code, properties):
        logger.info("MQTT monitor connected to %s:%s: %s", settings["host"], settings["port"], reason_code)
        for topic in settings["topics"]:
            client.subscribe(topic)

    def on_message(client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="replace")
        record_message(msg.topic, payload)

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect_async(settings["host"], settings["port"], keepalive=60)
        client.loop_start()
    except Exception as exc:
        logger.warning("Failed to start MQTT monitor: %s", exc)
        return False

    _client = client
    _started = True
    return True


def _update_device_from_heartbeat(payload: dict[str, Any]) -> None:
    robot_id = str(payload.get("robotId") or "").strip()
    if not robot_id:
        return

    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.serial == robot_id).first()
        if not device:
            device = Device(
                serial=robot_id,
                name="NBMower",
                model=str(payload.get("productModel") or "NBMower"),
                status="online",
            )
            db.add(device)
            db.flush()

        device.status = "online"
        device.last_seen_at = datetime.utcnow()
        power = payload.get("power")
        if isinstance(power, (int, float)):
            device.battery_percent = max(0, min(100, int(power)))
        product_model = payload.get("productModel")
        if product_model:
            device.model = str(product_model)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to update device from heartbeat: %s", exc)
    finally:
        db.close()
