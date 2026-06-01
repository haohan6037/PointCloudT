# LAS Source to Top-View Color Image Design

## Goal

Generate a planar color image directly from source point-cloud data (`.las` / `.laz`), so the output is reproducible from raw scan data and is not an externally supplied image.

## Source of Truth

- Input source file: point cloud (`LAS` / `LAZ`)
- Primary script: `/Users/happyfamily/MyProject/PointCloudTT/scripts/render_topview.py`
- This script is the only generator for:
  - `topview_raw.png`
  - `topview_crop.png`
  - `topview_enhanced.png`
  - `topview_metadata.json`

## Processing Flow

1. Read point cloud with `laspy`.
2. Apply deterministic sampling by point count:
   - `step = max(1, total_points // max_points)`
3. Build color for each sampled point:
   - Prefer original LAS RGB channels if present.
   - Fallback to height-based `terrain` colormap if RGB is absent.
4. Render orthographic XY top-view scatter:
   - X/Y world coordinates to image plane
   - equal aspect ratio
   - white background
   - axis hidden
5. Save `topview_raw.png`.
6. Detect non-white content bounding box and apply padding to produce `topview_crop.png`.
7. Apply lawn-readability enhancement (mid-tone lift + mild green emphasis) to produce `topview_enhanced.png`.
8. Save metadata in `topview_metadata.json`:
   - sampled point count
   - world coordinate bounds
   - raw/crop image sizes
   - crop box in raw image

## Why this proves the image is parsed from LAS

- The rendered image depends on sampled `x/y` coordinates from the LAS file.
- Color channels are read from LAS RGB fields, or derived from LAS `z` values when RGB is missing.
- Metadata links output image dimensions to LAS world bounds.
- Re-running the script with the same input and params reproduces the same geometric layout.

## Reproducible Command

```bash
.venv/bin/python scripts/render_topview.py \
  "16 pounamu pl.las" \
  ".codex-artifacts/topview/pointcloud_topview.png" \
  --bundle-dir ".codex-artifacts/topview/stage1_bundle"
```

## Current Outputs Used by Later Stages

- Display-friendly layer: `topview_crop.png`
- Recognition-friendly layer: `topview_enhanced.png`
- Pixel-to-world conversion anchor: `topview_metadata.json`

## Known Limits

- Sampling can drop tiny structures when `max_points` is low.
- No georeferencing output is embedded in PNG itself; world mapping comes from metadata JSON.
- Enhancement is rule-based and not semantic.
