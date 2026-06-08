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


WORKERS = [
    {"id": "w-001", "name": "张师傅", "area": "North Shore", "available": True},
    {"id": "w-002", "name": "李师傅", "area": "Mt Eden / Epsom", "available": True},
    {"id": "w-003", "name": "王师傅", "area": "Howick / Botany", "available": False},
    {"id": "w-004", "name": "陈师傅", "area": "Henderson / Westgate", "available": True},
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
        "price": "",
        "priceNote": "",
        "assignedWorkerId": "",
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
        "price": "95",
        "priceNote": "规则草坪，含花坛边人工修整。",
        "assignedWorkerId": "",
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
        "price": "145",
        "priceNote": "面积较大，包含较多边角收尾。",
        "assignedWorkerId": "w-001",
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
        "price": "85",
        "priceNote": "小面积，人工精细收尾占比较高。",
        "assignedWorkerId": "w-004",
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
        "price": "130",
        "priceNote": "草较高，原报价含额外处理。",
        "assignedWorkerId": "w-003",
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
        order["activity"] = [f"平台保存报价：${price}。", *order["activity"]]
        return order

    def assign_worker(self, order_id: str, worker_id: str) -> dict[str, Any]:
        order = self._find_order(order_id)
        order["assignedWorkerId"] = worker_id
        order["status"] = "assigned"
        order["updatedAt"] = timestamp()
        name = next((worker["name"] for worker in self.workers if worker["id"] == worker_id), worker_id)
        order["activity"] = [f"平台派单给{name}。", *order["activity"]]
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
        order["activity"] = [f"{name}已确认接单。", *order["activity"]]
        return order

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
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
            "updatedAt": timestamp(),
            "photos": ["客户照片 1", "客户照片 2", "客户照片 3"],
            "activity": ["运营新增演示订单。"],
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
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
            "updatedAt": timestamp(),
            "photos": ["待上传照片 1", "待上传照片 2", "待上传照片 3"],
            "activity": ["运营人员创建订单，等待平台确认报价。"],
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
                cur.execute("select count(*) from mowing_workers")
                if cur.fetchone()[0] == 0:
                    cur.executemany(
                        """
                        insert into mowing_workers (id, name, area, available)
                        values (%(id)s, %(name)s, %(area)s, %(available)s)
                        """,
                        WORKERS,
                    )
                cur.execute("select count(*) from mowing_orders")
                if cur.fetchone()[0] == 0:
                    self._seed_orders(cur)
            conn.commit()

    def _seed_orders(self, cur) -> None:
        for order in SEED_ORDERS:
            cur.execute(
                """
                insert into mowing_orders (
                    id, user_name, phone, address, service_type, requested_time, lawn_size,
                    condition_note, customer_note, status, quoted_price, price_note,
                    assigned_worker_id, updated_at, photos_json, activity_json
                ) values (
                    %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                    %(lawnSize)s, %(condition)s, %(note)s, %(status)s, %(quoted_price)s, %(priceNote)s,
                    %(assignedWorkerId)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                )
                """,
                {
                    **order,
                    "quoted_price": Decimal(order["price"]) if order["price"] else None,
                    "assignedWorkerId": order["assignedWorkerId"] or None,
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
                           condition_note, customer_note, status, quoted_price, price_note,
                           assigned_worker_id, updated_at, photos_json, activity_json
                    from mowing_orders
                    order by updated_at desc, id asc
                    """
                )
                orders = [self._row_to_order(row) for row in cur.fetchall()]
                cur.execute("select id, name, area, available from mowing_workers order by id")
                workers = [
                    {"id": row[0], "name": row[1], "area": row[2], "available": row[3]}
                    for row in cur.fetchall()
                ]
        return {"orders": orders, "workers": workers}

    def update_worker_availability(self, worker_id: str, available: bool) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update mowing_workers
                    set available = %s
                    where id = %s
                    returning id, name, area, available
                    """,
                    (available, worker_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Worker not found")
            conn.commit()
        return {"id": row[0], "name": row[1], "area": row[2], "available": row[3]}

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
        photos = self._decode_json_value(row[14])
        activity = self._decode_json_value(row[15])
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
            "price": str(row[10]) if row[10] is not None else "",
            "priceNote": row[11] or "",
            "assignedWorkerId": row[12] or "",
            "updatedAt": row[13].strftime("%Y-%m-%d %H:%M"),
            "photos": photos,
            "activity": activity,
        }

    def save_quote(self, order_id: str, price: str, price_note: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select activity_json, status from mowing_orders where id = %s", (order_id,))
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Order not found")
                activity = self._decode_json_value(row[0])
                activity.insert(0, f"平台保存报价：${price}。")
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
                activity.insert(0, f"平台派单给{worker[0]}。")
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
                activity.insert(0, f"{row[1]}已确认接单。")
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
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
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
                        condition_note, customer_note, status, quoted_price, price_note,
                        assigned_worker_id, updated_at, photos_json, activity_json
                    ) values (
                        %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                        %(lawnSize)s, %(condition)s, %(note)s, %(status)s, null, %(priceNote)s,
                        %(assignedWorkerId)s, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                    )
                    """,
                    {
                        **order,
                        "assignedWorkerId": None,
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
            "price": "",
            "priceNote": "",
            "assignedWorkerId": "",
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
                        condition_note, customer_note, status, quoted_price, price_note,
                        assigned_worker_id, updated_at, photos_json, activity_json
                    ) values (
                        %(id)s, %(user)s, %(phone)s, %(address)s, %(serviceType)s, %(requestedTime)s,
                        %(lawnSize)s, %(condition)s, %(note)s, %(status)s, null, %(priceNote)s,
                        null, %(updatedAt)s, %(photos_json)s, %(activity_json)s
                    )
                    """,
                    {
                        **order,
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
                           condition_note, customer_note, status, quoted_price, price_note,
                           assigned_worker_id, updated_at, photos_json, activity_json
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


@app.post("/api/workers/{worker_id}/availability")
def update_worker_availability(worker_id: str, payload: WorkerAvailabilityPayload) -> dict[str, Any]:
    worker = service.store.update_worker_availability(worker_id, payload.available)
    return {"worker": worker, **service.bootstrap()}
