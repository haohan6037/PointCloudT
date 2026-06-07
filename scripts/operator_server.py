#!/usr/bin/env python3

import cgi
import json
import shutil
import subprocess
import threading
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / ".codex-artifacts" / "operator_jobs"
PYTHON_BIN = REPO_ROOT / ".venv" / "bin" / "python"
RENDER_SCRIPT = REPO_ROOT / "scripts" / "render_topview.py"

JOBS = {}
JOBS_LOCK = threading.Lock()


def set_job(job_id, **patch):
    with JOBS_LOCK:
      JOBS[job_id].update(patch)


def get_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return None
        return dict(job)


def create_job_record(filename):
    job_id = uuid.uuid4().hex[:12]
    job_dir = ARTIFACT_ROOT / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "bundle"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 5,
            "message": "任务已创建，等待开始生成高质量底图",
            "filename": filename,
            "job_dir": str(job_dir),
            "bundle_dir": str(output_dir),
        }
    return job_id, input_dir, output_dir


def build_bundle_payload(job_id, bundle_dir):
    metadata_path = bundle_dir / "topview_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError("topview_metadata.json")

    return {
        "metadata_url": f"/.codex-artifacts/operator_jobs/{job_id}/bundle/topview_metadata.json",
        "topview_raw_url": f"/.codex-artifacts/operator_jobs/{job_id}/bundle/topview_raw.png",
        "topview_crop_url": f"/.codex-artifacts/operator_jobs/{job_id}/bundle/topview_crop.png",
        "topview_enhanced_url": f"/.codex-artifacts/operator_jobs/{job_id}/bundle/topview_enhanced.png",
        "topview_truecolor_url": f"/.codex-artifacts/operator_jobs/{job_id}/bundle/topview_truecolor.png",
    }


def run_topview_job(job_id, input_path, output_dir):
    set_job(
        job_id,
        status="running",
        progress=18,
        message="点云文件已保存，准备生成高质量底图",
    )
    output_png = output_dir / "topview_preview.png"
    command = [
        str(PYTHON_BIN),
        str(RENDER_SCRIPT),
        str(input_path),
        str(output_png),
        "--bundle-dir",
        str(output_dir),
    ]

    try:
        set_job(
            job_id,
            progress=38,
            message="高质量底图生成中，这一步可能需要几十秒",
        )
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            error_text = (completed.stderr or completed.stdout or "").strip() or "未知错误"
            set_job(
                job_id,
                status="failed",
                progress=100,
                message=f"高质量底图生成失败：{error_text}",
            )
            return

        set_job(
            job_id,
            progress=82,
            message="底图已生成，正在整理输出文件",
        )
        bundle = build_bundle_payload(job_id, output_dir)
        set_job(
            job_id,
            status="succeeded",
            progress=100,
            message="高质量底图生成完成",
            bundle=bundle,
        )
    except Exception as exc:
        set_job(
            job_id,
            status="failed",
            progress=100,
            message=f"高质量底图生成失败：{exc!r}",
        )


class OperatorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/operator/topview-jobs":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )
        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "file", None):
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing uploaded file")
            return

        filename = Path(file_item.filename or "pointcloud.las").name
        job_id, input_dir, output_dir = create_job_record(filename)
        input_path = input_dir / filename
        with input_path.open("wb") as target:
            shutil.copyfileobj(file_item.file, target)

        worker = threading.Thread(
            target=run_topview_job,
            args=(job_id, input_path, output_dir),
            daemon=True,
        )
        worker.start()

        payload = {
            "job_id": job_id,
            "status": "queued",
            "progress": 5,
            "message": "文件上传完成，等待高质量底图生成开始",
        }
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.ACCEPTED)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/operator/topview-jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = get_job(job_id)
            if not job:
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown job id")
                return
            payload = {
                "job_id": job["job_id"],
                "status": job["status"],
                "progress": job["progress"],
                "message": job["message"],
                "filename": job["filename"],
            }
            if job.get("bundle"):
                payload["bundle"] = job["bundle"]
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()


def main():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8125), OperatorHandler)
    print("Operator server listening on http://127.0.0.1:8125")
    server.serve_forever()


if __name__ == "__main__":
    main()
