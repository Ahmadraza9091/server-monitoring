from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = Path(
    os.environ.get(
        "ACK_STATE_FILE",
        str(Path.home() / ".alert-action" / "acknowledgements.json"),
    )
)
HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("DASHBOARD_PORT", "5050"))
MAX_LIMIT = 500

app = Flask(__name__, template_folder="templates", static_folder="static")
_state_lock = threading.RLock()
_state_cache: dict[str, Any] = {}
_state_mtime_ns: int | None = None


def _load_state() -> dict[str, Any]:
    """Read the bot's state file only when it changes on disk."""
    global _state_cache, _state_mtime_ns
    try:
        mtime_ns = STATE_FILE.stat().st_mtime_ns
    except FileNotFoundError:
        with _state_lock:
            _state_cache = {}
            _state_mtime_ns = None
        return {}

    with _state_lock:
        if _state_mtime_ns == mtime_ns:
            return _state_cache
        try:
            with STATE_FILE.open("r", encoding="utf-8") as state_file:
                data = json.load(state_file)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Incident state file is not valid JSON: {exc}") from exc
        except OSError as exc:
            raise RuntimeError(f"Unable to read incident state file: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError("Incident state file must contain a JSON object")
        _state_cache = data
        _state_mtime_ns = mtime_ns
        return _state_cache


def _records() -> list[dict[str, Any]]:
    return [record for record in _load_state().values() if isinstance(record, dict)]


def _is_active(record: dict[str, Any]) -> bool:
    return not record.get("resolved_at")


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    alert = record.get("alert_data") or {}
    labels = alert.get("labels") or {}
    annotations = alert.get("annotations") or {}
    return {
        "occurrence_id": record.get("occurrence_id"),
        "alert": record.get("alert") or labels.get("alertname") or "Unknown alert",
        "server": record.get("server") or labels.get("instance") or "Unknown server",
        "severity": record.get("severity") or labels.get("severity") or "unknown",
        "action": record.get("action") or "not_acknowledged",
        "status_text": record.get("status_text") or (
            "RESOLVED" if record.get("resolved_at") else "FIRING"
        ),
        "starts_at": record.get("starts_at") or alert.get("startsAt"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "resolved_at": record.get("resolved_at"),
        "resolved_by": record.get("resolved_by"),
        "assignee_name": record.get("assignee_name"),
        "user_name": record.get("user_name"),
        "summary": annotations.get("summary", ""),
        "description": annotations.get("description", ""),
        "timeline_count": len(record.get("timeline") or []),
        "notes_count": len(record.get("notes") or []),
    }


def _sort_key(record: dict[str, Any]) -> str:
    return str(record.get("updated_at") or record.get("created_at") or "")


@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/")
def dashboard():
    return render_template("index.html")


@app.get("/health")
def health():
    _load_state()
    return jsonify(
        {
            "status": "healthy",
            "state_file": str(STATE_FILE),
            "state_file_exists": STATE_FILE.exists(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/api/summary")
def summary():
    records = _records()
    active = [record for record in records if _is_active(record)]
    resolved = [record for record in records if not _is_active(record)]
    severity = {"critical": 0, "warning": 0, "info": 0, "unknown": 0}
    for record in active:
        key = str(record.get("severity") or "unknown").lower()
        severity[key] = severity.get(key, 0) + 1
    return jsonify(
        {
            "total": len(records),
            "active": len(active),
            "resolved": len(resolved),
            "unacknowledged": sum(
                record.get("action", "not_acknowledged") == "not_acknowledged"
                for record in active
            ),
            "assigned": sum(bool(record.get("assignee_name")) for record in active),
            "severity": severity,
            "last_updated": max((_sort_key(record) for record in records), default=None),
        }
    )


@app.get("/api/incidents")
def incidents():
    records = sorted(_records(), key=_sort_key, reverse=True)
    status = request.args.get("status", "all").lower()
    severity = request.args.get("severity", "").lower()
    search = request.args.get("q", "").strip().lower()
    if status == "active":
        records = [record for record in records if _is_active(record)]
    elif status == "resolved":
        records = [record for record in records if not _is_active(record)]
    elif status != "all":
        return jsonify({"error": "status must be active, resolved, or all"}), 400
    if severity:
        records = [
            record for record in records
            if str(record.get("severity", "unknown")).lower() == severity
        ]
    if search:
        records = [
            record for record in records
            if search in json.dumps(_record_summary(record), ensure_ascii=False).lower()
        ]
    try:
        limit = min(max(int(request.args.get("limit", "100")), 1), MAX_LIMIT)
    except ValueError:
        return jsonify({"error": "limit must be a number"}), 400
    return jsonify({"items": [_record_summary(record) for record in records[:limit]], "total": len(records)})


@app.get("/api/incidents/<path:occurrence_id>")
def incident_detail(occurrence_id: str):
    record = _load_state().get(occurrence_id)
    if not isinstance(record, dict):
        return jsonify({"error": "incident not found"}), 404
    return jsonify(record)


@app.errorhandler(RuntimeError)
def state_error(error):
    return jsonify({"error": str(error)}), 503


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, threaded=True)
