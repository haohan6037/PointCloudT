#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ADDRESS_LAYER = "https://mapspublic.aklc.govt.nz/arcgis/rest/services/Address/MapServer/0/query"
PROPERTY_LAYER = "https://mapspublic.aklc.govt.nz/arcgis/rest/services/Landbase/MapServer/36/query"
PARCEL_LAYER = "https://mapspublic.aklc.govt.nz/arcgis/rest/services/Landbase/MapServer/38/query"
AERIAL_EXPORT = "https://mapspublic.aklc.govt.nz/arcgis/rest/services/Raster/AerialPhotography20242025/MapServer/export"


def fetch_json(url, params):
    query = urlencode(params)
    with urlopen(f"{url}?{query}") as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_bytes(url, params):
    query = urlencode(params)
    with urlopen(f"{url}?{query}") as response:
        return response.read()


def ring_bbox(rings):
    xs = []
    ys = []
    for ring in rings:
        for x, y in ring:
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def parse_legal_descriptions(legal_description):
    if not legal_description:
        return []
    matches = re.findall(r"(?:\d+/\d+\s+SH\s+)?LOT\s+\d+\s+DP\s+\d+", legal_description.upper())
    cleaned = []
    for token in matches:
        token = re.sub(r"^\d+/\d+\s+SH\s+", "", token).strip()
        if token and token not in cleaned:
            cleaned.append(token)
    return cleaned


def query_parcels_for_legal_descriptions(descriptions):
    if not descriptions:
        return []
    quoted = ",".join(f"'{d}'" for d in descriptions)
    parcel_data = fetch_json(
        PARCEL_LAYER,
        {
            "where": f"upper(ParcelDescription) in ({quoted})",
            "outFields": "LINZparcelID,ParcelDescription,ParcelArea,ParcelType,PlanType,PlanNumber,OBJECTID",
            "returnGeometry": "true",
            "f": "pjson",
        },
    )
    features = parcel_data.get("features", [])
    matched = []
    target = set(descriptions)
    for feature in features:
        desc = (feature.get("attributes", {}).get("ParcelDescription") or "").upper()
        if desc in target:
            matched.append(feature)
    return matched


def merge_rings_from_features(features):
    rings = []
    for feature in features:
        geom = feature.get("geometry", {})
        for ring in geom.get("rings", []):
            rings.append(ring)
    return rings


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


