#!/usr/bin/env python3

import argparse
import json
import math
from pathlib import Path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Overlay Auckland Council parcel boundary onto LAS-derived top-view images using candidate source CRS values."
    )
    parser.add_argument("las_path", type=Path, help="Input LAS/LAZ file")
    parser.add_argument("topview_image", type=Path, help="Top-view PNG generated from the LAS file")
    parser.add_argument("topview_metadata", type=Path, help="topview_metadata.json generated from render_topview.py")
    parser.add_argument("council_meta", type=Path, help="Council context JSON from fetch_council_property_context.py")
    parser.add_argument("council_image", type=Path, help="Council aerial PNG generated for the same address")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".codex-artifacts/crs-check"),
        help="Directory for rendered overlays and reports",
    )
    parser.add_argument(
        "--source-crs",
        nargs="+",
        default=["EPSG:32760", "EPSG:2135"],
        help="One or more candidate source CRS values to test",
    )
    parser.add_argument(
        "--topview-padding",
        type=float,
        default=0.18,
        help="Padding ratio around the projected parcel in the top-view zoom crop",
    )
    return parser


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def get_selected_council_rings(council_meta):
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
    rings = council_meta.get("property_geometry", {}).get("rings", [])
    return rings, council_meta.get("boundary_source", "property")


def flatten_rings(rings):
    for ring in rings:
        for x, y in ring:
            yield float(x), float(y)


