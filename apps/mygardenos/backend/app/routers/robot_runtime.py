import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Device, RobotTelemetry
from app.schemas.planning import RobotHeartbeatIn, RobotTelemetryOut
from app.services.auth_context import get_user_from_bearer
from app.services.planning_runtime import task_for_user, telemetry_out, update_task_from_heartbeat


router = APIRouter()


@router.post("/robots/{robot_identifier}/heartbeat", response_model=RobotTelemetryOut)
def robot_heartbeat(
    robot_identifier: str,
    payload: RobotHeartbeatIn,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    if payload.task_id is not None:
        task = task_for_user(db, user, payload.task_id)
        if task.robot_id is not None:
            device = db.get(Device, task.robot_id)
            allowed_identifiers = {str(task.robot_id)}
            if device:
                allowed_identifiers.add(device.serial)
            if robot_identifier not in allowed_identifiers:
                raise HTTPException(400, "robot_identifier does not match task robot")
        update_task_from_heartbeat(db, task, payload)

    telemetry = RobotTelemetry(
        robot_identifier=robot_identifier,
        task_id=payload.task_id,
        position=json.dumps(payload.position.model_dump()),
        battery_level=payload.battery_level,
        charging_status=payload.charging_status,
        task_status=payload.task_status,
        current_path_index=payload.current_path_index,
        rtk_status=json.dumps(payload.rtk_status),
        network_status=payload.network_status,
        exception_status=payload.exception_status,
    )
    db.add(telemetry)
    db.commit()
    db.refresh(telemetry)
    return telemetry_out(telemetry)


@router.get("/robots/{robot_identifier}/telemetry", response_model=list[RobotTelemetryOut])
def robot_telemetry(
    robot_identifier: str,
    limit: int = Query(20, ge=1, le=100),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    get_user_from_bearer(authorization, db)
    rows = (
        db.query(RobotTelemetry)
        .filter(RobotTelemetry.robot_identifier == robot_identifier)
        .order_by(RobotTelemetry.id.desc())
        .limit(limit)
        .all()
    )
    return [telemetry_out(row) for row in reversed(rows)]
