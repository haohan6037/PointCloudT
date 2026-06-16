from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field
from fastapi import HTTPException


class QuotePayload(BaseModel):
    """Quote for an order / 订单报价"""
    price: str = Field(min_length=1)
    priceNote: str = ""


class AssignPayload(BaseModel):
    """Assign a worker to an order / 派单给师傅"""
    workerId: str = Field(min_length=1)


class OrderCreatePayload(BaseModel):
    """Create a new mowing order / 创建新割草订单"""
    user: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    address: str = Field(min_length=1)
    serviceType: str = Field(min_length=1)
    requestedTime: str = Field(min_length=1)
    lawnSize: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    note: str = ""


class WorkerAvailabilityPayload(BaseModel):
    """Toggle worker availability / 切换师傅接单状态"""
    available: bool


class WorkerProfilePayload(BaseModel):
    """Update worker profile / 更新师傅资料"""
    name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    area: str = Field(min_length=1)
    approvalStatus: str = Field(min_length=1)
    serviceNote: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None


class AddressAutocompletePayload(BaseModel):
    """Address autocomplete query / 地址自动补全查询"""
    q: str = Field(min_length=2)


class OrderStatusPayload(BaseModel):
    """Update order status / 更新订单状态"""
    status: str = Field(min_length=1)


class CompletionPayload(BaseModel):
    """Completion and settlement data / 完工与结算数据"""
    actualAmount: str = ""
    settlementStatus: str = Field(min_length=1)
    completionNote: str = ""
    platformShare: str = ""
    workerPayout: str = ""


class OrderOpsPayload(BaseModel):
    """Operations metadata for an order / 订单运营标签"""
    priorityLevel: str = Field(min_length=1)
    opsTag: str = ""


class ServiceLogPayload(BaseModel):
    """Service activity log entry / 服务活动日志条目"""
    stage: str = Field(min_length=1)
    note: str = ""


class QualityReviewPayload(BaseModel):
    """Quality review action / 质量审核操作"""
    action: str = Field(min_length=1)
    note: str = ""


class ExceptionPayload(BaseModel):
    """Exception handling action / 异常处理操作"""
    action: str = Field(min_length=1)
    issueType: str = ""
    note: str = ""
    resolution: str = ""
    nextStatus: str = ""


class CancelPayload(BaseModel):
    """Cancel an order / 取消订单"""
    note: str = ""


class OrderUpdatePayload(BaseModel):
    """Partial update to an order / 部分更新订单"""
    user: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    serviceType: Optional[str] = None
    requestedTime: Optional[str] = None
    lawnSize: Optional[str] = None
    condition: Optional[str] = None
    note: Optional[str] = None


class InternalNotePayload(BaseModel):
    """Internal note for an order / 订单内部备注"""
    note: str = Field(min_length=1)


# ── Customer auth & profile / 用户认证和资料 ─────────────────────────

class SendCodePayload(BaseModel):
    """Send verification code to email / 发送邮箱验证码"""
    email: str = Field(min_length=5)


class VerifyCodePayload(BaseModel):
    """Verify code and login / 验证码登录"""
    email: str = Field(min_length=5)
    code: str = Field(min_length=4, max_length=6)


class CustomerProfilePayload(BaseModel):
    """Customer profile / 用户个人资料"""
    name: str = ""
    phone: str = ""
    whatsapp: str = ""
    wechat: str = ""
    address: str = ""


class SessionSyncPayload(BaseModel):
    """Sync Clerk session into local user store / 同步 Clerk 会话到本地用户存储"""
    email: str = Field(min_length=5)
    clerkUserId: str = ""
    displayName: str = ""


class UserRoleUpdatePayload(BaseModel):
    """Update app user role / 更新平台用户角色"""
    email: str = Field(min_length=5)
    role: str = Field(min_length=1)
    status: str = "active"


@dataclass
class StoreStatus:
    """Data store status / 数据存储状态"""
    mode: str
    database_enabled: bool
    error: Optional[str] = None
