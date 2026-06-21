# Robot Coordinate Alignment Spec V1

## Purpose

This document defines the coordinate contract that GardenOS/PointCloudTT will use before discussing robot position reporting with the robot manufacturer.

The goal is to make every geometry and every MQTT robot pose comparable in one canonical 2D frame, so the platform can calculate:

```text
manual_follow_up_area = work_area - robot_covered_area - excluded_area
```

This document does not define robot movement commands. It only defines map, pose, transform, and reporting requirements for coverage analysis.

## Canonical Frame

GardenOS uses one canonical 2D map frame for coverage analysis:

```text
Frame name: GOS-MAP-XY
Unit: meter
Origin: fixed per map
Axis: +X to map right/east, +Y to map up/north
Handedness: right-handed 2D frame
Angle: radians, counter-clockwise positive from +X
Timestamp: UTC, milliseconds since Unix epoch when available
```

Rules:

- All work areas, no-go zones, robot tracks, and coverage polygons must be converted into `GOS-MAP-XY` before analysis.
- UI image/pixel coordinates are never the source of truth for coverage.
- Pixel coordinates may be stored for review display, but exported analysis geometry must use meters.
- `GOS-MAP-XY` origin must not change after a map has robot history.
- If the source map comes from point-cloud top-view export, the map export must store the transform from point-cloud coordinates to `GOS-MAP-XY`.
- If the robot uses its own internal coordinate frame, the platform must store a transform from robot coordinates to `GOS-MAP-XY`.

## Recommended Origin

Preferred origin:

```text
origin = charging station / base station reference point
```

Use this if the robot firmware can define positions relative to the charging station or RTK/base station.

Fallback origin:

```text
origin = point-cloud map local origin
```

Use this only when the map is not tied to the charging station yet. In that case, a separate `T_robot_to_map` transform is mandatory before MQTT robot positions can be used for coverage.

The origin definition must be stored in map metadata:

```json
{
  "coordinateSystem": {
    "frame": "GOS-MAP-XY",
    "unit": "meter",
    "origin": [0, 0],
    "originType": "charging_station",
    "axis": {
      "xPositive": "map_right_or_east",
      "yPositive": "map_up_or_north"
    },
    "angleUnit": "radian",
    "yawConvention": "counter_clockwise_from_positive_x"
  }
}
```

## Coordinate Sources

The platform may receive geometry from several source frames.

### 1. Point-Cloud Local XY

Source:

```text
Frame name: PC-LOCAL-XY
Unit: meter, if source scale is known
Typical use: top-view image and editable work-area polygon
```

Required transform:

```text
T_pc_to_map: PC-LOCAL-XY -> GOS-MAP-XY
```

### 2. Robot Internal XY

Source:

```text
Frame name: ROBOT-LOCAL-XY
Unit: must be confirmed by manufacturer
Typical use: robot MQTT pose if firmware reports x/y
```

Required transform:

```text
T_robot_to_map: ROBOT-LOCAL-XY -> GOS-MAP-XY
```

Manufacturer must confirm:

- Unit: meter, centimeter, millimeter, or other.
- Origin: charging station, first boot point, map origin, RTK base, or another point.
- Axis direction: which physical direction is +X and +Y.
- Whether coordinates reset after reboot, remap, relocation, or firmware update.
- Whether `x/y` are robot center, antenna point, cutter center, or another reference point.
- Whether heading/yaw uses degrees or radians.
- Whether heading/yaw is clockwise or counter-clockwise.
- Whether heading/yaw is relative to +X, north, robot forward, or another axis.

### 3. WGS84 GPS

Source:

```text
Frame name: WGS84
Fields: latitude, longitude, optional altitude
Typical use: GPS/RTK reporting
```

Required transform:

```text
T_wgs84_to_map: WGS84 -> local ENU -> GOS-MAP-XY
```

Rules:

- Use WGS84 decimal degrees for raw latitude/longitude.
- Convert to local tangent plane in meters before coverage analysis.
- Store the reference latitude/longitude used for the local tangent plane.
- Store accuracy fields if available.

## Transform Model

The MVP transform is a 2D similarity transform:

```text
map_x = scale * (cos(theta) * source_x - sin(theta) * source_y) + translate_x
map_y = scale * (sin(theta) * source_x + cos(theta) * source_y) + translate_y
```

Stored as:

```json
{
  "fromFrame": "ROBOT-LOCAL-XY",
  "toFrame": "GOS-MAP-XY",
  "type": "similarity_2d",
  "scale": 1.0,
  "rotationRad": 0.0,
  "translation": [0.0, 0.0],
  "rmseM": 0.0,
  "controlPointCount": 0,
  "createdAt": "2026-06-21T00:00:00Z"
}
```

Quality thresholds:

```text
rmseM < 0.30   good for coverage analysis
0.30 - 0.80    usable, review edge cases manually
> 0.80         not acceptable for automatic missed-area output
```

If the robot coordinate frame has non-uniform scale, skew, or map warping, the manufacturer must document it explicitly. The platform should not guess.

## MQTT Pose Message Requirement

The platform will preserve the robot's existing topic behavior. The manufacturer does not need to rename existing topics if the payload can include these fields.

