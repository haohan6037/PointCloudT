# PointCloudTT Map Schema

## 1. Purpose

This document defines the first map data structure for PointCloudTT.

The schema must support:

- A stable coordinate system.
- One editable outer boundary.
- Multiple semantic annotations.
- Future annotation types.
- Import and export across versions.

The schema should stay separate from UI state. Editor-only values such as selected object, hover state, temporary handles, and undo history should not be exported as map data.

## 2. Top-Level Shape

```json
{
  "version": "0.1",
  "metadata": {},
  "coordinateSystem": {},
  "source": {},
  "boundary": {},
  "annotations": []
}
```

## 3. Example Map

```json
{
  "version": "0.1",
  "metadata": {
    "name": "Demo Map",
    "createdAt": "2026-05-29T00:00:00Z",
    "updatedAt": "2026-05-29T00:00:00Z"
  },
  "coordinateSystem": {
    "unit": "meter",
    "origin": [0, 0],
    "rotation": 0,
    "scale": 1
  },
  "source": {
    "type": "point_cloud",
    "filename": "demo.ply",
    "pointCount": 1200000,
    "bounds3d": {
      "min": [-5.2, -3.1, -0.4],
      "max": [18.6, 12.9, 2.8]
    }
  },
  "boundary": {
    "id": "boundary_main",
    "geometry": {
      "type": "polygon",
      "points": [[0, 0], [10, 0], [10, 8], [0, 8]]
    },
    "properties": {
      "name": "Main Boundary"
    }
  },
  "annotations": [
    {
      "id": "zone_001",
      "type": "no_go_zone",
      "geometry": {
        "type": "polygon",
        "points": [[2, 2], [4, 2], [4, 3], [2, 3]]
      },
      "properties": {
        "name": "No-Go Zone A",
        "priority": 1
      }
    },
    {
      "id": "corridor_001",
      "type": "corridor",
      "geometry": {
        "type": "polygon",
        "points": [[5, 1], [7, 1], [7, 2], [5, 2]]
      },
      "properties": {
        "name": "Corridor A",
        "direction": "bidirectional"
      }
    }
  ]
}
```

## 4. Coordinate System

```json
{
  "unit": "meter",
  "origin": [0, 0],
  "rotation": 0,
  "scale": 1
}
```

Fields:

- `unit`: Physical unit. MVP should use `meter`.
- `origin`: 2D world coordinate origin.
- `rotation`: Rotation in radians from source point-cloud frame to map frame.
- `scale`: Multiplier from source units to map units.

Rules:

- Exported geometry uses map world coordinates, not screen pixels.
- UI may transform map coordinates to canvas coordinates internally.
- Changing coordinate settings after annotation exists should be treated as a high-risk operation.

## 5. Geometry Types

### Point

```json
{
  "type": "point",
  "point": [1.2, 3.4]
}
```

### LineString

```json
{
  "type": "line_string",
  "points": [[1, 1], [2, 2], [3, 2]]
}
```

### Polygon

```json
{
  "type": "polygon",
  "points": [[0, 0], [10, 0], [10, 8], [0, 8]]
}
```

Polygon rules:

- The first point does not need to be repeated as the last point.
- A polygon must have at least 3 points.
- Self-intersection should be invalid unless a future schema explicitly allows it.
- Ring orientation should not carry semantic meaning in version `0.1`.

## 6. Boundary

The MVP supports one main boundary:

```json
{
  "id": "boundary_main",
  "geometry": {
    "type": "polygon",
    "points": []
  },
  "properties": {
    "name": "Main Boundary"
  }
}
```

Validation rules:

- Boundary must exist before export.
- Boundary must be a polygon.
- Boundary must have at least 3 points.
- Boundary must not self-intersect.

## 7. Annotation Object

All semantic map objects use the same wrapper:

```json
{
  "id": "annotation_id",
  "type": "annotation_type",
  "geometry": {},
  "properties": {}
}
```

Required fields:

- `id`: Stable unique identifier.
- `type`: Annotation type string.
- `geometry`: Geometry object.
- `properties`: Type-specific metadata.

This wrapper is the main extension point.

## 8. Initial Annotation Types

### no_go_zone

Purpose: Area that should be excluded from normal traversal or operation.

Geometry:

- MVP: `polygon`

Properties:

```json
{
  "name": "No-Go Zone A",
  "priority": 1,
  "reason": "restricted"
}
```

Validation:

- Must be inside or intersecting the main boundary.
- Should not fully cover the whole boundary.
- Must not self-intersect.

### corridor

Purpose: Passage or allowed route.

Geometry:

- MVP: `polygon`
- Future: `line_string` plus width

Properties:

```json
{
  "name": "Corridor A",
  "direction": "bidirectional",
  "width": 1.2
}
```

Allowed direction values:

- `bidirectional`
- `forward`
- `reverse`
- `unspecified`

Validation:

- Must have interpretable geometry.
- Should be inside the main boundary.
- If `width` exists, it must be positive.

## 9. Future Annotation Types

Potential future types:

- `work_area`
- `charging_zone`
- `obstacle`
- `temporary_block`
- `entry_point`
- `exit_point`
- `waypoint`
- `preferred_path`
- `speed_limit_zone`
- `slope_warning`

The editor should not hard-code all behavior into one large switch. Type-specific logic should be registered through annotation definitions.

## 10. Annotation Type Definition

A future internal registry can describe annotation behavior:

```json
{
  "type": "no_go_zone",
  "label": "No-Go Zone",
  "allowedGeometry": ["polygon"],
  "defaultProperties": {
    "name": "",
    "priority": 1
  },
  "style": {
    "stroke": "#d92d20",
    "fill": "#f0443833"
  }
}
```

This registry can drive:

- Toolbar items.
- Layer colors.
- Default properties.
- Validation rules.
- Export compatibility.

## 11. Versioning

Use a string version field:

```json
{
  "version": "0.1"
}
```

Rules:

- The app should reject unknown future versions unless migration exists.
- The app should preserve unknown annotation properties where possible.
- Breaking schema changes should increment the major version.

## 12. Export Validation Checklist

Before export:

- `version` exists.
- `coordinateSystem` exists.
- `boundary` exists and is valid.
- Every annotation has `id`, `type`, `geometry`, and `properties`.
- Every geometry uses map world coordinates.
- No required field is stored only in UI state.

