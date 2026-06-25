import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import (
    Dock,
    MowingPath,
    MowingTask,
    Property,
    PropertyMap,
    RobotTelemetry,
    TaskEvent,
    User,
    Zone,
)
from app.schemas.planning import (
    DockOut,
    MapOut,
    MowingPathOut,
    MowingTaskOut,
    PropertyOut,
    RobotHeartbeatIn,
    RobotTelemetryOut,
    TaskEventOut,
    ZoneOut,
)


def json_loads(value: str, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def property_for_user(db: Session, user: User, property_id: int) -> Property:
    garden_property = db.get(Property, property_id)
    if not garden_property or garden_property.customer_id != user.id:
        raise HTTPException(404, "Property not found")
    return garden_property


def map_for_user(db: Session, user: User, map_id: int) -> PropertyMap:
    garden_map = db.get(PropertyMap, map_id)
    if not garden_map:
        raise HTTPException(404, "Map not found")
    property_for_user(db, user, garden_map.property_id)
    return garden_map


def task_for_user(db: Session, user: User, task_id: int) -> MowingTask:
    task = db.get(MowingTask, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    property_for_user(db, user, task.property_id)
    return task


def property_out(garden_property: Property) -> PropertyOut:
    return PropertyOut.model_validate(garden_property)


def map_out(garden_map: PropertyMap) -> MapOut:
    return MapOut(
        id=garden_map.id,
        property_id=garden_map.property_id,
        map_type=garden_map.map_type,
        source_file_url=garden_map.source_file_url,
        image_url=garden_map.image_url,
        point_cloud_url=garden_map.point_cloud_url,
        coordinate_transform=json_loads(garden_map.coordinate_transform, {}),
        version=garden_map.version,
        status=garden_map.status,
        created_at=garden_map.created_at,
    )


def zone_out(zone: Zone) -> ZoneOut:
    return ZoneOut(
        id=zone.id,
        property_id=zone.property_id,
        map_id=zone.map_id,
        name=zone.name,
        zone_type=zone.zone_type,
        polygon_coordinates=json_loads(zone.polygon_coordinates, []),
        priority=zone.priority,
        metadata=json_loads(zone.metadata_json, {}),
        created_at=zone.created_at,
    )


def dock_out(dock: Dock) -> DockOut:
    return DockOut(
        id=dock.id,
        property_id=dock.property_id,
        map_id=dock.map_id,
        position=json_loads(dock.position, {}),
        heading=dock.heading,
        related_zone_id=dock.related_zone_id,
        network_available=dock.network_available,
        status=dock.status,
        created_at=dock.created_at,
    )


def path_out(path: MowingPath) -> MowingPathOut:
    return MowingPathOut(
        id=path.id,
        property_id=path.property_id,
        map_id=path.map_id,
        work_zone_id=path.work_zone_id,
        no_go_zone_ids=json_loads(path.no_go_zone_ids, []),
        dock_id=path.dock_id,
        path_points=json_loads(path.path_points, []),
        blade_width=path.blade_width,
        overlap_ratio=path.overlap_ratio,
        path_angle=path.path_angle,
        version=path.version,
        estimated_distance=path.estimated_distance,
        estimated_duration_seconds=path.estimated_duration_seconds,
        status=path.status,
        created_at=path.created_at,
    )


def task_out(task: MowingTask) -> MowingTaskOut:
    return MowingTaskOut(
        id=task.id,
        property_id=task.property_id,
        map_id=task.map_id,
        work_zone_id=task.work_zone_id,
        path_id=task.path_id,
        robot_id=task.robot_id,
        scheduled_at=task.scheduled_at,
        allowed_start_time=task.allowed_start_time,
        allowed_end_time=task.allowed_end_time,
        customer_confirmation_status=task.customer_confirmation_status,
        status=task.status,
        current_path_index=task.current_path_index,
        progress_percent=task.progress_percent,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def task_event_out(event: TaskEvent) -> TaskEventOut:
    return TaskEventOut(
        id=event.id,
        task_id=event.task_id,
        event_type=event.event_type,
        message=event.message,
        metadata=json_loads(event.metadata_json, {}),
        created_at=event.created_at,
    )


def telemetry_out(telemetry: RobotTelemetry) -> RobotTelemetryOut:
    return RobotTelemetryOut(
        id=telemetry.id,
        robot_identifier=telemetry.robot_identifier,
        task_id=telemetry.task_id,
        position=json_loads(telemetry.position, {}),
        battery_level=telemetry.battery_level,
        charging_status=telemetry.charging_status,
        task_status=telemetry.task_status,
        current_path_index=telemetry.current_path_index,
        rtk_status=json_loads(telemetry.rtk_status, {}),
        network_status=telemetry.network_status,
        exception_status=telemetry.exception_status,
        created_at=telemetry.created_at,
    )


def zone_polygon(zone: Zone) -> list[dict]:
    return json_loads(zone.polygon_coordinates, [])


def add_task_event(db: Session, task: MowingTask, event_type: str, message: str, metadata: Optional[dict] = None) -> None:
    db.add(TaskEvent(
        task_id=task.id,
        event_type=event_type,
        message=message,
        metadata_json=json.dumps(metadata or {}),
    ))


def update_task_from_heartbeat(db: Session, task: MowingTask, payload: RobotHeartbeatIn) -> None:
    path = db.get(MowingPath, task.path_id)
    path_points = json_loads(path.path_points, []) if path else []
    task.current_path_index = max(0, payload.current_path_index)
    if path_points:
        task.progress_percent = round(min(100.0, (task.current_path_index / max(1, len(path_points) - 1)) * 100), 2)

    previous_status = task.status
    rtk_reliable = payload.rtk_status.get("is_reliable", True)
    allowed_to_work = payload.rtk_status.get("allowed_to_work", True)
    fix_type = str(payload.rtk_status.get("fix_type", "")).upper()

    if payload.exception_status:
        task.status = "BLOCKED"
        event_type = "ROBOT_EXCEPTION"
        message = f"Robot reported exception: {payload.exception_status}"
    elif payload.battery_level <= 20 and payload.task_status.upper() == "RUNNING":
        task.status = "RETURNING"
        event_type = "LOW_BATTERY"
        message = "Robot reported low battery and should return to dock"
    elif not rtk_reliable or not allowed_to_work or fix_type == "NONE":
        task.status = "PAUSED"
        event_type = "RTK_UNRELIABLE"
        message = "Robot reported unreliable RTK; task paused in demo state"
    elif payload.task_status.upper() == "COMPLETED":
        task.status = "COMPLETED"
        task.progress_percent = 100.0
        event_type = "TASK_COMPLETED"
        message = "Robot reported task completed"
    elif payload.task_status.upper() == "RUNNING":
        task.status = "RUNNING"
        event_type = "ROBOT_RUNNING"
        message = "Robot heartbeat reported running progress"
    else:
        event_type = "ROBOT_HEARTBEAT"
        message = "Robot heartbeat received"

    if task.status != previous_status or event_type in {"ROBOT_EXCEPTION", "RTK_UNRELIABLE", "TASK_COMPLETED"}:
        add_task_event(
            db,
            task,
            event_type,
            message,
            {
                "battery_level": payload.battery_level,
                "current_path_index": payload.current_path_index,
                "rtk_status": payload.rtk_status,
                "network_status": payload.network_status,
            },
        )
