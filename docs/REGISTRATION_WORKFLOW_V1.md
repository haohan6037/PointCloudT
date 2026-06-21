# Registration Workflow V1

## Purpose

Align pointcloud top-view local XY coordinates with Auckland Council NZTM (EPSG:2193), so official property boundaries can be used for clipping.

## Files

- LAS CRS workflow: [LAS_EPSG_COORDINATE_WORKFLOW_V1.md](/Users/happyfamily/MyProject/PointCloudTT/docs/LAS_EPSG_COORDINATE_WORKFLOW_V1.md)
- Click tool: [registration_lab.html](/Users/happyfamily/MyProject/PointCloudTT/docs/registration_lab.html)
- Transform solver: [fit_similarity_transform.py](/Users/happyfamily/MyProject/PointCloudTT/scripts/fit_similarity_transform.py)

## Step 0: Identify LAS source CRS

Before collecting manual registration points, identify the LAS source coordinate system.

Rules:

1. Read LAS header with `laspy`.
2. Prefer `las.header.parse_crs()`.
3. If the file has no CRS, use the project fallback `EPSG:32760` (`WGS84 / UTM Zone 60S`) and record that fallback was used.
4. Convert the LAS center to `EPSG:4326` with `pyproj` and `always_xy=True`.
5. Open the Google Maps URL and confirm the location is near the expected property.

Reference code:

```python
from pyproj import CRS, Transformer

source_crs = las.header.parse_crs() or CRS.from_epsg(32760)
transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
lon, lat = transformer.transform(center_x, center_y)
google_maps_url = f"https://www.google.com/maps?q={lat},{lon}"
```

Do not treat LAS `x/y` as latitude/longitude.

## Step 1: Collect control-point pairs in browser

Open:

- `http://127.0.0.1:5276/docs/registration_lab.html`

Operation:

1. Click one point on PointCloud image.
2. Click the matching point on Council aerial image.
3. Repeat for 3-6 pairs spread across the property.
4. Click `Copy JSON`.
5. Save pasted JSON to:
   - `.codex-artifacts/council-context/registration_pairs.json`

## Step 2: Fit similarity transform

Run:

```bash
.venv/bin/python scripts/fit_similarity_transform.py \
  .codex-artifacts/council-context/registration_pairs.json
```

Default output:

- `.codex-artifacts/council-context/registration_transform.json`

## How to read result quality

- `rmse_m` is the control-point fit error in meters.
- Practical threshold for this project:
  - `< 0.8m`: good enough for first boundary clipping trial
  - `0.8m - 1.5m`: usable with caution; improve point picks
  - `> 1.5m`: re-pick control points

## Tips for stable control points

1. Pick hard corners or strong visual anchors visible in both images.
2. Avoid trees/shadows as anchor points.
3. Do not place all points in one small area.
4. Prefer points near property corners and long-edge bends.
