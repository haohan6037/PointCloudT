# LAS EPSG Coordinate Workflow V1

## Purpose

This document defines how PointCloudTT should locate uploaded LAS/LAZ point-cloud files in real-world coordinates.

The core rule is:

```text
Do not treat LAS x/y values as latitude/longitude.
```

LAS coordinates are usually projected coordinates in meters or feet. They must be interpreted through the LAS file CRS before generating Google Maps links, matching official property boundaries, or aligning robot MQTT positions.

## Coordinate Outputs

The workflow has two different outputs:

| Output | CRS | Purpose |
| --- | --- | --- |
| WGS84 longitude/latitude | `EPSG:4326` | Google Maps links, human location sanity check |
| Auckland Council / NZTM coordinates | `EPSG:2193` | Council imagery/boundary clipping and map registration |

Use `EPSG:4326` only for map links and human-readable location checks. Use meter-based projected coordinates for geometry analysis.

## Default Source CRS Rule

When reading a LAS file:

1. Read the LAS header with `laspy`.
2. Prefer `las.header.parse_crs()`.
3. If the LAS file has no CRS, use the project fallback:

```text
EPSG:32760
WGS84 / UTM Zone 60S
```

This fallback is intended for Auckland-area data when no embedded CRS exists. It must be treated as an assumption, not a verified fact.

Validation rules for fallback:

- If the converted center is far outside New Zealand, stop and ask for CRS confirmation.
- If the LAS bounds look like longitude/latitude values, do not force `EPSG:32760`; inspect manually.
- If official Council boundary alignment is required, verify against `EPSG:2193` data with control points.

## Center Point Calculation

Use the LAS header bounds to calculate the center:

```text
center_x = (min_x + max_x) / 2
center_y = (min_y + max_y) / 2
```

Use header bounds for fast location checks. Do not load all points just to calculate the file center.

## Convert LAS Center To WGS84

Use `pyproj` with `always_xy=True`.

Important:

- Input order is always `x, y`.
- Output order from this transformer is `lon, lat`.
- Google Maps URL wants `lat,lon`.

Reference code:

```python
import laspy
from pyproj import CRS, Transformer

las = laspy.open("input.las")
header = las.header

source_crs = header.parse_crs() or CRS.from_epsg(32760)

min_x, min_y = float(header.mins[0]), float(header.mins[1])
max_x, max_y = float(header.maxs[0]), float(header.maxs[1])

center_x = (min_x + max_x) / 2
center_y = (min_y + max_y) / 2

transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
lon, lat = transformer.transform(center_x, center_y)

google_maps_url = f"https://www.google.com/maps?q={lat},{lon}"
```

## Convert LAS Coordinates To NZTM

Auckland Council services used by this project return NZTM coordinates:

```text
EPSG:2193
```

When aligning LAS-derived top-view imagery with Council imagery or official property boundaries, convert the LAS source CRS to `EPSG:2193`:

```python
from pyproj import CRS, Transformer

source_crs = header.parse_crs() or CRS.from_epsg(32760)
to_nztm = Transformer.from_crs(source_crs, CRS.from_epsg(2193), always_xy=True)

nztm_x, nztm_y = to_nztm.transform(center_x, center_y)
```

Use `EPSG:2193` for:

- Auckland Council aerial imagery.
- Auckland Council property boundary overlays.
- Control-point registration against Council map data.
- Official clipping and spatial comparison.

## Relationship To PointCloudTT Map Frames

PointCloudTT uses these frames:

| Frame | Meaning |
| --- | --- |
| `LAS-SOURCE-CRS` | CRS from LAS header, or fallback `EPSG:32760` |
| `EPSG:4326` | WGS84 lon/lat for links and sanity checks |
| `EPSG:2193` | NZTM for Auckland Council data |
| `PC-LOCAL-XY` | Point-cloud top-view local map coordinates |
| `GOS-MAP-XY` | Canonical GardenOS robot coverage frame in meters |

Suggested pipeline:

```text
LAS-SOURCE-CRS
  -> EPSG:4326 for Google Maps sanity check
  -> EPSG:2193 for Council boundary/aerial registration
  -> PC-LOCAL-XY / GOS-MAP-XY for editable work areas and robot coverage
```

## Metadata To Store

When processing an uploaded LAS/LAZ file, store:

```json
{
  "sourceCrs": "EPSG:32760",
  "sourceCrsDetected": false,
  "sourceCrsFallbackReason": "las_header_missing_crs",
  "boundsSource": {
    "min": [0, 0, 0],
    "max": [0, 0, 0]
  },
  "centerSource": [0, 0],
  "centerWgs84": {
    "lat": -36.850123,
    "lon": 174.760456
  },
  "centerNztm2193": [0, 0],
  "googleMapsUrl": "https://www.google.com/maps?q=-36.850123,174.760456"
}
```

If the CRS came from the LAS header:

```json
{
  "sourceCrsDetected": true,
  "sourceCrsFallbackReason": null
}
```

If fallback was used, surface that in the UI so the user knows the location is assumed.

## Sanity Checks

For Auckland projects:

- WGS84 latitude should be roughly around `-37`.
- WGS84 longitude should be roughly around `174`.
- NZTM `EPSG:2193` values should be meter-scale projected coordinates, not decimal degrees.
- Google Maps links must use `lat,lon`, not `lon,lat`.
- Any LAS file with missing CRS must be flagged as assumed until visually confirmed.

## Common Mistakes

Avoid:

- Treating LAS `x/y` as `lat/lng`.
- Passing `lat,lng` into a transformer that expects `x,y`.
- Forgetting `always_xy=True`.
- Using WGS84 decimal degrees for polygon area or coverage calculations.
- Mixing image pixel coordinates with projected meter coordinates.
- Assuming fallback `EPSG:32760` is always correct.

## Acceptance Criteria

The LAS coordinate workflow is acceptable when:

- The source CRS is detected from LAS header or fallback is explicitly recorded.
- The LAS center can be transformed to `EPSG:4326`.
- Google Maps URL opens near the expected property.
- The same source CRS can transform LAS bounds/points to `EPSG:2193`.
- Council aerial/property overlay can be visually or control-point verified.
- All map exports record enough CRS metadata to repeat the transform later.
