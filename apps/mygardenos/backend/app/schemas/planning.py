from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MapPoint(BaseModel):
    x: float
    y: float
    lat: Optional[float] = None
    lng: Optional[float] = None


class PropertyCreate(BaseModel):
    name: str
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coordinate_system: str = "GOS-MAP-XY"
    status: str = "draft"


class PropertyOut(PropertyCreate):
    id: int
    customer_id: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class MapCreate(BaseModel):
    map_type: str = "manual"
    source_file_url: str = ""
    image_url: str = ""
    point_cloud_url: str = ""
    coordinate_transform: Dict[str, Any] = {}
    version: int = 1
    status: str = "draft"


class MapOut(MapCreate):
    id: int
    property_id: int
    created_at: datetime


class ZoneCreate(BaseModel):
    name: str
    zone_type: str
    polygon_coordinates: List[MapPoint]
    priority: int = 0
    metadata: Dict[str, Any] = {}


class ZoneOut(ZoneCreate):
    id: int
    property_id: int
    map_id: int
    created_at: datetime


class DockCreate(BaseModel):
    position: MapPoint
    heading: float = 0.0
    related_zone_id: Optional[int] = None
    network_available: bool = True
    status: str = "draft"


class DockOut(DockCreate):
    id: int
    property_id: int
    map_id: int
    created_at: datetime


class PathGenerateIn(BaseModel):
    work_zone_id: int
    no_go_zone_ids: Optional[List[int]] = None
    dock_id: Optional[int] = None
    blade_width: float = 0.21
    overlap_ratio: float = 0.1
    path_angle: float = 0.0
    status: str = "draft"


class MowingPathOut(BaseModel):
    id: int
    property_id: int
    map_id: int
    work_zone_id: int
    no_go_zone_ids: List[int]
    dock_id: Optional[int] = None
    path_points: List[MapPoint]
    blade_width: float
    overlap_ratio: float
    path_angle: float
    version: int
    estimated_distance: float
    estimated_duration_seconds: int
    status: str
    created_at: datetime


class MowingTaskCreate(BaseModel):
    path_id: int
    work_zone_id: int
    robot_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    customer_confirmation_required: bool = True


class CustomerConfirmationIn(BaseModel):
    yard_cleared: bool
    allowed_start_time: str
    allowed_end_time: str


class MowingTaskOut(BaseModel):
    id: int
    property_id: int
    map_id: int
    work_zone_id: int
    path_id: int
    robot_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    allowed_start_time: Optional[str] = None
    allowed_end_time: Optional[str] = None
    customer_confirmation_status: str
    status: str
    current_path_index: int
    progress_percent: float
    created_at: datetime
    updated_at: datetime


class TaskEventOut(BaseModel):
    id: int
    task_id: int
    event_type: str
    message: str
    metadata: Dict[str, Any]
    created_at: datetime


class RobotHeartbeatIn(BaseModel):
    task_id: Optional[int] = None
    position: MapPoint
    battery_level: int
    charging_status: str = "not_charging"
    task_status: str = "UNKNOWN"
    current_path_index: int = 0
    rtk_status: Dict[str, Any] = {}
    network_status: str = "online"
    exception_status: Optional[str] = None


class RobotTelemetryOut(BaseModel):
    id: int
    robot_identifier: str
    task_id: Optional[int] = None
    position: MapPoint
    battery_level: int
    charging_status: str
    task_status: str
    current_path_index: int
    rtk_status: Dict[str, Any]
    network_status: str
    exception_status: Optional[str] = None
    created_at: datetime
