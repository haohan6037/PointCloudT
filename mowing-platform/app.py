from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    import psycopg
except Exception:  # pragma: no cover - import failure handled at runtime
    psycopg = None


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def activity_entry(message: str) -> str:
    return f"{timestamp()} | {message}"


WORKERS = [
    {
        "id": "w-001",
        "name": "张师傅",
        "area": "North Shore",
        "phone": "021-900-1001",
        "approvalStatus": "approved",
        "serviceNote": "擅长大面积主体割草后的边缘收尾，适合北岸独立屋。",
        "available": True,
    },
    {
        "id": "w-002",
        "name": "李师傅",
        "area": "Mt Eden / Epsom",
        "phone": "021-900-1002",
        "approvalStatus": "approved",
        "serviceNote": "擅长规则草坪和花坛边人工修整，沟通响应快。",
        "available": True,
    },
    {
        "id": "w-003",
        "name": "王师傅",
        "area": "Howick / Botany",
        "phone": "021-900-1003",
        "approvalStatus": "probation",
        "serviceNote": "当前以东区订单为主，复杂院落需要平台先复核照片。",
        "available": False,
    },
    {
        "id": "w-004",
        "name": "陈师傅",
        "area": "Henderson / Westgate",
        "phone": "021-900-1004",
        "approvalStatus": "approved",
        "serviceNote": "西区订单经验较多，树下和墙边补刀处理稳定。",
        "available": True,
    },
]

SEED_ORDERS = [
    {
        "id": "MOW-1001",
        "user": "Helen Chen",
        "phone": "021-000-1001",
        "address": "16 Pounamu Place, Auckland",
        "serviceType": "一次性割草",
        "requestedTime": "2026-06-10 09:00-12:00",
        "lawnSize": "约 220 平方米",
        "condition": "前院规则，后院树多，靠围栏处边缘复杂",
        "note": "门在左侧小路，院内有一只小狗，服务前请电话确认。",
        "status": "pending_review",
        "priorityLevel": "high",
        "opsTag": "树下补刀",
        "price": "",
        "priceNote": "",
        "assignedWorkerId": "",
        "actualAmount": "",
        "settlementStatus": "pending",
        "completionNote": "",
        "reviewNote": "",
        "exceptionType": "",
        "exceptionNote": "",
        "exceptionResolution": "",
        "platformShare": "",
        "workerPayout": "",
        "settledAt": "",
        "updatedAt": "2026-06-08 16:30",
        "photos": ["前院参考", "后院树下", "围栏边缘"],
        "activity": ["用户提交订单，等待平台确认价格和时间。"],
    },
    {
        "id": "MOW-1002",
        "user": "Michael Lee",
        "phone": "021-000-1002",
        "address": "88 Landscape Road, Mt Eden",
        "serviceType": "定期割草预约",
        "requestedTime": "2026-06-11 13:00-16:00",
        "lawnSize": "约 160 平方米",
        "condition": "草坪较平整，花坛边需要人工修整",
        "note": "希望每两周一次，第一次服务后确认长期价格。",
        "status": "quoted",
        "priorityLevel": "normal",
        "opsTag": "定期客户",
        "price": "95",
        "priceNote": "规则草坪，含花坛边人工修整。",
        "assignedWorkerId": "",
        "actualAmount": "",
        "settlementStatus": "pending",
        "completionNote": "",
        "reviewNote": "",
        "exceptionType": "",
        "exceptionNote": "",
        "exceptionResolution": "",
        "platformShare": "",
        "workerPayout": "",
        "settledAt": "",
        "updatedAt": "2026-06-08 15:20",
        "photos": ["入口照片", "主草坪", "花坛边"],
        "activity": ["平台完成报价：$95。", "等待用户确认或运营继续派单。"],
    },
    {
        "id": "MOW-1003",
        "user": "Sarah Wang",
        "phone": "021-000-1003",
        "address": "21 Pine Street, Albany",
        "serviceType": "一次性割草",
        "requestedTime": "2026-06-10 14:00-17:00",
        "lawnSize": "约 300 平方米",
        "condition": "后院面积大，边角多，机器人适合处理主体区域",
        "note": "后门密码已通过短信发送给客服。",
        "status": "assigned",
        "priorityLevel": "urgent",
        "opsTag": "大院复杂边角",
        "price": "145",
        "priceNote": "面积较大，包含较多边角收尾。",
        "assignedWorkerId": "w-001",
        "actualAmount": "",
        "settlementStatus": "pending",
        "completionNote": "",
        "reviewNote": "",
        "exceptionType": "",
        "exceptionNote": "",
        "exceptionResolution": "",
        "platformShare": "",
        "workerPayout": "",
        "settledAt": "",
        "updatedAt": "2026-06-08 14:45",
        "photos": ["前院", "大面积后院", "角落区域"],
        "activity": ["平台完成报价：$145。", "订单已派给张师傅。"],
    },
    {
        "id": "MOW-1004",
        "user": "David Smith",
        "phone": "021-000-1004",
        "address": "5 Garden Lane, Henderson",
        "serviceType": "一次性割草",
        "requestedTime": "2026-06-12 10:00-12:00",
        "lawnSize": "约 120 平方米",
        "condition": "小块草坪，墙边和树下需要人工处理",
        "note": "客户强调树下区域要修整干净。",
        "status": "accepted_by_worker",
        "priorityLevel": "normal",
        "opsTag": "树下精修",
        "price": "85",
        "priceNote": "小面积，人工精细收尾占比较高。",
        "assignedWorkerId": "w-004",
        "actualAmount": "",
        "settlementStatus": "pending",
        "completionNote": "",
        "reviewNote": "",
        "exceptionType": "",
        "exceptionNote": "",
        "exceptionResolution": "",
        "platformShare": "",
        "workerPayout": "",
        "settledAt": "",
        "updatedAt": "2026-06-08 13:05",
        "photos": ["入口", "树下", "墙边"],
        "activity": ["平台完成报价：$85。", "订单已派给陈师傅。", "陈师傅已确认接单。"],
    },
    {
        "id": "MOW-1005",
        "user": "Anna Brown",
        "phone": "021-000-1005",
        "address": "42 Valley View Road, Howick",
        "serviceType": "一次性割草",
        "requestedTime": "2026-06-09 09:00-11:00",
        "lawnSize": "约 260 平方米",
        "condition": "草较高，可能需要额外处理",
        "note": "客户临时改期，等待平台重新确认。",
        "status": "cancelled",
        "priorityLevel": "low",
        "opsTag": "待改期",
        "price": "130",
        "priceNote": "草较高，原报价含额外处理。",
        "assignedWorkerId": "w-003",
        "actualAmount": "",
        "settlementStatus": "pending",
        "completionNote": "",
        "reviewNote": "",
        "exceptionType": "",
        "exceptionNote": "",
        "exceptionResolution": "",
        "platformShare": "",
        "workerPayout": "",
        "settledAt": "",
        "updatedAt": "2026-06-08 11:40",
        "photos": ["草况", "入口", "侧边"],
        "activity": ["平台完成报价：$130。", "原订单已取消，等待用户重新预约。"],
    },
]


