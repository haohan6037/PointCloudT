"""MQTT monitor for platform management / 平台管理 MQTT 监听."""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from data import ROOT

try:
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover - optional runtime dependency
    mqtt = None

logger = logging.getLogger(__name__)


class PlatformMqttMonitor:
    """Subscribe to robot MQTT topics and persist messages through the active store."""

    def __init__(self, service: Any) -> None:
        self.service = service
        self._client: Any = None
        self._started = False
        self._connected = False
        self._last_error = ""
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._writer_thread: threading.Thread | None = None
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=self._queue_max_size())
        self._queued_count = 0
        self._persisted_count = 0
        self._raw_written_count = 0
        self._dropped_count = 0
        self._last_flush_at = ""

    def settings(self) -> dict[str, Any]:
        topics = [
            item.strip()
            for item in os.getenv("MQTT_TOPICS", "HeartBeat,ResponseCommand,$SYS/broker/log/#").split(",")
            if item.strip()
        ]
        return {
            "enabled": os.getenv("MQTT_MONITOR_ENABLED", "1") == "1",
            "host": os.getenv("MQTT_HOST", "nozomi.proxy.rlwy.net"),
            "port": int(os.getenv("MQTT_PORT", "53239")),
            "username": os.getenv("MQTT_USERNAME", ""),
            "topics": topics,
            "queueMaxSize": self._queue.maxsize,
            "batchSize": self._batch_size(),
            "flushIntervalSeconds": self._flush_interval_seconds(),
            "rawLogDir": str(self._raw_log_dir()),
        }

    def status(self) -> dict[str, Any]:
        settings = self.settings()
        return {
            **settings,
            "dependencyAvailable": mqtt is not None,
            "started": self._started,
            "connected": self._connected,
            "lastError": self._last_error,
            "writerStarted": self._writer_thread is not None and self._writer_thread.is_alive(),
            "queueDepth": self._queue.qsize(),
            "queuedMessages": self._queued_count,
            "persistedMessages": self._persisted_count,
            "rawWrittenMessages": self._raw_written_count,
            "droppedMessages": self._dropped_count,
            "lastFlushAt": self._last_flush_at,
        }

    def start(self) -> bool:
        settings = self.settings()
        if not settings["enabled"]:
            self._last_error = "MQTT monitor disabled by MQTT_MONITOR_ENABLED=0"
            return False
        if mqtt is None:
            self._last_error = "paho-mqtt is not installed"
            return False
        self._ensure_writer()
        with self._lock:
            if self._started:
                return True
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="gardenos-platform-monitor")
            if settings["username"]:
                client.username_pw_set(settings["username"], os.getenv("MQTT_PASSWORD", ""))

            def on_connect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
                self._connected = True
                self._last_error = ""
                for topic in settings["topics"]:
                    client.subscribe(topic)
                logger.info("Platform MQTT monitor connected to %s:%s", settings["host"], settings["port"])

            def on_disconnect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
                self._connected = False

            def on_message(client, userdata, msg):  # noqa: ANN001
                payload = msg.payload.decode("utf-8", errors="replace")
                self.record_received_message(msg.topic, payload, "mqtt")

            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_message = on_message
            try:
                client.connect_async(settings["host"], settings["port"], keepalive=60)
                client.loop_start()
            except Exception as exc:
                self._last_error = str(exc)
                logger.warning("Failed to start platform MQTT monitor: %s", exc)
                return False
            self._client = client
            self._started = True
            return True

    def record_received_message(self, topic: str, payload: str, source: str = "mqtt") -> bool:
        """Queue a received MQTT message without blocking the MQTT callback / 入队即返回."""
        self._ensure_writer()
        item = {
            "topic": topic,
            "payload": payload,
            "source": source,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._dropped_count += 1
            self._last_error = "MQTT message queue is full; newest message dropped"
            logger.warning("MQTT message queue full; dropped message on topic %s", topic)
            return False
        self._queued_count += 1
        return True

    def stop(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.loop_stop()
                self._client.disconnect()
            self._client = None
            self._started = False
            self._connected = False
        self._stop_event.set()
        writer = self._writer_thread
        if writer is not None and writer.is_alive():
            writer.join(timeout=max(1.0, self._flush_interval_seconds() + 0.5))

    @staticmethod
    def _queue_max_size() -> int:
        try:
            return max(100, int(os.getenv("MQTT_QUEUE_MAX_SIZE", "10000")))
        except ValueError:
            return 10000

    @staticmethod
    def _batch_size() -> int:
        try:
            return max(1, int(os.getenv("MQTT_BATCH_SIZE", "500")))
        except ValueError:
            return 500

    @staticmethod
    def _flush_interval_seconds() -> float:
        try:
            return max(0.1, float(os.getenv("MQTT_FLUSH_INTERVAL_SECONDS", "2")))
        except ValueError:
            return 2.0

    @staticmethod
    def _raw_log_dir() -> Path:
        return Path(os.getenv("MQTT_RAW_LOG_DIR", str(ROOT / "data" / "mqtt-raw")))

    def _ensure_writer(self) -> None:
        with self._lock:
            if self._writer_thread is not None and self._writer_thread.is_alive():
                return
            self._stop_event.clear()
            self._writer_thread = threading.Thread(
                target=self._writer_loop,
                name="platform-mqtt-writer",
                daemon=True,
            )
            self._writer_thread.start()

    def _writer_loop(self) -> None:
        batch: list[dict[str, Any]] = []
        last_flush = monotonic()
        while not self._stop_event.is_set() or not self._queue.empty():
            flush_interval = self._flush_interval_seconds()
            try:
                item = self._queue.get(timeout=flush_interval)
            except queue.Empty:
                item = None

            if item is not None:
                self._append_raw_line(item)
                batch.append(item)
                self._queue.task_done()

            enough_items = len(batch) >= self._batch_size()
            enough_time = bool(batch) and monotonic() - last_flush >= flush_interval
            if enough_items or enough_time:
                self._flush_batch(batch)
                batch.clear()
                last_flush = monotonic()

        if batch:
            self._flush_batch(batch)

    def _append_raw_line(self, item: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        path = self._raw_log_dir() / now.strftime("%Y-%m-%d") / f"{now:%H}.ndjson"
        record = {
            "topic": item["topic"],
            "payload": item["payload"],
            "source": item.get("source") or "mqtt",
            "received_at": item.get("received_at") or now.isoformat(),
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            self._raw_written_count += 1
        except OSError as exc:
            self._last_error = f"Failed to write MQTT raw log: {exc}"
            logger.warning("Failed to write MQTT raw log: %s", exc)

    def _flush_batch(self, batch: list[dict[str, Any]]) -> None:
        if not batch:
            return
        try:
            self.service.store.record_mqtt_messages(batch)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._last_error = f"Failed to persist MQTT batch: {exc}"
            logger.warning("Failed to persist MQTT batch: %s", exc)
            return
        self._persisted_count += len(batch)
        self._last_flush_at = datetime.now(timezone.utc).isoformat()