def choose_main_parcel(parcel_features, legal_descriptions, property_area):
    if not parcel_features:
        return None

    first_legal = legal_descriptions[0] if legal_descriptions else None
    if first_legal:
        for feature in parcel_features:
            desc = (feature.get("attributes", {}).get("ParcelDescription") or "").upper()
            if desc == first_legal:
                return feature

    target_area = safe_float(property_area)
    if target_area is not None:
        ranked = []
        for feature in parcel_features:
            area = safe_float(feature.get("attributes", {}).get("ParcelArea"))
            if area is None:
                continue
            ranked.append((abs(area - target_area), feature))
        if ranked:
            ranked.sort(key=lambda item: item[0])
            return ranked[0][1]

    return parcel_features[0]


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Auckland Council address, property boundary, and aerial context."
    )
    parser.add_argument("address", help="Address search text")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(".codex-artifacts/council-context"),
        help="Output directory",
    )
    parser.add_argument(
        "--padding-m",
        type=float,
        default=8.0,
        help="Padding around property boundary for aerial export",
    )
    parser.add_argument(
        "--image-size",
        default="1200,1200",
        help="Export image size as width,height",
    )
    parser.add_argument(
        "--boundary-mode",
        choices=("main_parcel", "legal_parcel", "property"),
        default="main_parcel",
        help="Boundary source: main_parcel (default), legal_parcel merge, or property polygon.",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    address_data = fetch_json(
        ADDRESS_LAYER,
        {
            "where": f"upper(FullAddress) like upper('%{args.address}%')",
            "outFields": "FullAddress",
            "returnGeometry": "true",
            "resultRecordCount": 5,
            "f": "pjson",
        },
    )
    features = address_data.get("features", [])
    if not features:
        raise SystemExit(f"No address match found for: {args.address}")

    address_feature = features[0]
    address_point = address_feature["geometry"]

    property_data = fetch_json(
        PROPERTY_LAYER,
        {
            "geometry": json.dumps(address_point),
            "geometryType": "esriGeometryPoint",
            "inSR": 2193,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "PROPERTYID,ADDRESSINONELINE,PROPERTYAREA,PROPERTYTYPE,VALUATIONREF,PROPERTYDESCRIPTION,FORMATTEDTITLES",
            "returnGeometry": "true",
            "f": "pjson",
        },
    )
    property_features = property_data.get("features", [])
    if not property_features:
        raise SystemExit(f"No property polygon found for address: {args.address}")

    property_feature = property_features[0]
    property_rings = property_feature["geometry"]["rings"]
    legal_descriptions = parse_legal_descriptions(
        property_feature.get("attributes", {}).get("PROPERTYDESCRIPTION")
    )
    parcel_features = query_parcels_for_legal_descriptions(legal_descriptions)
    parcel_rings = merge_rings_from_features(parcel_features)
    main_parcel = choose_main_parcel(
        parcel_features,
        legal_descriptions,
        property_feature.get("attributes", {}).get("PROPERTYAREA"),
    )

    boundary_rings = property_rings
    boundary_source = "property"
    if args.boundary_mode == "legal_parcel" and parcel_rings:
        boundary_rings = parcel_rings
        boundary_source = "legal_parcel"
    elif args.boundary_mode == "main_parcel" and main_parcel:
        boundary_rings = main_parcel.get("geometry", {}).get("rings", property_rings)
        boundary_source = "main_parcel"

    rings = boundary_rings
    xmin, ymin, xmax, ymax = ring_bbox(rings)
    pad = args.padding_m
    bbox = [xmin - pad, ymin - pad, xmax + pad, ymax + pad]

    image_bytes = fetch_bytes(
        AERIAL_EXPORT,
        {
            "bbox": ",".join(str(v) for v in bbox),
            "bboxSR": 2193,
            "imageSR": 2193,
            "size": args.image_size,
            "format": "png32",
            "transparent": "false",
            "f": "image",
        },
    )

    meta = {
        "requested_address": args.address,
        "matched_address": address_feature["attributes"]["FullAddress"],
        "address_point": address_point,
        "property": property_feature["attributes"],
        "property_geometry": {
            "rings": rings,
        },
        "boundary_source": boundary_source,
        "property_geometry_raw": property_feature["geometry"],
        "legal_descriptions": legal_descriptions,
        "main_parcel": {
            "attributes": main_parcel.get("attributes", {}),
            "geometry": main_parcel.get("geometry", {}),
        } if main_parcel else None,
        "parcel_matches": [
            {
                "attributes": f.get("attributes", {}),
                "geometry": f.get("geometry", {}),
            }
            for f in parcel_features
        ],
        "bbox_2193": {
            "xmin": bbox[0],
            "ymin": bbox[1],
            "xmax": bbox[2],
            "ymax": bbox[3],
        },
        "services": {
            "address_layer": ADDRESS_LAYER,
            "property_layer": PROPERTY_LAYER,
            "parcel_layer": PARCEL_LAYER,
            "aerial_export": AERIAL_EXPORT,
        },
    }

    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in args.address).strip("-")
    slug = "-".join(part for part in slug.split("-") if part) or "address"
    meta_path = args.out_dir / f"{slug}.json"
    image_path = args.out_dir / f"{slug}.png"

    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    image_path.write_bytes(image_bytes)

    print(f"Wrote {meta_path}")
    print(f"Wrote {image_path}")


if __name__ == "__main__":
    main()
