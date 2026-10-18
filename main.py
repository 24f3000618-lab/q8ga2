import json
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

# ---- Setup ----
EMAIL = os.getenv("EMAIL", "24f3000618@ds.study.iitm.ac.in")  # <-- put YOUR email here
START = time.monotonic()          # the moment the app started
LOGS = deque(maxlen=1000)         # a notebook that keeps the last 1000 entries
REQUESTS = Counter("http_requests_total", "Total HTTP requests")  # the turnstile

app = FastAPI()


# ---- Middleware: runs on EVERY request, like a security guard at the door ----
@app.middleware("http")
async def track_everything(request: Request, call_next):
    REQUESTS.inc()                       # click the turnstile
    request_id = str(uuid.uuid4())       # unique ticket number for this request
    began = time.monotonic()

    response = await call_next(request)  # let the request do its actual job

    entry = {
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
        "duration_ms": round((time.monotonic() - began) * 1000, 2),
    }
    LOGS.append(entry)                   # write in the notebook
    print(json.dumps(entry), flush=True) # also print it (shows in hosting dashboards)
    return response


# ---- Endpoints ----
@app.get("/work")
def work(n: int = 1):
    total = 0
    for i in range(min(n, 100_000)):     # "work" = a small loop (capped for safety)
        total += i * i
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": float(time.monotonic() - START)}


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    limit = max(0, limit)
    return list(LOGS)[-limit:] if limit else []