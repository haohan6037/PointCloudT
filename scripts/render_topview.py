#!/usr/bin/env python3

import argparse
import io
import json
from pathlib import Path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Render a LAS/LAZ point cloud into a top-view PNG."
    )
    parser.add_argument("input", type=Path, help="Input LAS/LAZ file")
    parser.add_argument("output", type=Path, help="Output PNG file")
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=None,
        help="Output directory for stage-1 bundle images (raw/crop/enhanced)",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=2_000_000,
        help="Maximum number of rendered points after sampling",
    )
    parser.add_argument("--width", type=float, default=8.0, help="Figure width in inches")
    parser.add_argument("--height", type=float, default=12.0, help="Figure height in inches")
    parser.add_argument("--dpi", type=int, default=200, help="Output DPI")
    parser.add_argument(
        "--point-size",
        type=float,
        default=0.05,
        help="Scatter point size",
    )
    return parser


def render_scatter_image(plt, x, y, rgb, width, height, dpi, point_size, facecolor):
    from PIL import Image

    fig = plt.figure(figsize=(width, height), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.scatter(x, y, s=point_size, c=rgb, linewidths=0)
    ax.set_aspect("equal")
    ax.axis("off")
    buffer = io.BytesIO()
    plt.savefig(buffer, bbox_inches="tight", pad_inches=0, facecolor=facecolor)
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB").copy()


def compute_content_bbox(np, rgb_u8, mode="nonwhite"):
    if mode == "nonblack":
        content = np.any(rgb_u8 > 12, axis=2)
    else:
        content = np.any(rgb_u8 < 250, axis=2)
    ys, xs = np.where(content)
    if len(xs) == 0 or len(ys) == 0:
        return (0, 0, rgb_u8.shape[1], rgb_u8.shape[0])
    return (int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1))


def expand_bbox(x0, y0, x1, y1, width, height, pad):
    return (
        max(0, x0 - pad),
        max(0, y0 - pad),
        min(width, x1 + pad),
        min(height, y1 + pad),
    )


def enhance_lawn_readability(np, rgb_u8):
    rgb = rgb_u8.astype(np.float32) / 255.0
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]

    # Lift mid-tones and mildly emphasize green-dominant vegetation.
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    lift = np.clip((0.55 - luma) * 0.35, 0.0, 0.22)
    r = np.clip(r + lift * 0.75, 0.0, 1.0)
    g = np.clip(g + lift * 1.05, 0.0, 1.0)
    b = np.clip(b + lift * 0.7, 0.0, 1.0)

    green_mask = ((g > r * 0.93) & (g > b * 0.93)).astype(np.float32)
    g = np.clip(g + green_mask * 0.08, 0.0, 1.0)
    r = np.clip(r - green_mask * 0.02, 0.0, 1.0)
    b = np.clip(b - green_mask * 0.02, 0.0, 1.0)

    out = np.stack([r, g, b], axis=2)
    out = np.clip((out - 0.5) * 1.08 + 0.5, 0.0, 1.0)  # mild contrast
    return (out * 255.0).astype(np.uint8)


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        import laspy
        import matplotlib
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        parser.error(
            "Missing dependency: {}. Install with `python3 -m pip install laspy numpy matplotlib pillow`.".format(
                exc.name
            )
        )

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    las = laspy.read(args.input)
    count = len(las.x)
    step = max(1, count // max(args.max_points, 1))

    x = np.asarray(las.x[::step])
    y = np.asarray(las.y[::step])

    has_rgb = hasattr(las, "red") and hasattr(las, "green") and hasattr(las, "blue")
    if has_rgb:
        rgb = np.stack(
            [las.red[::step], las.green[::step], las.blue[::step]],
            axis=1,
        ).astype(float)
        scale = max(float(rgb.max()), 1.0)
        rgb = np.clip(rgb / scale, 0.0, 1.0)
    else:
        z = np.asarray(las.z[::step])
        z_span = max(float(z.max() - z.min()), 1e-9)
        normalized = (z - z.min()) / z_span
        rgb = plt.cm.terrain(normalized)[:, :3]

    raw_image = render_scatter_image(
        plt, x, y, rgb, args.width, args.height, args.dpi, args.point_size, facecolor="white"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw_image.save(args.output)

    if args.bundle_dir is not None:
        args.bundle_dir.mkdir(parents=True, exist_ok=True)
        raw_path = args.bundle_dir / "topview_raw.png"
        crop_path = args.bundle_dir / "topview_crop.png"
        enhanced_path = args.bundle_dir / "topview_enhanced.png"
        truecolor_path = args.bundle_dir / "topview_truecolor.png"
        metadata_path = args.bundle_dir / "topview_metadata.json"

        raw_image.save(raw_path)
        raw_np = np.asarray(raw_image)
        x0, y0, x1, y1 = compute_content_bbox(np, raw_np)
        x0, y0, x1, y1 = expand_bbox(x0, y0, x1, y1, raw_np.shape[1], raw_np.shape[0], pad=80)

        crop_np = raw_np[y0:y1, x0:x1]
        Image.fromarray(crop_np).save(crop_path)

        enhanced_np = enhance_lawn_readability(np, crop_np)
        Image.fromarray(enhanced_np).save(enhanced_path)

        if has_rgb:
            truecolor_raw = render_scatter_image(
                plt, x, y, rgb, args.width, args.height, args.dpi, args.point_size, facecolor="black"
            )
            truecolor_raw_np = np.asarray(truecolor_raw)
            tx0, ty0, tx1, ty1 = compute_content_bbox(np, truecolor_raw_np, mode="nonblack")
            tx0, ty0, tx1, ty1 = expand_bbox(
                tx0, ty0, tx1, ty1, truecolor_raw_np.shape[1], truecolor_raw_np.shape[0], pad=80
            )
            truecolor_crop_np = truecolor_raw_np[ty0:ty1, tx0:tx1]
            Image.fromarray(truecolor_crop_np).save(truecolor_path)

        metadata = {
            "input_file": str(args.input),
            "sampled_points": int(len(x)),
            "has_rgb": bool(has_rgb),
            "world_bounds": {
                "x_min": float(x.min()),
                "x_max": float(x.max()),
                "y_min": float(y.min()),
                "y_max": float(y.max()),
            },
            "raw_image": {
                "width": int(raw_np.shape[1]),
                "height": int(raw_np.shape[0]),
            },
            "crop_bbox_in_raw": {
                "x0": int(x0),
                "y0": int(y0),
                "x1": int(x1),
                "y1": int(y1),
            },
            "crop_image": {
                "width": int(crop_np.shape[1]),
                "height": int(crop_np.shape[0]),
            },
            "truecolor_image": {
                "path": truecolor_path.name if has_rgb else None,
            },
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        print("Bundle images:", raw_path, crop_path, enhanced_path, truecolor_path if has_rgb else "-", metadata_path)

    print("Rendered {} points from {} to {}".format(len(x), args.input, args.output))


if __name__ == "__main__":
    main()
