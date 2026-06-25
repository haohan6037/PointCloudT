import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Dock, Property, PropertyMap, Zone
from app.schemas.planning import (
    DockCreate,
    DockOut,
    MapCreate,
    MapOut,
    PropertyCreate,
    PropertyOut,
    ZoneCreate,
    ZoneOut,
)
from app.services.auth_context import get_user_from_bearer
from app.services.planning_runtime import (
    dock_out,
    map_for_user,
    map_out,
    property_for_user,
    property_out,
    zone_out,
)


router = APIRouter()


@router.get("/properties", response_model=list[PropertyOut])
def list_properties(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    properties = db.query(Property).filter(Property.customer_id == user.id).order_by(Property.id).all()
    return [property_out(garden_property) for garden_property in properties]


@router.post("/properties", response_model=PropertyOut)
def create_property(
    payload: PropertyCreate,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    garden_property = Property(
        customer_id=user.id,
        name=payload.name,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        coordinate_system=payload.coordinate_system,
        status=payload.status,
    )
    db.add(garden_property)
    db.commit()
    db.refresh(garden_property)
    return property_out(garden_property)


@router.get("/properties/{property_id}/maps", response_model=list[MapOut])
def list_property_maps(
    property_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    property_for_user(db, user, property_id)
    maps = db.query(PropertyMap).filter(PropertyMap.property_id == property_id).order_by(PropertyMap.version).all()
    return [map_out(garden_map) for garden_map in maps]


@router.post("/properties/{property_id}/maps", response_model=MapOut)
def create_property_map(
    property_id: int,
    payload: MapCreate,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    property_for_user(db, user, property_id)
    garden_map = PropertyMap(
        property_id=property_id,
        map_type=payload.map_type,
        source_file_url=payload.source_file_url,
        image_url=payload.image_url,
        point_cloud_url=payload.point_cloud_url,
        coordinate_transform=json.dumps(payload.coordinate_transform),
        version=payload.version,
        status=payload.status,
    )
    db.add(garden_map)
    db.commit()
    db.refresh(garden_map)
    return map_out(garden_map)


@router.get("/maps/{map_id}/zones", response_model=list[ZoneOut])
def list_zones(
    map_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    map_for_user(db, user, map_id)
    zones = db.query(Zone).filter(Zone.map_id == map_id).order_by(Zone.priority, Zone.id).all()
    return [zone_out(zone) for zone in zones]


@router.post("/maps/{map_id}/zones", response_model=ZoneOut)
def create_zone(
    map_id: int,
    payload: ZoneCreate,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    garden_map = map_for_user(db, user, map_id)
    if len(payload.polygon_coordinates) < 3:
        raise HTTPException(400, "Zone polygon must include at least three points")
    zone = Zone(
        property_id=garden_map.property_id,
        map_id=garden_map.id,
        name=payload.name,
        zone_type=payload.zone_type,
        polygon_coordinates=json.dumps([point.model_dump() for point in payload.polygon_coordinates]),
        priority=payload.priority,
        metadata_json=json.dumps(payload.metadata),
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone_out(zone)


@router.get("/maps/{map_id}/docks", response_model=list[DockOut])
def list_docks(
    map_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    map_for_user(db, user, map_id)
    docks = db.query(Dock).filter(Dock.map_id == map_id).order_by(Dock.id).all()
    return [dock_out(dock) for dock in docks]


@router.post("/maps/{map_id}/docks", response_model=DockOut)
def create_dock(
    map_id: int,
    payload: DockCreate,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = get_user_from_bearer(authorization, db)
    garden_map = map_for_user(db, user, map_id)
    if payload.related_zone_id is not None:
        zone = db.get(Zone, payload.related_zone_id)
        if not zone or zone.map_id != garden_map.id:
            raise HTTPException(400, "related_zone_id must belong to this map")
    dock = Dock(
        property_id=garden_map.property_id,
        map_id=garden_map.id,
        position=json.dumps(payload.position.model_dump()),
        heading=payload.heading,
        related_zone_id=payload.related_zone_id,
        network_available=payload.network_available,
        status=payload.status,
    )
    db.add(dock)
    db.commit()
    db.refresh(dock)
    return dock_out(dock)
