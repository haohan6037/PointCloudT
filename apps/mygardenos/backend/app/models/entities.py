from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# PostGIS-ready note: address-bearing tables keep latitude/longitude now for SQLite/dev
# portability. Production Alembic migration can add geography(Point,4326) columns,
# e.g. GeoAlchemy2 Geography('POINT', srid=4326), populated from these fields.

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(120), default="Hector")
    gender: Mapped[str] = mapped_column(String(40), default="Male")
    address: Mapped[str] = mapped_column(String(500), default="")
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Family(Base):
    __tablename__ = "families"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), default="happy family")
    address: Mapped[str] = mapped_column(String(500), default="")
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")

class FamilyMember(Base):
    __tablename__ = "family_members"
    __table_args__ = (UniqueConstraint("family_id", "user_id", name="uq_family_user"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(80), default="Family Creator")
    family = relationship("Family", back_populates="members")
    user = relationship("User")

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serial: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    model: Mapped[str] = mapped_column(String(120), default="AN-1600")
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    family_id: Mapped[Optional[int]] = mapped_column(ForeignKey("families.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="mock_available")
    battery_percent: Mapped[int] = mapped_column(Integer, default=54)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    schedule_start_time: Mapped[str] = mapped_column(String(5), default="08:00")
    schedule_end_time: Mapped[str] = mapped_column(String(5), default="18:00")


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(String(500), default="")
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coordinate_system: Mapped[str] = mapped_column(String(80), default="GOS-MAP-XY")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PropertyMap(Base):
    __tablename__ = "property_maps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    map_type: Mapped[str] = mapped_column(String(80), default="manual")
    source_file_url: Mapped[str] = mapped_column(String(500), default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")
    point_cloud_url: Mapped[str] = mapped_column(String(500), default="")
    coordinate_transform: Mapped[str] = mapped_column(Text, default="{}")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    map_id: Mapped[int] = mapped_column(ForeignKey("property_maps.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    zone_type: Mapped[str] = mapped_column(String(40), index=True)
    polygon_coordinates: Mapped[str] = mapped_column(Text, default="[]")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Dock(Base):
    __tablename__ = "docks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    map_id: Mapped[int] = mapped_column(ForeignKey("property_maps.id"), index=True)
    position: Mapped[str] = mapped_column(Text, default="{}")
    heading: Mapped[float] = mapped_column(Float, default=0.0)
    related_zone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("zones.id"), nullable=True)
    network_available: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MowingPath(Base):
    __tablename__ = "mowing_paths"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    map_id: Mapped[int] = mapped_column(ForeignKey("property_maps.id"), index=True)
    work_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    no_go_zone_ids: Mapped[str] = mapped_column(Text, default="[]")
    dock_id: Mapped[Optional[int]] = mapped_column(ForeignKey("docks.id"), nullable=True)
    path_points: Mapped[str] = mapped_column(Text, default="[]")
    blade_width: Mapped[float] = mapped_column(Float, default=0.21)
    overlap_ratio: Mapped[float] = mapped_column(Float, default=0.1)
    path_angle: Mapped[float] = mapped_column(Float, default=0.0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    estimated_distance: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MowingTask(Base):
    __tablename__ = "mowing_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    map_id: Mapped[int] = mapped_column(ForeignKey("property_maps.id"), index=True)
    work_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("mowing_paths.id"), index=True)
    robot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("devices.id"), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    allowed_start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    allowed_end_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    customer_confirmation_status: Mapped[str] = mapped_column(String(40), default="pending")
    status: Mapped[str] = mapped_column(String(60), default="WAITING_CUSTOMER_CONFIRMATION")
    current_path_index: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskEvent(Base):
    __tablename__ = "task_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("mowing_tasks.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RobotTelemetry(Base):
    __tablename__ = "robot_telemetry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    robot_identifier: Mapped[str] = mapped_column(String(120), index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mowing_tasks.id"), nullable=True)
    position: Mapped[str] = mapped_column(Text, default="{}")
    battery_level: Mapped[int] = mapped_column(Integer, default=0)
    charging_status: Mapped[str] = mapped_column(String(40), default="unknown")
    task_status: Mapped[str] = mapped_column(String(60), default="UNKNOWN")
    current_path_index: Mapped[int] = mapped_column(Integer, default=0)
    rtk_status: Mapped[str] = mapped_column(Text, default="{}")
    network_status: Mapped[str] = mapped_column(String(60), default="unknown")
    exception_status: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(40))  # device/system
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    language: Mapped[str] = mapped_column(String(40), default="English")
    region: Mapped[str] = mapped_column(String(40), default="Auto")
    device_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    system_notifications: Mapped[bool] = mapped_column(Boolean, default=True)

class HelpArticle(Base):
    __tablename__ = "help_articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), default="operation")
    content: Mapped[str] = mapped_column(Text)


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
