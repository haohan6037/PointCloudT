#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ADDRESS_LAYER = "https://mapspublic.aklc.govt.nz/arcgis/rest/services/Address/MapServer/0/query"
PROPERTY_LAYER = "https://mapspublic.aklc.govt.nz/arcgis/rest/services/Landbase/MapServer/36/query"
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
            "outFields": "PROPERTYID,ADDRESSINONELINE,PROPERTYAREA,PROPERTYTYPE,VALUATIONREF",
            "returnGeometry": "true",
            "f": "pjson",
        },
    )
    property_features = property_data.get("features", [])
    if not property_features:
        raise SystemExit(f"No property polygon found for address: {args.address}")

    property_feature = property_features[0]
    rings = property_feature["geometry"]["rings"]
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
        "property_geometry": property_feature["geometry"],
        "bbox_2193": {
            "xmin": bbox[0],
            "ymin": bbox[1],
            "xmax": bbox[2],
            "ymax": bbox[3],
        },
        "services": {
            "address_layer": ADDRESS_LAYER,
            "property_layer": PROPERTY_LAYER,
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
