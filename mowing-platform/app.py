"""Mowing Platform Stage 1 / 割草服务平台阶段1 — entry point.

Run with:
    python3 -m uvicorn app:app --app-dir mowing-platform --host 127.0.0.1 --port 8011
"""

from importlib import util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROUTES_PATH = ROOT / "routes.py"

spec = util.spec_from_file_location("mowing_platform_routes", ROUTES_PATH)
if spec is None or spec.loader is None:  # pragma: no cover - import-time guard
    raise RuntimeError(f"Unable to load routes module from {ROUTES_PATH}")
routes = util.module_from_spec(spec)
spec.loader.exec_module(routes)

app = routes.app  # noqa: F401 — routes module registers all endpoints on `app`
