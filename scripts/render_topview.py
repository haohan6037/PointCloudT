#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Render a LAS/LAZ point cloud into a high-quality top-view bundle."
    )
    parser.add_argument("input", type=Path, help="Input LAS/LAZ file")
    parser.add_argument("output", type=Path, help="Primary output PNG file")
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=None,
        help="Output directory for stage-1 bundle images",
    )
    parser.add_argument(
        "--long-side",
        type=int,
        default=2400,
        help="Long side in pixels for rasterized top-view output",
    )
    parser.add_argument(
        "--fill-iterations",
        type=int,
        default=4,
        help="How many neighborhood fill passes to apply",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=24,
        help="Crop padding in pixels around non-empty content",
    )
    return parser


def to_uint8_color(np, values):
    arr = np.asarray(values)
    if arr.dtype == np.uint8:
        return arr
    if arr.size == 0:
        return arr.astype(np.uint8)
    max_value = int(arr.max())
    if max_value > 255:
        arr = arr / 256.0
    return np.clip(arr, 0, 255).astype(np.uint8)


def crop_to_alpha(np, rgba_image, padding):
    alpha = rgba_image[..., 3]
    ys, xs = np.nonzero(alpha > 0)
    if len(xs) == 0:
        return rgba_image, (0, 0, rgba_image.shape[1], rgba_image.shape[0])

    x0 = max(0, int(xs.min()) - padding)
    x1 = min(rgba_image.shape[1], int(xs.max()) + padding + 1)
    y0 = max(0, int(ys.min()) - padding)
    y1 = min(rgba_image.shape[0], int(ys.max()) + padding + 1)
    return rgba_image[y0:y1, x0:x1], (x0, y0, x1, y1)


def composite_on_color(np, rgba_image, background_rgb):
    rgb = rgba_image[..., :3].astype(np.float32)
    alpha = rgba_image[..., 3:4].astype(np.float32) / 255.0
    bg = np.zeros_like(rgb) + np.asarray(background_rgb, dtype=np.float32)
    return np.clip(rgb * alpha + bg * (1.0 - alpha), 0, 255).astype(np.uint8)


def fill_small_holes(np, rgba_image, iterations):
    result = rgba_image.copy()
    for _ in range(max(0, iterations)):
        alpha = result[..., 3]
        missing = alpha == 0
        if not missing.any():
            break

        updated = result.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                shifted = np.roll(np.roll(result, dy, axis=0), dx, axis=1)

                if dy > 0:
                    shifted[:dy, :, 3] = 0
                elif dy < 0:
                    shifted[dy:, :, 3] = 0

                if dx > 0:
                    shifted[:, :dx, 3] = 0
                elif dx < 0:
                    shifted[:, dx:, 3] = 0

                mask = (updated[..., 3] == 0) & (shifted[..., 3] > 0)
                updated[mask] = shifted[mask]

        result = updated
    return result


def enhance_lawn_readability(np, rgb_u8):
    rgb = rgb_u8.astype(np.float32) / 255.0
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]

    luma = 0.299 * r + 0.587 * g + 0.114 * b
    lift = np.clip((0.48 - luma) * 0.32, 0.0, 0.22)
    r = np.clip(r + lift * 0.65, 0.0, 1.0)
    g = np.clip(g + lift * 1.05, 0.0, 1.0)
    b = np.clip(b + lift * 0.55, 0.0, 1.0)

    green_mask = ((g > r * 0.92) & (g > b * 0.92)).astype(np.float32)
    g = np.clip(g + green_mask * 0.1, 0.0, 1.0)
    r = np.clip(r - green_mask * 0.025, 0.0, 1.0)
    b = np.clip(b - green_mask * 0.025, 0.0, 1.0)

    out = np.stack([r, g, b], axis=2)
    out = np.clip((out - 0.5) * 1.08 + 0.5, 0.0, 1.0)
    return (out * 255.0).astype(np.uint8)


