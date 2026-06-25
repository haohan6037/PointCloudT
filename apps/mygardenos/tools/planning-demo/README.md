# MyGardenOS Planning Demo

Browser demo for the next-stage chain:

```text
property -> map -> zones -> dock -> path -> task -> heartbeat -> RTK pause
```

Run the backend:

```bash
cd apps/mygardenos/backend
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload
```

If port `8000` is already in use, run:

```bash
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8012
```

Run this static tool:

```bash
cd apps/mygardenos/tools/planning-demo
python3 -m http.server 4176 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:4176
```

The demo uses the backend debug email-code flow. It creates a fresh session, a demo property, map, work zone, no-go zone, dock, path, task, and simulated robot telemetry. It does not publish MQTT commands or control a real robot.
