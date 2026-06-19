import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before any app module is imported so database.py picks it up.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUTH_DEBUG_CODES"] = "1"

from app.database import Base, get_db
from app.main import app, seed

# Re-create engine with StaticPool so all connections share the same in-memory DB.
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency before any test runs.
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def init_db():
    """Create all tables and seed initial data once per test session."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestingSessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)