def rasterize_highest_points(np, x, y, z, red, green, blue, long_side):
    min_x = float(x.min())
    max_x = float(x.max())
    min_y = float(y.min())
    max_y = float(y.max())
    min_z = float(z.min())
    max_z = float(z.max())

    width_m = max(max_x - min_x, 1e-9)
    height_m = max(max_y - min_y, 1e-9)

    if width_m >= height_m:
        width = int(long_side)
        height = max(1, int(round(long_side * height_m / width_m)))
    else:
        height = int(long_side)
        width = max(1, int(round(long_side * width_m / height_m)))

    ix = ((x - min_x) / width_m * (width - 1)).astype(np.int32)
    iy = ((max_y - y) / height_m * (height - 1)).astype(np.int32)
    flat = iy * width + ix

    # Keep the highest point in each pixel so roofs, trees, and lawn texture stay readable.
    order = np.lexsort((z, flat))
    flat_sorted = flat[order]
    red_sorted = red[order]
    green_sorted = green[order]
    blue_sorted = blue[order]

    starts = np.r_[0, np.flatnonzero(flat_sorted[1:] != flat_sorted[:-1]) + 1]
    ends = np.r_[starts[1:], len(flat_sorted)]
    selected = ends - 1
    selected_flat = flat_sorted[selected]

    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba.reshape(-1, 4)[selected_flat, :3] = np.stack(
        [red_sorted[selected], green_sorted[selected], blue_sorted[selected]],
        axis=1,
    )
    rgba.reshape(-1, 4)[selected_flat, 3] = 255

    return rgba, {
        "x_min": min_x,
        "x_max": max_x,
        "y_min": min_y,
        "y_max": max_y,
        "z_min": min_z,
        "z_max": max_z,
        "width_px": int(width),
        "height_px": int(height),
        "width_m": float(width_m),
        "height_m": float(height_m),
    }


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        import laspy
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        parser.error(
            "Missing dependency: {}. Install with `python3 -m pip install laspy numpy pillow`.".format(
                exc.name
            )
        )

    las = laspy.read(args.input)
    dims = list(las.point_format.dimension_names)
    has_rgb = all(name in dims for name in ("red", "green", "blue"))

    x = np.asarray(las.x)
    y = np.asarray(las.y)
    z = np.asarray(las.z)
    point_count = int(len(x))

    if has_rgb:
        red = to_uint8_color(np, las.red)
        green = to_uint8_color(np, las.green)
        blue = to_uint8_color(np, las.blue)
    else:
        normalized_z = (z - z.min()) / max(float(z.max() - z.min()), 1e-9)
        gray = np.clip(normalized_z * 255.0, 0, 255).astype(np.uint8)
        red = gray
        green = gray
        blue = gray

    rgba_raw, bounds = rasterize_highest_points(
        np=np,
        x=x,
        y=y,
        z=z,
        red=red,
        green=green,
        blue=blue,
        long_side=args.long_side,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    primary_rgb = composite_on_color(np, rgba_raw, (255, 255, 255))
    Image.fromarray(primary_rgb, "RGB").save(args.output)

    if args.bundle_dir is not None:
        args.bundle_dir.mkdir(parents=True, exist_ok=True)
        raw_path = args.bundle_dir / "topview_raw.png"
        crop_path = args.bundle_dir / "topview_crop.png"
        enhanced_path = args.bundle_dir / "topview_enhanced.png"
        truecolor_path = args.bundle_dir / "topview_truecolor.png"
        metadata_path = args.bundle_dir / "topview_metadata.json"

        Image.fromarray(rgba_raw, "RGBA").save(raw_path)

        rgba_filled = fill_small_holes(np, rgba_raw, args.fill_iterations)
        rgba_crop, (x0, y0, x1, y1) = crop_to_alpha(np, rgba_filled, args.padding)

        crop_white = composite_on_color(np, rgba_crop, (255, 255, 255))
        crop_black = composite_on_color(np, rgba_crop, (0, 0, 0))
        enhanced_rgb = enhance_lawn_readability(np, crop_white)

        Image.fromarray(crop_white, "RGB").save(crop_path)
        Image.fromarray(enhanced_rgb, "RGB").save(enhanced_path)
        Image.fromarray(crop_black, "RGB").save(truecolor_path)

        metadata = {
            "input_file": str(args.input),
            "point_count": point_count,
            "sampled_points": point_count,
            "has_rgb": bool(has_rgb),
            "world_bounds": {
                "x_min": bounds["x_min"],
                "x_max": bounds["x_max"],
                "y_min": bounds["y_min"],
                "y_max": bounds["y_max"],
                "z_min": bounds["z_min"],
                "z_max": bounds["z_max"],
            },
            "raw_image": {
                "width": int(rgba_raw.shape[1]),
                "height": int(rgba_raw.shape[0]),
            },
            "crop_bbox_in_raw": {
                "x0": int(x0),
                "y0": int(y0),
                "x1": int(x1),
                "y1": int(y1),
            },
            "crop_image": {
                "width": int(rgba_crop.shape[1]),
                "height": int(rgba_crop.shape[0]),
            },
            "render": {
                "long_side": int(args.long_side),
                "fill_iterations": int(args.fill_iterations),
                "padding": int(args.padding),
            },
            "files": {
                "topview_raw": raw_path.name,
                "topview_crop": crop_path.name,
                "topview_enhanced": enhanced_path.name,
                "topview_truecolor": truecolor_path.name,
            },
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        print(
            "Bundle images:",
            raw_path,
            crop_path,
            enhanced_path,
            truecolor_path,
            metadata_path,
        )

    print("Rendered {} points from {} to {}".format(point_count, args.input, args.output))


if __name__ == "__main__":
    main()