class QuotePayload(BaseModel):
    price: str = Field(min_length=1)
    priceNote: str = ""


class AssignPayload(BaseModel):
    workerId: str = Field(min_length=1)


class OrderCreatePayload(BaseModel):
    user: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    address: str = Field(min_length=1)
    serviceType: str = Field(min_length=1)
    requestedTime: str = Field(min_length=1)
    lawnSize: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    note: str = ""


class WorkerAvailabilityPayload(BaseModel):
    available: bool


class WorkerProfilePayload(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    area: str = Field(min_length=1)
    approvalStatus: str = Field(min_length=1)
    serviceNote: str = ""


class OrderStatusPayload(BaseModel):
    status: str = Field(min_length=1)


class CompletionPayload(BaseModel):
    actualAmount: str = ""
    settlementStatus: str = Field(min_length=1)
    completionNote: str = ""
    platformShare: str = ""
    workerPayout: str = ""


class OrderOpsPayload(BaseModel):
    priorityLevel: str = Field(min_length=1)
    opsTag: str = ""


class ServiceLogPayload(BaseModel):
    stage: str = Field(min_length=1)
    note: str = ""


class QualityReviewPayload(BaseModel):
    action: str = Field(min_length=1)
    note: str = ""


class ExceptionPayload(BaseModel):
    action: str = Field(min_length=1)
    issueType: str = ""
    note: str = ""
    resolution: str = ""
    nextStatus: str = ""


@dataclass
class StoreStatus:
    mode: str
    database_enabled: bool
    error: str | None = None


class InMemoryStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.orders = copy.deepcopy(SEED_ORDERS)
        self.workers = copy.deepcopy(WORKERS)

    def bootstrap(self) -> dict[str, Any]:
        return {"orders": self.orders, "workers": self.workers}

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
                worker["phone"] = payload.phone
                worker["area"] = payload.area
                worker["approvalStatus"] = payload.approvalStatus
                worker["serviceNote"] = payload.serviceNote
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
        if payload.settlementStatus not in {"pending", "settled"}:
            raise HTTPException(status_code=400, detail="Unsupported settlement status")
        order["actualAmount"] = payload.actualAmount.strip()
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
        return psycopg.connect(self.dsn, connect_timeout=3, sslmode="disable")

    @staticmethod
    def _decode_json_value(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        return json.loads(value or "[]")

    def prepare(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(self.schema_sql)
                self._upsert_seed_workers(cur)
                cur.execute("select count(*) from mowing_orders")
                if cur.fetchone()[0] == 0:
                    self._seed_orders(cur)
            conn.commit()

    def _upsert_seed_workers(self, cur) -> None:
        cur.executemany(
            """
            insert into mowing_workers (id, name, area, phone, approval_status, service_note, available)
            values (
                %(id)s, %(name)s, %(area)s, %(phone)s, %(approvalStatus)s, %(serviceNote)s, %(available)s
            )
            on conflict (id) do update set
                name = case
                    when coalesce(nullif(mowing_workers.name, ''), '') = '' then excluded.name
                    else mowing_workers.name
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
                end
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
                    assigned_worker_id, actual_amount, settlement_status, completion_note, review_note,
                    exception_type, exception_note, exception_resolution,
                    platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                ) values (
                    %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                    %(lawnSize)s, %(condition)s, %(note)s, %(status)s, %(priorityLevel)s, %(opsTag)s, %(quoted_price)s, %(priceNote)s,
                    %(assignedWorkerId)s, %(actual_amount)s, %(settlementStatus)s, %(completionNote)s, %(reviewNote)s,
                    %(exceptionType)s, %(exceptionNote)s, %(exceptionResolution)s,
                    %(platform_share)s, %(worker_payout)s, %(settledAt)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                )
                """,
                {
                    **order,
                    "quoted_price": Decimal(order["price"]) if order["price"] else None,
                    "assignedWorkerId": order["assignedWorkerId"] or None,
                    "actual_amount": Decimal(order["actualAmount"]) if order["actualAmount"] else None,
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
                           assigned_worker_id, actual_amount, settlement_status, completion_note, review_note,
                           exception_type, exception_note, exception_resolution,
                           platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    from mowing_orders
                    order by updated_at desc, id asc
                    """
                )
                orders = [self._row_to_order(row) for row in cur.fetchall()]
                cur.execute(
                    """
                    select id, name, area, phone, approval_status, service_note, available
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
                    returning id, name, area, phone, approval_status, service_note, available
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
                        area = %s,
                        approval_status = %s,
                        service_note = %s
                    where id = %s
                    returning id, name, area, phone, approval_status, service_note, available
                    """,
                    (
                        payload.name,
                        payload.phone,
                        payload.area,
                        payload.approvalStatus,
                        payload.serviceNote,
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
        photos = self._decode_json_value(row[26])
        activity = self._decode_json_value(row[27])
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
            "settlementStatus": row[16] or "pending",
            "completionNote": row[17] or "",
            "reviewNote": row[18] or "",
            "exceptionType": row[19] or "",
            "exceptionNote": row[20] or "",
            "exceptionResolution": row[21] or "",
            "platformShare": str(row[22]) if row[22] is not None else "",
            "workerPayout": str(row[23]) if row[23] is not None else "",
            "settledAt": row[24].strftime("%Y-%m-%d %H:%M") if row[24] is not None else "",
            "updatedAt": row[25].strftime("%Y-%m-%d %H:%M"),
            "photos": photos,
            "activity": activity,
        }

    @staticmethod
    def _row_to_worker(row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "name": row[1],
            "area": row[2],
            "phone": row[3] or "",
            "approvalStatus": row[4] or "approved",
            "serviceNote": row[5] or "",
            "available": row[6],
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
                        assigned_worker_id, actual_amount, settlement_status, completion_note, review_note,
                        exception_type, exception_note, exception_resolution,
                        platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    ) values (
                        %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                        %(lawnSize)s, %(condition)s, %(note)s, %(status)s, %(priorityLevel)s, %(opsTag)s, null, %(priceNote)s,
                        %(assignedWorkerId)s, %(actual_amount)s, %(settlementStatus)s, %(completionNote)s, %(reviewNote)s,
                        %(exceptionType)s, %(exceptionNote)s, %(exceptionResolution)s,
                        %(platform_share)s, %(worker_payout)s, %(settledAt)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                    )
                    """,
                    {
                        **order,
                        "assignedWorkerId": None,
                        "actual_amount": None,
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
                        assigned_worker_id, actual_amount, settlement_status, completion_note, review_note,
                        exception_type, exception_note, exception_resolution,
                        platform_share, worker_payout, settled_at, updated_at, photos_json, activity_json
                    ) values (
                        %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                        %(lawnSize)s, %(condition)s, %(note)s, %(status)s, %(priorityLevel)s, %(opsTag)s, null, %(priceNote)s,
                        null, %(actual_amount)s, %(settlementStatus)s, %(completionNote)s, %(reviewNote)s,
                        %(exceptionType)s, %(exceptionNote)s, %(exceptionResolution)s,
                        %(platform_share)s, %(worker_payout)s, %(settledAt)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                    )
                    """,
                    {
                        **order,
                        "actual_amount": None,
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
                           assigned_worker_id, actual_amount, settlement_status, completion_note, review_note,
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


class PlatformService:
    def __init__(self) -> None:
        self.memory = InMemoryStore()
        self.status = StoreStatus(mode="fallback", database_enabled=False, error="No PostgreSQL connection available")
        self.store: InMemoryStore | PostgresStore = self.memory
        dsn = build_dsn()
        if dsn:
            self.status.database_enabled = True
            try:
                db_store = PostgresStore(dsn)
                db_store.prepare()
                self.store = db_store
                self.status.mode = "postgres"
                self.status.error = None
            except Exception as exc:  # pragma: no cover - exercised in runtime
                self.status.mode = "fallback"
                self.status.error = str(exc)

    def bootstrap(self) -> dict[str, Any]:
        return {
            "store": {
                "mode": self.status.mode,
                "databaseEnabled": self.status.database_enabled,
                "error": self.status.error,
            },
            **self.store.bootstrap(),
        }


service = PlatformService()
app = FastAPI(title="Mowing Platform Stage 1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/mowing-platform", StaticFiles(directory=ROOT), name="mowing-platform")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(ROOT / "admin-prototype.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "mode": service.status.mode,
        "databaseEnabled": service.status.database_enabled,
        "error": service.status.error,
    }


@app.get("/api/bootstrap")
def bootstrap() -> dict[str, Any]:
    return service.bootstrap()


@app.post("/api/orders/reset-demo")
def reset_demo() -> dict[str, Any]:
    if isinstance(service.store, InMemoryStore):
        service.store.reset()
        return service.bootstrap()
    raise HTTPException(status_code=400, detail="Demo reset is only available in fallback mode")


@app.post("/api/orders/demo")
def add_demo_order() -> dict[str, Any]:
    order = service.store.add_demo_order()
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders")
def create_order(payload: OrderCreatePayload) -> dict[str, Any]:
    order = service.store.create_order(payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/quote")
def save_quote(order_id: str, payload: QuotePayload) -> dict[str, Any]:
    order = service.store.save_quote(order_id, payload.price, payload.priceNote)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/assign")
def assign_worker(order_id: str, payload: AssignPayload) -> dict[str, Any]:
    order = service.store.assign_worker(order_id, payload.workerId)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/accept")
def accept_order(order_id: str) -> dict[str, Any]:
    order = service.store.accept_order(order_id)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/status")
def update_order_status(order_id: str, payload: OrderStatusPayload) -> dict[str, Any]:
    order = service.store.update_order_status(order_id, payload.status)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/ops")
def update_order_ops(order_id: str, payload: OrderOpsPayload) -> dict[str, Any]:
    order = service.store.update_order_ops(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/service-log")
def add_service_log(order_id: str, payload: ServiceLogPayload) -> dict[str, Any]:
    order = service.store.add_service_log(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/quality-review")
def submit_quality_review(order_id: str, payload: QualityReviewPayload) -> dict[str, Any]:
    order = service.store.submit_quality_review(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/exception")
def handle_exception(order_id: str, payload: ExceptionPayload) -> dict[str, Any]:
    order = service.store.handle_exception(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/completion")
def update_completion(order_id: str, payload: CompletionPayload) -> dict[str, Any]:
    order = service.store.update_completion(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/workers/{worker_id}/availability")
def update_worker_availability(worker_id: str, payload: WorkerAvailabilityPayload) -> dict[str, Any]:
    worker = service.store.update_worker_availability(worker_id, payload.available)
    return {"worker": worker, **service.bootstrap()}


@app.post("/api/workers/{worker_id}/profile")
def update_worker_profile(worker_id: str, payload: WorkerProfilePayload) -> dict[str, Any]:
    worker = service.store.update_worker_profile(worker_id, payload)
    return {"worker": worker, **service.bootstrap()}
