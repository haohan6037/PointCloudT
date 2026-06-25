import json
import math
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Dock, MowingPath, MowingTask, TaskEvent, Zone
from app.schemas.planning import (
    CustomerConfirmationIn,
    MowingPathOut,
    MowingTaskCreate,
    MowingTaskOut,
    PathGenerateIn,
    TaskEventOut,
)
from app.services.auth_context import device_for_user, get_user_from_bearer, validate_time_hhmm
from app.services.path_planner import estimate_path_distance, generate_parallel_path_points
from app.services.planning_runtime import (
    add_task_event,
    json_loads,
    map_for_user,
    path_out,
    task_event_out,
    task_for_user,
    task_out,
    zone_polygon,
)


router = APIRouter()


@router.get("/maps/{map_id}/paths", response_model=list[MowingPathOut])
def list_paths(
    map_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    map_for_user(db, user, map_id)
    paths = db.query(MowingPath).filter(MowingPath.map_id == map_id).order_by(MowingPath.version, MowingPath.id).all()
    return [path_out(path) for path in paths]


@router.post("/maps/{map_id}/paths/generate", response_model=MowingPathOut)
def generate_path(
    map_id: int,
    payload: PathGenerateIn,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    garden_map = map_for_user(db, user, map_id)
    if payload.blade_width <= 0:
        raise HTTPException(400, "blade_width must be greater than 0")
    if payload.overlap_ratio < 0 or payload.overlap_ratio >= 1:
        raise HTTPException(400, "overlap_ratio must be between 0 and 1")

    work_zone = db.get(Zone, payload.work_zone_id)
    if not work_zone or work_zone.map_id != garden_map.id:
        raise HTTPException(400, "work_zone_id must belong to this map")
    if work_zone.zone_type.upper() != "WORK_AREA":
        raise HTTPException(400, "work_zone_id must reference a WORK_AREA zone")

    if payload.no_go_zone_ids is None:
        no_go_zones = db.query(Zone).filter(Zone.map_id == garden_map.id, Zone.zone_type == "NO_GO").all()
    else:
        no_go_zones = []
        for zone_id in payload.no_go_zone_ids:
            zone = db.get(Zone, zone_id)
            if not zone or zone.map_id != garden_map.id:
                raise HTTPException(400, "no_go_zone_ids must belong to this map")
            no_go_zones.append(zone)

    dock_position = None
    if payload.dock_id is not None:
        dock = db.get(Dock, payload.dock_id)
        if not dock or dock.map_id != garden_map.id:
            raise HTTPException(400, "dock_id must belong to this map")
        dock_position = json_loads(dock.position, None)

    try:
        path_points = generate_parallel_path_points(
            zone_polygon(work_zone),
            [zone_polygon(zone) for zone in no_go_zones],
            payload.blade_width,
            payload.overlap_ratio,
            payload.path_angle,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not path_points:
        raise HTTPException(400, "Unable to generate path points for this work zone")
    if dock_position:
        path_points = [dock_position, *path_points, dock_position]

    latest_version = (
        db.query(MowingPath)
        .filter(MowingPath.map_id == garden_map.id, MowingPath.work_zone_id == work_zone.id)
        .count()
    )
    distance = estimate_path_distance(path_points)
    path = MowingPath(
        property_id=garden_map.property_id,
        map_id=garden_map.id,
        work_zone_id=work_zone.id,
        no_go_zone_ids=json.dumps([zone.id for zone in no_go_zones]),
        dock_id=payload.dock_id,
        path_points=json.dumps(path_points),
        blade_width=payload.blade_width,
        overlap_ratio=payload.overlap_ratio,
        path_angle=payload.path_angle,
        version=latest_version + 1,
        estimated_distance=distance,
        estimated_duration_seconds=math.ceil(distance / 0.35),
        status=payload.status,
    )
    db.add(path)
    db.commit()
    db.refresh(path)
    return path_out(path)


@router.get("/maps/{map_id}/tasks", response_model=list[MowingTaskOut])
def list_tasks(
    map_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    map_for_user(db, user, map_id)
    tasks = db.query(MowingTask).filter(MowingTask.map_id == map_id).order_by(MowingTask.id).all()
    return [task_out(task) for task in tasks]


@router.post("/maps/{map_id}/tasks", response_model=MowingTaskOut)
def create_task(
    map_id: int,
    payload: MowingTaskCreate,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    garden_map = map_for_user(db, user, map_id)
    path = db.get(MowingPath, payload.path_id)
    if not path or path.map_id != garden_map.id:
        raise HTTPException(400, "path_id must belong to this map")
    if path.work_zone_id != payload.work_zone_id:
        raise HTTPException(400, "work_zone_id must match the selected path")
    if payload.robot_id is not None:
        device_for_user(db, user, payload.robot_id)

    status = "WAITING_CUSTOMER_CONFIRMATION" if payload.customer_confirmation_required else "SCHEDULED"
    confirmation_status = "pending" if payload.customer_confirmation_required else "not_required"
    task = MowingTask(
        property_id=garden_map.property_id,
        map_id=garden_map.id,
        work_zone_id=payload.work_zone_id,
        path_id=path.id,
        robot_id=payload.robot_id,
        scheduled_at=payload.scheduled_at,
        customer_confirmation_status=confirmation_status,
        status=status,
    )
    db.add(task)
    db.flush()
    add_task_event(db, task, "TASK_CREATED", "Mowing task created", {"status": status})
    db.commit()
    db.refresh(task)
    return task_out(task)


@router.get("/tasks/{task_id}/events", response_model=list[TaskEventOut])
def list_task_events(
    task_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    task_for_user(db, user, task_id)
    events = db.query(TaskEvent).filter(TaskEvent.task_id == task_id).order_by(TaskEvent.id).all()
    return [task_event_out(event) for event in events]


@router.post("/tasks/{task_id}/customer-confirm", response_model=MowingTaskOut)
def confirm_task_by_customer(
    task_id: int,
    payload: CustomerConfirmationIn,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    task = task_for_user(db, user, task_id)
    task.allowed_start_time = validate_time_hhmm(payload.allowed_start_time, "allowed_start_time")
    task.allowed_end_time = validate_time_hhmm(payload.allowed_end_time, "allowed_end_time")
    if not payload.yard_cleared:
        task.customer_confirmation_status = "blocked"
        task.status = "BLOCKED"
        add_task_event(db, task, "CUSTOMER_BLOCKED", "Customer has not confirmed yard is clear")
    else:
        task.customer_confirmation_status = "confirmed"
        task.status = "SCHEDULED"
        add_task_event(
            db,
            task,
            "CUSTOMER_CONFIRMED",
            "Customer confirmed yard is clear and approved work window",
            {"allowed_start_time": task.allowed_start_time, "allowed_end_time": task.allowed_end_time},
        )
    db.commit()
    db.refresh(task)
    return task_out(task)


@router.post("/tasks/{task_id}/dispatch", response_model=MowingTaskOut)
def dispatch_task(
    task_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    task = task_for_user(db, user, task_id)
    if task.customer_confirmation_status == "pending":
        raise HTTPException(409, "Task is waiting for customer confirmation")
    if task.status not in {"SCHEDULED", "PAUSED", "RESUMING"}:
        raise HTTPException(409, f"Task cannot be dispatched from status {task.status}")
    task.status = "DISPATCHED"
    add_task_event(db, task, "TASK_DISPATCHED", "Task moved to dispatched state for demo flow")
    db.commit()
    db.refresh(task)
    return task_out(task)
