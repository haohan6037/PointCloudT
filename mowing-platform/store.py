"""Data store layer / 数据存储层 — InMemoryStore + PostgresStore."""
from __future__ import annotations

import copy
import json
import os
from collections import deque
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from data import ROOT, WORKERS, SEED_ORDERS, timestamp, activity_entry
from models import (
    OrderCreatePayload, WorkerProfilePayload, CompletionPayload, OrderOpsPayload,
    ServiceLogPayload, QualityReviewPayload, ExceptionPayload, OrderUpdatePayload,
)

try:
    import psycopg
except Exception:
    psycopg = None

DEFAULT_CUSTOMER_EMAIL = "helen.chen@example.com"
DEFAULT_CUSTOMER_NAME = "Helen Chen"
DEFAULT_ADMIN_EMAILS = {"haohan6037@gmail.com", "kaiyu.yang@youngproperty.co.nz"}
ROLE_ALIASES = {"provider": "server"}
VALID_USER_ROLES = {"admin", "customer", "server"}
VALID_USER_STATUSES = {"active", "disabled"}


def parse_json_payload(payload: str) -> Any:
    """Parse JSON payload when possible / 尽量解析 JSON payload."""
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def mqtt_message_metadata(topic: str, payload: str, parsed: Any = None) -> dict[str, str]:
    """Extract analysis-friendly MQTT metadata / 提取便于分析的 MQTT 元数据."""
    parsed_value = parsed if parsed is not None else parse_json_payload(payload)
    robot_id = ""
    message_type = topic
    if isinstance(parsed_value, dict):
        robot_id = str(parsed_value.get("robotId") or parsed_value.get("robot_id") or "").strip()
        command = str(parsed_value.get("command") or "").strip()
        if command:
            message_type = command.split(",", 1)[0]
        elif topic == "HeartBeat":
            message_type = "HeartBeat"
        elif topic == "ResponseCommand":
            message_type = "ResponseCommand"
    elif topic.startswith("$SYS/"):
        message_type = "$SYS"
    return {"robotId": robot_id, "messageType": message_type}


def normalize_user_role(role: str) -> str:
    """Normalize public user roles / 统一平台角色命名."""
    normalized = (role or "customer").strip().lower()
    return ROLE_ALIASES.get(normalized, normalized)


def configured_role_for_email(email: str) -> str:
    """Resolve bootstrap role from environment / 从环境变量推断初始角色."""
    normalized = email.strip().lower()
    admin_emails = {
        *DEFAULT_ADMIN_EMAILS,
        *{item.strip().lower() for item in os.getenv("ADMIN_EMAILS", "").split(",") if item.strip()},
    }
    provider_emails = {item.strip().lower() for item in os.getenv("PROVIDER_EMAILS", "").split(",") if item.strip()}
    if normalized in admin_emails:
        return "admin"
    if normalized in provider_emails:
        return "server"
    if normalized in {str(worker.get("email", "")).strip().lower() for worker in WORKERS if worker.get("email")}:
        return "server"
    return "customer"


class InMemoryStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.orders = copy.deepcopy(SEED_ORDERS)
        self.workers = copy.deepcopy(WORKERS)
        self.customers: dict[str, dict[str, Any]] = {
            DEFAULT_CUSTOMER_EMAIL: self._blank_customer_profile(DEFAULT_CUSTOMER_EMAIL, DEFAULT_CUSTOMER_NAME),
        }
        self.mqtt_messages: deque[dict[str, Any]] = deque(maxlen=1000)
        self.users: dict[str, dict[str, Any]] = {
            DEFAULT_CUSTOMER_EMAIL: self._blank_user(DEFAULT_CUSTOMER_EMAIL, DEFAULT_CUSTOMER_NAME),
        }
        for admin_email in sorted(DEFAULT_ADMIN_EMAILS):
            self.users[admin_email] = self._blank_user(admin_email)
        self._next_mqtt_id = 1

    def bootstrap(self) -> dict[str, Any]:
        return {"orders": self.orders, "workers": self.workers}

    @staticmethod
    def _blank_customer_profile(email: str, name: str = "") -> dict[str, Any]:
        return {
            "email": email,
            "name": name,
            "phone": "",
            "whatsapp": "",
            "wechat": "",
            "address": "",
            "created_at": timestamp(),
            "updated_at": timestamp(),
        }

    @staticmethod
    def _blank_user(email: str, display_name: str = "", clerk_user_id: str = "") -> dict[str, Any]:
        role = normalize_user_role(configured_role_for_email(email))
        return {
            "email": email,
            "clerkUserId": clerk_user_id,
            "displayName": display_name,
            "role": role,
            "status": "active",
            "created_at": timestamp(),
            "updated_at": timestamp(),
        }

    def update_worker_availability(self, worker_id: str, available: bool) -> dict[str, Any]:
        for worker in self.workers:
            if worker["id"] == worker_id:
                worker["available"] = available
                return worker
        raise HTTPException(status_code=404, detail="Worker not found")

    def update_worker_profile(self, worker_id: str, payload: WorkerProfilePayload) -> dict[str, Any]:
        for worker in self.workers:
            if worker["id"] == worker_id:
                worker["name"] = payload.name
                if payload.email.strip():
                    worker["email"] = payload.email.strip().lower()
                worker["phone"] = payload.phone
                worker["area"] = payload.area
                worker["approvalStatus"] = payload.approvalStatus
                worker["serviceNote"] = payload.serviceNote
                if payload.lat is not None:
                    worker["lat"] = payload.lat
                if payload.lng is not None:
                    worker["lng"] = payload.lng
                return worker
        raise HTTPException(status_code=404, detail="Worker not found")

    def _next_order_id(self) -> str:
        numbers = []
        for order in self.orders:
            try:
                numbers.append(int(order["id"].split("-")[1]))
            except Exception:
                continue
        next_number = (max(numbers) if numbers else 1000) + 1
        return f"MOW-{next_number}"

    def _find_order(self, order_id: str) -> dict[str, Any]:
        for order in self.orders:
            if order["id"] == order_id:
                return order
        raise HTTPException(status_code=404, detail="Order not found")

    def save_quote(self, order_id: str, price: str, price_note: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        order["price"] = price
        order["priceNote"] = price_note
        if order["status"] == "pending_review":
            order["status"] = "quoted"
        order["updatedAt"] = timestamp()
        order["activity"] = [activity_entry(f"平台保存报价：${price}。"), *order["activity"]]
        return order

    def assign_worker(self, order_id: str, worker_id: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        order["assignedWorkerId"] = worker_id
        order["status"] = "assigned"
        order["updatedAt"] = timestamp()
        name = next((worker["name"] for worker in self.workers if worker["id"] == worker_id), worker_id)
        order["activity"] = [activity_entry(f"平台派单给{name}。"), *order["activity"]]
        return order

    def accept_by_customer(self, order_id: str) -> dict[str, Any]:
        """Customer accepts the quoted price / 客户确认报价."""
        order = self._find_order(order_id)
        if order["status"] != "quoted":
            raise HTTPException(status_code=400, detail="Order must be in quoted status")
        order["status"] = "accepted_by_customer"
        order["paymentStatus"] = "pending"
        order["updatedAt"] = timestamp()
        order["activity"] = [activity_entry("客户已确认报价，等待平台派单。"), *order["activity"]]
        return order

    def reject_by_customer(self, order_id: str) -> dict[str, Any]:
        """Customer rejects the quoted price / 客户拒绝报价."""
        order = self._find_order(order_id)
        if order["status"] != "quoted":
            raise HTTPException(status_code=400, detail="Order must be in quoted status")
        order["status"] = "pending_review"
        order["price"] = ""
        order["priceNote"] = ""
        order["updatedAt"] = timestamp()
        order["activity"] = [activity_entry("客户拒绝报价，订单回到待平台确认。"), *order["activity"]]
        return order

    def accept_order(self, order_id: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        if not order["assignedWorkerId"]:
            raise HTTPException(status_code=400, detail="Order must be assigned first")
        order["status"] = "accepted_by_worker"
        order["updatedAt"] = timestamp()
        name = next(
            (worker["name"] for worker in self.workers if worker["id"] == order["assignedWorkerId"]),
            order["assignedWorkerId"],
        )
        order["activity"] = [activity_entry(f"{name}已确认接单。"), *order["activity"]]
        return order

    def update_order_status(self, order_id: str, status: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        if status == "accepted_by_worker":
            return self.accept_order(order_id)
        if status == "in_service":
            if not order["assignedWorkerId"]:
                raise HTTPException(status_code=400, detail="Order must be assigned first")
            order["status"] = "in_service"
            order["updatedAt"] = timestamp()
            name = next(
                (worker["name"] for worker in self.workers if worker["id"] == order["assignedWorkerId"]),
                order["assignedWorkerId"],
            )
            order["activity"] = [activity_entry(f"{name}开始上门服务。"), *order["activity"]]
            return order
        if status == "pending_quality_review":
            if not order["assignedWorkerId"]:
                raise HTTPException(status_code=400, detail="Order must be assigned first")
            order["status"] = "pending_quality_review"
            order["updatedAt"] = timestamp()
            name = next(
                (worker["name"] for worker in self.workers if worker["id"] == order["assignedWorkerId"]),
                order["assignedWorkerId"],
            )
            order["activity"] = [activity_entry(f"{name}已提交完工，等待平台质量审核。"), *order["activity"]]
            return order
        if status == "completed":
            order["status"] = "completed"
            order["settlementStatus"] = order.get("settlementStatus") or "pending"
            order["updatedAt"] = timestamp()
            order["activity"] = [activity_entry("平台已审核通过，订单进入已完成。"), *order["activity"]]
            return order
        raise HTTPException(status_code=400, detail="Unsupported status")

    def update_order_ops(self, order_id: str, payload: OrderOpsPayload) -> dict[str, Any]:
        order = self._find_order(order_id)
        if payload.priorityLevel not in {"low", "normal", "high", "urgent"}:
            raise HTTPException(status_code=400, detail="Unsupported priority level")
        order["priorityLevel"] = payload.priorityLevel
        order["opsTag"] = payload.opsTag.strip()
        order["updatedAt"] = timestamp()
        order["activity"] = [
            activity_entry(f"运营标记已更新：{payload.priorityLevel} / {payload.opsTag.strip() or '无标签'}。"),
            *order["activity"],
        ]
        return order

    def update_completion(self, order_id: str, payload: CompletionPayload) -> dict[str, Any]:
        order = self._find_order(order_id)
        if order["status"] != "completed":
            raise HTTPException(status_code=400, detail="Only completed orders can be archived")
        if payload.actualAmount:
            try:
                Decimal(payload.actualAmount)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid actual amount") from exc
        if payload.platformShare:
            try:
                Decimal(payload.platformShare)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid platform share") from exc
        if payload.workerPayout:
            try:
                Decimal(payload.workerPayout)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid worker payout") from exc
        if payload.paymentStatus not in {"unpaid", "pending", "paid", "waived"}:
            raise HTTPException(status_code=400, detail="Unsupported payment status")
        if payload.settlementStatus not in {"pending", "settled"}:
            raise HTTPException(status_code=400, detail="Unsupported settlement status")
        order["actualAmount"] = payload.actualAmount.strip()
        order["paymentStatus"] = payload.paymentStatus
        order["paymentMethod"] = payload.paymentMethod.strip()
        order["paymentReceivedAt"] = payload.paymentReceivedAt.strip()
        order["paymentNote"] = payload.paymentNote.strip()
        order["settlementStatus"] = payload.settlementStatus
        order["completionNote"] = payload.completionNote.strip()
        order["platformShare"] = payload.platformShare.strip()
        order["workerPayout"] = payload.workerPayout.strip()
        order["settledAt"] = timestamp() if payload.settlementStatus == "settled" else ""
        order["updatedAt"] = timestamp()
        order["activity"] = [
            activity_entry(f"归档信息已更新，结算状态：{'已结算' if payload.settlementStatus == 'settled' else '待结算'}。"),
            *order["activity"],
        ]
        return order

    def add_service_log(self, order_id: str, payload: ServiceLogPayload) -> dict[str, Any]:
        order = self._find_order(order_id)
        stage_labels = {
            "pre_visit": "上门前确认",
            "arrival": "到场签到",
            "service_note": "服务中记录",
            "completion_followup": "完工回传",
        }
        if payload.stage not in stage_labels:
            raise HTTPException(status_code=400, detail="Unsupported service log stage")
        worker_name = next(
            (worker["name"] for worker in self.workers if worker["id"] == order["assignedWorkerId"]),
            "服务商",
        )
        note = payload.note.strip() or "未填写补充说明。"
        order["updatedAt"] = timestamp()
        order["activity"] = [activity_entry(f"{worker_name}{stage_labels[payload.stage]}：{note}"), *order["activity"]]
        return order

    def append_order_photos(self, order_id: str, photo_urls: list[str], note: str = "") -> dict[str, Any]:
        """Append evidence photos to an order / 向订单追加现场证据照片."""
        order = self._find_order(order_id)
        if not photo_urls:
            raise HTTPException(status_code=400, detail="At least one photo is required")
        order.setdefault("photos", [])
        order["photos"].extend(photo_urls)
        order["updatedAt"] = timestamp()
        note_text = f"：{note.strip()}" if note.strip() else ""
        order["activity"] = [activity_entry(f"服务商上传现场照片 {len(photo_urls)} 张{note_text}。"), *order["activity"]]
        return order

    def submit_quality_review(self, order_id: str, payload: QualityReviewPayload) -> dict[str, Any]:
        order = self._find_order(order_id)
        note = payload.note.strip() or "未填写审核说明。"
        if payload.action == "approve":
            if order["status"] not in {"pending_quality_review", "exception_open"}:
                raise HTTPException(status_code=400, detail="Order is not waiting for quality review")
            order["status"] = "completed"
            order["settlementStatus"] = order.get("settlementStatus") or "pending"
            order["reviewNote"] = note
            order["exceptionResolution"] = order.get("exceptionResolution") or "平台审核通过后关闭异常。"
            order["updatedAt"] = timestamp()
            order["activity"] = [activity_entry(f"平台审核通过：{note}"), *order["activity"]]
            return order
        if payload.action == "rework":
            if order["status"] not in {"pending_quality_review", "exception_open"}:
                raise HTTPException(status_code=400, detail="Order is not waiting for quality review")
            order["status"] = "in_service"
            order["reviewNote"] = note
            order["updatedAt"] = timestamp()
            order["activity"] = [activity_entry(f"平台打回补做：{note}"), *order["activity"]]
            return order
        raise HTTPException(status_code=400, detail="Unsupported quality review action")

    def handle_exception(self, order_id: str, payload: ExceptionPayload) -> dict[str, Any]:
        order = self._find_order(order_id)
        action = payload.action
        issue_type = payload.issueType.strip()
        note = payload.note.strip() or "未填写异常说明。"
        resolution = payload.resolution.strip() or "未填写处理结果。"
        if action == "open":
            order["status"] = "exception_open"
            order["exceptionType"] = issue_type or "现场异常"
            order["exceptionNote"] = note
            order["exceptionResolution"] = ""
            order["updatedAt"] = timestamp()
            order["activity"] = [activity_entry(f"异常上报：{order['exceptionType']}，{note}"), *order["activity"]]
            return order
        if action == "resume":
            if order["status"] != "exception_open":
                raise HTTPException(status_code=400, detail="Order is not in exception flow")
            next_status = payload.nextStatus.strip() or "in_service"
            if next_status not in {"assigned", "accepted_by_worker", "in_service", "pending_quality_review", "completed"}:
                raise HTTPException(status_code=400, detail="Unsupported next status")
            order["status"] = next_status
            order["exceptionResolution"] = resolution
            order["reviewNote"] = resolution if next_status == "completed" else order.get("reviewNote", "")
            if next_status == "completed":
                order["settlementStatus"] = order.get("settlementStatus") or "pending"
            order["updatedAt"] = timestamp()
            order["activity"] = [activity_entry(f"异常处理完成，恢复流转：{resolution}"), *order["activity"]]
            return order
        if action == "close":
            if order["status"] != "exception_open":
                raise HTTPException(status_code=400, detail="Order is not in exception flow")
            order["status"] = "cancelled"
            order["exceptionResolution"] = resolution
            order["updatedAt"] = timestamp()
            order["activity"] = [activity_entry(f"异常关闭订单：{resolution}"), *order["activity"]]
            return order
        raise HTTPException(status_code=400, detail="Unsupported exception action")

    def reassign_worker(self, order_id: str, worker_id: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        old_name = next(
            (worker["name"] for worker in self.workers if worker["id"] == order["assignedWorkerId"]),
            order["assignedWorkerId"] or "未派单",
        )
        order["assignedWorkerId"] = worker_id
        order["status"] = "assigned"
        order["updatedAt"] = timestamp()
        name = next((worker["name"] for worker in self.workers if worker["id"] == worker_id), worker_id)
        order["activity"] = [activity_entry(f"平台改派：{old_name} → {name}。"), *order["activity"]]
        return order

    def cancel_order(self, order_id: str, note: str = "") -> dict[str, Any]:
        order = self._find_order(order_id)
        if order["status"] in {"completed", "cancelled"}:
            raise HTTPException(status_code=400, detail="Cannot cancel a completed or already cancelled order")
        order["status"] = "cancelled"
        order["updatedAt"] = timestamp()
        note_text = f"：{note}" if note.strip() else ""
        order["activity"] = [activity_entry(f"平台取消订单{note_text}。"), *order["activity"]]
        return order

    def reject_order(self, order_id: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        if not order["assignedWorkerId"]:
            raise HTTPException(status_code=400, detail="Order is not assigned to any worker")
        if order["status"] not in {"assigned", "accepted_by_worker"}:
            raise HTTPException(status_code=400, detail="Only assigned or accepted orders can be rejected")
        name = next(
            (worker["name"] for worker in self.workers if worker["id"] == order["assignedWorkerId"]),
            order["assignedWorkerId"],
        )
        order["assignedWorkerId"] = ""
        order["status"] = "quoted"
        order["updatedAt"] = timestamp()
        order["activity"] = [activity_entry(f"{name}拒单，订单重新进入待派单。"), *order["activity"]]
        return order

    def update_order(self, order_id: str, payload: OrderUpdatePayload) -> dict[str, Any]:
        order = self._find_order(order_id)
        changed: list[str] = []
        field_map = [
            ("user", "客户姓名"), ("phone", "联系电话"), ("address", "服务地址"),
            ("serviceType", "服务类型"), ("requestedTime", "期望时间"),
            ("lawnSize", "草坪面积"), ("condition", "现场情况"), ("note", "客户备注"),
        ]
        for attr, label in field_map:
            val = getattr(payload, attr, None)
            if val is not None and val != order.get(attr, ""):
                order[attr] = val
                changed.append(label)
        if changed:
            order["updatedAt"] = timestamp()
            order["activity"] = [activity_entry(f"运营编辑订单：{'、'.join(changed)}。"), *order["activity"]]
        return order

    def save_internal_note(self, order_id: str, note: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        order["internalNote"] = note
        order["updatedAt"] = timestamp()
        order["activity"] = [activity_entry("运营更新内部备注。"), *order["activity"]]
        return order

    # ── Customer profile / 用户资料 ─────────────────────────────────

    def get_customer_profile(self, email: str) -> dict[str, Any] | None:
        """Get customer profile by email / 按邮箱获取用户资料."""
        return self.customers.get(email)

    def save_customer_profile(self, email: str, payload: Any) -> dict[str, Any]:
        """Save customer profile / 保存用户资料."""
        if email not in self.customers:
            self.customers[email] = self._blank_customer_profile(email)
        profile = self.customers[email]
        if payload.name is not None:
            profile["name"] = payload.name
        if payload.phone is not None:
            profile["phone"] = payload.phone
        if payload.whatsapp is not None:
            profile["whatsapp"] = payload.whatsapp
        if payload.wechat is not None:
            profile["wechat"] = payload.wechat
        if payload.address is not None:
            profile["address"] = payload.address
        profile["updated_at"] = timestamp()
        return profile

    def sync_user_session(self, email: str, clerk_user_id: str = "", display_name: str = "") -> dict[str, Any]:
        """Create or update app user from Clerk session / 从 Clerk 会话创建或更新平台用户."""
        if email not in self.users:
            self.users[email] = self._blank_user(email, display_name, clerk_user_id)
        user = self.users[email]
        if clerk_user_id:
            user["clerkUserId"] = clerk_user_id
        if display_name:
            user["displayName"] = display_name
        configured_role = configured_role_for_email(email)
        user["role"] = normalize_user_role(user.get("role", "customer"))
        if user["role"] == "customer" and configured_role != "customer":
            user["role"] = configured_role
        user["updated_at"] = timestamp()
        return user

    def get_user(self, email: str) -> dict[str, Any] | None:
        """Get app user by email / 按邮箱获取平台用户."""
        return self.users.get(email)

    def list_users(self) -> list[dict[str, Any]]:
        """List all app users / 列出全部平台用户."""
        users = [{**item, "role": normalize_user_role(item.get("role", "customer"))} for item in self.users.values()]
        return sorted(users, key=lambda item: (item["role"], item["email"]))

    def get_worker_by_email(self, email: str) -> dict[str, Any] | None:
        """Find a worker profile by login email / 按登录邮箱查找服务商档案."""
        normalized = email.strip().lower()
        return next((worker for worker in self.workers if worker.get("email", "").strip().lower() == normalized), None)

    def list_orders_for_worker(self, worker_id: str) -> list[dict[str, Any]]:
        """List active orders assigned to one worker / 查询分配给某服务商的活跃订单."""
        return [
            order for order in self.orders
            if order.get("assignedWorkerId") == worker_id and order.get("status") != "cancelled"
        ]

    def update_user_role(self, email: str, role: str, status: str = "active") -> dict[str, Any]:
        """Update app user role / 更新平台用户角色."""
        role = normalize_user_role(role)
        if role not in VALID_USER_ROLES:
            raise HTTPException(status_code=400, detail="Unsupported user role")
        if status not in VALID_USER_STATUSES:
            raise HTTPException(status_code=400, detail="Unsupported user status")
        user = self.users.get(email)
        if user is None:
            user = self._blank_user(email)
            self.users[email] = user
        user["role"] = role
        user["status"] = status
        user["updated_at"] = timestamp()
        return user

    def record_mqtt_message(
        self,
        topic: str,
        payload: str,
        source: str = "mqtt",
        received_at: str | None = None,
    ) -> dict[str, Any]:
        """Persist an MQTT message in fallback memory / 在内存模式保存 MQTT 消息."""
        return self.record_mqtt_messages([
            {"topic": topic, "payload": payload, "source": source, "received_at": received_at}
        ])[0]

    def record_mqtt_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Persist a batch of MQTT messages in fallback memory / 批量保存 MQTT 消息到内存."""
        saved: list[dict[str, Any]] = []
        for item in messages:
            payload = str(item["payload"])
            parsed = parse_json_payload(payload)
            metadata = mqtt_message_metadata(str(item["topic"]), payload, parsed)
            message = {
                "id": self._next_mqtt_id,
                "topic": str(item["topic"]),
                "payload": payload,
                "json": parsed,
                "robotId": metadata["robotId"],
                "messageType": metadata["messageType"],
                "source": str(item.get("source") or "mqtt"),
                "receivedAt": item.get("received_at") or timestamp(),
            }
            self._next_mqtt_id += 1
            self.mqtt_messages.appendleft(message)
            saved.append(message)
        return saved

    def list_mqtt_messages(self, limit: int = 100, topic: str = "", q: str = "") -> list[dict[str, Any]]:
        """List MQTT messages from fallback memory / 从内存模式读取 MQTT 消息."""
        normalized_topic = topic.strip()
        query = q.strip().lower()
        items = list(self.mqtt_messages)
        if normalized_topic:
            items = [item for item in items if item["topic"] == normalized_topic]
        if query:
            items = [
                item for item in items
                if query in item["topic"].lower()
                or query in item["payload"].lower()
                or query in item.get("robotId", "").lower()
                or query in item.get("messageType", "").lower()
            ]
        return items[: max(1, min(limit, 500))]

    @staticmethod
    def _try_parse_json(payload: str) -> Any:
        return parse_json_payload(payload)

    def add_demo_order(self) -> dict[str, Any]:
        order = {
            "id": self._next_order_id(),
            "user": "新客户",
            "phone": "021-000-0000",
            "address": "待确认地址, Auckland",
            "serviceType": "一次性割草",
            "requestedTime": "2026-06-13 09:00-12:00",
            "lawnSize": "待确认",
            "condition": "待平台运营确认草坪情况",
            "note": "演示订单，可用于测试报价和派单。",
            "status": "pending_review",
            "priorityLevel": "normal",
            "opsTag": "",
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
            "actualAmount": "",
            "paymentStatus": "unpaid",
            "paymentMethod": "",
            "paymentReceivedAt": "",
            "paymentNote": "",
            "settlementStatus": "pending",
            "completionNote": "",
            "reviewNote": "",
            "exceptionType": "",
            "exceptionNote": "",
            "exceptionResolution": "",
            "platformShare": "",
            "workerPayout": "",
            "settledAt": "",
            "updatedAt": timestamp(),
            "photos": ["客户照片 1", "客户照片 2", "客户照片 3"],
            "activity": [activity_entry("运营新增演示订单。")],
            "internalNote": "",
        }
        self.orders.insert(0, order)
        return order

    def create_order(self, payload: OrderCreatePayload) -> dict[str, Any]:
        order = {
            "id": self._next_order_id(),
            "user": payload.user,
            "phone": payload.phone,
            "address": payload.address,
            "serviceType": payload.serviceType,
            "requestedTime": payload.requestedTime,
            "lawnSize": payload.lawnSize,
            "condition": payload.condition,
            "note": payload.note,
            "status": "pending_review",
            "priorityLevel": "normal",
            "opsTag": "",
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
            "actualAmount": "",
            "paymentStatus": "unpaid",
            "paymentMethod": "",
            "paymentReceivedAt": "",
            "paymentNote": "",
            "settlementStatus": "pending",
            "completionNote": "",
            "reviewNote": "",
            "exceptionType": "",
            "exceptionNote": "",
            "exceptionResolution": "",
            "platformShare": "",
            "workerPayout": "",
            "settledAt": "",
            "updatedAt": timestamp(),
            "photos": ["待上传照片 1", "待上传照片 2", "待上传照片 3"],
            "activity": [activity_entry("运营人员创建订单，等待平台确认报价。")],
            "internalNote": "",
        }
        self.orders.insert(0, order)
        return order



class PostgresStore:
    def __init__(self, dsn: str) -> None:
        if psycopg is None:
            raise RuntimeError("psycopg is not installed")
        self.dsn = dsn
        self.schema_sql = (ROOT / "schema.sql").read_text(encoding="utf-8")

    def _connect(self):
        return psycopg.connect(self.dsn, connect_timeout=3)

    @staticmethod
    def _decode_json_value(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        return json.loads(value or "[]")

    @staticmethod
    def _blank_customer_profile(email: str, name: str = "") -> dict[str, Any]:
        return {
            "email": email,
            "name": name,
            "phone": "",
            "whatsapp": "",
            "wechat": "",
            "address": "",
            "created_at": timestamp(),
            "updated_at": timestamp(),
        }

    @staticmethod
    def _blank_user(email: str, display_name: str = "", clerk_user_id: str = "") -> dict[str, Any]:
        role = normalize_user_role(configured_role_for_email(email))
        return {
            "email": email,
            "clerkUserId": clerk_user_id,
            "displayName": display_name,
            "role": role,
            "status": "active",
            "created_at": timestamp(),
            "updated_at": timestamp(),
        }

    def prepare(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(self.schema_sql)
                cur.execute(
                    """
                    create table if not exists customer_profiles (
                        email text primary key,
                        name text not null default '',
                        phone text not null default '',
                        whatsapp text not null default '',
                        wechat text not null default '',
                        address text not null default '',
                        created_at timestamptz not null default now(),
                        updated_at timestamptz not null default now()
                    )
                    """
                )
                self._upsert_seed_workers(cur)
                cur.execute(
                    """
                    insert into customer_profiles (email, name)
                    values (%s, %s)
                    on conflict (email) do update set
                        name = case
                            when coalesce(nullif(customer_profiles.name, ''), '') = '' then excluded.name
                            else customer_profiles.name
                        end
                    """,
                    (DEFAULT_CUSTOMER_EMAIL, DEFAULT_CUSTOMER_NAME),
                )
                cur.execute(
                    """
                    insert into app_users (email, display_name, role, status)
                    values (%s, %s, %s, 'active')
                    on conflict (email) do update set
                        display_name = case
                            when coalesce(nullif(app_users.display_name, ''), '') = '' then excluded.display_name
                            else app_users.display_name
                        end,
                        role = case
                            when app_users.role = 'customer' and excluded.role <> 'customer' then excluded.role
                            else app_users.role
                        end,
                        updated_at = now()
                    """,
                    (
                        DEFAULT_CUSTOMER_EMAIL,
                        DEFAULT_CUSTOMER_NAME,
                        configured_role_for_email(DEFAULT_CUSTOMER_EMAIL),
                    ),
                )
                for admin_email in sorted(DEFAULT_ADMIN_EMAILS):
                    cur.execute(
                        """
                        insert into app_users (email, display_name, role, status)
                        values (%s, %s, 'admin', 'active')
                        on conflict (email) do update set
                            role = case
                                when app_users.role = 'customer' then 'admin'
                                else app_users.role
                            end,
                            status = 'active',
                            updated_at = now()
                        """,
                        (admin_email, ""),
                    )
                cur.execute("select count(*) from mowing_orders")
                if cur.fetchone()[0] == 0:
                    self._seed_orders(cur)
            conn.commit()

    def _upsert_seed_workers(self, cur) -> None:
        cur.executemany(
            """
            insert into mowing_workers (id, name, email, area, phone, approval_status, service_note, available, lat, lng)
            values (
                %(id)s, %(name)s, %(email)s, %(area)s, %(phone)s, %(approvalStatus)s, %(serviceNote)s, %(available)s, %(lat)s, %(lng)s
            )
            on conflict (id) do update set
                name = case
                    when coalesce(nullif(mowing_workers.name, ''), '') = '' then excluded.name
                    else mowing_workers.name
                end,
                email = case
                    when coalesce(nullif(mowing_workers.email, ''), '') = '' then excluded.email
                    else mowing_workers.email
                end,
                area = case
                    when coalesce(nullif(mowing_workers.area, ''), '') = '' then excluded.area
                    else mowing_workers.area
                end,
                phone = case
                    when coalesce(nullif(mowing_workers.phone, ''), '') = '' then excluded.phone
                    else mowing_workers.phone
                end,
                approval_status = case
                    when coalesce(nullif(mowing_workers.approval_status, ''), '') = '' then excluded.approval_status
                    else mowing_workers.approval_status
                end,
                service_note = case
                    when coalesce(nullif(mowing_workers.service_note, ''), '') = '' then excluded.service_note
                    else mowing_workers.service_note
                end,
                lat = coalesce(excluded.lat, mowing_workers.lat),
                lng = coalesce(excluded.lng, mowing_workers.lng)
            """,
            WORKERS,
        )

    def _seed_orders(self, cur) -> None:
        for order in SEED_ORDERS:
            cur.execute(
                """
                insert into mowing_orders (
                    id, user_name, phone, address, service_type, requested_time, lawn_size,
                    condition_note, customer_note, status, priority_level, ops_tag, quoted_price, price_note,
                    assigned_worker_id, actual_amount, payment_status, payment_method, payment_received_at, payment_note,
                    settlement_status, completion_note, review_note,
                    exception_type, exception_note, exception_resolution,
                    platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                ) values (
                    %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                    %(lawnSize)s, %(condition)s, %(note)s, %(status)s, %(priorityLevel)s, %(opsTag)s, %(quoted_price)s, %(priceNote)s,
                    %(assignedWorkerId)s, %(actual_amount)s, %(paymentStatus)s, %(paymentMethod)s, %(paymentReceivedAt)s, %(paymentNote)s,
                    %(settlementStatus)s, %(completionNote)s, %(reviewNote)s,
                    %(exceptionType)s, %(exceptionNote)s, %(exceptionResolution)s,
                    %(platform_share)s, %(worker_payout)s, %(settledAt)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                )
                """,
                {
                    **order,
                    "quoted_price": Decimal(order["price"]) if order["price"] else None,
                    "assignedWorkerId": order["assignedWorkerId"] or None,
                    "actual_amount": Decimal(order["actualAmount"]) if order["actualAmount"] else None,
                    "paymentReceivedAt": order.get("paymentReceivedAt") or None,
                    "platform_share": Decimal(order["platformShare"]) if order["platformShare"] else None,
                    "worker_payout": Decimal(order["workerPayout"]) if order["workerPayout"] else None,
                    "settledAt": order["settledAt"] or None,
                    "photos_json": json.dumps(order["photos"], ensure_ascii=False),
                    "activity_json": json.dumps(order["activity"], ensure_ascii=False),
                },
            )

    def bootstrap(self) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, user_name, phone, address, service_type, requested_time, lawn_size,
                           condition_note, customer_note, status, priority_level, ops_tag, quoted_price, price_note,
                           assigned_worker_id, actual_amount, payment_status, payment_method, payment_received_at, payment_note,
                           settlement_status, completion_note, review_note,
                           exception_type, exception_note, exception_resolution,
                           platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    from mowing_orders
                    order by updated_at desc, id asc
                    """
                )
                orders = [self._row_to_order(row) for row in cur.fetchall()]
                cur.execute(
                    """
                    select id, name, email, area, phone, approval_status, service_note, available, lat, lng
                    from mowing_workers
                    order by id
                    """
                )
                workers = [self._row_to_worker(row) for row in cur.fetchall()]
        return {"orders": orders, "workers": workers}

    def update_worker_availability(self, worker_id: str, available: bool) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update mowing_workers
                    set available = %s
                    where id = %s
                    returning id, name, email, area, phone, approval_status, service_note, available, lat, lng
                    """,
                    (available, worker_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Worker not found")
            conn.commit()
        return self._row_to_worker(row)

    def update_worker_profile(self, worker_id: str, payload: WorkerProfilePayload) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update mowing_workers
                    set name = %s,
                        phone = %s,
                        email = case when %s <> '' then %s else email end,
                        area = %s,
                        approval_status = %s,
                        service_note = %s,
                        lat = coalesce(%s, lat),
                        lng = coalesce(%s, lng)
                    where id = %s
                    returning id, name, email, area, phone, approval_status, service_note, available, lat, lng
                    """,
                    (
                        payload.name,
                        payload.phone,
                        payload.email.strip().lower(),
                        payload.email.strip().lower(),
                        payload.area,
                        payload.approvalStatus,
                        payload.serviceNote,
                        payload.lat,
                        payload.lng,
                        worker_id,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Worker not found")
            conn.commit()
        return self._row_to_worker(row)

    def update_order_ops(self, order_id: str, payload: OrderOpsPayload) -> dict[str, Any]:
        if payload.priorityLevel not in {"low", "normal", "high", "urgent"}:
            raise HTTPException(status_code=400, detail="Unsupported priority level")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry(f"运营标记已更新：{payload.priorityLevel} / {payload.opsTag.strip() or '无标签'}。"))
                cur.execute(
                    """
                    update mowing_orders
                    set priority_level = %s,
                        ops_tag = %s,
                        updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (payload.priorityLevel, payload.opsTag.strip(), json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def _next_order_id(self) -> str:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select max(nullif(substring(id from 5), '')::int)
                    from mowing_orders
                    where id like 'MOW-%'
                    """
                )
                row = cur.fetchone()
        next_number = (row[0] or 1000) + 1
        return f"MOW-{next_number}"

    def _row_to_order(self, row: tuple[Any, ...]) -> dict[str, Any]:
        photos = self._decode_json_value(row[30])
        activity = self._decode_json_value(row[31])
        return {
            "id": row[0],
            "user": row[1],
            "phone": row[2],
            "address": row[3],
            "serviceType": row[4],
            "requestedTime": row[5],
            "lawnSize": row[6],
            "condition": row[7],
            "note": row[8],
            "status": row[9],
            "priorityLevel": row[10] or "normal",
            "opsTag": row[11] or "",
            "price": str(row[12]) if row[12] is not None else "",
            "priceNote": row[13] or "",
            "assignedWorkerId": row[14] or "",
            "actualAmount": str(row[15]) if row[15] is not None else "",
            "paymentStatus": row[16] or "unpaid",
            "paymentMethod": row[17] or "",
            "paymentReceivedAt": row[18].strftime("%Y-%m-%d %H:%M") if row[18] is not None else "",
            "paymentNote": row[19] or "",
            "settlementStatus": row[20] or "pending",
            "completionNote": row[21] or "",
            "reviewNote": row[22] or "",
            "exceptionType": row[23] or "",
            "exceptionNote": row[24] or "",
            "exceptionResolution": row[25] or "",
            "platformShare": str(row[26]) if row[26] is not None else "",
            "workerPayout": str(row[27]) if row[27] is not None else "",
            "settledAt": row[28].strftime("%Y-%m-%d %H:%M") if row[28] is not None else "",
            "updatedAt": row[29].strftime("%Y-%m-%d %H:%M"),
            "photos": photos,
            "activity": activity,
        }

    @staticmethod
    def _row_to_worker(row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2] or "",
            "area": row[3],
            "phone": row[4] or "",
            "approvalStatus": row[5] or "approved",
            "serviceNote": row[6] or "",
            "available": row[7],
            "lat": float(row[8]) if len(row) > 8 and row[8] is not None else None,
            "lng": float(row[9]) if len(row) > 9 and row[9] is not None else None,
        }

    def save_quote(self, order_id: str, price: str, price_note: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry(f"平台保存报价：${price}。"))
                status = "quoted" if row[1] == "pending_review" else row[1]
                cur.execute(
                    """
                    update mowing_orders
                    set quoted_price = %s, price_note = %s, status = %s, updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (Decimal(price), price_note, status, json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def assign_worker(self, order_id: str, worker_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select name from mowing_workers where id = %s", (worker_id,))
                worker = cur.fetchone()
                if worker is None:
                    raise HTTPException(status_code=400, detail="Worker not found")
                cur.execute("select activity_json from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry(f"平台派单给{worker[0]}。"))
                cur.execute(
                    """
                    update mowing_orders
                    set assigned_worker_id = %s, status = 'assigned', updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (worker_id, json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def accept_by_customer(self, order_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if row[1] != "quoted":
                    raise HTTPException(status_code=400, detail="Order must be in quoted status")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry("客户已确认报价，等待平台派单。"))
                cur.execute(
                    """
                    update mowing_orders
                    set status = 'accepted_by_customer',
                        payment_status = 'pending',
                        updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def reject_by_customer(self, order_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if row[1] != "quoted":
                    raise HTTPException(status_code=400, detail="Order must be in quoted status")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry("客户拒绝报价，订单回到待平台确认。"))
                cur.execute(
                    """
                    update mowing_orders
                    set status = 'pending_review',
                        quoted_price = null,
                        price_note = '',
                        payment_status = 'unpaid',
                        updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def accept_order(self, order_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select o.activity_json, w.name
                    from mowing_orders o
                    left join mowing_workers w on w.id = o.assigned_worker_id
                    where o.id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if row[1] is None:
                    raise HTTPException(status_code=400, detail="Order must be assigned first")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry(f"{row[1]}已确认接单。"))
                cur.execute(
                    """
                    update mowing_orders
                    set status = 'accepted_by_worker', updated_at = now(), activity_json = %s
                    where id = %s
                    """,
                    (json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def update_order_status(self, order_id: str, status: str) -> dict[str, Any]:
        if status == "accepted_by_worker":
            return self.accept_order(order_id)
        status_activity = {
            "in_service": "开始上门服务。",
            "pending_quality_review": "已提交完工，等待平台质量审核。",
            "completed": "平台已审核通过，订单进入已完成。",
        }
        if status not in status_activity:
            raise HTTPException(status_code=400, detail="Unsupported status")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select o.activity_json, w.name, o.assigned_worker_id
                    from mowing_orders o
                    left join mowing_workers w on w.id = o.assigned_worker_id
                    where o.id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if row[2] is None:
                    raise HTTPException(status_code=400, detail="Order must be assigned first")
                worker_name = row[1] or row[2]
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry(f"{worker_name}{status_activity[status]}"))
                cur.execute(
                    """
                    update mowing_orders
                    set status = %s,
                        settlement_status = case when %s = 'completed' then coalesce(settlement_status, 'pending') else settlement_status end,
                        updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (status, status, json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def submit_quality_review(self, order_id: str, payload: QualityReviewPayload) -> dict[str, Any]:
        action = payload.action
        note = payload.note.strip() or "未填写审核说明。"
        if action not in {"approve", "rework"}:
            raise HTTPException(status_code=400, detail="Unsupported quality review action")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if row[1] not in {"pending_quality_review", "exception_open"}:
                    raise HTTPException(status_code=400, detail="Order is not waiting for quality review")
                activity = self._decode_json_value(row[0])
                if action == "approve":
                    activity.insert(0, activity_entry(f"平台审核通过：{note}"))
                    cur.execute(
                        """
                        update mowing_orders
                        set status = 'completed',
                            settlement_status = coalesce(settlement_status, 'pending'),
                            review_note = %s,
                            updated_at = now(),
                            activity_json = %s
                        where id = %s
                        """,
                        (note, json.dumps(activity, ensure_ascii=False), order_id),
                    )
                else:
                    activity.insert(0, activity_entry(f"平台打回补做：{note}"))
                    cur.execute(
                        """
                        update mowing_orders
                        set status = 'in_service',
                            review_note = %s,
                            updated_at = now(),
                            activity_json = %s
                        where id = %s
                        """,
                        (note, json.dumps(activity, ensure_ascii=False), order_id),
                    )
            conn.commit()
        return self.get_order(order_id)

    def handle_exception(self, order_id: str, payload: ExceptionPayload) -> dict[str, Any]:
        action = payload.action
        issue_type = payload.issueType.strip() or "现场异常"
        note = payload.note.strip() or "未填写异常说明。"
        resolution = payload.resolution.strip() or "未填写处理结果。"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                current_status = row[1]
                if action == "open":
                    activity.insert(0, activity_entry(f"异常上报：{issue_type}，{note}"))
                    cur.execute(
                        """
                        update mowing_orders
                        set status = 'exception_open',
                            exception_type = %s,
                            exception_note = %s,
                            exception_resolution = '',
                            updated_at = now(),
                            activity_json = %s
                        where id = %s
                        """,
                        (issue_type, note, json.dumps(activity, ensure_ascii=False), order_id),
                    )
                elif action == "resume":
                    if current_status != "exception_open":
                        raise HTTPException(status_code=400, detail="Order is not in exception flow")
                    next_status = payload.nextStatus.strip() or "in_service"
                    if next_status not in {"assigned", "accepted_by_worker", "in_service", "pending_quality_review", "completed"}:
                        raise HTTPException(status_code=400, detail="Unsupported next status")
                    activity.insert(0, activity_entry(f"异常处理完成，恢复流转：{resolution}"))
                    cur.execute(
                        """
                        update mowing_orders
                        set status = %s,
                            review_note = case when %s = 'completed' then %s else review_note end,
                            settlement_status = case when %s = 'completed' then coalesce(settlement_status, 'pending') else settlement_status end,
                            exception_resolution = %s,
                            updated_at = now(),
                            activity_json = %s
                        where id = %s
                        """,
                        (
                            next_status,
                            next_status,
                            resolution,
                            next_status,
                            resolution,
                            json.dumps(activity, ensure_ascii=False),
                            order_id,
                        ),
                    )
                elif action == "close":
                    if current_status != "exception_open":
                        raise HTTPException(status_code=400, detail="Order is not in exception flow")
                    activity.insert(0, activity_entry(f"异常关闭订单：{resolution}"))
                    cur.execute(
                        """
                        update mowing_orders
                        set status = 'cancelled',
                            exception_resolution = %s,
                            updated_at = now(),
                            activity_json = %s
                        where id = %s
                        """,
                        (resolution, json.dumps(activity, ensure_ascii=False), order_id),
                    )
                else:
                    raise HTTPException(status_code=400, detail="Unsupported exception action")
            conn.commit()
        return self.get_order(order_id)

    def reassign_worker(self, order_id: str, worker_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select name from mowing_workers where id = %s",
                    (worker_id,),
                )
                worker = cur.fetchone()
                if worker is None:
                    raise HTTPException(status_code=400, detail="Worker not found")
                cur.execute(
                    """
                    select activity_json, coalesce(assigned_worker_id, ''),
                           coalesce((select name from mowing_workers where id = mowing_orders.assigned_worker_id), '未派单')
                    from mowing_orders where id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                old_name = row[2] if row[1] else "未派单"
                activity.insert(0, activity_entry(f"平台改派：{old_name} → {worker[0]}。"))
                cur.execute(
                    """
                    update mowing_orders
                    set assigned_worker_id = %s, status = 'assigned', updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (worker_id, json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def cancel_order(self, order_id: str, note: str = "") -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if row[1] in {"completed", "cancelled"}:
                    raise HTTPException(status_code=400, detail="Cannot cancel a completed or already cancelled order")
                activity = self._decode_json_value(row[0])
                note_text = f"：{note}" if note.strip() else ""
                activity.insert(0, activity_entry(f"平台取消订单{note_text}。"))
                cur.execute(
                    """
                    update mowing_orders
                    set status = 'cancelled', updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def reject_order(self, order_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select activity_json, status, coalesce(assigned_worker_id, ''),
                           coalesce((select name from mowing_workers where id = mowing_orders.assigned_worker_id), '')
                    from mowing_orders where id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if not row[2]:
                    raise HTTPException(status_code=400, detail="Order is not assigned to any worker")
                if row[1] not in {"assigned", "accepted_by_worker"}:
                    raise HTTPException(status_code=400, detail="Only assigned or accepted orders can be rejected")
                activity = self._decode_json_value(row[0])
                worker_name = row[3] or row[2]
                activity.insert(0, activity_entry(f"{worker_name}拒单，订单重新进入待派单。"))
                cur.execute(
                    """
                    update mowing_orders
                    set assigned_worker_id = null, status = 'quoted', updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def update_completion(self, order_id: str, payload: CompletionPayload) -> dict[str, Any]:
        if payload.actualAmount:
            try:
                actual_amount = Decimal(payload.actualAmount)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid actual amount") from exc
        else:
            actual_amount = None
        if payload.platformShare:
            try:
                platform_share = Decimal(payload.platformShare)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid platform share") from exc
        else:
            platform_share = None
        if payload.workerPayout:
            try:
                worker_payout = Decimal(payload.workerPayout)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid worker payout") from exc
        else:
            worker_payout = None
        if payload.paymentStatus not in {"unpaid", "pending", "paid", "waived"}:
            raise HTTPException(status_code=400, detail="Unsupported payment status")
        if payload.settlementStatus not in {"pending", "settled"}:
            raise HTTPException(status_code=400, detail="Unsupported settlement status")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                if row[1] != "completed":
                    raise HTTPException(status_code=400, detail="Only completed orders can be archived")
                activity = self._decode_json_value(row[0])
                activity.insert(
                    0,
                    activity_entry(f"归档信息已更新，结算状态：{'已结算' if payload.settlementStatus == 'settled' else '待结算'}。"),
                )
                cur.execute(
                    """
                    update mowing_orders
                    set actual_amount = %s,
                        payment_status = %s,
                        payment_method = %s,
                        payment_received_at = case
                            when %s <> '' then %s::timestamptz
                            when %s = 'paid' and payment_received_at is null then now()
                            else payment_received_at
                        end,
                        payment_note = %s,
                        settlement_status = %s,
                        completion_note = %s,
                        platform_share = %s,
                        worker_payout = %s,
                        settled_at = case when %s = 'settled' then now() else null end,
                        updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (
                        actual_amount,
                        payload.paymentStatus,
                        payload.paymentMethod.strip(),
                        payload.paymentReceivedAt.strip(),
                        payload.paymentReceivedAt.strip(),
                        payload.paymentStatus,
                        payload.paymentNote.strip(),
                        payload.settlementStatus,
                        payload.completionNote.strip(),
                        platform_share,
                        worker_payout,
                        payload.settlementStatus,
                        json.dumps(activity, ensure_ascii=False),
                        order_id,
                    ),
                )
            conn.commit()
        return self.get_order(order_id)

    def add_service_log(self, order_id: str, payload: ServiceLogPayload) -> dict[str, Any]:
        stage_labels = {
            "pre_visit": "上门前确认",
            "arrival": "到场签到",
            "service_note": "服务中记录",
            "completion_followup": "完工回传",
        }
        if payload.stage not in stage_labels:
            raise HTTPException(status_code=400, detail="Unsupported service log stage")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select o.activity_json, w.name, o.assigned_worker_id
                    from mowing_orders o
                    left join mowing_workers w on w.id = o.assigned_worker_id
                    where o.id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                worker_name = row[1] or row[2] or "服务商"
                note = payload.note.strip() or "未填写补充说明。"
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry(f"{worker_name}{stage_labels[payload.stage]}：{note}"))
                cur.execute(
                    """
                    update mowing_orders
                    set updated_at = now(),
                        activity_json = %s
                    where id = %s
                    """,
                    (json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def append_order_photos(self, order_id: str, photo_urls: list[str], note: str = "") -> dict[str, Any]:
        """Append evidence photos to an order / 向订单追加现场证据照片."""
        if not photo_urls:
            raise HTTPException(status_code=400, detail="At least one photo is required")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select photos_json, activity_json from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                photos = self._decode_json_value(row[0])
                activity = self._decode_json_value(row[1])
                photos.extend(photo_urls)
                note_text = f"：{note.strip()}" if note.strip() else ""
                activity.insert(0, activity_entry(f"服务商上传现场照片 {len(photo_urls)} 张{note_text}。"))
                cur.execute(
                    """
                    update mowing_orders
                    set photos_json = %s,
                        activity_json = %s,
                        updated_at = now()
                    where id = %s
                    """,
                    (json.dumps(photos, ensure_ascii=False), json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    def update_order(self, order_id: str, payload: OrderUpdatePayload) -> dict[str, Any]:
        col_map = {
            "user": "user_name", "phone": "phone", "address": "address",
            "serviceType": "service_type", "requestedTime": "requested_time",
            "lawnSize": "lawn_size", "condition": "condition_note", "note": "customer_note",
        }
        label_map = {
            "user": "客户姓名", "phone": "联系电话", "address": "服务地址",
            "serviceType": "服务类型", "requestedTime": "期望时间",
            "lawnSize": "草坪面积", "condition": "现场情况", "note": "客户备注",
        }
        set_parts: list[str] = []
        vals: list[Any] = []
        changed: list[str] = []
        for attr, col in col_map.items():
            val = getattr(payload, attr, None)
            if val is not None:
                set_parts.append(f"{col} = %s")
                vals.append(val)
                changed.append(label_map[attr])
        if not changed:
            return self.get_order(order_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select activity_json from mowing_orders where id = %s", (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry(f"运营编辑订单：{'、'.join(changed)}。"))
                vals.extend([json.dumps(activity, ensure_ascii=False), order_id])
                set_parts.extend(["updated_at = now()", "activity_json = %s"])
                cur.execute(
                    f"update mowing_orders set {', '.join(set_parts)} where id = %s",
                    vals,
                )
            conn.commit()
        return self.get_order(order_id)

    def save_internal_note(self, order_id: str, note: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select activity_json from mowing_orders where id = %s", (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                activity.insert(0, activity_entry("运营更新内部备注。"))
                cur.execute(
                    """
                    update mowing_orders
                    set internal_note = %s, updated_at = now(), activity_json = %s
                    where id = %s
                    """,
                    (note, json.dumps(activity, ensure_ascii=False), order_id),
                )
            conn.commit()
        return self.get_order(order_id)

    # ── Customer profile / 用户资料 ─────────────────────────────────

    @staticmethod
    def _row_to_customer_profile(row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "email": row[0],
            "name": row[1] or "",
            "phone": row[2] or "",
            "whatsapp": row[3] or "",
            "wechat": row[4] or "",
            "address": row[5] or "",
            "created_at": row[6].strftime("%Y-%m-%d %H:%M"),
            "updated_at": row[7].strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def _row_to_app_user(row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "email": row[0],
            "clerkUserId": row[1] or "",
            "displayName": row[2] or "",
            "role": normalize_user_role(row[3] or "customer"),
            "status": row[4] or "active",
            "created_at": row[5].strftime("%Y-%m-%d %H:%M"),
            "updated_at": row[6].strftime("%Y-%m-%d %H:%M"),
        }

    def get_customer_profile(self, email: str) -> dict[str, Any] | None:
        """Get customer profile by email / 按邮箱获取用户资料."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select email, name, phone, whatsapp, wechat, address, created_at, updated_at
                    from customer_profiles
                    where email = %s
                    """,
                    (email,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_customer_profile(row)

    def save_customer_profile(self, email: str, payload: Any) -> dict[str, Any]:
        """Save customer profile / 保存用户资料."""
        current = self.get_customer_profile(email) or self._blank_customer_profile(email)
        fields = {
            "name": payload.name if payload.name is not None else current["name"],
            "phone": payload.phone if payload.phone is not None else current["phone"],
            "whatsapp": payload.whatsapp if payload.whatsapp is not None else current["whatsapp"],
            "wechat": payload.wechat if payload.wechat is not None else current["wechat"],
            "address": payload.address if payload.address is not None else current["address"],
        }
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into customer_profiles (
                        email, name, phone, whatsapp, wechat, address, created_at, updated_at
                    ) values (
                        %s, %s, %s, %s, %s, %s, now(), now()
                    )
                    on conflict (email) do update set
                        name = %s,
                        phone = %s,
                        whatsapp = %s,
                        wechat = %s,
                        address = %s,
                        updated_at = now()
                    returning email, name, phone, whatsapp, wechat, address, created_at, updated_at
                    """,
                    (
                        email,
                        fields["name"],
                        fields["phone"],
                        fields["whatsapp"],
                        fields["wechat"],
                        fields["address"],
                        fields["name"],
                        fields["phone"],
                        fields["whatsapp"],
                        fields["wechat"],
                        fields["address"],
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return self._row_to_customer_profile(row)

    def sync_user_session(self, email: str, clerk_user_id: str = "", display_name: str = "") -> dict[str, Any]:
        """Create or update app user from Clerk session / 从 Clerk 会话创建或更新平台用户."""
        role = configured_role_for_email(email)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into app_users (
                        email, clerk_user_id, display_name, role, status, created_at, updated_at
                    ) values (
                        %s, %s, %s, %s, 'active', now(), now()
                    )
                    on conflict (email) do update set
                        clerk_user_id = case
                            when excluded.clerk_user_id <> '' then excluded.clerk_user_id
                            else app_users.clerk_user_id
                        end,
                        display_name = case
                            when excluded.display_name <> '' then excluded.display_name
                            else app_users.display_name
                        end,
                        role = case
                            when app_users.role = 'customer' and excluded.role <> 'customer' then excluded.role
                            else app_users.role
                        end,
                        updated_at = now()
                    returning email, clerk_user_id, display_name, role, status, created_at, updated_at
                    """,
                    (email, clerk_user_id, display_name, role),
                )
                row = cur.fetchone()
            conn.commit()
        return self._row_to_app_user(row)

    def get_user(self, email: str) -> dict[str, Any] | None:
        """Get app user by email / 按邮箱获取平台用户."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select email, clerk_user_id, display_name, role, status, created_at, updated_at
                    from app_users
                    where email = %s
                    """,
                    (email,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_app_user(row)

    def list_users(self) -> list[dict[str, Any]]:
        """List all app users / 列出全部平台用户."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select email, clerk_user_id, display_name, role, status, created_at, updated_at
                    from app_users
                    order by role asc, email asc
                    """
                )
                rows = cur.fetchall()
        return [self._row_to_app_user(row) for row in rows]

    def get_worker_by_email(self, email: str) -> dict[str, Any] | None:
        """Find a worker profile by login email / 按登录邮箱查找服务商档案."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, name, email, area, phone, approval_status, service_note, available, lat, lng
                    from mowing_workers
                    where lower(email) = lower(%s)
                    """,
                    (email.strip(),),
                )
                row = cur.fetchone()
        return self._row_to_worker(row) if row else None

    def list_orders_for_worker(self, worker_id: str) -> list[dict[str, Any]]:
        """List active orders assigned to one worker / 查询分配给某服务商的活跃订单."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, user_name, phone, address, service_type, requested_time, lawn_size,
                           condition_note, customer_note, status, priority_level, ops_tag, quoted_price, price_note,
                           assigned_worker_id, actual_amount, payment_status, payment_method, payment_received_at, payment_note,
                           settlement_status, completion_note, review_note,
                           exception_type, exception_note, exception_resolution,
                           platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    from mowing_orders
                    where assigned_worker_id = %s and status <> 'cancelled'
                    order by updated_at desc, id asc
                    """,
                    (worker_id,),
                )
                rows = cur.fetchall()
        return [self._row_to_order(row) for row in rows]

    def update_user_role(self, email: str, role: str, status: str = "active") -> dict[str, Any]:
        """Update app user role / 更新平台用户角色."""
        role = normalize_user_role(role)
        if role not in VALID_USER_ROLES:
            raise HTTPException(status_code=400, detail="Unsupported user role")
        if status not in VALID_USER_STATUSES:
            raise HTTPException(status_code=400, detail="Unsupported user status")
        current = self.get_user(email) or self._blank_user(email)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into app_users (
                        email, clerk_user_id, display_name, role, status, created_at, updated_at
                    ) values (
                        %s, %s, %s, %s, %s, now(), now()
                    )
                    on conflict (email) do update set
                        clerk_user_id = case
                            when excluded.clerk_user_id <> '' then excluded.clerk_user_id
                            else app_users.clerk_user_id
                        end,
                        display_name = case
                            when excluded.display_name <> '' then excluded.display_name
                            else app_users.display_name
                        end,
                        role = excluded.role,
                        status = excluded.status,
                        updated_at = now()
                    returning email, clerk_user_id, display_name, role, status, created_at, updated_at
                    """,
                    (
                        email,
                        current["clerkUserId"],
                        current["displayName"],
                        role,
                        status,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return self._row_to_app_user(row)

    def record_mqtt_message(
        self,
        topic: str,
        payload: str,
        source: str = "mqtt",
        received_at: str | None = None,
    ) -> dict[str, Any]:
        """Persist an MQTT message / 持久化 MQTT 消息."""
        return self.record_mqtt_messages([
            {"topic": topic, "payload": payload, "source": source, "received_at": received_at}
        ])[0]

    def record_mqtt_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Persist MQTT messages in one transaction / 单事务批量持久化 MQTT 消息."""
        saved: list[dict[str, Any]] = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                for item in messages:
                    payload = str(item["payload"])
                    parsed = parse_json_payload(payload)
                    metadata = mqtt_message_metadata(str(item["topic"]), payload, parsed)
                    cur.execute(
                        """
                        insert into mqtt_messages (
                            topic, payload, payload_json, robot_id, message_type, source, received_at
                        )
                        values (%s, %s, %s, %s, %s, %s, coalesce(%s::timestamptz, now()))
                        returning id, topic, payload, payload_json, robot_id, message_type, source, received_at
                        """,
                        (
                            str(item["topic"]),
                            payload,
                            json.dumps(parsed, ensure_ascii=False) if parsed is not None else None,
                            metadata["robotId"],
                            metadata["messageType"],
                            str(item.get("source") or "mqtt"),
                            item.get("received_at"),
                        ),
                    )
                    saved.append(self._row_to_mqtt_message(cur.fetchone()))
            conn.commit()
        return saved

    def list_mqtt_messages(self, limit: int = 100, topic: str = "", q: str = "") -> list[dict[str, Any]]:
        """List persisted MQTT messages / 读取持久化 MQTT 消息."""
        limit = max(1, min(limit, 500))
        where: list[str] = []
        params: list[Any] = []
        if topic.strip():
            where.append("topic = %s")
            params.append(topic.strip())
        if q.strip():
            where.append("(topic ilike %s or payload ilike %s or robot_id ilike %s or message_type ilike %s)")
            needle = f"%{q.strip()}%"
            params.extend([needle, needle, needle, needle])
        where_sql = f"where {' and '.join(where)}" if where else ""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    select id, topic, payload, payload_json, robot_id, message_type, source, received_at
                    from mqtt_messages
                    {where_sql}
                    order by received_at desc, id desc
                    limit %s
                    """,
                    (*params, limit),
                )
                rows = cur.fetchall()
        return [self._row_to_mqtt_message(row) for row in rows]

    @staticmethod
    def _try_parse_json(payload: str) -> Any:
        return parse_json_payload(payload)

    @staticmethod
    def _row_to_mqtt_message(row: tuple[Any, ...]) -> dict[str, Any]:
        payload_json = row[3]
        if isinstance(payload_json, str):
            try:
                payload_json = json.loads(payload_json)
            except json.JSONDecodeError:
                payload_json = None
        return {
            "id": row[0],
            "topic": row[1],
            "payload": row[2],
            "json": payload_json,
            "robotId": row[4],
            "messageType": row[5],
            "source": row[6],
            "receivedAt": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
        }

    def add_demo_order(self) -> dict[str, Any]:
        order = {
            "id": self._next_order_id(),
            "user": "新客户",
            "phone": "021-000-0000",
            "address": "待确认地址, Auckland",
            "serviceType": "一次性割草",
            "requestedTime": "2026-06-13 09:00-12:00",
            "lawnSize": "待确认",
            "condition": "待平台运营确认草坪情况",
            "note": "演示订单，可用于测试报价和派单。",
            "status": "pending_review",
            "priorityLevel": "normal",
            "opsTag": "",
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
            "actualAmount": "",
            "paymentStatus": "unpaid",
            "paymentMethod": "",
            "paymentReceivedAt": "",
            "paymentNote": "",
            "settlementStatus": "pending",
            "completionNote": "",
            "reviewNote": "",
            "exceptionType": "",
            "exceptionNote": "",
            "exceptionResolution": "",
            "platformShare": "",
            "workerPayout": "",
            "settledAt": "",
            "updatedAt": timestamp(),
            "photos": ["客户照片 1", "客户照片 2", "客户照片 3"],
            "activity": ["运营新增演示订单。"],
        }
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into mowing_orders (
                        id, user_name, phone, address, service_type, requested_time, lawn_size,
                        condition_note, customer_note, status, priority_level, ops_tag, quoted_price, price_note,
                        assigned_worker_id, actual_amount, payment_status, payment_method, payment_received_at, payment_note,
                        settlement_status, completion_note, review_note,
                        exception_type, exception_note, exception_resolution,
                        platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    ) values (
                        %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                        %(lawnSize)s, %(condition)s, %(note)s, %(status)s, %(priorityLevel)s, %(opsTag)s, null, %(priceNote)s,
                        %(assignedWorkerId)s, %(actual_amount)s, %(paymentStatus)s, %(paymentMethod)s, %(paymentReceivedAt)s, %(paymentNote)s,
                        %(settlementStatus)s, %(completionNote)s, %(reviewNote)s,
                        %(exceptionType)s, %(exceptionNote)s, %(exceptionResolution)s,
                        %(platform_share)s, %(worker_payout)s, %(settledAt)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                    )
                    """,
                    {
                        **order,
                        "assignedWorkerId": None,
                        "actual_amount": None,
                        "paymentReceivedAt": None,
                        "platform_share": None,
                        "worker_payout": None,
                        "settledAt": None,
                        "photos_json": json.dumps(order["photos"], ensure_ascii=False),
                        "activity_json": json.dumps(order["activity"], ensure_ascii=False),
                    },
                )
            conn.commit()
        return order

    def create_order(self, payload: OrderCreatePayload) -> dict[str, Any]:
        order = {
            "id": self._next_order_id(),
            "user": payload.user,
            "phone": payload.phone,
            "address": payload.address,
            "serviceType": payload.serviceType,
            "requestedTime": payload.requestedTime,
            "lawnSize": payload.lawnSize,
            "condition": payload.condition,
            "note": payload.note,
            "status": "pending_review",
            "priorityLevel": "normal",
            "opsTag": "",
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
            "actualAmount": "",
            "paymentStatus": "unpaid",
            "paymentMethod": "",
            "paymentReceivedAt": "",
            "paymentNote": "",
            "settlementStatus": "pending",
            "completionNote": "",
            "reviewNote": "",
            "exceptionType": "",
            "exceptionNote": "",
            "exceptionResolution": "",
            "platformShare": "",
            "workerPayout": "",
            "settledAt": "",
            "updatedAt": timestamp(),
            "photos": ["待上传照片 1", "待上传照片 2", "待上传照片 3"],
            "activity": ["运营人员创建订单，等待平台确认报价。"],
        }
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into mowing_orders (
                        id, user_name, phone, address, service_type, requested_time, lawn_size,
                        condition_note, customer_note, status, priority_level, ops_tag, quoted_price, price_note,
                        assigned_worker_id, actual_amount, payment_status, payment_method, payment_received_at, payment_note,
                        settlement_status, completion_note, review_note,
                        exception_type, exception_note, exception_resolution,
                        platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    ) values (
                        %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                        %(lawnSize)s, %(condition)s, %(note)s, %(status)s, %(priorityLevel)s, %(opsTag)s, null, %(priceNote)s,
                        null, %(actual_amount)s, %(paymentStatus)s, %(paymentMethod)s, %(paymentReceivedAt)s, %(paymentNote)s,
                        %(settlementStatus)s, %(completionNote)s, %(reviewNote)s,
                        %(exceptionType)s, %(exceptionNote)s, %(exceptionResolution)s,
                        %(platform_share)s, %(worker_payout)s, %(settledAt)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                    )
                    """,
                    {
                        **order,
                        "actual_amount": None,
                        "paymentReceivedAt": None,
                        "platform_share": None,
                        "worker_payout": None,
                        "settledAt": None,
                        "photos_json": json.dumps(order["photos"], ensure_ascii=False),
                        "activity_json": json.dumps(order["activity"], ensure_ascii=False),
                    },
                )
            conn.commit()
        return order

    def get_order(self, order_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, user_name, phone, address, service_type, requested_time, lawn_size,
                           condition_note, customer_note, status, priority_level, ops_tag, quoted_price, price_note,
                           assigned_worker_id, actual_amount, payment_status, payment_method, payment_received_at, payment_note,
                           settlement_status, completion_note, review_note,
                           exception_type, exception_note, exception_resolution,
                           platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    from mowing_orders
                    where id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
        return self._row_to_order(row)


def build_dsn() -> str | None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    host = os.getenv("PGHOST", "127.0.0.1")
    port = os.getenv("PGPORT", "5433")
    database = os.getenv("PGDATABASE", "MyGardenOSManagementSyetem")
    user = os.getenv("PGUSER") or os.getenv("USER")
    password = os.getenv("PGPASSWORD")
    if not user:
        return None
    auth = user if not password else f"{user}:{password}"
    return f"postgresql://{auth}@{host}:{port}/{database}"
