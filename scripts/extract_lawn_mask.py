#!/usr/bin/env python3

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


REVIEW_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>草坪候选复核</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f1e6;
      --panel: #fffdf7;
      --line: #d8cdb8;
      --ink: #1f1d19;
      --sub: #6b665d;
      --green: #1ea65c;
      --green-soft: rgba(30, 166, 92, 0.22);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    .page {
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 10px 30px rgba(93, 76, 48, 0.05);
    }
    h1, h2, p { margin: 0; }
    h1 { font-size: 28px; line-height: 1.1; margin-bottom: 10px; }
    h2 { font-size: 16px; margin-bottom: 10px; }
    p, li { color: var(--sub); line-height: 1.5; }
    .meta { display: grid; gap: 10px; margin-top: 18px; }
    .meta-row { display: flex; justify-content: space-between; gap: 12px; }
    .meta-row strong { color: var(--ink); }
    .actions { display: flex; gap: 10px; margin-top: 16px; }
    button {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 14px;
      cursor: pointer;
    }
    button.primary {
      background: var(--green);
      border-color: var(--green);
      color: #fff;
    }
    .viewer {
      position: relative;
      overflow: hidden;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #fff;
      min-height: 70vh;
    }
    .viewer img, .viewer canvas {
      display: block;
      width: 100%;
      height: auto;
    }
    .viewer canvas {
      position: absolute;
      inset: 0;
      pointer-events: none;
    }
    .hint {
      font-size: 13px;
      margin-top: 12px;
    }
    @media (max-width: 960px) {
      .page { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="panel">
      <h1>草坪候选复核</h1>
      <p>点击右侧图中的目标草坪，系统会只保留该连通区域，并显示估算面积。</p>
      <div class="meta">
        <div class="meta-row"><span>最小候选面积</span><strong id="minArea"></strong></div>
        <div class="meta-row"><span>像素面积换算</span><strong id="pixelArea"></strong></div>
        <div class="meta-row"><span>保留连通域数</span><strong id="componentCount"></strong></div>
        <div class="meta-row"><span>当前选中面积</span><strong id="selectedArea">未选择</strong></div>
      </div>
      <div class="actions">
        <button class="primary" id="toggleBtn" type="button">切换显示</button>
        <button id="resetBtn" type="button">清空选择</button>
      </div>
      <p class="hint">深绿色是当前点击选中的主草坪，浅绿色是面积达标但未选中的其他候选。</p>
    </section>
    <section class="viewer panel">
      <img id="baseImage" src="topview_crop.png" alt="topview crop">
      <canvas id="overlayCanvas"></canvas>
    </section>
  </div>
  <script>
    const reviewData = __REVIEW_DATA__;
    const baseImage = document.getElementById("baseImage");
    const overlayCanvas = document.getElementById("overlayCanvas");
    const toggleBtn = document.getElementById("toggleBtn");
    const resetBtn = document.getElementById("resetBtn");
    const minAreaEl = document.getElementById("minArea");
    const pixelAreaEl = document.getElementById("pixelArea");
    const componentCountEl = document.getElementById("componentCount");
    const selectedAreaEl = document.getElementById("selectedArea");
    const ctx = overlayCanvas.getContext("2d");

    minAreaEl.textContent = reviewData.min_area_m2.toFixed(1) + " m2";
    pixelAreaEl.textContent = reviewData.pixel_area_m2.toFixed(4) + " m2 / px";
    componentCountEl.textContent = String(reviewData.kept_components.length);

    let mode = "crop";
    let selectedIndex = -1;
    let compMap = null;

    function resizeCanvas() {
      overlayCanvas.width = baseImage.clientWidth;
      overlayCanvas.height = baseImage.clientHeight;
      drawOverlay();
    }

    function buildComponentMap() {
      const width = reviewData.image.width;
      const height = reviewData.image.height;
      compMap = new Int32Array(width * height);
      compMap.fill(-1);
      reviewData.kept_components.forEach((comp, idx) => {
        for (const [x, y] of comp.pixels) {
          compMap[y * width + x] = idx;
        }
      });
    }

    function drawOverlay() {
      if (!compMap) return;
      const width = reviewData.image.width;
      const height = reviewData.image.height;
      const imgData = new ImageData(width, height);
      for (let i = 0; i < compMap.length; i += 1) {
        const idx = compMap[i];
        if (idx < 0) continue;
        const offset = i * 4;
        const selected = idx === selectedIndex;
        imgData.data[offset + 0] = selected ? 18 : 44;
        imgData.data[offset + 1] = selected ? 128 : 186;
        imgData.data[offset + 2] = selected ? 72 : 99;
        imgData.data[offset + 3] = selected ? 190 : 85;
      }
      const temp = document.createElement("canvas");
      temp.width = width;
      temp.height = height;
      temp.getContext("2d").putImageData(imgData, 0, 0);
      ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
      ctx.drawImage(temp, 0, 0, overlayCanvas.width, overlayCanvas.height);
    }

    function setMode(nextMode) {
      mode = nextMode;
      baseImage.src = nextMode === "crop" ? "topview_crop.png" : "topview_enhanced.png";
      toggleBtn.textContent = nextMode === "crop" ? "切到增强图" : "切到展示图";
    }

    function updateSelection(idx) {
      selectedIndex = idx;
      if (idx < 0) {
        selectedAreaEl.textContent = "未选择";
      } else {
        selectedAreaEl.textContent = reviewData.kept_components[idx].area_m2.toFixed(1) + " m2";
      }
      drawOverlay();
    }

    baseImage.addEventListener("load", resizeCanvas);
    window.addEventListener("resize", resizeCanvas);

    toggleBtn.addEventListener("click", () => {
      setMode(mode === "crop" ? "enhanced" : "crop");
    });

    resetBtn.addEventListener("click", () => updateSelection(-1));

    baseImage.addEventListener("click", (evt) => {
      const rect = baseImage.getBoundingClientRect();
      const px = Math.floor(((evt.clientX - rect.left) / rect.width) * reviewData.image.width);
      const py = Math.floor(((evt.clientY - rect.top) / rect.height) * reviewData.image.height);
      const idx = compMap[py * reviewData.image.width + px];
      if (idx >= 0) updateSelection(idx);
    });

    buildComponentMap();
    setMode("crop");
    drawOverlay();
  </script>
</body>
</html>
"""


def build_parser():
    parser = argparse.ArgumentParser(
        description="Extract a lawn candidate mask from enhanced top-view image."
    )
    parser.add_argument("input", type=Path, help="Input enhanced PNG")
    parser.add_argument("output_mask", type=Path, help="Output binary mask PNG")
    parser.add_argument("output_overlay", type=Path, help="Output overlay preview PNG")
    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="Stage-1 metadata JSON from render_topview.py",
    )
    parser.add_argument(
        "--output-metadata",
        type=Path,
        default=None,
        help="Optional JSON with component stats",
    )
    parser.add_argument(
        "--output-review",
        type=Path,
        default=None,
        help="Optional HTML review page",
    )
    parser.add_argument(
        "--min-area-m2",
        type=float,
        default=30.0,
        help="Minimum connected lawn area in square meters",
    )
    parser.add_argument(
        "--min-width-m",
        type=float,
        default=1.6,
        help="Minimum traversable neck width in meters",
    )
    parser.add_argument(
        "--polygon-epsilon-px",
        type=float,
        default=18.0,
        help="RDP simplification tolerance in pixels",
    )
    parser.add_argument(
        "--output-polygon-overlay",
        type=Path,
        default=None,
        help="Optional polygon outline preview PNG",
    )
    return parser


def rgb_to_hsv(r, g, b):
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    diff = cmax - cmin

    h = np.zeros_like(cmax)
    s = np.zeros_like(cmax)
    v = cmax

    nz = diff > 1e-6
    s[nz] = diff[nz] / np.maximum(cmax[nz], 1e-6)

    ridx = nz & (cmax == r)
    gidx = nz & (cmax == g)
    bidx = nz & (cmax == b)

    h[ridx] = ((g[ridx] - b[ridx]) / diff[ridx]) % 6.0
    h[gidx] = ((b[gidx] - r[gidx]) / diff[gidx]) + 2.0
    h[bidx] = ((r[bidx] - g[bidx]) / diff[bidx]) + 4.0
    h = h / 6.0
    return h, s, v


def majority_filter(mask, rounds=2):
    out = mask.copy()
    height, width = out.shape
    for _ in range(rounds):
        padded = np.pad(out.astype(np.uint8), 1)
        count = np.zeros_like(out, dtype=np.uint8)
        for dy in range(3):
            for dx in range(3):
                count += padded[dy:dy + height, dx:dx + width]
        out = count >= 5
    return out


def window_sum(mask, radius):
    if radius <= 0:
        return mask.astype(np.int32)
    padded = np.pad(mask.astype(np.int32), radius)
    integral = np.pad(padded, ((1, 0), (1, 0))).cumsum(axis=0).cumsum(axis=1)
    size = radius * 2 + 1
    return (
        integral[size:, size:]
        - integral[:-size, size:]
        - integral[size:, :-size]
        + integral[:-size, :-size]
    )


def binary_erode(mask, radius):
    if radius <= 0:
        return mask.copy()
    size = (radius * 2 + 1) ** 2
    return window_sum(mask, radius) == size


def binary_dilate(mask, radius):
    if radius <= 0:
        return mask.copy()
    return window_sum(mask, radius) > 0


def binary_open(mask, radius):
    return binary_dilate(binary_erode(mask, radius), radius)


def binary_close(mask, radius):
    return binary_erode(binary_dilate(mask, radius), radius)


def load_pixel_area_m2(metadata_path):
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    world = meta["world_bounds"]
    crop = meta["crop_image"]
    meters_per_px_x = (world["x_max"] - world["x_min"]) / max(crop["width"], 1)
    meters_per_px_y = (world["y_max"] - world["y_min"]) / max(crop["height"], 1)
    return meta, meters_per_px_x * meters_per_px_y


def extract_components(mask):
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components = []
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            q = deque([(y, x)])
            visited[y, x] = True
            pixels = []
            while q:
                cy, cx = q.popleft()
                pixels.append((cx, cy))
                for dy, dx in dirs:
                    ny, nx = cy + dy, cx + dx
                    if ny < 0 or ny >= height or nx < 0 or nx >= width:
                        continue
                    if visited[ny, nx] or not mask[ny, nx]:
                        continue
                    visited[ny, nx] = True
                    q.append((ny, nx))
            components.append(pixels)
    return components


def summarize_component(pixels, pixel_area_m2):
    xs = [p[0] for p in pixels]
    ys = [p[1] for p in pixels]
    area_px = len(pixels)
    return {
        "area_px": area_px,
        "area_m2": area_px * pixel_area_m2,
        "centroid": {
            "x": float(sum(xs) / max(area_px, 1)),
            "y": float(sum(ys) / max(area_px, 1)),
        },
        "bbox": {
            "x0": int(min(xs)),
            "y0": int(min(ys)),
            "x1": int(max(xs) + 1),
            "y1": int(max(ys) + 1),
        },
        "pixels": pixels,
    }


def rdp(points, epsilon):
    if len(points) <= 2:
        return points

    start = points[0]
    end = points[-1]
    line = end - start
    line_norm = np.linalg.norm(line)
    if line_norm < 1e-9:
        distances = np.linalg.norm(points[1:-1] - start, axis=1)
    else:
        offsets = points[1:-1] - start
        distances = np.abs(line[0] * offsets[:, 1] - line[1] * offsets[:, 0]) / line_norm

    if len(distances) == 0:
        return points[[0, -1]]

    idx = int(np.argmax(distances))
    dmax = float(distances[idx])
    if dmax <= epsilon:
        return points[[0, -1]]

    left = rdp(points[: idx + 2], epsilon)
    right = rdp(points[idx + 1 :], epsilon)
    return np.vstack([left[:-1], right])


def extract_polygon_from_mask(mask, epsilon):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure()
    try:
        contours = plt.contour(mask.astype(float), levels=[0.5]).allsegs[0]
    finally:
        plt.close(fig)

    if not contours:
        return []

    contour = max(contours, key=lambda pts: len(pts))
    pts = np.asarray(contour, dtype=np.float32)
    if len(pts) < 3:
        return []

    if not np.allclose(pts[0], pts[-1]):
        pts = np.vstack([pts, pts[0]])

    simplified = rdp(pts, epsilon)
    if len(simplified) >= 2 and np.allclose(simplified[0], simplified[-1]):
        simplified = simplified[:-1]

    polygon = []
    for x, y in simplified:
        polygon.append({"x": float(x), "y": float(y)})
    return polygon


def main():
    args = build_parser().parse_args()
    meta, pixel_area_m2 = load_pixel_area_m2(args.metadata)
    meters_per_px = pixel_area_m2 ** 0.5

    img = Image.open(args.input).convert("RGB")
    arr = np.asarray(img).astype(np.float32) / 255.0
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    h, s, v = rgb_to_hsv(r, g, b)

    exg = 2.0 * g - r - b
    not_white = v < 0.985
    greenish = (h > 0.18) & (h < 0.42) & (s > 0.10) & (v > 0.15)
    exg_hit = exg > 0.03
    seed = not_white & (greenish | exg_hit)

    smooth = majority_filter(seed, rounds=2)
    width_radius_px = max(1, int(round((args.min_width_m / max(meters_per_px, 1e-9)) / 2.0)))
    width_filtered = binary_open(smooth, width_radius_px)
    width_filtered = binary_close(width_filtered, max(1, width_radius_px // 2))

    components = extract_components(width_filtered)
    kept_components = []
    keep_mask = np.zeros_like(width_filtered, dtype=bool)
    for pixels in components:
        summary = summarize_component(pixels, pixel_area_m2)
        if summary["area_m2"] >= args.min_area_m2:
            kept_components.append(summary)
            for x, y in pixels:
                keep_mask[y, x] = True

    keep_mask = majority_filter(keep_mask, rounds=1)
    keep_mask = binary_close(keep_mask, 2)
    refined_components = []
    for pixels in extract_components(keep_mask):
        summary = summarize_component(pixels, pixel_area_m2)
        if summary["area_m2"] >= args.min_area_m2:
            refined_components.append(summary)

    final_mask = np.zeros_like(keep_mask, dtype=bool)
    for summary in refined_components:
        for x, y in summary["pixels"]:
            final_mask[y, x] = True

    polygon = extract_polygon_from_mask(final_mask, args.polygon_epsilon_px)

    args.output_mask.parent.mkdir(parents=True, exist_ok=True)
    args.output_overlay.parent.mkdir(parents=True, exist_ok=True)

    mask_u8 = (final_mask.astype(np.uint8) * 255)
    Image.fromarray(mask_u8).save(args.output_mask)

    overlay = np.asarray(img).copy()
    green = np.array([44, 186, 99], dtype=np.uint8)
    alpha = 0.42
    overlay[final_mask] = ((1 - alpha) * overlay[final_mask] + alpha * green).astype(np.uint8)
    Image.fromarray(overlay).save(args.output_overlay)

    if args.output_polygon_overlay is not None:
        from PIL import ImageDraw

        args.output_polygon_overlay.parent.mkdir(parents=True, exist_ok=True)
        polygon_overlay = np.asarray(img).copy()
        polygon_image = Image.fromarray(polygon_overlay)
        draw = ImageDraw.Draw(polygon_image)
        if len(polygon) >= 3:
            line_points = [(pt["x"], pt["y"]) for pt in polygon] + [(polygon[0]["x"], polygon[0]["y"])]
            draw.line(line_points, fill=(16, 134, 74), width=6)
        polygon_image.save(args.output_polygon_overlay)

    review_data = {
        "image": {
            "width": int(arr.shape[1]),
            "height": int(arr.shape[0]),
        },
        "min_area_m2": float(args.min_area_m2),
        "min_width_m": float(args.min_width_m),
        "pixel_area_m2": float(pixel_area_m2),
        "world_bounds": meta["world_bounds"],
        "kept_components": refined_components,
        "polygon": polygon,
    }

    if args.output_metadata is not None:
        args.output_metadata.parent.mkdir(parents=True, exist_ok=True)
        args.output_metadata.write_text(json.dumps(review_data), encoding="utf-8")

    if args.output_review is not None:
        args.output_review.parent.mkdir(parents=True, exist_ok=True)
        html = REVIEW_HTML.replace("__REVIEW_DATA__", json.dumps(review_data))
        args.output_review.write_text(html, encoding="utf-8")

    max_component = max((c["area_m2"] for c in refined_components), default=0.0)
    print(
        "kept_components={} pixel_area_m2={:.5f} max_component_m2={:.1f} polygon_vertices={}".format(
            len(refined_components),
            pixel_area_m2,
            max_component,
            len(polygon),
        )
    )


if __name__ == "__main__":
    main()
