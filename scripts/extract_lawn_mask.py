#!/usr/bin/env python3

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


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

    let mode = reviewData.background_mode === "dark" ? "base" : "crop";
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
      if (nextMode === "base") {
        baseImage.src = reviewData.base_image;
        toggleBtn.textContent = reviewData.compare_image ? "切到对比图" : "切到识别图";
      } else {
        baseImage.src = reviewData.compare_image || reviewData.base_image;
        toggleBtn.textContent = "切到展示图";
      }
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
      setMode(mode === "base" ? "compare" : "base");
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
    setMode(mode);
    drawOverlay();
  </script>
</body>
</html>
"""


def build_parser():
    parser = argparse.ArgumentParser(
        description="Extract a lawn candidate mask from top-view image."
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
        "--inset-m",
        type=float,
        default=0.45,
        help="Conservative inward offset in meters before polygon fitting",
    )
    parser.add_argument(
        "--output-inset-mask",
        type=Path,
        default=None,
        help="Optional inset binary mask PNG",
    )
    parser.add_argument(
        "--output-inset-overlay",
        type=Path,
        default=None,
        help="Optional inset overlay preview PNG",
    )
    parser.add_argument(
        "--output-polygon-overlay",
        type=Path,
        default=None,
        help="Optional polygon outline preview PNG",
    )
    parser.add_argument(
        "--council-meta",
        type=Path,
        default=None,
        help="Optional council context JSON (for parcel clipping)",
    )
    parser.add_argument(
        "--registration-transform",
        type=Path,
        default=None,
        help="Optional similarity transform JSON from fit_similarity_transform.py",
    )
    parser.add_argument(
        "--output-parcel-clip-overlay",
        type=Path,
        default=None,
        help="Optional parcel clip overlay preview PNG",
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


def pick_council_rings(council_meta):
    mode = council_meta.get("boundary_mode")
    if mode == "main_parcel":
        main = council_meta.get("main_parcel", {})
        geom = main.get("geometry", {})
        rings = geom.get("rings", [])
        if rings:
            return rings, "main_parcel"
    if mode == "legal_parcel":
        geom = council_meta.get("legal_parcel_geometry", {})
        rings = geom.get("rings", [])
        if rings:
            return rings, "legal_parcel"
    geom = council_meta.get("property_geometry", {})
    rings = geom.get("rings", [])
    return rings, "property"


def pc_world_to_crop_pixel(world_pt, pc_meta):
    world = pc_meta["world_bounds"]
    crop = pc_meta["crop_image"]
    width = max(int(crop["width"]), 1)
    height = max(int(crop["height"]), 1)
    px = ((world_pt["x"] - world["x_min"]) / max(world["x_max"] - world["x_min"], 1e-9)) * (width - 1)
    py = ((world["y_max"] - world_pt["y"]) / max(world["y_max"] - world["y_min"], 1e-9)) * (height - 1)
    return {"x": float(px), "y": float(py)}


def build_parcel_clip_mask(image_w, image_h, pc_meta, council_meta, transform_json):
    council_data = json.loads(council_meta.read_text(encoding="utf-8"))
    transform_data = json.loads(transform_json.read_text(encoding="utf-8"))
    tf = transform_data["transform"]
    rings_world, ring_source = pick_council_rings(council_data)
    if not rings_world:
        return np.ones((image_h, image_w), dtype=bool), {"enabled": False, "reason": "no_rings"}

    crop = pc_meta["crop_image"]
    crop_w = max(int(crop["width"]), 1)
    crop_h = max(int(crop["height"]), 1)
    sx = image_w / float(crop_w)
    sy = image_h / float(crop_h)

    rings_img = []
    for ring in rings_world:
        pts = []
        for x, y in ring:
            pc_world = inverse_similarity(float(x), float(y), tf)
            if pc_world is None:
                continue
            px = pc_world_to_crop_pixel(pc_world, pc_meta)
            pts.append((px["x"] * sx, px["y"] * sy))
        if len(pts) >= 3:
            rings_img.append(pts)

    if not rings_img:
        return np.ones((image_h, image_w), dtype=bool), {"enabled": False, "reason": "no_projected_polygon"}

    mask_img = Image.new("L", (image_w, image_h), 0)
    draw = ImageDraw.Draw(mask_img)
    for pts in rings_img:
        draw.polygon(pts, fill=255)

    mask = np.asarray(mask_img, dtype=np.uint8) > 0
    clip_info = {
        "enabled": True,
        "boundary_source": ring_source,
        "rings": [
            [{"x": float(x), "y": float(y)} for x, y in pts]
            for pts in rings_img
        ],
        "transform": {
            "a": float(tf["a"]),
            "b": float(tf["b"]),
            "tx": float(tf["tx"]),
            "ty": float(tf["ty"]),
        },
        "rmse_m": float(transform_data.get("rmse_m", 0.0)),
    }
    return mask, clip_info


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


def summarize_component(pixels, pixel_area_m2, green_channel=None, exg_map=None):
    xs = [p[0] for p in pixels]
    ys = [p[1] for p in pixels]
    area_px = len(pixels)
    bbox_x0 = int(min(xs))
    bbox_y0 = int(min(ys))
    bbox_x1 = int(max(xs) + 1)
    bbox_y1 = int(max(ys) + 1)
    bbox_width = max(1, bbox_x1 - bbox_x0)
    bbox_height = max(1, bbox_y1 - bbox_y0)
    bbox_area_px = bbox_width * bbox_height
    fill_ratio = float(area_px / max(bbox_area_px, 1))

    pixels_set = set(pixels)
    perimeter_px = 0
    for x, y in pixels_set:
        if (x - 1, y) not in pixels_set:
            perimeter_px += 1
        if (x + 1, y) not in pixels_set:
            perimeter_px += 1
        if (x, y - 1) not in pixels_set:
            perimeter_px += 1
        if (x, y + 1) not in pixels_set:
            perimeter_px += 1

    compactness = 0.0
    if perimeter_px > 0:
        compactness = float((4.0 * np.pi * area_px) / (perimeter_px * perimeter_px))

    mean_green = None
    mean_exg = None
    if green_channel is not None:
        green_vals = green_channel[ys, xs]
        mean_green = float(np.mean(green_vals))
    if exg_map is not None:
        exg_vals = exg_map[ys, xs]
        mean_exg = float(np.mean(exg_vals))

    return {
        "area_px": area_px,
        "area_m2": area_px * pixel_area_m2,
        "centroid": {
            "x": float(sum(xs) / max(area_px, 1)),
            "y": float(sum(ys) / max(area_px, 1)),
        },
        "bbox": {
            "x0": bbox_x0,
            "y0": bbox_y0,
            "x1": bbox_x1,
            "y1": bbox_y1,
        },
        "bbox_width_px": bbox_width,
        "bbox_height_px": bbox_height,
        "bbox_area_px": bbox_area_px,
        "fill_ratio": fill_ratio,
        "perimeter_px": perimeter_px,
        "compactness": compactness,
        "mean_green": mean_green,
        "mean_exg": mean_exg,
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


def choose_primary_component(components):
    if not components:
        return None
    max_area = max(component["area_m2"] for component in components)
    max_shape_score = max(
        component["fill_ratio"] * component["compactness"] for component in components
    )

    ranked = []
    for idx, component in enumerate(components):
        area_norm = component["area_m2"] / max(max_area, 1e-9)
        shape_score = component["fill_ratio"] * component["compactness"]
        shape_norm = shape_score / max(max_shape_score, 1e-9)
        exg_norm = 0.0
        if component["mean_exg"] is not None:
            exg_norm = float(np.clip(component["mean_exg"] / 0.6, 0.0, 1.0))

        selection_score = (
            0.22 * area_norm
            + 0.23 * component["fill_ratio"]
            + 0.50 * shape_norm
            + 0.05 * exg_norm
        )
        component["selection_score"] = float(selection_score)
        ranked.append((idx, component))

    ranked.sort(
        key=lambda item: (
            item[1]["selection_score"],
            item[1]["compactness"],
            item[1]["fill_ratio"],
            item[1]["area_m2"],
        ),
        reverse=True,
    )
    return ranked[0][0]


def candidate_profiles(args):
    return [
        {
            "key": "conservative",
            "label": "保守版",
            "description": "优先主草坪核心，尽量少吃边界",
            "green_shift": 0.01,
            "s_shift": 0.04,
            "v_shift": 0.04,
            "exg_shift": 0.03,
            "majority_rounds": 2,
            "width_scale": 1.22,
            "cleanup_close_radius": 1,
            "inset_m": args.inset_m + 0.18,
        },
        {
            "key": "balanced",
            "label": "平衡版",
            "description": "面积与纯度折中，作为默认推荐",
            "green_shift": 0.0,
            "s_shift": 0.0,
            "v_shift": 0.0,
            "exg_shift": 0.0,
            "majority_rounds": 2,
            "width_scale": 1.0,
            "cleanup_close_radius": 2,
            "inset_m": args.inset_m,
        },
        {
            "key": "aggressive",
            "label": "激进版",
            "description": "尽量覆盖完整草坪，允许更宽松外扩",
            "green_shift": -0.02,
            "s_shift": -0.04,
            "v_shift": -0.05,
            "exg_shift": -0.02,
            "majority_rounds": 1,
            "width_scale": 0.72,
            "cleanup_close_radius": 3,
            "inset_m": max(0.18, args.inset_m - 0.18),
        },
    ]


def build_seed_mask(valid_surface, h, s, v, exg, dark_background, profile):
    if dark_background:
        h_min = 0.10 + profile["green_shift"]
        h_max = 0.22 - profile["green_shift"] * 0.3
        s_min = 0.18 + profile["s_shift"]
        v_min = 0.28 + profile["v_shift"]
        exg_limit = 0.02 + profile["exg_shift"]
    else:
        h_min = 0.11 + profile["green_shift"]
        h_max = 0.23 - profile["green_shift"] * 0.3
        s_min = 0.16 + profile["s_shift"]
        v_min = 0.30 + profile["v_shift"]
        exg_limit = 0.04 + profile["exg_shift"]

    h_min = float(np.clip(h_min, 0.02, 0.35))
    h_max = float(np.clip(h_max, h_min + 0.03, 0.35))
    s_min = float(np.clip(s_min, 0.06, 0.55))
    v_min = float(np.clip(v_min, 0.14, 0.75))
    exg_limit = float(np.clip(exg_limit, -0.02, 0.20))

    greenish = (h > h_min) & (h < h_max) & (s > s_min) & (v > v_min)
    exg_hit = exg > exg_limit
    return valid_surface & (greenish | exg_hit)


def compute_candidate_from_profile(
    profile,
    args,
    pixel_area_m2,
    meters_per_px,
    valid_surface,
    h,
    s,
    v,
    g,
    exg,
    dark_background,
    parcel_clip_mask,
):
    seed = build_seed_mask(valid_surface, h, s, v, exg, dark_background, profile)
    smooth = majority_filter(seed, rounds=profile["majority_rounds"])
    width_radius_px = max(
        1,
        int(round(((args.min_width_m * profile["width_scale"]) / max(meters_per_px, 1e-9)) / 2.0)),
    )
    width_filtered = binary_open(smooth, width_radius_px)
    width_filtered = binary_close(width_filtered, max(1, width_radius_px // 2))
    width_filtered = width_filtered & parcel_clip_mask

    components = extract_components(width_filtered)
    keep_mask = np.zeros_like(width_filtered, dtype=bool)
    for pixels in components:
        area_m2 = len(pixels) * pixel_area_m2
        if area_m2 >= args.min_area_m2:
            for x, y in pixels:
                keep_mask[y, x] = True

    keep_mask = majority_filter(keep_mask, rounds=1)
    keep_mask = binary_close(keep_mask, profile["cleanup_close_radius"])

    refined_components = []
    for pixels in extract_components(keep_mask):
        area_m2 = len(pixels) * pixel_area_m2
        if area_m2 >= args.min_area_m2:
            summary = summarize_component(pixels, pixel_area_m2, g, exg)
            refined_components.append(summary)

    primary_component_index = choose_primary_component(refined_components)
    final_mask = np.zeros_like(keep_mask, dtype=bool)
    selected_component = None
    if primary_component_index is not None and 0 <= primary_component_index < len(refined_components):
        selected_component = refined_components[primary_component_index]
        for x, y in selected_component["pixels"]:
            final_mask[y, x] = True
    final_mask = final_mask & parcel_clip_mask

    inset_radius_px = max(0, int(round(profile["inset_m"] / max(meters_per_px, 1e-9))))
    inset_mask = binary_erode(final_mask, inset_radius_px) if inset_radius_px > 0 else final_mask.copy()
    if not np.any(inset_mask):
        inset_mask = final_mask.copy()
        inset_radius_px = 0

    return {
        "profile": {
            "key": profile["key"],
            "label": profile["label"],
            "description": profile["description"],
        },
        "component_count": len(refined_components),
        "selected_component_index": primary_component_index,
        "selected_component": selected_component,
        "kept_components": refined_components,
        "final_mask": final_mask,
        "inset_mask": inset_mask,
        "inset_radius_px": inset_radius_px,
        "polygon": extract_polygon_from_mask(inset_mask, args.polygon_epsilon_px),
    }


def mask_iou(mask_a, mask_b):
    union = np.logical_or(mask_a, mask_b)
    if not np.any(union):
        return 0.0
    inter = np.logical_and(mask_a, mask_b)
    return float(np.count_nonzero(inter) / max(np.count_nonzero(union), 1))


def serialize_candidate(candidate):
    selected = candidate["selected_component"]
    return {
        "key": candidate["profile"]["key"],
        "label": candidate["profile"]["label"],
        "description": candidate["profile"]["description"],
        "component_count": candidate["component_count"],
        "selected_component_index": candidate["selected_component_index"],
        "selected_area_m2": selected["area_m2"] if selected else None,
        "selected_bbox": selected["bbox"] if selected else None,
        "selection_score": selected.get("selection_score") if selected else None,
        "polygon": candidate["polygon"],
        "inset_radius_px": candidate["inset_radius_px"],
    }


def main():
    args = build_parser().parse_args()
    meta, pixel_area_m2 = load_pixel_area_m2(args.metadata)
    meters_per_px = pixel_area_m2 ** 0.5

    img = Image.open(args.input).convert("RGB")
    arr = np.asarray(img).astype(np.float32) / 255.0
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    h, s, v = rgb_to_hsv(r, g, b)

    exg = 2.0 * g - r - b
    border = np.concatenate([v[0, :], v[-1, :], v[:, 0], v[:, -1]])
    dark_background = float(np.median(border)) < 0.12
    valid_surface = (v > 0.05) if dark_background else (v < 0.985)

    parcel_clip_mask = np.ones_like(valid_surface, dtype=bool)
    parcel_clip_info = {"enabled": False, "reason": "not_requested"}
    if args.council_meta is not None and args.registration_transform is not None:
        parcel_clip_mask, parcel_clip_info = build_parcel_clip_mask(
            valid_surface.shape[1],
            valid_surface.shape[0],
            meta,
            args.council_meta,
            args.registration_transform,
        )

    generated_candidates = []
    for profile in candidate_profiles(args):
        candidate = compute_candidate_from_profile(
            profile,
            args,
            pixel_area_m2,
            meters_per_px,
            valid_surface,
            h,
            s,
            v,
            g,
            exg,
            dark_background,
            parcel_clip_mask,
        )
        if candidate["selected_component"] is None or len(candidate["polygon"]) < 3:
            continue
        duplicate = any(mask_iou(candidate["final_mask"], existing["final_mask"]) >= 0.985 for existing in generated_candidates)
        if not duplicate:
            generated_candidates.append(candidate)

    if not generated_candidates:
        fallback_profile = candidate_profiles(args)[1]
        generated_candidates = [
            compute_candidate_from_profile(
                fallback_profile,
                args,
                pixel_area_m2,
                meters_per_px,
                valid_surface,
                h,
                s,
                v,
                g,
                exg,
                dark_background,
                parcel_clip_mask,
            )
        ]

    default_candidate_index = next(
        (idx for idx, candidate in enumerate(generated_candidates) if candidate["profile"]["key"] == "balanced"),
        0,
    )
    default_candidate = generated_candidates[default_candidate_index]
    final_mask = default_candidate["final_mask"]
    inset_mask = default_candidate["inset_mask"]
    polygon = default_candidate["polygon"]
    refined_components = default_candidate["kept_components"]
    primary_component_index = default_candidate["selected_component_index"]
    inset_radius_px = default_candidate["inset_radius_px"]

    args.output_mask.parent.mkdir(parents=True, exist_ok=True)
    args.output_overlay.parent.mkdir(parents=True, exist_ok=True)

    mask_u8 = (final_mask.astype(np.uint8) * 255)
    Image.fromarray(mask_u8).save(args.output_mask)

    overlay = np.asarray(img).copy()
    green = np.array([44, 186, 99], dtype=np.uint8)
    alpha = 0.42
    overlay[final_mask] = ((1 - alpha) * overlay[final_mask] + alpha * green).astype(np.uint8)
    Image.fromarray(overlay).save(args.output_overlay)

    if args.output_inset_mask is not None:
        args.output_inset_mask.parent.mkdir(parents=True, exist_ok=True)
        inset_u8 = (inset_mask.astype(np.uint8) * 255)
        Image.fromarray(inset_u8).save(args.output_inset_mask)

    if args.output_inset_overlay is not None:
        args.output_inset_overlay.parent.mkdir(parents=True, exist_ok=True)
        inset_overlay = np.asarray(img).copy()
        inset_overlay[inset_mask] = ((1 - alpha) * inset_overlay[inset_mask] + alpha * green).astype(np.uint8)
        Image.fromarray(inset_overlay).save(args.output_inset_overlay)

    if args.output_polygon_overlay is not None:
        args.output_polygon_overlay.parent.mkdir(parents=True, exist_ok=True)
        polygon_overlay = np.asarray(img).copy()
        polygon_image = Image.fromarray(polygon_overlay)
        draw = ImageDraw.Draw(polygon_image)
        if len(polygon) >= 3:
            line_points = [(pt["x"], pt["y"]) for pt in polygon] + [(polygon[0]["x"], polygon[0]["y"])]
            draw.line(line_points, fill=(16, 134, 74), width=6)
        polygon_image.save(args.output_polygon_overlay)

    if args.output_parcel_clip_overlay is not None:
        args.output_parcel_clip_overlay.parent.mkdir(parents=True, exist_ok=True)
        clip_overlay = np.asarray(img).copy()
        clip_rgb = np.array([35, 145, 95], dtype=np.uint8)
        clip_alpha = 0.26
        clip_overlay[parcel_clip_mask] = (
            (1 - clip_alpha) * clip_overlay[parcel_clip_mask] + clip_alpha * clip_rgb
        ).astype(np.uint8)
        Image.fromarray(clip_overlay).save(args.output_parcel_clip_overlay)

    review_data = {
        "image": {
            "width": int(arr.shape[1]),
            "height": int(arr.shape[0]),
        },
        "base_image": args.input.name,
        "compare_image": "topview_enhanced.png" if args.input.name != "topview_enhanced.png" else "topview_crop.png",
        "min_area_m2": float(args.min_area_m2),
        "min_width_m": float(args.min_width_m),
        "inset_m": float(args.inset_m),
        "inset_radius_px": int(inset_radius_px),
        "pixel_area_m2": float(pixel_area_m2),
        "world_bounds": meta["world_bounds"],
        "parcel_clip": parcel_clip_info,
        "background_mode": "dark" if dark_background else "light",
        "kept_components": refined_components,
        "selected_component_index": int(primary_component_index) if primary_component_index is not None else -1,
        "default_candidate_index": int(default_candidate_index),
        "candidates": [serialize_candidate(candidate) for candidate in generated_candidates],
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
        "kept_components={} selected_component_index={} background={} pixel_area_m2={:.5f} max_component_m2={:.1f} polygon_vertices={} candidates={}".format(
            len(refined_components),
            primary_component_index if primary_component_index is not None else -1,
            "dark" if dark_background else "light",
            pixel_area_m2,
            max_component,
            len(polygon),
            len(generated_candidates),
        )
    )


if __name__ == "__main__":
    main()
