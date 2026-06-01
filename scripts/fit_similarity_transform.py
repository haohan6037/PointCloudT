#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np


def solve_similarity(pairs):
    rows = []
    obs = []
    for pair in pairs:
        x = float(pair["pcWorld"]["x"])
        y = float(pair["pcWorld"]["y"])
        xp = float(pair["councilWorld"]["x"])
        yp = float(pair["councilWorld"]["y"])
        rows.append([x, -y, 1.0, 0.0])
        rows.append([y, x, 0.0, 1.0])
        obs.append(xp)
        obs.append(yp)

    a = np.asarray(rows, dtype=float)
    b = np.asarray(obs, dtype=float)
    solution, _, _, _ = np.linalg.lstsq(a, b, rcond=None)
    scale_rot_a, scale_rot_b, tx, ty = solution
    return float(scale_rot_a), float(scale_rot_b), float(tx), float(ty)


def apply_similarity(x, y, a, b, tx, ty):
    return a * x - b * y + tx, b * x + a * y + ty


def compute_rmse(pairs, a, b, tx, ty):
    errs = []
    for pair in pairs:
        x = float(pair["pcWorld"]["x"])
        y = float(pair["pcWorld"]["y"])
        xp = float(pair["councilWorld"]["x"])
        yp = float(pair["councilWorld"]["y"])
        xx, yy = apply_similarity(x, y, a, b, tx, ty)
        errs.append((xx - xp) ** 2 + (yy - yp) ** 2)
    if not errs:
        return 0.0
    return float(np.sqrt(np.mean(errs)))


def main():
    parser = argparse.ArgumentParser(description="Fit similarity transform from pointcloud XY to council NZTM.")
    parser.add_argument("pairs_json", type=Path, help="Registration pairs JSON from registration_lab.html")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(".codex-artifacts/council-context/registration_transform.json"),
        help="Output transform JSON",
    )
    args = parser.parse_args()

    data = json.loads(args.pairs_json.read_text(encoding="utf-8"))
    pairs = data.get("pairs", [])
    if len(pairs) < 2:
        raise SystemExit("Need at least 2 control-point pairs.")

    a, b, tx, ty = solve_similarity(pairs)
    rmse = compute_rmse(pairs, a, b, tx, ty)
    scale = float(np.sqrt(a * a + b * b))
    theta_rad = float(np.arctan2(b, a))
    theta_deg = float(np.degrees(theta_rad))

    out = {
        "version": "similarity-transform-v1",
        "control_points": len(pairs),
        "transform": {
            "a": a,
            "b": b,
            "tx": tx,
            "ty": ty,
            "scale": scale,
            "rotation_rad": theta_rad,
            "rotation_deg": theta_deg,
        },
        "rmse_m": rmse,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"control_points={len(pairs)} rmse_m={rmse:.3f} scale={scale:.6f} rotation_deg={theta_deg:.3f}")


if __name__ == "__main__":
    main()