def bbox_from_points(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    if not xs or not ys:
        return None
    return {
        "xmin": min(xs),
        "ymin": min(ys),
        "xmax": max(xs),
        "ymax": max(ys),
    }


def transform_point(transformer, x, y):
    tx, ty = transformer.transform(x, y)
    return float(tx), float(ty)


def load_font(size):
    try:
        from PIL import ImageFont

        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except Exception:
        from PIL import ImageFont

        return ImageFont.load_default()


def world_to_topview_px(point, top_meta):
    world = top_meta["world_bounds"]
    image = top_meta["crop_image"]
    w = max(int(image["width"]), 1)
    h = max(int(image["height"]), 1)
    px = ((point[0] - world["x_min"]) / max(world["x_max"] - world["x_min"], 1e-9)) * (w - 1)
    py = ((world["y_max"] - point[1]) / max(world["y_max"] - world["y_min"], 1e-9)) * (h - 1)
    return float(px), float(py)


def topview_px_to_relative(point, top_meta):
    image = top_meta["crop_image"]
    w = max(int(image["width"]), 1)
    h = max(int(image["height"]), 1)
    return float(point[0]) / w, float(point[1]) / h


def world_to_council_px(point, council_meta):
    extent = council_meta.get("actual_extent_2193") or council_meta.get("bbox_2193")
    img_w = int(council_meta.get("export_image", {}).get("width", 1200))
    img_h = int(council_meta.get("export_image", {}).get("height", 1200))
    px = ((point[0] - extent["xmin"]) / max(extent["xmax"] - extent["xmin"], 1e-9)) * (img_w - 1)
    py = ((extent["ymax"] - point[1]) / max(extent["ymax"] - extent["ymin"], 1e-9)) * (img_h - 1)
    return float(px), float(py)


def draw_world_polygon(draw, points, to_px, color, width):
    if len(points) < 2:
        return
    px_pts = [to_px(pt) for pt in points]
    draw.line(px_pts, fill=color, width=width)
    if len(px_pts) >= 3:
        draw.line([px_pts[-1], px_pts[0]], fill=color, width=width)


def project_rings(transformer, rings):
    projected = []
    for ring in rings:
        pts = [transform_point(transformer, x, y) for x, y in ring]
        if len(pts) >= 3:
            projected.append(pts)
    return projected


def render_candidate(candidate, top_image_path, council_image_path, top_meta, council_meta, rings_world, output_dir, padding_ratio):
    from PIL import Image, ImageDraw
    from pyproj import CRS, Transformer

    source_crs = CRS.from_user_input(candidate)
    to_source = Transformer.from_crs(CRS.from_epsg(2193), source_crs, always_xy=True)
    to_council = Transformer.from_crs(source_crs, CRS.from_epsg(2193), always_xy=True)

    top_img = Image.open(top_image_path).convert("RGBA")
    council_img = Image.open(council_image_path).convert("RGBA")

    projected_to_source = project_rings(to_source, rings_world)
    projected_to_topview = [
        [world_to_topview_px(pt, top_meta) for pt in ring]
        for ring in projected_to_source
    ]
    top_points = [pt for ring in projected_to_topview for pt in ring]
    top_bbox = bbox_from_points(top_points)

    if top_bbox is None:
        top_bbox = {
            "xmin": 0,
            "ymin": 0,
            "xmax": top_img.width - 1,
            "ymax": top_img.height - 1,
        }

    pad_x = max((top_bbox["xmax"] - top_bbox["xmin"]) * float(padding_ratio), 40.0)
    pad_y = max((top_bbox["ymax"] - top_bbox["ymin"]) * float(padding_ratio), 40.0)
    crop_box = (
        max(0, int(math.floor(top_bbox["xmin"] - pad_x))),
        max(0, int(math.floor(top_bbox["ymin"] - pad_y))),
        min(top_img.width, int(math.ceil(top_bbox["xmax"] + pad_x))),
        min(top_img.height, int(math.ceil(top_bbox["ymax"] + pad_y))),
    )
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        crop_box = (0, 0, top_img.width, top_img.height)
    crop = top_img.crop(crop_box)
    crop_draw = ImageDraw.Draw(crop)

    def crop_px(pt):
        return (pt[0] - crop_box[0], pt[1] - crop_box[1])

    for ring in projected_to_topview:
        draw_world_polygon(crop_draw, ring, crop_px, (28, 171, 133, 255), 5)
        for x, y in ring:
            px = crop_px((x, y))
            crop_draw.ellipse((px[0] - 3, px[1] - 3, px[0] + 3, px[1] + 3), fill=(28, 171, 133, 255))

    # Council overlay with LAS bbox transformed by the same candidate source CRS.
    las = None
    try:
        import laspy

        las = laspy.open(top_meta["input_file"])
    except Exception:
        las = None

    if las is not None:
        h = las.header
        las_corners_source = [
            (float(h.mins[0]), float(h.mins[1])),
            (float(h.mins[0]), float(h.maxs[1])),
            (float(h.maxs[0]), float(h.maxs[1])),
            (float(h.maxs[0]), float(h.mins[1])),
            (float(h.mins[0]), float(h.mins[1])),
        ]
        las_corners_council = [transform_point(to_council, x, y) for x, y in las_corners_source]
    else:
        las_corners_council = []

    council_draw = ImageDraw.Draw(council_img)
    for ring in rings_world:
        council_pts = [world_to_council_px((x, y), council_meta) for x, y in ring]
        draw_world_polygon(council_draw, council_pts, lambda pt: pt, (44, 186, 155, 255), 5)

    if las_corners_council:
        draw_world_polygon(
            council_draw,
            [world_to_council_px(pt, council_meta) for pt in las_corners_council],
            lambda pt: pt,
            (231, 88, 0, 255),
            4,
        )

    # Make a simple compare panel.
    font = load_font(18)
    title_font = load_font(22)
    label = f"Candidate source CRS: {candidate}"
    top_label = "Projected official boundary on top-view"
    council_label = "Council aerial with LAS bbox transformed to 2193"

    panel_w = max(crop.width, council_img.width)
    panel_h = max(crop.height, council_img.height) + 88
    panel = Image.new("RGBA", (panel_w * 2 + 24, panel_h), (248, 244, 235, 255))
    panel_draw = ImageDraw.Draw(panel)

    panel.alpha_composite(crop, (0, 68))
    panel.alpha_composite(council_img, (panel_w + 24, 68))

    panel_draw.rounded_rectangle((16, 10, panel_w * 2 + 8, 58), radius=10, fill=(255, 255, 255, 235), outline=(180, 170, 150, 255), width=2)
    panel_draw.text((32, 18), label, fill=(28, 26, 23, 255), font=title_font)
    panel_draw.text((32, 42), top_label, fill=(60, 58, 54, 255), font=font)
    panel_draw.text((panel_w + 40, 42), council_label, fill=(60, 58, 54, 255), font=font)

    compare_path = output_dir / f"compare_{candidate.replace(':', '_').replace('/', '_')}.png"
    top_overlay_path = output_dir / f"topview_{candidate.replace(':', '_').replace('/', '_')}.png"
    council_overlay_path = output_dir / f"council_{candidate.replace(':', '_').replace('/', '_')}.png"

    crop.save(top_overlay_path)
    council_img.save(council_overlay_path)
    panel.save(compare_path)

    report = {
        "candidate": candidate,
        "topview_crop_bbox": {
            "x0": int(crop_box[0]),
            "y0": int(crop_box[1]),
            "x1": int(crop_box[2]),
            "y1": int(crop_box[3]),
        },
        "topview_projected_bbox": top_bbox,
        "projected_boundary_world_points": [[float(x), float(y)] for ring in projected_to_source for x, y in ring],
        "projected_boundary_topview_pixels": [[float(x), float(y)] for ring in projected_to_topview for x, y in ring],
        "projected_boundary_topview_relative": [
            [[float(rx), float(ry)] for rx, ry in (topview_px_to_relative(pt, top_meta) for pt in ring)]
            for ring in projected_to_topview
        ],
        "council_boundary_source": candidate,
        "las_bbox_source": {
            "xmin": float(h.mins[0]),
            "ymin": float(h.mins[1]),
            "xmax": float(h.maxs[0]),
            "ymax": float(h.maxs[1]),
        } if las is not None else None,
        "las_bbox_council": bbox_from_points(las_corners_council) if las_corners_council else None,
        "topview_overlay": str(top_overlay_path),
        "council_overlay": str(council_overlay_path),
        "compare_image": str(compare_path),
    }

    report_path = output_dir / f"report_{candidate.replace(':', '_').replace('/', '_')}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, compare_path


def main():
    args = build_parser().parse_args()

    try:
        from pyproj import CRS, Transformer
    except ImportError as exc:
        raise SystemExit(
            f"Missing dependency: {exc}. Install with `.venv/bin/python -m pip install pyproj`."
        )

    _ = CRS  # keep imported for clarity in local helper usage
    _ = Transformer

    top_meta = load_json(args.topview_metadata)
    council_meta = load_json(args.council_meta)
    rings_world, boundary_source = get_selected_council_rings(council_meta)
    if not rings_world:
        raise SystemExit("No council boundary rings found.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "las_path": str(args.las_path),
        "topview_image": str(args.topview_image),
        "topview_metadata": str(args.topview_metadata),
        "council_meta": str(args.council_meta),
        "boundary_source": boundary_source,
        "candidates": [],
    }

    for candidate in args.source_crs:
        report, compare_path = render_candidate(
            candidate,
            args.topview_image,
            args.council_image,
            top_meta,
            council_meta,
            rings_world,
            args.output_dir,
            args.topview_padding,
        )
        summary["candidates"].append(
            {
                "candidate": candidate,
                "compare_image": str(compare_path),
                "topview_projected_bbox": report["topview_projected_bbox"],
                "las_bbox_council": report["las_bbox_council"],
            }
        )

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