Minimum normalized pose fields needed by GardenOS:

```json
{
  "robotId": "robot-001",
  "timestampMs": 1782024985300,
  "frame": "ROBOT-LOCAL-XY",
  "x": 12.345,
  "y": 6.789,
  "yawRad": 1.5708,
  "state": "working",
  "positionQuality": "valid"
}
```

Accepted alternatives:

```json
{
  "robotId": "robot-001",
  "timestampMs": 1782024985300,
  "frame": "WGS84",
  "lat": -36.8501234,
  "lng": 174.7605678,
  "headingDeg": 90.0,
  "state": "working",
  "accuracyM": 0.15
}
```

Required meaning:

- `robotId`: stable device identifier.
- `timestampMs`: position sample time, not server receive time.
- `frame`: source coordinate frame of this message.
- `x/y` or `lat/lng`: position of a declared robot reference point.
- `yawRad` or `headingDeg`: robot heading if available.
- `state`: enough to distinguish working/mowing from idle/charging/error/manual movement.
- `positionQuality`: valid, degraded, invalid, or unknown.
- `accuracyM`: estimated horizontal accuracy if available.

If the robot cannot change payload names, the manufacturer must provide a field mapping table.

Example mapping table:

| GardenOS field | Manufacturer field | Unit | Notes |
| --- | --- | --- | --- |
| `robotId` | `id` | string | Stable per robot |
| `timestampMs` | `ts` | ms | UTC preferred |
| `x` | `pos_x` | meter | Confirm reference point |
| `y` | `pos_y` | meter | Confirm axis direction |
| `state` | `work_state` | enum | Map to working/idle/error |

## Robot Reference Point

Coverage depends on the physical point represented by the position sample.

Manufacturer must confirm one of:

```text
robot_center
cutter_center
gps_antenna
rear_axle_center
custom_point
```

If the position point is not the cutter center, the platform must store an offset:

```json
{
  "robotPoseReference": "gps_antenna",
  "cutterOffsetM": {
    "forward": -0.35,
    "left": 0.0
  },
  "cutWidthM": 0.42
}
```

## Coverage Analysis Inputs

Coverage analysis requires:

```text
map_id
work_area polygon in GOS-MAP-XY
excluded_area polygons in GOS-MAP-XY
robot_id
time range
pose samples converted to GOS-MAP-XY
working-state filter
cut_width_m
position accuracy policy
```

Default coverage rule:

```text
covered_area = buffer(working_track_line, cut_width_m / 2 + tolerance_m)
missed_area = work_area - covered_area - excluded_area
```

Recommended defaults:

```text
sample_gap_max_seconds = 10
track_segment_max_distance_m = 2.0
tolerance_m = max(0.05, accuracyM if available)
minimum_report_area_m2 = 0.25
minimum_report_width_m = 0.20
```

If two consecutive pose samples are too far apart or too far apart in time, do not connect them into one coverage segment.

## Calibration Procedure Before Manufacturer Integration

Before accepting robot coordinates as production input:

1. Export or create a point-cloud map with a fixed work area.
2. Mark 3-6 physical control points visible in the map and reachable by the robot.
3. Ask the robot/manufacturer system to report coordinates at each control point.
4. Fit `T_robot_to_map` using those paired points.
5. Store transform and `rmseM`.
6. Drive or manually move the robot around a simple test path.
7. Verify the plotted MQTT path aligns with the map within the acceptance threshold.
8. Only then use coverage and missed-area output for operations.

## Questions For Manufacturer

Ask these before implementation:

1. What coordinate frame does the robot report over MQTT?
2. Is the reported position `x/y`, `lat/lng`, both, or something else?
3. What is the unit of `x/y`?
4. Where is the origin?
5. Which direction is +X?
6. Which direction is +Y?
7. Does the frame reset after reboot, docking, firmware update, remap, or loss of signal?
8. Does the robot report heading/yaw? What unit and convention?
9. Which physical point on the robot does the reported position represent?
10. What is the mower cut width?
11. How frequently is pose reported while working?
12. What field shows the robot is actively mowing/working?
13. Is there a position accuracy or quality field?
14. Can the robot include `mapId` or task/session id in MQTT?
15. Are timestamps generated on the robot or by the server?
16. What happens to position reporting when the robot loses GPS/RTK/localization?

## Acceptance Criteria

GardenOS can accept the manufacturer coordinate integration when:

- The robot pose payload can be mapped into the normalized GardenOS pose fields.
- Every sample declares or implies a source frame.
- A stored transform exists from the source frame to `GOS-MAP-XY`.
- Control-point fit has `rmseM <= 0.80`.
- A field can distinguish working/mowing from non-working movement.
- The robot reference point and cut width are known.
- Test MQTT tracks overlay correctly on the point-cloud work-area map.
- Missed-area output is manually reviewed before being used for customer or contractor workflow.

## Non-Goals

This spec does not cover:

- Robot movement command publishing.
- Emergency stop behavior.
- Duplicate command prevention.
- Route planning.
- Autonomous control authority.
- Payment or service settlement.

Those require separate safety design.
