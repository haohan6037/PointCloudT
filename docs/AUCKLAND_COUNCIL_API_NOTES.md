# Auckland Council API Notes

## Goal

Validate whether Auckland Council public GeoMaps services can provide:

1. official aerial imagery
2. official property boundary geometry

for clipping lawn candidates to the real property extent.

## Confirmed Public Services

The GeoMaps public viewer uses ArcGIS services behind:

- Portal: `https://mapspublic.aklc.govt.nz/portal/`
- Geometry service: `https://mapspublic.aklc.govt.nz/arcgis/rest/services/Utilities/Geometry/GeometryServer`

Confirmed public imagery services:

- Aerial basemap:
  `https://mapspublic.aklc.govt.nz/arcgis/rest/services/Basemap/AerialBasemap/MapServer`
- Aerial photography 2024/2025:
  `https://mapspublic.aklc.govt.nz/arcgis/rest/services/Raster/AerialPhotography20242025/MapServer`

Confirmed public boundary / property services:

- Address layer:
  `https://mapspublic.aklc.govt.nz/arcgis/rest/services/Address/MapServer/0`
- Property polygon layer:
  `https://mapspublic.aklc.govt.nz/arcgis/rest/services/Landbase/MapServer/36`
- Parcel polygon layer:
  `https://mapspublic.aklc.govt.nz/arcgis/rest/services/Landbase/MapServer/38`

## Confirmed Spatial Reference

All key public services above return `WKID 2193` / NZTM.

This matters because current point-cloud outputs are not yet aligned to the same coordinate expression.

## Current Key Constraint

The current LAS-derived work uses coordinates around:

- `x ~ 317k`
- `y ~ 5.913M`

The council property and aerial services use coordinates around:

- `x ~ 1.7M`
- `y ~ 5.9M`

So the next phase is not only API access. It also requires a registration or transform step between local point-cloud coordinates and council NZTM coordinates.

Without that alignment, official boundaries cannot be directly clipped against the current lawn polygon.

## Public Query Path That Works

The following public path is already validated:

1. query address point from `Address/MapServer/0`
2. use that point to query `Landbase/MapServer/36`
3. get property polygon geometry
4. export aerial image from `AerialPhotography20242025/MapServer/export`

## Local POC Script

Script:

- [fetch_council_property_context.py](/Users/happyfamily/MyProject/PointCloudTT/scripts/fetch_council_property_context.py)

Purpose:

- search an address
- fetch one matching property polygon
- export one aerial image around that property
- save both geometry metadata and PNG locally

Example:

```bash
.venv/bin/python scripts/fetch_council_property_context.py \
  "127 Captain Springs Road Te Papapa Auckland 1061"
```

## What Is Not Confirmed Yet

1. best production source for clipping:
   - `Property` layer vs `Parcels` layer
2. whether address search alone is enough for all user cases
3. the exact coordinate transform or control-point workflow needed to align point cloud to council NZTM
4. whether any internal GP service is needed for edge cases

## Important Access Note

The viewer configuration references a GP service named:

- `https://mapspublic.aklc.govt.nz/arcgis2/rest/services/GPTools/getRequiredPropertyGeometry/GPServer/getRequiredGeometry`

Direct public access currently returns `Token Required`.

So the stable public integration path should assume:

- public address layer query
- public property/parcels layer query
- public aerial export

and should not depend on that GP endpoint unless authenticated access is later arranged.

## Recommended Next Engineering Step

Build a small registration workflow:

1. show council aerial image
2. show council property polygon
3. let user place 2-4 anchor points between council map and point-cloud top-view
4. solve transform
5. clip lawn candidate polygon against transformed official property boundary
