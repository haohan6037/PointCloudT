"""Shared fixtures for mowing-platform tests / 共享测试夹具."""

from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

# Ensure mowing-platform package is importable / 确保模块可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MQTT_MONITOR_ENABLED", "0")


@pytest.fixture
def store():
    """Fresh InMemoryStore with seed data / 带种子数据的新 InMemoryStore."""
    from store import InMemoryStore

    return InMemoryStore()


@pytest.fixture
def client():
    """FastAPI TestClient / FastAPI 测试客户端."""
    from fastapi.testclient import TestClient

    from routes import app

    return TestClient(app)


@pytest.fixture
def sample_order_data():
    """Minimal valid order creation payload / 最小有效订单负载."""
    return {
        "user": "Test User",
        "phone": "021-999-9999",
        "address": "1 Test Street, Auckland",
        "serviceType": "一次性割草",
        "requestedTime": "2026-06-15 09:00-12:00",
        "lawnSize": "约 150 平方米",
        "condition": "平整规则草坪",
        "note": "自动化测试订单",
    }
