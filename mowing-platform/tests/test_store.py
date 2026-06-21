"""InMemoryStore unit tests / InMemoryStore 单元测试.

Covers the full order lifecycle:
    bootstrap → create → quote → assign → accept → service → review → complete → archive
Plus edge branches: reassign, cancel, reject, update, internal-note.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from models import (
    CancelPayload,
    CompletionPayload,
    ExceptionPayload,
    InternalNotePayload,
    OrderCreatePayload,
    OrderOpsPayload,
    OrderUpdatePayload,
    QualityReviewPayload,
    ServiceLogPayload,
    WorkerProfilePayload,
)
from store import InMemoryStore


# ── Bootstrap & seed data / 启动和种子数据 ────────────────────────────

class TestBootstrap:
    """Bootstrap should return 5 seed orders and 4 workers / 应返回5条订单4位服务商."""

    def test_seed_orders_count(self, store):
        data = store.bootstrap()
        assert len(data["orders"]) == 5

    def test_seed_workers_count(self, store):
        data = store.bootstrap()
        assert len(data["workers"]) == 4

    def test_workers_have_lat_lng(self, store):
        data = store.bootstrap()
        for w in data["workers"]:
            assert "lat" in w
            assert "lng" in w

    def test_reset_restores_seed(self, store):
        store.create_order(OrderCreatePayload(
            user="X", phone="021", address="A", serviceType="一次性割草",
            requestedTime="2026-06-10", lawnSize="100", condition="flat",
        ))
        assert len(store.bootstrap()["orders"]) == 6
        store.reset()
        assert len(store.bootstrap()["orders"]) == 5


# ── Order CRUD / 订单增删查 ────────────────────────────────────────────

class TestOrderCreate:
    """Create order and verify defaults / 创建订单并验证默认值."""

    def test_create_order_defaults(self, store):
        payload = OrderCreatePayload(
            user="Alice", phone="021", address="Addr", serviceType="一次性割草",
            requestedTime="2026-06-10", lawnSize="100", condition="flat",
        )
        order = store.create_order(payload)
        assert order["status"] == "pending_review"
        assert order["priorityLevel"] == "normal"
        assert order["price"] == ""
        assert order["assignedWorkerId"] == ""
        assert order["internalNote"] == ""

    def test_create_order_id_increment(self, store):
        o1 = store.create_order(OrderCreatePayload(
            user="A", phone="1", address="a", serviceType="一次性割草",
            requestedTime="t", lawnSize="s", condition="c",
        ))
        o2 = store.create_order(OrderCreatePayload(
            user="B", phone="2", address="b", serviceType="一次性割草",
            requestedTime="t", lawnSize="s", condition="c",
        ))
        num1 = int(o1["id"].split("-")[1])
        num2 = int(o2["id"].split("-")[1])
        assert num2 == num1 + 1


class TestOrderUpdate:
    """Edit order fields / 编辑订单字段."""

    def test_update_user_and_address(self, store):
        payload = OrderUpdatePayload(user="Bob", address="New St")
        order = store.update_order("MOW-1001", payload)
        assert order["user"] == "Bob"
        assert order["address"] == "New St"

    def test_update_no_change(self, store):
        payload = OrderUpdatePayload()
        order = store.update_order("MOW-1001", payload)
        assert order["user"] == "Helen Chen"  # unchanged

    def test_update_not_found(self, store):
        with pytest.raises(HTTPException, match="Order not found"):
            store.update_order("MOW-9999", OrderUpdatePayload(user="X"))


# ── Quote → assign → accept pipeline / 报价→派单→接单 ────────────────

class TestQuoteAssignAccept:
    """Happy path: quote → assign → accept / 正常流程."""

    def test_save_quote_changes_status(self, store):
        order = store.save_quote("MOW-1001", "120", "标准报价")
        assert order["status"] == "quoted"
        assert order["price"] == "120"

    def test_assign_worker(self, store):
        store.save_quote("MOW-1001", "100", "")
        order = store.assign_worker("MOW-1001", "w-001")
        assert order["status"] == "assigned"
        assert order["assignedWorkerId"] == "w-001"

    def test_accept_order(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        order = store.accept_order("MOW-1001")
        assert order["status"] == "accepted_by_worker"

    def test_accept_without_assign_fails(self, store):
        with pytest.raises(HTTPException, match="must be assigned first"):
            store.accept_order("MOW-1002")


# ── Status advancement / 状态推进 ──────────────────────────────────────

class TestStatusAdvance:
    """Advance through service lifecycle / 推进服务生命周期."""

    def test_in_service(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        order = store.update_order_status("MOW-1001", "in_service")
        assert order["status"] == "in_service"

    def test_pending_quality_review(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        store.update_order_status("MOW-1001", "in_service")
        order = store.update_order_status("MOW-1001", "pending_quality_review")
        assert order["status"] == "pending_quality_review"

    def test_completed_via_approve(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        store.update_order_status("MOW-1001", "in_service")
        store.update_order_status("MOW-1001", "pending_quality_review")
        order = store.submit_quality_review(
            "MOW-1001", QualityReviewPayload(action="approve", note="通过"),
        )
        assert order["status"] == "completed"


# ── Reassign / 改派 ───────────────────────────────────────────────────

class TestReassign:
    """Reassign to different worker / 改派给其他服务商."""

    def test_reassign(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        order = store.reassign_worker("MOW-1001", "w-002")
        assert order["assignedWorkerId"] == "w-002"
        assert order["status"] == "assigned"
        assert "改派" in order["activity"][0]


# ── Cancel / 取消 ─────────────────────────────────────────────────────

class TestCancel:
    """Cancel order workflow / 取消订单."""

    def test_cancel_pending_order(self, store):
        order = store.cancel_order("MOW-1001", "客户取消")
        assert order["status"] == "cancelled"

    def test_cancel_completed_fails(self, store):
        with pytest.raises(HTTPException, match="Cannot cancel"):
            store.cancel_order("MOW-1005")  # MOW-1005 is already cancelled


# ── Reject / 拒单 ─────────────────────────────────────────────────────

class TestReject:
    """Worker reject / 服务商拒单."""

    def test_reject_assigned(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        order = store.reject_order("MOW-1001")
        assert order["status"] == "quoted"
        assert order["assignedWorkerId"] == ""
        assert "拒单" in order["activity"][0]

    def test_reject_unassigned_fails(self, store):
        with pytest.raises(HTTPException, match="not assigned"):
            store.reject_order("MOW-1002")  # not assigned yet


# ── Quality review / 质量审核 ─────────────────────────────────────────

class TestQualityReview:
    """Quality review approve / rework / 质量审核."""

    def test_approve(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        store.update_order_status("MOW-1001", "in_service")
        store.update_order_status("MOW-1001", "pending_quality_review")
        order = store.submit_quality_review(
            "MOW-1001", QualityReviewPayload(action="approve", note="OK"),
        )
        assert order["status"] == "completed"
        assert order["settlementStatus"] == "pending"

    def test_rework(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        store.update_order_status("MOW-1001", "in_service")
        store.update_order_status("MOW-1001", "pending_quality_review")
        order = store.submit_quality_review(
            "MOW-1001", QualityReviewPayload(action="rework", note="补做边缘"),
        )
        assert order["status"] == "in_service"


# ── Exception / 异常处理 ──────────────────────────────────────────────

class TestException:
    """Exception handling / 异常处理流程."""

    def test_open_exception(self, store):
        order = store.handle_exception(
            "MOW-1001",
            ExceptionPayload(action="open", issueType="现场障碍物", note="有建筑材料"),
        )
        assert order["status"] == "exception_open"
        assert order["exceptionType"] == "现场障碍物"

    def test_resume_exception(self, store):
        store.handle_exception(
            "MOW-1001",
            ExceptionPayload(action="open", issueType="机器人异常", note=""),
        )
        order = store.handle_exception(
            "MOW-1001",
            ExceptionPayload(action="resume", nextStatus="in_service", resolution="已修复"),
        )
        assert order["status"] == "in_service"

    def test_close_exception(self, store):
        store.handle_exception(
            "MOW-1001",
            ExceptionPayload(action="open", issueType="其他", note=""),
        )
        order = store.handle_exception(
            "MOW-1001",
            ExceptionPayload(action="close", resolution="客户不再需要"),
        )
        assert order["status"] == "cancelled"


# ── Completion & archive / 完成归档 ───────────────────────────────────

class TestCompletion:
    """Completion archive / 完成归档."""

    def test_archive(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        store.update_order_status("MOW-1001", "in_service")
        store.update_order_status("MOW-1001", "pending_quality_review")
        store.submit_quality_review(
            "MOW-1001", QualityReviewPayload(action="approve"),
        )
        order = store.update_completion(
            "MOW-1001",
            CompletionPayload(
                actualAmount="95", paymentStatus="paid", paymentMethod="Bank transfer",
                paymentNote="已人工确认到账", settlementStatus="settled",
                completionNote="完成", platformShare="20", workerPayout="75",
            ),
        )
        assert order["settlementStatus"] == "settled"
        assert order["actualAmount"] == "95"
        assert order["paymentStatus"] == "paid"
        assert order["paymentMethod"] == "Bank transfer"

    def test_archive_non_completed_fails(self, store):
        with pytest.raises(HTTPException, match="Only completed orders"):
            store.update_completion(
                "MOW-1001",
                CompletionPayload(actualAmount="", settlementStatus="pending"),
            )


# ── Internal note / 内部备注 ──────────────────────────────────────────

class TestInternalNote:
    """Internal note / 内部备注."""

    def test_save_internal_note(self, store):
        order = store.save_internal_note("MOW-1001", "已联系客户确认时间")
        assert order["internalNote"] == "已联系客户确认时间"


# ── Service log / 服务记录 ────────────────────────────────────────────

class TestServiceLog:
    """Service log entries / 服务记录."""

    def test_add_service_log(self, store):
        store.save_quote("MOW-1001", "100", "")
        store.assign_worker("MOW-1001", "w-001")
        order = store.add_service_log(
            "MOW-1001", ServiceLogPayload(stage="arrival", note="已到达"),
        )
        assert "到场签到" in order["activity"][0]

    def test_append_order_photos(self, store):
        order = store.append_order_photos(
            "MOW-1003",
            ["/mowing-platform/uploads/provider/MOW-1003/evidence.jpg"],
            "服务前照片",
        )
        assert "/mowing-platform/uploads/provider/MOW-1003/evidence.jpg" in order["photos"]
        assert "上传现场照片" in order["activity"][0]


# ── Operations tag / 运营标记 ─────────────────────────────────────────

class TestOpsTag:
    """Priority and ops tag / 优先级和运营标签."""

    def test_update_ops(self, store):
        order = store.update_order_ops(
            "MOW-1001", OrderOpsPayload(priorityLevel="urgent", opsTag="VIP客户"),
        )
        assert order["priorityLevel"] == "urgent"
        assert order["opsTag"] == "VIP客户"

    def test_invalid_priority_fails(self, store):
        with pytest.raises(HTTPException, match="Unsupported priority"):
            store.update_order_ops(
                "MOW-1001", OrderOpsPayload(priorityLevel="critical"),
            )


# ── Worker management / 服务商管理 ────────────────────────────────────

class TestWorker:
    """Worker profile and availability / 服务商资料和可接单状态."""

    def test_toggle_availability(self, store):
        w = store.update_worker_availability("w-001", False)
        assert w["available"] is False

    def test_update_profile(self, store):
        w = store.update_worker_profile(
            "w-001", WorkerProfilePayload(
                name="张师傅改名", email="zhang.new@example.com", phone="021-111", area="North Shore",
                approvalStatus="approved", serviceNote="更新备注",
                lat=-36.72, lng=174.70,
            ),
        )
        assert w["name"] == "张师傅改名"
        assert w["email"] == "zhang.new@example.com"
        assert w["lat"] == -36.72

    def test_worker_email_lookup_and_orders(self, store):
        worker = store.get_worker_by_email("zhang.worker@example.com")
        assert worker is not None
        assert worker["id"] == "w-001"
        orders = store.list_orders_for_worker("w-001")
        assert all(order["assignedWorkerId"] == "w-001" for order in orders)

    def test_worker_not_found(self, store):
        with pytest.raises(HTTPException, match="Worker not found"):
            store.update_worker_availability("w-999", True)


# ── Demo order / 演示订单 ─────────────────────────────────────────────

class TestDemoOrder:
    """Demo order creation / 演示订单."""

    def test_add_demo(self, store):
        order = store.add_demo_order()
        assert order["status"] == "pending_review"
        assert order["id"].startswith("MOW-")
