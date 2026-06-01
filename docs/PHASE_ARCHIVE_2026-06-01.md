# Phase Archive 2026-06-01

## Why This Archive

Current mask-to-lawn work reached a useful draft stage. We pause further tuning on pure point-cloud mask logic and move next to official geospatial data integration.

## What Is Stable Now

1. LAS to top-view color image is reproducible by code:
   - script: `scripts/render_topview.py`
   - outputs: `topview_raw.png`, `topview_crop.png`, `topview_enhanced.png`, `topview_metadata.json`
2. Lawn candidate draft pipeline is reproducible by code:
   - script: `scripts/extract_lawn_mask.py`
   - supports area filter (`min_area_m2`), width filter (`min_width_m`), conservative inset (`inset_m`), polygon simplification
3. Current editing-friendly output:
   - conservative polygon draft from inset mask
   - lower boundary noise than direct mask edge

## Current Limits (Reason to Stop Tuning Here)

1. Remaining error sources are increasingly tied to missing context:
   - property boundary not enforced
   - satellite/orthophoto context not used
2. More local threshold tuning would produce diminishing returns and weaker cross-site generalization.
3. Product requirement needs official boundary clipping for out-of-property removal.

## Next Phase Goal

Integrate `geomapspublic.aucklandcouncil.govt.nz` map services to pull:

1. Satellite imagery layer for visual grounding.
2. Official parcel/property boundary geometry.

Then clip lawn candidates against official boundary so any area outside user property is removed automatically.

## Planned Technical Work (Next Phase)

1. Discover available Auckland Council map service endpoints and layers.
2. Confirm coordinate reference systems and transform path to local map coordinates.
3. Fetch parcel boundary by address/parcel id and cache normalized geometry.
4. Add boundary clip stage after lawn candidate generation.
5. Produce before/after comparison overlays for verification.

## Completion Criteria for Next Phase

1. Same input LAS generates two overlays:
   - pre-clip lawn candidate
   - post-clip lawn candidate (inside official boundary only)
2. Areas outside official boundary are removed consistently.
3. Boundary geometry is traceable to source API response.

## Notes

- This archive intentionally stops short of implementing council API calls.
- API integration begins in a separate phase to keep risk and debugging surface controlled.
