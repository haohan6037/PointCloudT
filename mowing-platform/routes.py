"""FastAPI routes / FastAPI 路由 — all API endpoints for the mowing platform."""

from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import quote, urlencode

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from address_service import AddressService, haversine_m
from data import ROOT
from models import (
    AddressAutocompletePayload,
    AssignPayload,
    CancelPayload,
    CompletionPayload,
    CustomerProfilePayload,
    ExceptionPayload,
    InternalNotePayload,
    OrderCreatePayload,
    OrderOpsPayload,
    OrderStatusPayload,
    OrderUpdatePayload,
    QualityReviewPayload,
    QuotePayload,
    SessionSyncPayload,
    SendCodePayload,
    ServiceLogPayload,
    StoreStatus,
    UserRoleUpdatePayload,
    VerifyCodePayload,
    WorkerAvailabilityPayload,
    WorkerProfilePayload,
)
from store import InMemoryStore, PostgresStore


# ── Platform service / 平台服务 ────────────────────────────────────────

class PlatformService:
    """Service locator / 服务定位器 — picks between InMemoryStore and PostgresStore."""

    def __init__(self) -> None:
        self.memory = InMemoryStore()
        self.status = StoreStatus(
            mode="fallback",
            database_enabled=False,
            error="No PostgreSQL connection available",
        )
        self.store: InMemoryStore | PostgresStore = self.memory
        dsn = _build_dsn()
        if dsn:
            self.status.database_enabled = True
            try:
                db_store = PostgresStore(dsn)
                db_store.prepare()
                self.store = db_store
                self.status.mode = "postgres"
                self.status.error = None
            except Exception as exc:  # pragma: no cover
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


def _build_dsn() -> str | None:
    """Build PostgreSQL DSN from environment / 从环境变量构建数据库连接串."""
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
    auth = quote(user, safe="")
    if password:
        auth = f"{auth}:{quote(password, safe='')}"
    query: dict[str, str] = {}
    sslmode = os.getenv("PGSSLMODE")
    sslrootcert = os.getenv("PGSSLROOTCERT")
    if sslmode:
        query["sslmode"] = sslmode
    if sslrootcert:
        query["sslrootcert"] = sslrootcert
    query_string = f"?{urlencode(query)}" if query else ""
    return f"postgresql://{auth}@{host}:{port}/{quote(database, safe='')}{query_string}"


# ── App factory / 应用工厂 ─────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure FastAPI app / 创建并配置 FastAPI 应用."""
    app = FastAPI(title="Mowing Platform Stage 1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/mowing-platform", StaticFiles(directory=ROOT), name="mowing-platform")
    return app


# Module-level singleton / 模块级单例
service = PlatformService()
app = create_app()


# ── Page & health routes / 页面和健康检查路由 ──────────────────────────

def _inject_clerk_key(html_path: str) -> HTMLResponse:
    """Read an HTML file and inject the Clerk Publishable Key from env.
    / 读取 HTML 文件并从环境变量注入 Clerk Publishable Key。"""
    content = (ROOT / html_path).read_text(encoding="utf-8")
    clerk_key = os.getenv("Clerk_Public_Key", "").strip().rstrip("$")
    if clerk_key:
        tag = f"<script>window.__GARDENOS_CLERK_PUBLISHABLE_KEY__=\"{clerk_key}\";</script>"
        content = content.replace("</head>", f"  {tag}\n</head>", 1)
    return HTMLResponse(content)


@app.get("/")
def root() -> HTMLResponse:
    """Serve admin prototype / 返回管理后台原型页面."""
    return _inject_clerk_key("admin-prototype.html")


