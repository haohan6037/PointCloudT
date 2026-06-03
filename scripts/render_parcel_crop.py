#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def build_parser():
    parser = argparse.ArgumentParser(
        description="Render a top-view parcel-clipped image using council boundary and registration transform."
    )
    parser.add_argument("topview_image", type=Path, help="Input topview crop PNG")
    parser.add_argument("topview_metadata", type=Path, help="Stage-1 topview metadata JSON")
    parser.add_argument("council_meta", type=Path, help="Council context JSON")
    parser.add_argument("registration_transform", type=Path, help="Registration transform JSON")
    parser.add_argument("output_image", type=Path, help="Output parcel-clipped PNG")
    parser.add_argument(
        "--output-metadata",
        type=Path,
        default=None,
        help="Optional metadata JSON for the projected parcel boundary",
    )
    return parser


def pick_council_rings(council_meta):
    mode = council_meta.get("boundary_mode")
    if mode == "main_parcel":
        main = council_meta.get("main_parcel", {})
        rings = main.get("geometry", {}).get("rings", [])
        if rings:
            return rings, "main_parcel"
    if mode == "legal_parcel":
        rings = council_meta.get("legal_parcel_geometry", {}).get("rings", [])
        if rings:
            return rings, "legal_parcel"
    return council_meta.get("property_geometry", {}).get("rings", []), "property"


def inverse_similarity(x, y, transform):
    a = float(transform["a"])
    b = float(transform["b"])
    tx = float(transform["tx"])
    ty = float(transform["ty"])
    den = a * a + b * b
    if den < 1e-12:
        return None
    dx = x - tx
    dy = y - ty
    return {
        "x": (a * dx + b * dy) / den,
        "y": (-b * dx + a * dy) / den,
    }


def pc_world_to_crop_pixel(world_pt, pc_meta):
    world = pc_meta["world_bounds"]
    crop = pc_meta["crop_image"]
    width = max(int(crop["width"]), 1)
    height = max(int(crop["height"]), 1)
    px = ((world_pt["x"] - world["x_min"]) / max(world["x_max"] - world["x_min"], 1e-9)) * (width - 1)
    py = ((world["y_max"] - world_pt["y"]) / max(world["y_max"] - world["y_min"], 1e-9)) * (height - 1)
    return {"x": float(px), "y": float(py)}


def normalize_point(pt, width, height):
    return {
        "x": float(pt["x"]) / max(width, 1),
        "y": float(pt["y"]) / max(height, 1),
    }


def main():
    args = build_parser().parse_args()

    top_meta = json.loads(args.topview_metadata.read_text(encoding="utf-8"))
    council_meta = json.loads(args.council_meta.read_text(encoding="utf-8"))
    transform_json = json.loads(args.registration_transform.read_text(encoding="utf-8"))
    rings_world, boundary_source = pick_council_rings(council_meta)
    transform = transform_json["transform"]

    source_image = Image.open(args.topview_image).convert("RGBA")
    image_w, image_h = source_image.size

    rings_img = []
    for ring in rings_world:
        pts = []
        for x, y in ring:
            pc_world = inverse_similarity(float(x), float(y), transform)
            if pc_world is None:
                continue
            px = pc_world_to_crop_pixel(pc_world, top_meta)
            pts.append((px["x"], px["y"]))
        if len(pts) >= 3:
            rings_img.append(pts)

    if not rings_img:
        raise SystemExit("No projected parcel polygon could be built.")

    mask_img = Image.new("L", (image_w, image_h), 0)
    draw = ImageDraw.Draw(mask_img)
    for pts in rings_img:
        draw.polygon(pts, fill=255)

    clipped = source_image.copy()
    clipped.putalpha(mask_img)
    args.output_image.parent.mkdir(parents=True, exist_ok=True)
    clipped.save(args.output_image)

    if args.output_metadata is not None:
        payload = {
            "boundary_source": boundary_source,
            "image": {
                "width": image_w,
                "height": image_h,
            },
            "projected_boundary": [
                {
                    "pixels": [
                        {"x": round(float(x), 3), "y": round(float(y), 3)}
                        for x, y in ring
                    ],
                    "relative": [
                        {
                            "x": round(normalize_point({"x": x, "y": y}, image_w, image_h)["x"], 6),
                            "y": round(normalize_point({"x": x, "y": y}, image_w, image_h)["y"], 6),
                        }
                        for x, y in ring
                    ],
                }
                for ring in rings_img
            ],
        }
        args.output_metadata.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {args.output_image}")


if __name__ == "__main__":
    main()
