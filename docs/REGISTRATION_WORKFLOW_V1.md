# Registration Workflow V1

## Purpose

Align pointcloud top-view local XY coordinates with Auckland Council NZTM (EPSG:2193), so official property boundaries can be used for clipping.

## Files

- Click tool: [registration_lab.html](/Users/happyfamily/MyProject/PointCloudTT/docs/registration_lab.html)
- Transform solver: [fit_similarity_transform.py](/Users/happyfamily/MyProject/PointCloudTT/scripts/fit_similarity_transform.py)

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