@app.get("/provider")
def provider_page() -> HTMLResponse:
    """Serve provider-facing page / 返回服务商端页面."""
    return _inject_clerk_key("provider.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Health check / 健康检查."""
    return {
        "ok": True,
        "mode": service.status.mode,
        "databaseEnabled": service.status.database_enabled,
        "error": service.status.error,
    }


@app.get("/api/bootstrap")
def bootstrap() -> dict[str, Any]:
    """Load all orders and workers / 加载全部订单和服务商数据."""
    return service.bootstrap()


# ── Order CRUD / 订单增删改查 ──────────────────────────────────────────

@app.post("/api/orders/reset-demo")
def reset_demo() -> dict[str, Any]:
    """Reset to seed data (InMemoryStore only) / 重置为演示数据（仅内存模式）."""
    if isinstance(service.store, InMemoryStore):
        service.store.reset()
        return service.bootstrap()
    raise HTTPException(status_code=400, detail="Demo reset is only available in fallback mode")


@app.post("/api/orders/demo")
def add_demo_order() -> dict[str, Any]:
    """Add a demo order / 添加演示订单."""
    order = service.store.add_demo_order()
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders")
def create_order(payload: OrderCreatePayload) -> dict[str, Any]:
    """Create new order / 创建新订单."""
    order = service.store.create_order(payload)
    return {"order": order, **service.bootstrap()}


@app.put("/api/orders/{order_id}")
def update_order(order_id: str, payload: OrderUpdatePayload) -> dict[str, Any]:
    """Edit order fields / 编辑订单字段."""
    order = service.store.update_order(order_id, payload)
    return {"order": order, **service.bootstrap()}


# ── Order workflow / 订单工作流 ────────────────────────────────────────

@app.post("/api/orders/{order_id}/quote")
def save_quote(order_id: str, payload: QuotePayload) -> dict[str, Any]:
    """Save quote / 保存报价."""
    order = service.store.save_quote(order_id, payload.price, payload.priceNote)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/assign")
def assign_worker(order_id: str, payload: AssignPayload) -> dict[str, Any]:
    """Assign worker / 派单."""
    order = service.store.assign_worker(order_id, payload.workerId)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/reassign")
def reassign_worker(order_id: str, payload: AssignPayload) -> dict[str, Any]:
    """Reassign to different worker / 改派给其他服务商."""
    order = service.store.reassign_worker(order_id, payload.workerId)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/accept")
def accept_order(order_id: str) -> dict[str, Any]:
    """Worker accepts order / 服务商接单."""
    order = service.store.accept_order(order_id)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/status")
def update_order_status(order_id: str, payload: OrderStatusPayload) -> dict[str, Any]:
    """Advance order status / 推进订单状态."""
    order = service.store.update_order_status(order_id, payload.status)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/reject")
def reject_order(order_id: str) -> dict[str, Any]:
    """Worker rejects order / 服务商拒单."""
    order = service.store.reject_order(order_id)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/cancel")
def cancel_order(order_id: str, payload: Optional[CancelPayload] = None) -> dict[str, Any]:
    """Cancel order / 取消订单."""
    note = payload.note if payload else ""
    order = service.store.cancel_order(order_id, note)
    return {"order": order, **service.bootstrap()}


# ── Order details / 订单详情操作 ───────────────────────────────────────

@app.post("/api/orders/{order_id}/ops")
def update_order_ops(order_id: str, payload: OrderOpsPayload) -> dict[str, Any]:
    """Update priority and ops tag / 更新优先级和运营标签."""
    order = service.store.update_order_ops(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/service-log")
def add_service_log(order_id: str, payload: ServiceLogPayload) -> dict[str, Any]:
    """Add service log entry / 添加服务记录."""
    order = service.store.add_service_log(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/quality-review")
def submit_quality_review(order_id: str, payload: QualityReviewPayload) -> dict[str, Any]:
    """Quality review (approve/rework) / 质量审核（通过/打回）."""
    order = service.store.submit_quality_review(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/exception")
def handle_exception(order_id: str, payload: ExceptionPayload) -> dict[str, Any]:
    """Handle exception / 异常处理."""
    order = service.store.handle_exception(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/completion")
def update_completion(order_id: str, payload: CompletionPayload) -> dict[str, Any]:
    """Archive completion data / 归档完成数据."""
    order = service.store.update_completion(order_id, payload)
    return {"order": order, **service.bootstrap()}


@app.post("/api/orders/{order_id}/internal-note")
def save_internal_note(order_id: str, payload: InternalNotePayload) -> dict[str, Any]:
    """Save internal note / 保存内部备注."""
    order = service.store.save_internal_note(order_id, payload.note)
    return {"order": order, **service.bootstrap()}


# ── Worker management / 服务商管理 ─────────────────────────────────────

@app.post("/api/workers/{worker_id}/availability")
def update_worker_availability(worker_id: str, payload: WorkerAvailabilityPayload) -> dict[str, Any]:
    """Toggle worker availability / 切换服务商可接单状态."""
    worker = service.store.update_worker_availability(worker_id, payload.available)
    return {"worker": worker, **service.bootstrap()}


@app.post("/api/workers/{worker_id}/profile")
def update_worker_profile(worker_id: str, payload: WorkerProfilePayload) -> dict[str, Any]:
    """Update worker profile / 更新服务商资料."""
    worker = service.store.update_worker_profile(worker_id, payload)
    return {"worker": worker, **service.bootstrap()}


@app.post("/api/workers/suggest")
def suggest_workers_for_address(payload: AddressAutocompletePayload) -> dict[str, Any]:
    """Geocode address and rank workers by distance / 地址→坐标→按距离排序服务商."""
    geo = AddressService.geocode(payload.q)
    workers_with_distance: list[dict[str, Any]] = []
    for worker in service.store.bootstrap()["workers"]:
        w_lat = worker.get("lat")
        w_lng = worker.get("lng")
        if w_lat is None or w_lng is None:
            workers_with_distance.append({**worker, "distance_km": None})
            continue
        if geo and geo.get("lat") is not None and geo.get("lng") is not None:
            dist = haversine_m(float(geo["lat"]), float(geo["lng"]), w_lat, w_lng)
            workers_with_distance.append({**worker, "distance_km": round(dist / 1000.0, 1)})
        else:
            workers_with_distance.append({**worker, "distance_km": None})
    workers_with_distance.sort(
        key=lambda w: (
            w["distance_km"] if w["distance_km"] is not None else 1e9,
            not w.get("available", False),
        )
    )
    return {"workers": workers_with_distance, "geocoded": geo}


# ── Address services / 地址服务 ────────────────────────────────────────

@app.post("/api/address/autocomplete")
def address_autocomplete(payload: AddressAutocompletePayload) -> list[dict[str, Any]]:
    """Address autocomplete via Geoapify / Geoapify 地址自动补全."""
    return AddressService.autocomplete(payload.q)


@app.post("/api/address/geocode")
def address_geocode(payload: AddressAutocompletePayload) -> dict[str, Any]:
    """Geocode address to WGS84 / 地址→WGS84坐标."""
    result = AddressService.geocode(payload.q)
    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")
    return result


@app.get("/api/address/reverse-geocode")
def address_reverse_geocode(lat: float, lng: float) -> dict[str, Any]:
    """Reverse geocode WGS84 lat/lng → nearest address from Geoapify.
    / 反向地理编码：WGS84 经纬度 → Geoapify 最近地址。"""
    result = AddressService.reverse_geocode(lat, lng)
    if result is None:
        raise HTTPException(status_code=404, detail="No address found near this location")
    return result


# ═══════════════════════════════════════════════════════════════════════
# Customer-facing API / 用户端 API
# ═══════════════════════════════════════════════════════════════════════

UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/api/customer/orders")
async def customer_create_order(
    user: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    serviceType: str = Form(...),
    requestedDate: str = Form(...),
    requestedTime: str = Form(""),
    lawnSize: str = Form(...),
    condition: str = Form(...),
    note: str = Form(""),
    photos: list[UploadFile] = File(default_factory=list),
) -> dict[str, Any]:
    """Customer submits a new order / 用户提交新订单."""
    saved_photos: list[str] = []
    for photo in photos:
        if photo.filename:
            safe_name = f"{photo.filename}"
            dest = UPLOAD_DIR / safe_name
            content = await photo.read()
            dest.write_bytes(content)
            saved_photos.append(f"/uploads/{safe_name}")

    requested_time = f"{requestedDate} {requestedTime}" if requestedTime else requestedDate

    from models import OrderCreatePayload
    payload = OrderCreatePayload(
        user=user, phone=phone, address=address,
        serviceType=serviceType, requestedTime=requested_time,
        lawnSize=lawnSize, condition=condition, note=note,
    )
    order = service.store.create_order(payload)
    # Set the initial activity to reflect customer submission / 标记为客户提交
    order["activity"] = ["客户通过用户端提交订单，等待平台确认。", *order["activity"]]
    if saved_photos:
        order["photos"] = saved_photos
    return {"order": order, **service.bootstrap()}


@app.get("/api/customer/orders")
def customer_list_orders(phone: str = "") -> dict[str, Any]:
    """Customer views their orders by phone / 用户按手机号查订单."""
    data = service.store.bootstrap()
    if phone:
        data["orders"] = [o for o in data["orders"] if o.get("phone") == phone]
    return data


@app.post("/api/customer/orders/{order_id}/confirm")
def customer_confirm_quote(order_id: str) -> dict[str, Any]:
    """Customer accepts the quoted price / 用户确认报价."""
    order = service.store.accept_by_customer(order_id)
    return {"order": order, **service.bootstrap()}


@app.post("/api/customer/orders/{order_id}/reject")
def customer_reject_quote(order_id: str) -> dict[str, Any]:
    """Customer rejects the quoted price / 用户拒绝报价."""
    order = service.store.reject_by_customer(order_id)
    return {"order": order, **service.bootstrap()}


@app.get("/customer")
def customer_page() -> HTMLResponse:
    """Serve customer-facing page / 返回用户端页面."""
    return _inject_clerk_key("customer.html")


# ── Customer auth / 用户认证 ──────────────────────────────────────────

@app.post("/api/session/sync")
def sync_user_session(payload: SessionSyncPayload) -> dict[str, Any]:
    """Sync Clerk session into app user store / 同步 Clerk 会话到平台用户."""
    user = service.store.sync_user_session(
        payload.email,
        payload.clerkUserId.strip(),
        payload.displayName.strip(),
    )
    return {"user": user}


@app.get("/api/users/me")
def get_current_user(email: str = "") -> dict[str, Any]:
    """Get current app user / 获取当前平台用户."""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    user = service.store.get_user(email)
    if user is None:
        user = service.store.sync_user_session(email)
    return {"user": user}


@app.get("/api/users")
def list_users() -> dict[str, Any]:
    """List app users / 列出平台用户."""
    return {"users": service.store.list_users()}


@app.put("/api/users/role")
def update_user_role(payload: UserRoleUpdatePayload) -> dict[str, Any]:
    """Update app user role / 更新平台用户角色."""
    user = service.store.update_user_role(payload.email, payload.role, payload.status)
    return {"user": user}


@app.post("/api/customer/auth/send-code")
def send_verification_code(payload: SendCodePayload) -> dict[str, Any]:
    """Send verification code to email / 发送邮箱验证码."""
    from auth_service import send_verification_code as send_code

    ok = send_code(payload.email)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to send verification code")
    return {"ok": True, "message": "验证码已发送，请检查邮箱（开发模式下打印在控制台）。"}


@app.post("/api/customer/auth/verify")
def verify_code_and_login(payload: VerifyCodePayload) -> dict[str, Any]:
    """Verify code and login / 验证码登录."""
    from auth_service import verify_code as check_code

    if not check_code(payload.email, payload.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    # Return existing profile if any / 返回已有资料
    profile = service.store.get_customer_profile(payload.email)
    return {
        "ok": True,
        "email": payload.email,
        "profile": profile,
    }


# ── Customer profile / 用户资料 ───────────────────────────────────────

@app.get("/api/customer/profile")
def get_customer_profile(email: str = "") -> dict[str, Any]:
    """Get customer profile / 获取用户资料."""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    profile = service.store.get_customer_profile(email)
    if profile is None:
        profile = {
            "email": email, "name": "", "phone": "",
            "whatsapp": "", "wechat": "", "address": "",
        }
    return {"profile": profile}


@app.put("/api/customer/profile")
def save_customer_profile(payload: CustomerProfilePayload, email: str = "") -> dict[str, Any]:
    """Save customer profile / 保存用户资料."""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    profile = service.store.save_customer_profile(email, payload)
    return {"profile": profile}
