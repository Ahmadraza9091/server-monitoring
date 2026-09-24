from __future__ import annotations

import logging
import threading
import os
import sys
import json
import copy
import time
import gc
import signal

from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

<<<<<<< HEAD
from flask import Flask, request, jsonify
=======
import hashlib
import secrets
import re
from functools import wraps
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory, session, redirect

try:
    import bcrypt as _bcrypt
    HAVE_BCRYPT = True
except ImportError:
    HAVE_BCRYPT = False
>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

<<<<<<< HEAD
=======
try:
    import pymysql
    import pymysql.cursors
    HAVE_PYMYSQL = True
except ImportError:
    HAVE_PYMYSQL = False

>>>>>>> 381d0a9 (update the alert-action dashboard add more features)

# ============================================================
# CONFIGURATION
# ============================================================

def _default_state_path() -> str:
    if os.name == "nt":
        return os.path.join(os.path.expanduser("~"), ".alert-action", "acknowledgements.json")
    return "/var/lib/alert-action/acknowledgements.json"


def _default_log_path() -> str:
    if os.name == "nt":
        return os.path.join(os.path.expanduser("~"), ".alert-action", "alert-action.log")
    return "/var/log/alert-action.log"


@dataclass(frozen=True)
class AppConfig:

    slack_channel: str = os.environ.get(
        "SLACK_CHANNEL",
        "#warning-alerts"
    )

    alertmanager_url: str = os.environ.get(
        "ALERTMANAGER_URL",
        "http://127.0.0.1:9093"
    ).rstrip("/")

    grafana_url: str = os.environ.get(
        "GRAFANA_URL",
        ""
    ).rstrip("/")

    prometheus_url: str = os.environ.get(
        "PROMETHEUS_URL",
        ""
    ).rstrip("/")

    slack_bot_token: str = os.environ.get(
        "SLACK_BOT_TOKEN",
        ""
    )
    slack_signing_secret: str = os.environ.get(

        "SLACK_SIGNING_SECRET",
        ""

    )


    slack_app_token: str = os.environ.get(

        "SLACK_APP_TOKEN",
        ""

    )


    ack_state_file: str = os.environ.get(

        "ACK_STATE_FILE",

        _default_state_path()

    )


    log_file: str = os.environ.get(

        "LOG_FILE",
        _default_log_path()

    )


    silence_duration_hours: int = int(

        os.environ.get(

            "SILENCE_DURATION_HOURS",
            "4"
        )

    )


    resolve_monitor_interval: int = int(

        os.environ.get(
            "RESOLVE_MONITOR_INTERVAL",

            "15"
        )

    )


    http_timeout: int = int(
        os.environ.get(

            "HTTP_TIMEOUT",
            "10"
        )
    )


    retention_days: int = int(
        os.environ.get(
            "RETENTION_DAYS",

            "7"
        )
    )

    reject_escalation_seconds: int = int(
        os.environ.get(
            "REJECT_ESCALATION_SECONDS",
            os.environ.get(
                "ESCALATION_INTERVAL",
                "0"
            )
        )
    )

<<<<<<< HEAD
=======
    # MariaDB is the primary store. JSON is available only when explicitly
    # selected with STORAGE_BACKEND=json.
    storage_backend: str = os.environ.get("STORAGE_BACKEND", "mariadb").lower()
    db_host: str = os.environ.get("DB_HOST", "127.0.0.1")
    db_port: int = int(os.environ.get("DB_PORT", "3306"))
    db_name: str = os.environ.get("DB_NAME", "proxmox_alerts")
    db_user: str = os.environ.get("DB_USER", "proxmox_user")
    db_password: str = os.environ.get("DB_PASSWORD", "tbcadmin123@")

>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
    def validate(self) -> List[str]:
        missing = []
        if not self.slack_bot_token:
            missing.append("SLACK_BOT_TOKEN")
        if not self.slack_signing_secret:
            missing.append("SLACK_SIGNING_SECRET")
        if not self.slack_app_token:
            missing.append("SLACK_APP_TOKEN")
        return missing


config = AppConfig()


# ============================================================
# LOGGING
# ============================================================

def setup_logging(cfg: AppConfig) -> logging.Logger:
    handlers: List[logging.Handler] = [
        logging.StreamHandler(sys.stdout)
    ]

    if cfg.log_file:
        try:
            log_dir = os.path.dirname(os.path.abspath(cfg.log_file))
            os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                cfg.log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8"
            )
            handlers.append(file_handler)
        except Exception as e:
            print(
                f"Warning: Failed to setup file logger at {cfg.log_file}: {e}"
            )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True
    )

    return logging.getLogger("alert-action")


logger = setup_logging(config)

missing_vars = config.validate()
if missing_vars:
    logger.warning(
        "Missing required environment variables: %s (Normal during tests or local setup)",
        ", ".join(missing_vars)
    )


# ============================================================
# OCCURRENCE ID & TIME HELPERS
# ============================================================

def build_occurrence_id(
    fingerprint: str,
    starts_at: Optional[str]
) -> str:
    clean_starts = (
        starts_at or "unknown"
    ).strip().replace(":", "-")
    return f"{fingerprint}_{clean_starts}"


def parse_alert_time(
    value: Any
) -> Optional[datetime]:
    if not value:
        return None

    try:
<<<<<<< HEAD
=======
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
        val_str = str(value).strip()
        if val_str.startswith("0001-01-01"):
            return None

<<<<<<< HEAD
        if val_str.endswith("Z"):
=======
        # Clean trailing UTC or Z
        if val_str.endswith(" UTC"):
            val_str = val_str[:-4].strip() + "+00:00"
        elif val_str.endswith("Z"):
>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
            val_str = val_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(val_str)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc)
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
<<<<<<< HEAD
=======
        # Fallback to common timestamp formats
        clean_str = str(value).replace(" UTC", "").replace("Z", "").strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(clean_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
        return None


def format_display_time(
    value: Any
) -> str:
    parsed = (
        parse_alert_time(value)
        if not isinstance(value, datetime)
        else value
    )
    return (
        parsed.strftime("%Y-%m-%d %H:%M:%S UTC")
        if parsed
        else str(value or "Unknown")
    )


def format_duration(
    seconds: int | float
) -> str:
    try:
        sec = max(0, int(seconds))
    except (ValueError, TypeError):
        return "0s"

    days, sec = divmod(sec, 86400)
    hours, sec = divmod(sec, 3600)
    minutes, sec = divmod(sec, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if sec or not parts:
        parts.append(f"{sec}s")

    return " ".join(parts)


def get_alert_duration(
    alert: Dict[str, Any],
    end_time: Optional[datetime] = None
) -> Optional[int]:
    starts_at = parse_alert_time(
        alert.get("startsAt")
    )
    if not starts_at:
        return None

    if end_time is None:
        end_time = datetime.now(timezone.utc)

    return max(
        0,
        int((end_time - starts_at).total_seconds())
    )


def is_downtime_alert(
    alert: Dict[str, Any]
) -> bool:
    labels = alert.get("labels", {})
    alert_type = labels.get("alert_type", "").lower()

    if alert_type in ("availability", "downtime"):
        return True

    if alert_type in ("resource", "performance", "capacity"):
        return False

    alertname = labels.get("alertname", "").lower()
    service = labels.get("service", "").lower()

    return (
        "down" in alertname
        or (
            service == "server"
            and any(
                k in alertname
                for k in ("offline", "unreachable", "unavailable")
            )
        )
    )


def calculate_pause_end_time(
    pause_key: str,
    now: Optional[datetime] = None
) -> Tuple[datetime, str]:
    if now is None:
        now = datetime.now(timezone.utc)

    if pause_key == "30m":
        end_time = now + timedelta(minutes=30)
        label = "30 Minutes"
    elif pause_key == "1h":
        end_time = now + timedelta(hours=1)
        label = "1 Hour"
    elif pause_key == "4h":
        end_time = now + timedelta(hours=4)
        label = "4 Hours"
    elif pause_key == "8h":
        end_time = now + timedelta(hours=8)
        label = "8 Hours (Workday)"
    elif pause_key == "24h":
        end_time = now + timedelta(hours=24)
        label = "24 Hours (1 Day)"
    elif pause_key == "tomorrow_9am":
        tomorrow = now.date() + timedelta(days=1)
        end_time = datetime(
            tomorrow.year, tomorrow.month, tomorrow.day, 9, 0, 0, tzinfo=timezone.utc
        )
        if (end_time - now).total_seconds() < 1800:
            end_time += timedelta(days=1)
        diff_hours = (end_time - now).total_seconds() / 3600.0
        label = f"Tomorrow 09:00 UTC (~{diff_hours:.1f}h)"
    elif pause_key == "next_monday_9am":
        days_ahead = (0 - now.weekday()) % 7
        if days_ahead == 0 and now.hour >= 8:
            days_ahead = 7
        if days_ahead == 0:
            days_ahead = 7
        target_date = now.date() + timedelta(days=days_ahead)
        end_time = datetime(
            target_date.year, target_date.month, target_date.day, 9, 0, 0, tzinfo=timezone.utc
        )
        diff_hours = (end_time - now).total_seconds() / 3600.0
        label = f"Next Monday 09:00 UTC (~{diff_hours:.1f}h)"
    else:
        end_time = now + timedelta(hours=4)
        label = "4 Hours"

    return end_time, label


def resolve_by_from_record(
    record: Optional[Dict[str, Any]],
    explicit: Optional[str] = None
) -> str:
    """
    Resolution attribution:
    - If acknowledged (accepted) -> resolving user
    - Else if assigned -> assignee
    - Else -> System Auto-detect
    Explicit override (e.g. webhook metadata) wins when provided.
    """
    if explicit:
        return explicit
    if not record:
        return "System Auto-detect"

    action = record.get("action")
    if action == "accepted" and record.get("user_id"):
        uid = record.get("user_id")
        uname = record.get("user_name") or "User"
        return f"<@{uid}> ({uname})"

    if record.get("assignee_id"):
        aid = record.get("assignee_id")
        aname = record.get("assignee_name") or "Assignee"
        return f"<@{aid}> ({aname})"

    return "System Auto-detect"


# ============================================================
# FAST IN-MEMORY & ATOMIC JSON STATE STORE
# ============================================================

class JsonStateStore:
    """
    High performance atomic JSON state store with memory cache.
    Eliminates repetitive disk I/O on every lookup for ultra-fast alerts.
    """

    def __init__(
        self,
        filepath: str,
        retention_days: int = 7
    ):
        self.filepath = filepath
        self.retention_days = retention_days
        self.lock = threading.RLock()
        self._cache: Dict[str, Any] = {}

        try:
            os.makedirs(
                os.path.dirname(os.path.abspath(filepath)),
                exist_ok=True
            )
        except Exception as e:
            logger.warning("Could not create state store directory: %s", e)

        self._load_from_disk()

    def _load_from_disk(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._cache = {}
                return

            try:
<<<<<<< HEAD
                with open(self.filepath, "r", encoding="utf-8") as f:
=======
                with open(self.filepath, "r", encoding="utf-8-sig") as f:
>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
                    data = json.load(f)
                    self._cache = data if isinstance(data, dict) else {}
            except Exception as e:
                logger.error("Error reading JSON state file: %s", e)
                self._cache = {}

    def _save_to_disk_locked(self) -> None:
        temp_file = f"{self.filepath}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

            os.replace(temp_file, self.filepath)
        except Exception as e:
            logger.error("Error saving JSON state file: %s", e)
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

    def get(
        self,
        occurrence_id: str
    ) -> Optional[Dict[str, Any]]:
        if not occurrence_id:
            return None
        with self.lock:
            val = self._cache.get(occurrence_id)
            return copy.deepcopy(val) if val else None

    def get_latest_active_by_fingerprint(
        self,
        fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            candidates = [
                v
                for v in self._cache.values()
                if (
                    v.get("fingerprint") == fingerprint
                    and not v.get("resolved_at")
                )
            ]
            if not candidates:
                return None

            return copy.deepcopy(
                sorted(
                    candidates,
                    key=lambda x: x.get("created_at", ""),
                    reverse=True
                )[0]
            )

    def save_or_append_notification(
        self,
        occurrence_id: str,
        fingerprint: str,
        starts_at: str,
        channel_id: str,
        message_ts: str,
        alert_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self.lock:
            now = datetime.now(timezone.utc).isoformat()
            record = self._cache.get(occurrence_id)

            msg_entry = {
                "channel_id": channel_id,
                "message_ts": message_ts,
                "posted_at": now,
                "action": "not_acknowledged"
            }

            if not record:
                labels = alert_data.get("labels", {})
                record = {
                    "occurrence_id": occurrence_id,
                    "fingerprint": fingerprint,
                    "starts_at": starts_at,
                    "action": "not_acknowledged",
                    "status_text": "FIRING",
                    "channel_id": channel_id,
                    "message_ts": message_ts,
                    "messages": [msg_entry],
                    "alert": labels.get("alertname", "Unknown"),
                    "server": labels.get("instance", "Unknown"),
                    "severity": labels.get("severity", "unknown"),
                    "alert_data": self._trim_alert(alert_data),
                    "assignee_id": None,
                    "assignee_name": None,
                    "referred_by_id": None,
                    "referred_by_name": None,
                    "assigned_at": None,
                    "user_id": None,
                    "user_name": None,
                    "action_at": None,
                    "silence_id": None,
                    "silence_ends_at": None,
                    "silence_label": None,
                    "timeline": [
                        {
                            "time": now,
                            "type": "fired",
                            "text": "🚨 Incident triggered and posted to Slack"
                        }
                    ],
                    "notes": [],
                    "resolved_at": None,
                    "created_at": now,
                    "updated_at": now
                }
            else:
                messages = record.get("messages", [])
                messages.append(msg_entry)
                record["messages"] = messages
                record["message_ts"] = message_ts
                record["channel_id"] = channel_id
                record["updated_at"] = now

                # After REJECT: reset action state so the new card shows FIRING with buttons active
                if record.get("action") == "rejected":
                    record["action"] = "not_acknowledged"
                    record["status_text"] = "FIRING"
                    record["user_id"] = None
                    record["user_name"] = None
                    record["action_at"] = None
                    record["silence_id"] = None
                    record["silence_ends_at"] = None
                    record["silence_label"] = None

                    timeline = record.get("timeline", [])
                    timeline.append({
                        "time": now,
                        "type": "refired",
                        "text": "🚨 Re-notified / Escalated after rejection (FIRING)"
                    })
                    record["timeline"] = timeline

            self._cache[occurrence_id] = record
            self._save_to_disk_locked()
            return copy.deepcopy(record)

    def update_action(
        self,
        occurrence_id: str,
        action: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        action_at: Optional[str] = None,
        target_message_ts: Optional[str] = None,
        silence_id: Optional[str] = None,
        silence_ends_at: Optional[str] = None,
        silence_label: Optional[str] = None,
        timeline_entry: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            if not record:
                return None

            record["action"] = action
            # For rejected action, keep user details anonymous
            if action == "rejected":
                record["user_id"] = None
                record["user_name"] = None
            else:
                record["user_id"] = user_id
                record["user_name"] = user_name

            record["action_at"] = action_at

            # Always update silence fields when explicitly resuming/clearing.
            # Guard prevents accidentally overwriting on actions that don't touch silence.
            if action == "not_acknowledged":
                # Resume: always clear ALL silence fields
                record["silence_id"] = None
                record["silence_ends_at"] = None
                record["silence_label"] = None
            else:
                # For paused/accepted: only update if caller explicitly passed a value
                if silence_id is not None:
                    record["silence_id"] = silence_id
                if silence_ends_at is not None:
                    record["silence_ends_at"] = silence_ends_at
                if silence_label is not None:
                    record["silence_label"] = silence_label

            now_iso = datetime.now(timezone.utc).isoformat()
            record["updated_at"] = now_iso

            timeline = record.get("timeline", [])
            if timeline_entry:
                t_entry: Dict[str, Any] = {
                    "time": now_iso,
                    "type": action,
                    "text": timeline_entry
                }
                if action != "rejected" and user_id:
                    t_entry["user_id"] = user_id
                    t_entry["user_name"] = user_name
                timeline.append(t_entry)
                record["timeline"] = timeline

            for msg in record.get("messages", []):
                if target_message_ts and msg.get("message_ts") == target_message_ts:
                    msg["action"] = action
                    if action != "rejected":
                        msg["user_id"] = user_id
                        msg["user_name"] = user_name
                    msg["action_at"] = action_at

            self._cache[occurrence_id] = record
            self._save_to_disk_locked()
            return copy.deepcopy(record)

    def update_assignment(
        self,
        occurrence_id: str,
        assignee_id: str,
        assignee_name: str,
        referred_by_id: str,
        referred_by_name: str,
        action_at: str
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            if not record:
                return None

            record["assignee_id"] = assignee_id
            record["assignee_name"] = assignee_name
            record["referred_by_id"] = referred_by_id
            record["referred_by_name"] = referred_by_name
            record["assigned_at"] = action_at

            now_iso = datetime.now(timezone.utc).isoformat()
            record["updated_at"] = now_iso

            timeline = record.get("timeline", [])
            timeline.append({
                "time": now_iso,
                "type": "assigned",
                "user_id": referred_by_id,
                "user_name": referred_by_name,
                "assignee_id": assignee_id,
                "text": f"👤 Assigned to <@{assignee_id}> by <@{referred_by_id}>"
            })
            record["timeline"] = timeline

            self._cache[occurrence_id] = record
            self._save_to_disk_locked()
            return copy.deepcopy(record)

    def add_timeline_note(
        self,
        occurrence_id: str,
        user_id: str,
        user_name: str,
        note: str
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            if not record:
                return None

            now_iso = datetime.now(timezone.utc).isoformat()
            timeline = record.get("timeline", [])
            timeline.append({
                "time": now_iso,
                "type": "note",
                "user_id": user_id,
                "user_name": user_name,
                "text": note
            })
            record["timeline"] = timeline

            notes = record.get("notes", [])
            notes.append({
                "time": now_iso,
                "user_id": user_id,
                "user_name": user_name,
                "text": note
            })
            record["notes"] = notes
            record["updated_at"] = now_iso

            self._cache[occurrence_id] = record
            self._save_to_disk_locked()
            return copy.deepcopy(record)

    def try_claim_resolution(
        self,
        occurrence_id: str,
        resolution_time_str: str,
        alert_data: Optional[Dict[str, Any]] = None,
        resolved_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            now = datetime.now(timezone.utc).isoformat()

            if not record:
                record = {
                    "occurrence_id": occurrence_id,
                    "fingerprint": occurrence_id.split("_")[0],
                    "action": "not_acknowledged",
                    "messages": [],
                    "alert_data": self._trim_alert(alert_data or {}),
                    "resolved_at": resolution_time_str,
                    "resolved_by": resolved_by or "System Auto-detect",
                    "timeline": [
                        {
                            "time": now,
                            "type": "resolved",
                            "text": f"🟢 Resolved at {resolution_time_str}"
                        }
                    ],
                    "notes": [],
                    "created_at": now,
                    "updated_at": now
                }
                self._cache[occurrence_id] = record
                self._save_to_disk_locked()
                return copy.deepcopy(record)

            if record.get("resolved_at"):
                return None

            record["resolved_at"] = resolution_time_str
            record["resolved_by"] = resolved_by or "System Auto-detect"
            record["updated_at"] = now

            timeline = record.get("timeline", [])
            timeline.append({
                "time": now,
                "type": "resolved",
                "text": f"🟢 Resolved ({record['resolved_by']})"
            })
            record["timeline"] = timeline

            self._cache[occurrence_id] = record
            self._save_to_disk_locked()
            return copy.deepcopy(record)

    def has_unresolved_active_alerts(self) -> bool:
        with self.lock:
            return any(not v.get("resolved_at") for v in self._cache.values())

    def get_unresolved_active_alerts(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [
                copy.deepcopy(v)
                for v in self._cache.values()
                if not v.get("resolved_at")
            ]

<<<<<<< HEAD
=======
    def get_all_records(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [copy.deepcopy(v) for v in self._cache.values()]

>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
    def prune_old_records(self) -> None:
        with self.lock:
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            ).isoformat()

            new_data = {
                k: v
                for k, v in self._cache.items()
                if not (v.get("resolved_at") and v.get("updated_at", "") < cutoff)
            }

            if len(new_data) != len(self._cache):
                count = len(self._cache) - len(new_data)
                self._cache = new_data
                self._save_to_disk_locked()
                logger.info("Pruned %d expired occurrences from JSON state store.", count)

    @staticmethod
    def _trim_alert(
        alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        return {
            "fingerprint": alert.get("fingerprint"),
            "startsAt": alert.get("startsAt"),
            "endsAt": alert.get("endsAt"),
            "generatorURL": alert.get("generatorURL", ""),
            "labels": {
                k: v for k, v in labels.items() if not k.startswith("__")
            },
            "annotations": {
                "summary": annotations.get("summary", "")[:400],
                "description": annotations.get("description", "")[:800],
                "runbook_url": annotations.get("runbook_url", ""),
                "dashboard": annotations.get("dashboard", "")
            }
        }


<<<<<<< HEAD
store = JsonStateStore(
    config.ack_state_file,
    retention_days=config.retention_days
=======
# ============================================================
# DIRECT MARIADB STATE STORE
# ============================================================

class MariaDBStateStore:
    """
    Direct MariaDB State Store with in-memory caching.
    Ensures zero-latency responses for Slack interactions while persisting
    all incidents, actions, notes, and resolutions directly into MariaDB.
    """

    def __init__(self, cfg: AppConfig):
        self.config = cfg
        self.retention_days = cfg.retention_days
        self.lock = threading.RLock()
        self._cache: Dict[str, Any] = {}
        self._conn: Optional[Any] = None

        self._init_db()

    def _get_connection(self):
        if self._conn is not None:
            try:
                self._conn.ping(reconnect=True)
                return self._conn
            except Exception:
                self._conn = None

        max_attempts = 15
        last_err = None
        for attempt in range(1, max_attempts + 1):
            try:
                self._conn = pymysql.connect(
                    host=self.config.db_host,
                    port=self.config.db_port,
                    user=self.config.db_user,
                    password=self.config.db_password,
                    database=self.config.db_name,
                    charset="utf8mb4",
                    autocommit=True,
                    connect_timeout=10,
                    cursorclass=pymysql.cursors.DictCursor
                )
                logger.info("Connected to MariaDB database '%s' at %s:%s.", self.config.db_name, self.config.db_host, self.config.db_port)
                return self._conn
            except pymysql.err.OperationalError as err:
                last_err = err
                # 1049 is ER_BAD_DB_ERROR: database does not exist
                if err.args and err.args[0] == 1049:
                    logger.info("Database '%s' does not exist. Creating it automatically...", self.config.db_name)
                    root_pass = os.environ.get("DB_ROOT_PASSWORD", "tbcroot123@")
                    created = False
                    for u, p in [(self.config.db_user, self.config.db_password), ("root", root_pass)]:
                        try:
                            admin_conn = pymysql.connect(
                                host=self.config.db_host,
                                port=self.config.db_port,
                                user=u,
                                password=p,
                                charset="utf8mb4",
                                autocommit=True,
                                connect_timeout=10
                            )
                            with admin_conn.cursor() as cur:
                                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.config.db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                                cur.execute(f"GRANT ALL PRIVILEGES ON `{self.config.db_name}`.* TO '{self.config.db_user}'@'%';")
                                cur.execute("FLUSH PRIVILEGES;")
                            admin_conn.close()
                            created = True
                            break
                        except Exception as ex:
                            logger.debug("Could not create DB as %s: %s", u, ex)
                    if created:
                        continue

                # If connection refused or name resolution failed, wait and retry
                logger.warning(
                    "Waiting for MariaDB at %s:%s (attempt %d/%d): %s",
                    self.config.db_host, self.config.db_port, attempt, max_attempts, err
                )
                time.sleep(2)
            except Exception as ex:
                last_err = ex
                logger.warning(
                    "Waiting for MariaDB connection (attempt %d/%d): %s",
                    attempt, max_attempts, ex
                )
                time.sleep(2)

        if last_err:
            raise last_err
        return self._conn

    def _init_db(self) -> None:
        with self.lock:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS acknowledgements (
                    occurrence_id VARCHAR(128) NOT NULL PRIMARY KEY,
                    fingerprint VARCHAR(64) NOT NULL,
                    alert_name VARCHAR(128) NOT NULL,
                    server VARCHAR(128) DEFAULT '',
                    severity VARCHAR(32) DEFAULT 'info',
                    action VARCHAR(64) DEFAULT 'not_acknowledged',
                    assignee_id VARCHAR(64) DEFAULT '',
                    assignee_name VARCHAR(128) DEFAULT '',
                    user_id VARCHAR(64) DEFAULT '',
                    user_name VARCHAR(128) DEFAULT '',
                    channel_id VARCHAR(64) DEFAULT '',
                    message_ts VARCHAR(64) DEFAULT '',
                    starts_at VARCHAR(64) DEFAULT '',
                    ends_at VARCHAR(64) DEFAULT '',
                    resolved_at VARCHAR(64) DEFAULT '',
                    silence_id VARCHAR(128) DEFAULT '',
                    record_data JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_fingerprint (fingerprint),
                    INDEX idx_alert_name (alert_name),
                    INDEX idx_server (server),
                    INDEX idx_severity (severity),
                    INDEX idx_action (action),
                    INDEX idx_resolved_at (resolved_at),
                    INDEX idx_updated_at (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

                # Upgrade databases created by the older init.sql schema.
                cur.execute("SHOW COLUMNS FROM acknowledgements LIKE 'record_data';")
                if not cur.fetchone():
                    cur.execute(
                        "ALTER TABLE acknowledgements ADD COLUMN record_data JSON NULL AFTER silence_id;"
                    )
                    cur.execute("""
                        UPDATE acknowledgements
                        SET record_data = JSON_OBJECT(
                            'occurrence_id', occurrence_id,
                            'fingerprint', fingerprint,
                            'alert', alert_name,
                            'server', server,
                            'severity', severity,
                            'action', action,
                            'assignee_id', assignee_id,
                            'assignee_name', assignee_name,
                            'user_id', user_id,
                            'user_name', user_name,
                            'channel_id', channel_id,
                            'message_ts', message_ts,
                            'starts_at', starts_at,
                            'ends_at', ends_at,
                            'resolved_at', resolved_at,
                            'silence_id', silence_id,
                            'alert_data', alert_data,
                            'timeline', timeline,
                            'notes', notes,
                            'messages', messages
                        )
                        WHERE record_data IS NULL;
                    """)

                # Load existing records into cache
                cur.execute(
                    "SELECT occurrence_id, record_data FROM acknowledgements "
                    "WHERE record_data IS NOT NULL;"
                )
                rows = cur.fetchall()
                for row in rows:
                    occ_id = row.get("occurrence_id")
                    raw_data = row.get("record_data")
                    if occ_id and raw_data:
                        try:
                            self._cache[occ_id] = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                        except Exception:
                            pass

            logger.info("Loaded %d records from MariaDB into active memory cache.", len(self._cache))

            # If MariaDB was completely empty, check if existing JSON file has records to auto-populate
            if not self._cache and os.path.exists(self.config.ack_state_file):
                try:
                    with open(self.config.ack_state_file, "r", encoding="utf-8-sig") as f:
                        disk_data = json.load(f)
                    if isinstance(disk_data, dict) and disk_data:
                        logger.info("Auto-syncing %d records from existing JSON into MariaDB...", len(disk_data))
                        for k, v in disk_data.items():
                            if isinstance(v, dict):
                                self._cache[k] = v
                                self._persist_record(v)
                except Exception as ex:
                    logger.warning("Could not auto-populate MariaDB from JSON: %s", ex)

    def _persist_record(self, record: Dict[str, Any]) -> None:
        occ_id = record.get("occurrence_id", "")
        if not occ_id:
            return

        labels = (record.get("alert_data") or {}).get("labels") or {}
        alert_name = record.get("alert") or labels.get("alertname") or "Unknown"
        server = record.get("server") or labels.get("instance") or ""
        severity = (record.get("severity") or labels.get("severity") or "info").lower()
        action = record.get("action") or "not_acknowledged"

        sql = """
        INSERT INTO acknowledgements (
            occurrence_id, fingerprint, alert_name, server, severity,
            action, assignee_id, assignee_name, user_id, user_name,
            channel_id, message_ts, starts_at, ends_at, resolved_at,
            silence_id, record_data
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s
        ) ON DUPLICATE KEY UPDATE
            fingerprint = VALUES(fingerprint),
            alert_name = VALUES(alert_name),
            server = VALUES(server),
            severity = VALUES(severity),
            action = VALUES(action),
            assignee_id = VALUES(assignee_id),
            assignee_name = VALUES(assignee_name),
            user_id = VALUES(user_id),
            user_name = VALUES(user_name),
            channel_id = VALUES(channel_id),
            message_ts = VALUES(message_ts),
            starts_at = VALUES(starts_at),
            ends_at = VALUES(ends_at),
            resolved_at = VALUES(resolved_at),
            silence_id = VALUES(silence_id),
            record_data = VALUES(record_data),
            updated_at = CURRENT_TIMESTAMP;
        """

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(sql, (
                    str(occ_id),
                    str(record.get("fingerprint") or occ_id.split("_")[0]),
                    str(alert_name),
                    str(server),
                    str(severity),
                    str(action),
                    str(record.get("assignee_id") or ""),
                    str(record.get("assignee_name") or ""),
                    str(record.get("user_id") or ""),
                    str(record.get("user_name") or ""),
                    str(record.get("channel_id") or ""),
                    str(record.get("message_ts") or ""),
                    str(record.get("starts_at") or ""),
                    str(record.get("ends_at") or ""),
                    str(record.get("resolved_at") or ""),
                    str(record.get("silence_id") or ""),
                    json.dumps(record, ensure_ascii=False)
                ))
        except Exception as e:
            logger.error("Error persisting record %s to MariaDB: %s", occ_id, e)

    def get(self, occurrence_id: str) -> Optional[Dict[str, Any]]:
        if not occurrence_id:
            return None
        with self.lock:
            val = self._cache.get(occurrence_id)
            return copy.deepcopy(val) if val else None

    def get_latest_active_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            candidates = [
                v for v in self._cache.values()
                if (v.get("fingerprint") == fingerprint and not v.get("resolved_at"))
            ]
            if not candidates:
                return None
            return copy.deepcopy(
                sorted(candidates, key=lambda x: x.get("created_at", ""), reverse=True)[0]
            )

    def save_or_append_notification(
        self,
        occurrence_id: str,
        fingerprint: str,
        starts_at: str,
        channel_id: str,
        message_ts: str,
        alert_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self.lock:
            now = datetime.now(timezone.utc).isoformat()
            record = self._cache.get(occurrence_id)

            msg_entry = {
                "channel_id": channel_id,
                "message_ts": message_ts,
                "posted_at": now,
                "action": "not_acknowledged"
            }

            if not record:
                labels = alert_data.get("labels", {})
                record = {
                    "occurrence_id": occurrence_id,
                    "fingerprint": fingerprint,
                    "starts_at": starts_at,
                    "action": "not_acknowledged",
                    "status_text": "FIRING",
                    "channel_id": channel_id,
                    "message_ts": message_ts,
                    "messages": [msg_entry],
                    "alert": labels.get("alertname", "Unknown"),
                    "server": labels.get("instance", "Unknown"),
                    "severity": labels.get("severity", "unknown"),
                    "alert_data": JsonStateStore._trim_alert(alert_data),
                    "assignee_id": None,
                    "assignee_name": None,
                    "referred_by_id": None,
                    "referred_by_name": None,
                    "assigned_at": None,
                    "user_id": None,
                    "user_name": None,
                    "action_at": None,
                    "silence_id": None,
                    "silence_ends_at": None,
                    "silence_label": None,
                    "timeline": [
                        {
                            "time": now,
                            "type": "fired",
                            "text": "🚨 Incident triggered and posted to Slack"
                        }
                    ],
                    "notes": [],
                    "resolved_at": None,
                    "created_at": now,
                    "updated_at": now
                }
            else:
                messages = record.get("messages", [])
                messages.append(msg_entry)
                record["messages"] = messages
                record["message_ts"] = message_ts
                record["channel_id"] = channel_id
                record["updated_at"] = now

                if record.get("action") == "rejected":
                    record["action"] = "not_acknowledged"
                    record["status_text"] = "FIRING"
                    record["user_id"] = None
                    record["user_name"] = None
                    record["action_at"] = None
                    record["silence_id"] = None
                    record["silence_ends_at"] = None
                    record["silence_label"] = None

                    timeline = record.get("timeline", [])
                    timeline.append({
                        "time": now,
                        "type": "refired",
                        "text": "🚨 Re-notified / Escalated after rejection (FIRING)"
                    })
                    record["timeline"] = timeline

            self._cache[occurrence_id] = record
            self._persist_record(record)
            return copy.deepcopy(record)

    def update_action(
        self,
        occurrence_id: str,
        action: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        action_at: Optional[str] = None,
        target_message_ts: Optional[str] = None,
        silence_id: Optional[str] = None,
        silence_ends_at: Optional[str] = None,
        silence_label: Optional[str] = None,
        timeline_entry: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            if not record:
                return None

            record["action"] = action
            if action == "rejected":
                record["user_id"] = None
                record["user_name"] = None
            else:
                record["user_id"] = user_id
                record["user_name"] = user_name

            record["action_at"] = action_at

            if action == "not_acknowledged":
                record["silence_id"] = None
                record["silence_ends_at"] = None
                record["silence_label"] = None
            else:
                if silence_id is not None:
                    record["silence_id"] = silence_id
                if silence_ends_at is not None:
                    record["silence_ends_at"] = silence_ends_at
                if silence_label is not None:
                    record["silence_label"] = silence_label

            now_iso = datetime.now(timezone.utc).isoformat()
            record["updated_at"] = now_iso

            timeline = record.get("timeline", [])
            if timeline_entry:
                t_entry: Dict[str, Any] = {
                    "time": now_iso,
                    "type": action,
                    "text": timeline_entry
                }
                if action != "rejected" and user_id:
                    t_entry["user_id"] = user_id
                    t_entry["user_name"] = user_name
                timeline.append(t_entry)
                record["timeline"] = timeline

            for msg in record.get("messages", []):
                if target_message_ts and msg.get("message_ts") == target_message_ts:
                    msg["action"] = action
                    if action != "rejected":
                        msg["user_id"] = user_id
                        msg["user_name"] = user_name
                    msg["action_at"] = action_at

            self._cache[occurrence_id] = record
            self._persist_record(record)
            return copy.deepcopy(record)

    def update_assignment(
        self,
        occurrence_id: str,
        assignee_id: str,
        assignee_name: str,
        referred_by_id: str,
        referred_by_name: str,
        action_at: str
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            if not record:
                return None

            record["assignee_id"] = assignee_id
            record["assignee_name"] = assignee_name
            record["referred_by_id"] = referred_by_id
            record["referred_by_name"] = referred_by_name
            record["assigned_at"] = action_at

            now_iso = datetime.now(timezone.utc).isoformat()
            record["updated_at"] = now_iso

            timeline = record.get("timeline", [])
            timeline.append({
                "time": now_iso,
                "type": "assigned",
                "user_id": referred_by_id,
                "user_name": referred_by_name,
                "assignee_id": assignee_id,
                "text": f"👤 Assigned to <@{assignee_id}> by <@{referred_by_id}>"
            })
            record["timeline"] = timeline

            self._cache[occurrence_id] = record
            self._persist_record(record)
            return copy.deepcopy(record)

    def add_timeline_note(
        self,
        occurrence_id: str,
        user_id: str,
        user_name: str,
        note: str
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            if not record:
                return None

            now_iso = datetime.now(timezone.utc).isoformat()
            timeline = record.get("timeline", [])
            timeline.append({
                "time": now_iso,
                "type": "note",
                "user_id": user_id,
                "user_name": user_name,
                "text": note
            })
            record["timeline"] = timeline

            notes = record.get("notes", [])
            notes.append({
                "time": now_iso,
                "user_id": user_id,
                "user_name": user_name,
                "text": note
            })
            record["notes"] = notes
            record["updated_at"] = now_iso

            self._cache[occurrence_id] = record
            self._persist_record(record)
            return copy.deepcopy(record)

    def try_claim_resolution(
        self,
        occurrence_id: str,
        resolution_time_str: str,
        alert_data: Optional[Dict[str, Any]] = None,
        resolved_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            record = self._cache.get(occurrence_id)
            now = datetime.now(timezone.utc).isoformat()

            if not record:
                record = {
                    "occurrence_id": occurrence_id,
                    "fingerprint": occurrence_id.split("_")[0],
                    "action": "not_acknowledged",
                    "messages": [],
                    "alert_data": JsonStateStore._trim_alert(alert_data or {}),
                    "resolved_at": resolution_time_str,
                    "resolved_by": resolved_by or "System Auto-detect",
                    "timeline": [
                        {
                            "time": now,
                            "type": "resolved",
                            "text": f"🟢 Resolved at {resolution_time_str}"
                        }
                    ],
                    "notes": [],
                    "created_at": now,
                    "updated_at": now
                }
                self._cache[occurrence_id] = record
                self._persist_record(record)
                return copy.deepcopy(record)

            if record.get("resolved_at"):
                return None

            record["resolved_at"] = resolution_time_str
            record["resolved_by"] = resolved_by or "System Auto-detect"
            record["updated_at"] = now

            timeline = record.get("timeline", [])
            timeline.append({
                "time": now,
                "type": "resolved",
                "text": f"🟢 Resolved ({record['resolved_by']})"
            })
            record["timeline"] = timeline

            self._cache[occurrence_id] = record
            self._persist_record(record)
            return copy.deepcopy(record)

    def has_unresolved_active_alerts(self) -> bool:
        with self.lock:
            return any(not v.get("resolved_at") for v in self._cache.values())

    def get_unresolved_active_alerts(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [copy.deepcopy(v) for v in self._cache.values() if not v.get("resolved_at")]

    def get_all_records(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [copy.deepcopy(v) for v in self._cache.values()]

    def prune_old_records(self) -> None:
        with self.lock:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
            new_data = {
                k: v for k, v in self._cache.items()
                if not (v.get("resolved_at") and v.get("updated_at", "") < cutoff)
            }
            if len(new_data) != len(self._cache):
                count = len(self._cache) - len(new_data)
                self._cache = new_data
                try:
                    conn = self._get_connection()
                    with conn.cursor() as cur:
                        cur.execute(
                            "DELETE FROM acknowledgements WHERE resolved_at IS NOT NULL AND resolved_at != '' AND updated_at < %s;",
                            (cutoff,)
                        )
                    logger.info("Pruned %d expired occurrences from MariaDB state store.", count)
                except Exception as e:
                    logger.error("Error pruning old records from MariaDB: %s", e)


def _init_state_store(cfg: AppConfig):
    if cfg.storage_backend == "json":
        logger.warning("STORAGE_BACKEND=json selected; incident data will be stored in JSON.")
        return JsonStateStore(cfg.ack_state_file, retention_days=cfg.retention_days)

    if cfg.storage_backend != "mariadb":
        raise ValueError(
            f"Unsupported STORAGE_BACKEND={cfg.storage_backend!r}; use 'mariadb' or 'json'."
        )
    if not HAVE_PYMYSQL:
        raise RuntimeError(
            "MariaDB storage requires PyMySQL. Install requirements.txt or set STORAGE_BACKEND=json."
        )

    db_store = MariaDBStateStore(cfg)
    logger.info(
        "Direct MariaDB State Store initialized (Host: %s, DB: %s).",
        cfg.db_host, cfg.db_name
    )
    return db_store


store = _init_state_store(config)


# ============================================================
# ALERTMANAGER CLIENT
# ============================================================

class AlertmanagerClient:

    def __init__(
        self,
        base_url: str,
        timeout: int = 10
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

        retries = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )

        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=10,
            pool_maxsize=20
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def create_silence(
        self,
        labels: Dict[str, Any],
        author: str,
        ends_at: datetime,
        starts_at: Optional[datetime] = None,
        comment: Optional[str] = None
    ) -> str:
        volatile_keys = {
            "pod", "container", "container_id", "replica",
            "prometheus_replica", "endpoint", "instance_id"
        }

        matchers = [
            {
                "name": k,
                "value": str(v),
                "isRegex": False
            }
            for k, v in labels.items()
            if (
                v is not None
                and not k.startswith("__")
                and k.lower() not in volatile_keys
            )
        ]

        if not starts_at:
            starts_at = datetime.now(timezone.utc)

        comment_text = (
            comment or f"Silenced via Incident Bot by {author}"
        )

        payload = {
            "matchers": matchers,
            "startsAt": starts_at.isoformat(),
            "endsAt": ends_at.isoformat(),
            "createdBy": author,
            "comment": comment_text
        }

        resp = self.session.post(
            f"{self.base_url}/api/v2/silences",
            json=payload,
            timeout=self.timeout
        )
        resp.raise_for_status()

        return resp.json().get("silenceID", "")

    def delete_silence(
        self,
        silence_id: str
    ) -> bool:
        if not silence_id:
            return True

        try:
            resp = self.session.delete(
                f"{self.base_url}/api/v2/silence/{silence_id}",
                timeout=self.timeout
            )
            return resp.status_code in (200, 202, 204, 404)
        except Exception as e:
            logger.warning("Failed to delete silence %s: %s", silence_id, e)
            return False

    def get_alert_by_fingerprint(
        self,
        fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/v2/alerts",
                params={"active": "true"},
                timeout=self.timeout
            )
            resp.raise_for_status()

            for alert in resp.json():
                if alert.get("fingerprint") == fingerprint:
                    return alert
            return None
        except Exception as e:
            logger.warning("Error fetching alert %s: %s", fingerprint, e)
            return None

    def get_active_fingerprints(self) -> set[str]:
        resp = self.session.get(
            f"{self.base_url}/api/v2/alerts",
            params={"active": "true"},
            timeout=self.timeout
        )
        resp.raise_for_status()
        return {
            a.get("fingerprint")
            for a in resp.json()
            if a.get("fingerprint")
        }


am_client = AlertmanagerClient(
    config.alertmanager_url,
    timeout=config.http_timeout
>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
)


# ============================================================
<<<<<<< HEAD
# ALERTMANAGER CLIENT
# ============================================================

class AlertmanagerClient:

    def __init__(
        self,
        base_url: str,
        timeout: int = 10
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

        retries = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )

        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=10,
            pool_maxsize=20
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def create_silence(
        self,
        labels: Dict[str, Any],
        author: str,
        ends_at: datetime,
        starts_at: Optional[datetime] = None,
        comment: Optional[str] = None
    ) -> str:
        volatile_keys = {
            "pod", "container", "container_id", "replica",
            "prometheus_replica", "endpoint", "instance_id"
        }

        matchers = [
            {
                "name": k,
                "value": str(v),
                "isRegex": False
            }
            for k, v in labels.items()
            if (
                v is not None
                and not k.startswith("__")
                and k.lower() not in volatile_keys
            )
        ]

        if not starts_at:
            starts_at = datetime.now(timezone.utc)

        comment_text = (
            comment or f"Silenced via Incident Bot by {author}"
        )

        payload = {
            "matchers": matchers,
            "startsAt": starts_at.isoformat(),
            "endsAt": ends_at.isoformat(),
            "createdBy": author,
            "comment": comment_text
        }

        resp = self.session.post(
            f"{self.base_url}/api/v2/silences",
            json=payload,
            timeout=self.timeout
        )
        resp.raise_for_status()

        return resp.json().get("silenceID", "")

    def delete_silence(
        self,
        silence_id: str
    ) -> bool:
        if not silence_id:
            return True

        try:
            resp = self.session.delete(
                f"{self.base_url}/api/v2/silence/{silence_id}",
                timeout=self.timeout
            )
            return resp.status_code in (200, 202, 204, 404)
        except Exception as e:
            logger.warning("Failed to delete silence %s: %s", silence_id, e)
            return False

    def get_alert_by_fingerprint(
        self,
        fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/v2/alerts",
                params={"active": "true"},
                timeout=self.timeout
            )
            resp.raise_for_status()

            for alert in resp.json():
                if alert.get("fingerprint") == fingerprint:
                    return alert
            return None
        except Exception as e:
            logger.warning("Error fetching alert %s: %s", fingerprint, e)
            return None

    def get_active_fingerprints(self) -> set[str]:
        resp = self.session.get(
            f"{self.base_url}/api/v2/alerts",
            params={"active": "true"},
            timeout=self.timeout
        )
        resp.raise_for_status()
        return {
            a.get("fingerprint")
            for a in resp.json()
            if a.get("fingerprint")
        }


am_client = AlertmanagerClient(
    config.alertmanager_url,
    timeout=config.http_timeout
)


# ============================================================
# SLACK BLOCK KIT: FIRING / INCIDENT CARD
# ============================================================

def build_firing_blocks(
    alert: Dict[str, Any],
    acknowledgement: Optional[Dict[str, Any]] = None,
    occurrence_id: Optional[str] = None,
    is_resolved: bool = False,
    hide_buttons: bool = False
) -> Tuple[str, List[Dict[str, Any]]]:

    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Unknown Alert")
    severity = labels.get("severity", "unknown").upper()
    instance = labels.get("instance", "Unknown")

    summary = annotations.get("summary", "")
    description = annotations.get("description", "")
    runbook_url = annotations.get("runbook_url", "")
    dashboard_url = annotations.get("dashboard", "") or config.grafana_url
    generator_url = alert.get("generatorURL", "") or config.prometheus_url
    starts_at = alert.get("startsAt", "")

    action = (
        acknowledgement.get("action")
        if acknowledgement
        else "not_acknowledged"
    )
    assignee_id = (
        acknowledgement.get("assignee_id")
        if acknowledgement
        else None
    )
    referred_by_id = (
        acknowledgement.get("referred_by_id")
        if acknowledgement
        else None
    )

    sev_emoji = (
        "🔴" if severity in ("CRITICAL", "PAGE", "FATAL")
        else "🟡" if severity in ("WARNING", "WARN")
        else "ℹ️"
    )

    if is_resolved:
        header_emoji = "✅"
        title = "INCIDENT RESOLVED"
        status_line = "🟢 `RESOLVED`"
    elif action == "accepted":
        header_emoji = "🛠️"
        title = "INCIDENT ACKNOWLEDGED / IN PROGRESS"
        status_line = "🟡 `IN PROGRESS`"
    elif action == "paused":
        header_emoji = "⏸️"
        title = "INCIDENT SNOOZED"
        status_line = "🔵 `SNOOZED / SILENCED`"
    elif action == "rejected":
        header_emoji = "⚠️"
        title = "INCIDENT REJECTED"
        status_line = "🟠 `REJECTED (Escalating)`"
    else:
        header_emoji = sev_emoji
        title = "INCIDENT FIRING"
        status_line = f"{sev_emoji} `FIRING`"

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{header_emoji} [{severity}] {alertname}",
                "emoji": True
            }
        }
    ]

    # ========================================================
    # INCIDENT CONTEXT
    # ========================================================
    context_elements = []

    # ASSIGNEE
    if assignee_id:
        if referred_by_id and referred_by_id != assignee_id:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"👤 *Assigned to:* <@{assignee_id}> (Referred by <@{referred_by_id}>)"
            })
        else:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"👤 *Assigned to:* <@{assignee_id}>"
            })
    else:
        context_elements.append({
            "type": "mrkdwn",
            "text": "👤 *Assignee:* _Unassigned_"
        })

    # ACTION STATUS (Strict: Never show who rejected on card)
    if acknowledgement and action in ("accepted", "paused"):
        uid = acknowledgement.get("user_id")
        uname = acknowledgement.get("user_name", "Unknown")
        mention = f"<@{uid}>" if uid else f"@{uname}"
        action_time = acknowledgement.get("action_at", "")
        action_name = "Acknowledged" if action == "accepted" else "Snoozed"

        context_elements.append({
            "type": "mrkdwn",
            "text": f"⚡ *{action_name} by:* {mention} ({uname}) • {action_time}"
        })
    elif is_resolved and action == "not_acknowledged":
        context_elements.append({
            "type": "mrkdwn",
            "text": "🟢 *Auto-resolved (No manual intervention required)*"
        })

    if context_elements:
        blocks.append({
            "type": "context",
            "elements": context_elements
        })

    # ========================================================
    # INCIDENT DURATION
    # ========================================================
    if is_resolved:
        res_time = (
            parse_alert_time(alert.get("endsAt"))
            or parse_alert_time(
                acknowledgement.get("resolved_at") if acknowledgement else None
            )
            or datetime.now(timezone.utc)
        )
        dur_seconds = get_alert_duration(alert, res_time)
        dur_label = "Total Downtime" if is_downtime_alert(alert) else "Total Active Duration"
        dur_text = format_duration(dur_seconds) if dur_seconds is not None else "0s"
    else:
        dur_seconds = get_alert_duration(alert)
        dur_label = "Downtime" if is_downtime_alert(alert) else "Active Duration"
        dur_text = format_duration(dur_seconds) if dur_seconds is not None else "0s"

    body_text = (
        f"*Status:* {status_line}\n"
        f"*Severity:* `{severity}` | *Instance:* `{instance}`\n"
        f"*{dur_label}:* `{dur_text}`\n"
        f"*Started:* {format_display_time(starts_at)}"
    )

    if is_resolved and alert.get("endsAt"):
        body_text += f"\n*Resolved:* {format_display_time(alert.get('endsAt'))}"

    if summary:
        body_text += f"\n\n*Summary:*\n{summary}"

    if description:
        body_text += f"\n\n*Description:*\n{description}"

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": body_text
        }
    })

    # ========================================================
    # SILENCE / SNOOZE / REJECTION NOTICE
    # ========================================================
    if not is_resolved and acknowledgement and action == "paused":
        silence_id_val = acknowledgement.get("silence_id", "N/A")
        silence_ends_str = acknowledgement.get("silence_ends_at", "N/A")
        silence_label_str = acknowledgement.get("silence_label", "4 Hours")

        blocks.extend([
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"⏸️ *Incident Snoozed for {silence_label_str}*\n"
                        f"• *Snoozed Until:* `{silence_ends_str}`\n"
                        f"• *Alertmanager Silence ID:* `{silence_id_val}`"
                    )
                }
            }
        ])
    elif not is_resolved and acknowledgement and action == "accepted":
        silence_id_val = acknowledgement.get("silence_id")
        if silence_id_val:
            blocks.extend([
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔇 *Silenced in Alertmanager*\nSilence ID: `{silence_id_val}`"
                    }
                }
            ])
    elif not is_resolved and acknowledgement and action == "rejected":
        # Strict requirement: NO mention of who rejected it!
        blocks.extend([
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "⚠️ *Incident was rejected / escalated.*\n"
                        "Alertmanager will continue regular notification cycle."
                    )
                }
            }
        ])

    # ========================================================
    # LINKS
    # ========================================================
    link_buttons = []
    if runbook_url:
        link_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "📖 Runbook", "emoji": True},
            "url": runbook_url
        })
    if dashboard_url:
        link_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "📊 Grafana", "emoji": True},
            "url": dashboard_url
        })
    if generator_url:
        link_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "🔥 Prometheus", "emoji": True},
            "url": generator_url
        })

    if link_buttons:
        blocks.append({
            "type": "actions",
            "elements": link_buttons
        })

    # ========================================================
    # INTERACTIVE CONTROLS
    # Rules:
    # - REJECTED: ALL action buttons removed (hide_buttons / action)
    # - ACKNOWLEDGED (accepted): ALL action buttons removed
    # - PAUSED: Assign dropdown removed; Resume / Note / Reject / Pause remain
    # - Mark Resolved button permanently removed (auto-resolve only)
    # ========================================================
    # Link buttons (Runbook / Grafana / Prometheus) stay above this block.
    show_actions = (
        not is_resolved
        and not hide_buttons
        and action not in ("rejected", "accepted")
    )

    if show_actions:
        occ_id = (
            occurrence_id
            or build_occurrence_id(alert.get("fingerprint", ""), starts_at)
        )

        blocks.append({"type": "divider"})

        action_elements = []

        # Acknowledge only while still open (not accepted — already gated)
        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Acknowledge", "emoji": True},
            "style": "primary",
            "action_id": "accept_alert",
            "value": occ_id
        })

        if action == "paused":
            action_elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "▶️ Resume / Unpause", "emoji": True},
                "action_id": "resume_alert",
                "value": occ_id
            })

        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "💬 Add Note", "emoji": True},
            "action_id": "open_note_modal",
            "value": occ_id
        })

        # Mark Resolved intentionally removed — resolution is automatic
        # from Alertmanager with attribution (ack user / assignee / system).

        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "❌ Reject / Escalate", "emoji": True},
            "style": "danger",
            "action_id": "reject_alert",
            "value": occ_id
        })

        blocks.append({
            "type": "actions",
            "elements": action_elements
        })

        # Dropdown row: Pause always; Assign ONLY when not paused
        select_elements: List[Dict[str, Any]] = [
            {
                "type": "static_select",
                "action_id": "pause_alert_dropdown",
                "placeholder": {
                    "type": "plain_text",
                    "text": "⏸️ Pause / Snooze for...",
                    "emoji": True
                },
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 30 Minutes", "emoji": True},
                        "value": f"pause:30m:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 1 Hour", "emoji": True},
                        "value": f"pause:1h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 4 Hours", "emoji": True},
                        "value": f"pause:4h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 8 Hours (Workday)", "emoji": True},
                        "value": f"pause:8h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 24 Hours (1 Day)", "emoji": True},
                        "value": f"pause:24h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "🌅 Pause until Tomorrow 9 AM", "emoji": True},
                        "value": f"pause:tomorrow_9am:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "📅 Pause until Next Monday 9 AM", "emoji": True},
                        "value": f"pause:next_monday_9am:{occ_id}"
                    }
                ]
            }
        ]

        # Assign / Refer: hidden while paused (user requirement)
        if action != "paused":
            select_elements.append({
                "type": "users_select",
                "action_id": "refer_user_action",
                "placeholder": {
                    "type": "plain_text",
                    "text": "👤 Assign / Refer to teammate...",
                    "emoji": True
                }
            })

        blocks.append({
            "type": "actions",
            "block_id": f"incident_select_block_{occ_id}",
            "elements": select_elements
        })

    return f"{header_emoji} {alertname} - {title}", blocks


# ============================================================
# SEPARATE RESOLVED CARD
# ============================================================

def build_resolved_blocks(
    alert: Dict[str, Any],
    acknowledgement: Optional[Dict[str, Any]] = None,
    resolution_time: Optional[datetime] = None
) -> Tuple[str, List[Dict[str, Any]]]:

    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Unknown Alert")
    severity = labels.get("severity", "unknown").upper()
    instance = labels.get("instance", "Unknown")

    summary = annotations.get("summary", "")
    description = annotations.get("description", "")
    starts_at = alert.get("startsAt", "")

    res_time = (
        resolution_time
        or parse_alert_time(alert.get("endsAt"))
        or datetime.now(timezone.utc)
    )

    dur_seconds = get_alert_duration(alert, res_time)
    dur_label = "Total Downtime" if is_downtime_alert(alert) else "Total Active Duration"
    dur_text = format_duration(dur_seconds) if dur_seconds is not None else "Unknown"

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"✅ INCIDENT RESOLVED: {alertname}",
                "emoji": True
            }
        }
    ]

    context_items = []

    if acknowledgement:
        assignee_id = acknowledgement.get("assignee_id")
        if assignee_id:
            context_items.append({
                "type": "mrkdwn",
                "text": f"👤 *Lead Assignee:* <@{assignee_id}>"
            })

        act = acknowledgement.get("action")
        # Strict: Anonymity for rejected user, explicit Previous Action display
        if act == "rejected":
            context_items.append({
                "type": "mrkdwn",
                "text": "🟠 *Previous Action:* Rejected / Escalated"
            })
        elif act in ("accepted", "paused"):
            uid = acknowledgement.get("user_id")
            uname = acknowledgement.get("user_name", "Unknown")
            mention = f"<@{uid}>" if uid else f"@{uname}"
            action_name = "Acknowledged" if act == "accepted" else "Paused"
            act_time = acknowledgement.get("action_at", "")

            context_items.append({
                "type": "mrkdwn",
                "text": f"⚡ *Previous Action:* {action_name} by {mention} ({uname}) at {act_time}"
            })
        else:
            context_items.append({
                "type": "mrkdwn",
                "text": "⚪ *Previous Action:* None (Auto-resolved)"
            })

        resolved_by = acknowledgement.get("resolved_by")
        if resolved_by:
            context_items.append({
                "type": "mrkdwn",
                "text": f"🟢 *Resolved by:* {resolved_by}"
            })
    else:
        context_items.append({
            "type": "mrkdwn",
            "text": "⚪ *Previous Action:* None (Auto-resolved)"
        })
        context_items.append({
            "type": "mrkdwn",
            "text": "🟢 *Resolved by:* System Auto-detect"
        })

    if context_items:
        blocks.append({
            "type": "context",
            "elements": context_items
        })

    detail_lines = [
        "*Status:* 🟢 `RESOLVED`",
        f"*Severity:* `{severity}` | *Instance:* `{instance}`",
        f"*{dur_label}:* `{dur_text}`",
        f"*Started:* {format_display_time(starts_at)}",
        f"*Resolved:* {format_display_time(res_time)}"
    ]

    if summary:
        detail_lines.append(f"\n*Summary:*\n{summary}")

    if description:
        detail_lines.append(f"\n*Description:*\n{description}")

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "\n".join(detail_lines)
        }
    })

    if acknowledgement and acknowledgement.get("silence_id"):
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🔓 *Associated Alertmanager silence was automatically deleted.*"
                }
            ]
        })

    return f"✅ RESOLVED: {alertname} ({instance})", blocks


# ============================================================
# SLACK & FLASK INIT
# ============================================================

bot_token = config.slack_bot_token or "xoxb-dummy-token-for-initialization"
signing_secret = config.slack_signing_secret or "dummy-signing-secret"

slack = WebClient(
    token=bot_token
)

bolt_app = App(
    token=bot_token,
    signing_secret=signing_secret,
    token_verification_enabled=bool(config.slack_bot_token)
)

flask_app = Flask(__name__)


# ============================================================
# SLACK USER HELPER WITH IN-MEMORY CACHING
# ============================================================

_user_cache: Dict[str, Tuple[str, float]] = {}
_user_cache_lock = threading.Lock()
USER_CACHE_TTL = 3600  # 1 hour cache


def get_slack_user_name(
    client: WebClient,
    user_id: str,
    fallback_hint: Optional[str] = None
) -> str:
    """
    Ultra-fast user name lookup with in-memory caching to eliminate Slack API roundtrips.
    """
    if not user_id:
        return "Unknown"

    now = time.time()
    with _user_cache_lock:
        cached = _user_cache.get(user_id)
        if cached and now < cached[1]:
            return cached[0]

    if fallback_hint:
        with _user_cache_lock:
            _user_cache[user_id] = (fallback_hint, now + USER_CACHE_TTL)
        return fallback_hint

    try:
        response = client.users_info(user=user_id)
        user = response.get("user", {})
        name = (
            user.get("real_name")
            or user.get("profile", {}).get("display_name")
            or user.get("name")
            or user_id
        )
        with _user_cache_lock:
            _user_cache[user_id] = (name, now + USER_CACHE_TTL)
        return name
    except Exception as e:
        logger.warning("Could not fetch Slack user %s: %s", user_id, e)
        return user_id


# ============================================================
# INCIDENT THREAD AUDIT LOGGER
# ============================================================

def post_incident_thread_update(
    client: WebClient,
    channel_id: str,
    message_ts: str,
    text: str
) -> None:
    if not channel_id or not message_ts:
        return

    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=message_ts,
            text=text
        )
    except Exception as e:
        logger.warning("Failed to post thread update to %s/%s: %s", channel_id, message_ts, e)


# ============================================================
# RESOLUTION HANDLER
# ============================================================

def handle_alert_resolution(
    alert: Dict[str, Any],
    occurrence_id: Optional[str] = None,
    resolution_time: Optional[datetime] = None,
    resolved_by: Optional[str] = None,
    slack_client: Optional[WebClient] = None
) -> bool:
    client = slack_client or slack

    res_time = (
        resolution_time
        or parse_alert_time(alert.get("endsAt"))
        or datetime.now(timezone.utc)
    )
    res_time_str = format_display_time(res_time)

    if not occurrence_id:
        fp = alert.get("fingerprint", "")
        starts_at = alert.get("startsAt", "")
        occurrence_id = build_occurrence_id(fp, starts_at)

    # Attribution: explicit override, else ack user, else assignee, else system
    prior = store.get(occurrence_id)
    resolved_by_final = resolve_by_from_record(prior, explicit=resolved_by)

    claimed_record = store.try_claim_resolution(
        occurrence_id,
        res_time_str,
        alert,
        resolved_by=resolved_by_final
    )

    if not claimed_record:
        logger.debug("Resolution for %s already claimed. Skipping.", occurrence_id)
        return False

    logger.info("Claimed resolution for occurrence %s. Processing Slack updates.", occurrence_id)

    # Delete any active silence in Alertmanager
    if claimed_record.get("silence_id"):
        silence_deleted = am_client.delete_silence(claimed_record["silence_id"])
        if silence_deleted:
            logger.info(
                "Deleted Alertmanager silence %s for occurrence %s",
                claimed_record.get("silence_id"),
                occurrence_id
            )

    all_messages = claimed_record.get("messages", [])
    if (
        not all_messages
        and claimed_record.get("channel_id")
        and claimed_record.get("message_ts")
    ):
        all_messages = [
            {
                "channel_id": claimed_record["channel_id"],
                "message_ts": claimed_record["message_ts"]
            }
        ]

    # Update original Slack firing messages: mark resolved and remove all action buttons
    for msg in all_messages:
        ch = msg.get("channel_id")
        ts = msg.get("message_ts")
        if not ch or not ts:
            continue

        try:
            old_alert = copy.deepcopy(
                claimed_record.get("alert_data", alert)
            )
            old_alert["endsAt"] = res_time.isoformat()

            _, clean_blocks = build_firing_blocks(
                old_alert,
                claimed_record,
                occurrence_id,
                is_resolved=False,
                hide_buttons=True
            )

            alert_title = claimed_record.get("alert", "Alert")
            update_text = f"🚨 {alert_title} [Resolved]"

            client.chat_update(
                channel=ch,
                ts=ts,
                text=update_text,
                blocks=clean_blocks
            )

            post_incident_thread_update(
                client,
                ch,
                ts,
                f"🟢 *Incident Resolved* at {res_time_str} by {resolved_by_final}."
            )
        except SlackApiError as e:
            logger.warning("Could not update message %s: %s", ts, e.response.get("error"))
        except Exception as e:
            logger.warning("Could not update message %s: %s", ts, e)

    # Post separate RESOLVED card to channel
    res_text, res_blocks = build_resolved_blocks(
        alert,
        claimed_record,
        res_time
    )

    try:
        client.chat_postMessage(
            channel=config.slack_channel,
            text=res_text,
            blocks=res_blocks
        )
        logger.info("Separate resolved message posted for occurrence %s", occurrence_id)
    except SlackApiError as e:
        logger.error("Failed to post separate resolved message: %s", e.response.get("error"))
    except Exception as e:
        logger.error("Failed to post separate resolved message: %s", e)

    return True


# ============================================================
=======
# SLACK BLOCK KIT: FIRING / INCIDENT CARD
# ============================================================

def build_firing_blocks(
    alert: Dict[str, Any],
    acknowledgement: Optional[Dict[str, Any]] = None,
    occurrence_id: Optional[str] = None,
    is_resolved: bool = False,
    hide_buttons: bool = False
) -> Tuple[str, List[Dict[str, Any]]]:

    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Unknown Alert")
    severity = labels.get("severity", "unknown").upper()
    instance = labels.get("instance", "Unknown")

    summary = annotations.get("summary", "")
    description = annotations.get("description", "")
    runbook_url = annotations.get("runbook_url", "")
    dashboard_url = annotations.get("dashboard", "") or config.grafana_url
    generator_url = alert.get("generatorURL", "") or config.prometheus_url
    starts_at = alert.get("startsAt", "")

    action = (
        acknowledgement.get("action")
        if acknowledgement
        else "not_acknowledged"
    )
    assignee_id = (
        acknowledgement.get("assignee_id")
        if acknowledgement
        else None
    )
    referred_by_id = (
        acknowledgement.get("referred_by_id")
        if acknowledgement
        else None
    )

    sev_emoji = (
        "🔴" if severity in ("CRITICAL", "PAGE", "FATAL")
        else "🟡" if severity in ("WARNING", "WARN")
        else "ℹ️"
    )

    if is_resolved:
        header_emoji = "✅"
        title = "INCIDENT RESOLVED"
        status_line = "🟢 `RESOLVED`"
    elif action == "accepted":
        header_emoji = "🛠️"
        title = "INCIDENT ACKNOWLEDGED / IN PROGRESS"
        status_line = "🟡 `IN PROGRESS`"
    elif action == "paused":
        header_emoji = "⏸️"
        title = "INCIDENT SNOOZED"
        status_line = "🔵 `SNOOZED / SILENCED`"
    elif action == "rejected":
        header_emoji = "⚠️"
        title = "INCIDENT REJECTED"
        status_line = "🟠 `REJECTED (Escalating)`"
    else:
        header_emoji = sev_emoji
        title = "INCIDENT FIRING"
        status_line = f"{sev_emoji} `FIRING`"

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{header_emoji} [{severity}] {alertname}",
                "emoji": True
            }
        }
    ]

    # ========================================================
    # INCIDENT CONTEXT
    # ========================================================
    context_elements = []

    # ASSIGNEE
    if assignee_id:
        if referred_by_id and referred_by_id != assignee_id:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"👤 *Assigned to:* <@{assignee_id}> (Referred by <@{referred_by_id}>)"
            })
        else:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"👤 *Assigned to:* <@{assignee_id}>"
            })
    else:
        context_elements.append({
            "type": "mrkdwn",
            "text": "👤 *Assignee:* _Unassigned_"
        })

    # ACTION STATUS (Strict: Never show who rejected on card)
    if acknowledgement and action in ("accepted", "paused"):
        uid = acknowledgement.get("user_id")
        uname = acknowledgement.get("user_name", "Unknown")
        mention = f"<@{uid}>" if uid else f"@{uname}"
        action_time = acknowledgement.get("action_at", "")
        action_name = "Acknowledged" if action == "accepted" else "Snoozed"

        context_elements.append({
            "type": "mrkdwn",
            "text": f"⚡ *{action_name} by:* {mention} ({uname}) • {action_time}"
        })
    elif is_resolved and action == "not_acknowledged":
        context_elements.append({
            "type": "mrkdwn",
            "text": "🟢 *Auto-resolved (No manual intervention required)*"
        })

    if context_elements:
        blocks.append({
            "type": "context",
            "elements": context_elements
        })

    # ========================================================
    # INCIDENT DURATION
    # ========================================================
    if is_resolved:
        res_time = (
            parse_alert_time(alert.get("endsAt"))
            or parse_alert_time(
                acknowledgement.get("resolved_at") if acknowledgement else None
            )
            or datetime.now(timezone.utc)
        )
        dur_seconds = get_alert_duration(alert, res_time)
        dur_label = "Total Downtime" if is_downtime_alert(alert) else "Total Active Duration"
        dur_text = format_duration(dur_seconds) if dur_seconds is not None else "0s"
    else:
        dur_seconds = get_alert_duration(alert)
        dur_label = "Downtime" if is_downtime_alert(alert) else "Active Duration"
        dur_text = format_duration(dur_seconds) if dur_seconds is not None else "0s"

    body_text = (
        f"*Status:* {status_line}\n"
        f"*Severity:* `{severity}` | *Instance:* `{instance}`\n"
        f"*{dur_label}:* `{dur_text}`\n"
        f"*Started:* {format_display_time(starts_at)}"
    )

    if is_resolved and alert.get("endsAt"):
        body_text += f"\n*Resolved:* {format_display_time(alert.get('endsAt'))}"

    if summary:
        body_text += f"\n\n*Summary:*\n{summary}"

    if description:
        body_text += f"\n\n*Description:*\n{description}"

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": body_text
        }
    })

    # ========================================================
    # SILENCE / SNOOZE / REJECTION NOTICE
    # ========================================================
    if not is_resolved and acknowledgement and action == "paused":
        silence_id_val = acknowledgement.get("silence_id", "N/A")
        silence_ends_str = acknowledgement.get("silence_ends_at", "N/A")
        silence_label_str = acknowledgement.get("silence_label", "4 Hours")

        blocks.extend([
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"⏸️ *Incident Snoozed for {silence_label_str}*\n"
                        f"• *Snoozed Until:* `{silence_ends_str}`\n"
                        f"• *Alertmanager Silence ID:* `{silence_id_val}`"
                    )
                }
            }
        ])
    elif not is_resolved and acknowledgement and action == "accepted":
        silence_id_val = acknowledgement.get("silence_id")
        if silence_id_val:
            blocks.extend([
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔇 *Silenced in Alertmanager*\nSilence ID: `{silence_id_val}`"
                    }
                }
            ])
    elif not is_resolved and acknowledgement and action == "rejected":
        # Strict requirement: NO mention of who rejected it!
        blocks.extend([
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "⚠️ *Incident was rejected / escalated.*\n"
                        "Alertmanager will continue regular notification cycle."
                    )
                }
            }
        ])

    # ========================================================
    # LINKS
    # ========================================================
    link_buttons = []
    if runbook_url:
        link_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "📖 Runbook", "emoji": True},
            "url": runbook_url
        })
    if dashboard_url:
        link_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "📊 Grafana", "emoji": True},
            "url": dashboard_url
        })
    if generator_url:
        link_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "🔥 Prometheus", "emoji": True},
            "url": generator_url
        })

    if link_buttons:
        blocks.append({
            "type": "actions",
            "elements": link_buttons
        })

    # ========================================================
    # INTERACTIVE CONTROLS
    # Rules:
    # - REJECTED: ALL action buttons removed (hide_buttons / action)
    # - ACKNOWLEDGED (accepted): ALL action buttons removed
    # - PAUSED: Assign dropdown removed; Resume / Note / Reject / Pause remain
    # - Mark Resolved button permanently removed (auto-resolve only)
    # ========================================================
    # Link buttons (Runbook / Grafana / Prometheus) stay above this block.
    show_actions = (
        not is_resolved
        and not hide_buttons
        and action not in ("rejected", "accepted")
    )

    if show_actions:
        occ_id = (
            occurrence_id
            or build_occurrence_id(alert.get("fingerprint", ""), starts_at)
        )

        blocks.append({"type": "divider"})

        action_elements = []

        # Acknowledge only while still open (not accepted — already gated)
        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Acknowledge", "emoji": True},
            "style": "primary",
            "action_id": "accept_alert",
            "value": occ_id
        })

        if action == "paused":
            action_elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "▶️ Resume / Unpause", "emoji": True},
                "action_id": "resume_alert",
                "value": occ_id
            })

        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "💬 Add Note", "emoji": True},
            "action_id": "open_note_modal",
            "value": occ_id
        })

        # Mark Resolved intentionally removed — resolution is automatic
        # from Alertmanager with attribution (ack user / assignee / system).

        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "❌ Reject / Escalate", "emoji": True},
            "style": "danger",
            "action_id": "reject_alert",
            "value": occ_id
        })

        blocks.append({
            "type": "actions",
            "elements": action_elements
        })

        # Dropdown row: Pause always; Assign ONLY when not paused
        select_elements: List[Dict[str, Any]] = [
            {
                "type": "static_select",
                "action_id": "pause_alert_dropdown",
                "placeholder": {
                    "type": "plain_text",
                    "text": "⏸️ Pause / Snooze for...",
                    "emoji": True
                },
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 30 Minutes", "emoji": True},
                        "value": f"pause:30m:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 1 Hour", "emoji": True},
                        "value": f"pause:1h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 4 Hours", "emoji": True},
                        "value": f"pause:4h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 8 Hours (Workday)", "emoji": True},
                        "value": f"pause:8h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "⏸️ Pause 24 Hours (1 Day)", "emoji": True},
                        "value": f"pause:24h:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "🌅 Pause until Tomorrow 9 AM", "emoji": True},
                        "value": f"pause:tomorrow_9am:{occ_id}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "📅 Pause until Next Monday 9 AM", "emoji": True},
                        "value": f"pause:next_monday_9am:{occ_id}"
                    }
                ]
            }
        ]

        # Assign / Refer: hidden while paused (user requirement)
        if action != "paused":
            select_elements.append({
                "type": "users_select",
                "action_id": "refer_user_action",
                "placeholder": {
                    "type": "plain_text",
                    "text": "👤 Assign / Refer to teammate...",
                    "emoji": True
                }
            })

        blocks.append({
            "type": "actions",
            "block_id": f"incident_select_block_{occ_id}",
            "elements": select_elements
        })

    return f"{header_emoji} {alertname} - {title}", blocks


# ============================================================
# SEPARATE RESOLVED CARD
# ============================================================

def build_resolved_blocks(
    alert: Dict[str, Any],
    acknowledgement: Optional[Dict[str, Any]] = None,
    resolution_time: Optional[datetime] = None
) -> Tuple[str, List[Dict[str, Any]]]:

    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get("alertname", "Unknown Alert")
    severity = labels.get("severity", "unknown").upper()
    instance = labels.get("instance", "Unknown")

    summary = annotations.get("summary", "")
    description = annotations.get("description", "")
    starts_at = alert.get("startsAt", "")

    res_time = (
        resolution_time
        or parse_alert_time(alert.get("endsAt"))
        or datetime.now(timezone.utc)
    )

    dur_seconds = get_alert_duration(alert, res_time)
    dur_label = "Total Downtime" if is_downtime_alert(alert) else "Total Active Duration"
    dur_text = format_duration(dur_seconds) if dur_seconds is not None else "Unknown"

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"✅ INCIDENT RESOLVED: {alertname}",
                "emoji": True
            }
        }
    ]

    context_items = []

    if acknowledgement:
        assignee_id = acknowledgement.get("assignee_id")
        if assignee_id:
            context_items.append({
                "type": "mrkdwn",
                "text": f"👤 *Lead Assignee:* <@{assignee_id}>"
            })

        act = acknowledgement.get("action")
        # Strict: Anonymity for rejected user, explicit Previous Action display
        if act == "rejected":
            context_items.append({
                "type": "mrkdwn",
                "text": "🟠 *Previous Action:* Rejected / Escalated"
            })
        elif act in ("accepted", "paused"):
            uid = acknowledgement.get("user_id")
            uname = acknowledgement.get("user_name", "Unknown")
            mention = f"<@{uid}>" if uid else f"@{uname}"
            action_name = "Acknowledged" if act == "accepted" else "Paused"
            act_time = acknowledgement.get("action_at", "")

            context_items.append({
                "type": "mrkdwn",
                "text": f"⚡ *Previous Action:* {action_name} by {mention} ({uname}) at {act_time}"
            })
        else:
            context_items.append({
                "type": "mrkdwn",
                "text": "⚪ *Previous Action:* None (Auto-resolved)"
            })

        resolved_by = acknowledgement.get("resolved_by")
        if resolved_by:
            context_items.append({
                "type": "mrkdwn",
                "text": f"🟢 *Resolved by:* {resolved_by}"
            })
    else:
        context_items.append({
            "type": "mrkdwn",
            "text": "⚪ *Previous Action:* None (Auto-resolved)"
        })
        context_items.append({
            "type": "mrkdwn",
            "text": "🟢 *Resolved by:* System Auto-detect"
        })

    if context_items:
        blocks.append({
            "type": "context",
            "elements": context_items
        })

    detail_lines = [
        "*Status:* 🟢 `RESOLVED`",
        f"*Severity:* `{severity}` | *Instance:* `{instance}`",
        f"*{dur_label}:* `{dur_text}`",
        f"*Started:* {format_display_time(starts_at)}",
        f"*Resolved:* {format_display_time(res_time)}"
    ]

    if summary:
        detail_lines.append(f"\n*Summary:*\n{summary}")

    if description:
        detail_lines.append(f"\n*Description:*\n{description}")

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "\n".join(detail_lines)
        }
    })

    if acknowledgement and acknowledgement.get("silence_id"):
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🔓 *Associated Alertmanager silence was automatically deleted.*"
                }
            ]
        })

    return f"✅ RESOLVED: {alertname} ({instance})", blocks


# ============================================================
# SLACK & FLASK INIT
# ============================================================

bot_token = config.slack_bot_token or "xoxb-dummy-token-for-initialization"
signing_secret = config.slack_signing_secret or "dummy-signing-secret"

slack = WebClient(
    token=bot_token
)

bolt_app = App(
    token=bot_token,
    signing_secret=signing_secret,
    token_verification_enabled=bool(config.slack_bot_token)
)

flask_app = Flask(__name__)
flask_app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
flask_app.permanent_session_lifetime = timedelta(hours=8)
flask_app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Set SESSION_COOKIE_SECURE=True when running behind HTTPS
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
)


# ============================================================
# DB-BACKED DASHBOARD AUTH MANAGER
# ============================================================

# In-memory brute-force lockout tracker: {ip: {"count": int, "locked_until": float|None}}
_brute_force_lock = threading.Lock()
_login_attempts: Dict[str, Any] = {}
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 minutes


def _bcrypt_hash(plaintext: str) -> str:
    if not HAVE_BCRYPT:
        # Fallback: SHA-256 (not recommended for production — install bcrypt)
        return "sha256:" + hashlib.sha256(plaintext.encode()).hexdigest()
    return _bcrypt.hashpw(plaintext.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")


def _bcrypt_check(plaintext: str, hashed: str) -> bool:
    if not HAVE_BCRYPT or hashed.startswith("sha256:"):
        return ("sha256:" + hashlib.sha256(plaintext.encode()).hexdigest()) == hashed
    try:
        return _bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _validate_username(username: str) -> bool:
    """Only allow alphanumeric + underscore/hyphen, 3-32 chars."""
    return bool(re.match(r'^[a-zA-Z0-9_\-]{3,32}$', username))


def _run_db_migrations(conn) -> None:
    """Apply all schema migrations and seed admin user if needed."""
    try:
        with conn.cursor() as cur:
            # 1. dashboard_users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_users (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(64) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(32) NOT NULL DEFAULT 'viewer',
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    last_login TIMESTAMP NULL DEFAULT NULL,
                    failed_attempts INT NOT NULL DEFAULT 0,
                    locked_until TIMESTAMP NULL DEFAULT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_username (username),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # Add missing columns to dashboard_users
            for col, ddl in [
                ("email", "ALTER TABLE dashboard_users ADD COLUMN email VARCHAR(255) NULL AFTER username;"),
                ("name", "ALTER TABLE dashboard_users ADD COLUMN name VARCHAR(128) NULL AFTER username;"),
                ("phone", "ALTER TABLE dashboard_users ADD COLUMN phone VARCHAR(32) NULL AFTER email;"),
            ]:
                try:
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'dashboard_users' AND COLUMN_NAME = %s;",
                        (col,)
                    )
                    if cur.fetchone()["cnt"] == 0:
                        cur.execute(ddl)
                except Exception as ex:
                    logger.debug("Column check error for dashboard_users.%s: %s", col, ex)

            # 2. teams
            cur.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    description TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_team_name (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 3. team_members
            cur.execute("""
                CREATE TABLE IF NOT EXISTS team_members (
                    team_id INT UNSIGNED NOT NULL,
                    user_id INT UNSIGNED NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (team_id, user_id),
                    INDEX idx_tm_user (user_id),
                    CONSTRAINT fk_tm_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                    CONSTRAINT fk_tm_user FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 4. services
            cur.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    team_id INT UNSIGNED NULL,
                    description TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_svc_team (team_id),
                    CONSTRAINT fk_svc_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 5. escalation_policies
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escalation_policies (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    service_id INT UNSIGNED NULL,
                    team_id INT UNSIGNED NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_ep_service (service_id),
                    INDEX idx_ep_team (team_id),
                    CONSTRAINT fk_ep_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL,
                    CONSTRAINT fk_ep_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 6. schedules
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    team_id INT UNSIGNED NULL,
                    rotation_type VARCHAR(16) NOT NULL DEFAULT 'daily',
                    custom_interval_days INT NOT NULL DEFAULT 1,
                    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
                    start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_sched_team (team_id),
                    CONSTRAINT fk_sched_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 7. escalation_policy_steps
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escalation_policy_steps (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    policy_id INT UNSIGNED NOT NULL,
                    step_order INT NOT NULL DEFAULT 0,
                    notify_type VARCHAR(16) NOT NULL DEFAULT 'schedule',
                    schedule_id INT UNSIGNED NULL,
                    user_id INT UNSIGNED NULL,
                    delay_minutes INT NOT NULL DEFAULT 0,
                    UNIQUE KEY uq_step_order (policy_id, step_order),
                    INDEX idx_eps_schedule (schedule_id),
                    INDEX idx_eps_user (user_id),
                    CONSTRAINT fk_eps_policy FOREIGN KEY (policy_id) REFERENCES escalation_policies(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 8. schedule_participants
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schedule_participants (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    schedule_id INT UNSIGNED NOT NULL,
                    user_id INT UNSIGNED NOT NULL,
                    position INT NOT NULL DEFAULT 0,
                    UNIQUE KEY uq_sched_position (schedule_id, position),
                    INDEX idx_sp_user (user_id),
                    CONSTRAINT fk_sp_schedule FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
                    CONSTRAINT fk_sp_user FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 9. schedule_overrides
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schedule_overrides (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    schedule_id INT UNSIGNED NOT NULL,
                    override_user_id INT UNSIGNED NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    created_by INT UNSIGNED NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_so_schedule (schedule_id),
                    INDEX idx_so_user (override_user_id),
                    CONSTRAINT fk_so_schedule FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
                    CONSTRAINT fk_so_user FOREIGN KEY (override_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 10. acknowledgements extra columns
            for col, ddl in [
                ("service_id", "ALTER TABLE acknowledgements ADD COLUMN service_id INT UNSIGNED NULL AFTER record_data;"),
                ("urgency", "ALTER TABLE acknowledgements ADD COLUMN urgency VARCHAR(16) NOT NULL DEFAULT 'medium' AFTER service_id;"),
                ("source", "ALTER TABLE acknowledgements ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'alertmanager' AFTER urgency;"),
                ("created_by", "ALTER TABLE acknowledgements ADD COLUMN created_by INT UNSIGNED NULL AFTER source;"),
                ("title", "ALTER TABLE acknowledgements ADD COLUMN title VARCHAR(255) NULL AFTER created_by;"),
                ("description", "ALTER TABLE acknowledgements ADD COLUMN description TEXT NULL AFTER title;"),
            ]:
                try:
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'acknowledgements' AND COLUMN_NAME = %s;",
                        (col,)
                    )
                    if cur.fetchone()["cnt"] == 0:
                        cur.execute(ddl)
                except Exception as ex:
                    logger.debug("Column check error for acknowledgements.%s: %s", col, ex)

            # Auto-seed admin user if no admin exists
            cur.execute("SELECT COUNT(*) AS cnt FROM dashboard_users WHERE role='admin';")
            row = cur.fetchone()
            if row and row["cnt"] == 0:
                default_user = os.environ.get("DASH_DEFAULT_USER", "admin").strip().lower()
                default_password = os.environ.get("DASH_DEFAULT_PASSWORD", "admin123")
                hashed = _bcrypt_hash(default_password)
                cur.execute("""
                    INSERT INTO dashboard_users (username, password_hash, role, name, is_active)
                    VALUES (%s, %s, 'admin', 'Administrator', 1)
                    ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash), role = 'admin', is_active = 1;
                """, (default_user, hashed))
                logger.info("Auto-seeded admin user '%s' with default password.", default_user)

        logger.info("Database schema migration and auto-seeding completed.")
    except Exception as e:
        logger.warning("Database schema migration error: %s", e)


class DashAuthManager:
    """
    Production-ready authentication manager.
    Primary: MariaDB dashboard_users table with bcrypt-hashed passwords.
    Fallback: DASH_USERS env-var plain-text map (for JSON-backend or emergency access).
    """

    DEFAULT_ADMIN_PASSWORD = os.environ.get("DASH_DEFAULT_PASSWORD", "admin123")

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._db_available = False
        self._lock = threading.Lock()
        if cfg.storage_backend == "mariadb" and HAVE_PYMYSQL:
            self._init_db()

    # ----------------------------------------------------------
    # DB helpers
    # ----------------------------------------------------------

    def _get_conn(self):
        return pymysql.connect(
            host=self.cfg.db_host,
            port=self.cfg.db_port,
            user=self.cfg.db_user,
            password=self.cfg.db_password,
            database=self.cfg.db_name,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _init_db(self) -> None:
        try:
            conn = self._get_conn()
            _run_db_migrations(conn)
            conn.close()
            self._db_available = True
            logger.info("DashAuthManager: MariaDB tables ready and verified.")
        except Exception as e:
            logger.warning("DashAuthManager: cannot init DB tables (%s). Falling back to env-var auth.", e)
            self._db_available = False

    def _ensure_db(self) -> bool:
        if self._db_available:
            return True
        if self.cfg.storage_backend == "mariadb" and HAVE_PYMYSQL:
            with self._lock:
                if not self._db_available:
                    self._init_db()
        return self._db_available

    # ----------------------------------------------------------
    # Brute-force helpers (in-memory, per-IP)
    # ----------------------------------------------------------

    @staticmethod
    def _check_brute_force(ip: str) -> Optional[float]:
        """Return seconds remaining in lockout, or None if not locked."""
        with _brute_force_lock:
            entry = _login_attempts.get(ip)
            if not entry:
                return None
            locked_until = entry.get("locked_until")
            if locked_until and time.time() < locked_until:
                return locked_until - time.time()
            return None

    @staticmethod
    def _record_failed_attempt(ip: str) -> int:
        """Record a failed attempt; return remaining attempts before lockout."""
        with _brute_force_lock:
            entry = _login_attempts.get(ip)
            now = time.time()
            if entry:
                locked_until = entry.get("locked_until")
                if locked_until and now >= locked_until:
                    entry = {"count": 0, "locked_until": None}
                    _login_attempts[ip] = entry
            else:
                entry = {"count": 0, "locked_until": None}
                _login_attempts[ip] = entry

            entry["count"] += 1
            if entry["count"] >= _MAX_LOGIN_ATTEMPTS:
                entry["locked_until"] = now + _LOCKOUT_SECONDS
                return 0
            return _MAX_LOGIN_ATTEMPTS - entry["count"]

    @staticmethod
    def _clear_attempts(ip: str) -> None:
        with _brute_force_lock:
            _login_attempts.pop(ip, None)

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify credentials. Returns user dict on success, None on failure.
        Checks DB first; falls back to DASH_USERS env-var.
        """
        if self._ensure_db():
            try:
                conn = self._get_conn()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, username, password_hash, role, is_active, locked_until, failed_attempts "
                        "FROM dashboard_users WHERE username = %s LIMIT 1;",
                        (username,)
                    )
                    row = cur.fetchone()

                if not row or not row["is_active"]:
                    conn.close()
                    return None

                # DB-level lockout (in case multiple instances)
                if row.get("locked_until"):
                    lu = row["locked_until"]
                    if isinstance(lu, str):
                        try:
                            lu = datetime.fromisoformat(lu)
                        except Exception:
                            lu = None
                    if isinstance(lu, datetime):
                        now_dt = datetime.now(timezone.utc) if lu.tzinfo is not None else datetime.now()
                        if now_dt < lu:
                            conn.close()
                            return None

                ok = _bcrypt_check(password, row["password_hash"])
                if ok:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE dashboard_users SET last_login=NOW(), failed_attempts=0, locked_until=NULL WHERE id=%s;",
                            (row["id"],)
                        )
                    conn.close()
                    return {"username": row["username"], "role": row["role"]}
                else:
                    # Increment DB-level failed counter
                    new_count = (row.get("failed_attempts") or 0) + 1
                    if new_count >= _MAX_LOGIN_ATTEMPTS:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE dashboard_users SET failed_attempts=%s, "
                                "locked_until=DATE_ADD(NOW(), INTERVAL %s SECOND) WHERE id=%s;",
                                (new_count, _LOCKOUT_SECONDS, row["id"])
                            )
                    else:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE dashboard_users SET failed_attempts=%s WHERE id=%s;",
                                (new_count, row["id"])
                            )
                    conn.close()
                    return None
            except Exception as e:
                logger.error("DashAuthManager.authenticate DB error: %s", e)
                # Fall through to env-var fallback

        # Env-var fallback
        env_users = self._env_users()
        if username in env_users and env_users[username] == password:
            return {"username": username, "role": "admin"}
        return None

    def list_users(self) -> List[Dict[str, Any]]:
        """Return list of all dashboard users with extended fields and team memberships."""
        if not self._ensure_db():
            return [{"id": 1, "username": u, "email": "", "phone": "", "name": u, "role": "admin", "is_active": True, "team_ids": []} for u in self._env_users()]
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, email, phone, name, role, is_active, last_login, created_at FROM dashboard_users ORDER BY id;"
                )
                rows = cur.fetchall()
                cur.execute("SELECT team_id, user_id FROM team_members;")
                memberships = cur.fetchall()

            conn.close()

            user_teams: Dict[int, List[int]] = {}
            for m in memberships:
                uid = m["user_id"]
                user_teams.setdefault(uid, []).append(m["team_id"])

            result = []
            for r in rows:
                result.append({
                    "id": r["id"],
                    "username": r["username"],
                    "email": r.get("email") or "",
                    "phone": r.get("phone") or "",
                    "name": r.get("name") or r["username"],
                    "role": r["role"],
                    "is_active": bool(r["is_active"]),
                    "team_ids": user_teams.get(r["id"], []),
                    "last_login": r["last_login"].isoformat() if r["last_login"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                })
            return result
        except Exception as e:
            logger.error("DashAuthManager.list_users error: %s", e)
            return []

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "viewer",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Create a new user. Returns (success, message)."""
        if not _validate_username(username):
            return False, "Username must be 3-32 chars: letters, digits, _ or -"
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        valid_roles = ("admin", "manager", "responder", "viewer")
        if role not in valid_roles:
            return False, f"Role must be one of {valid_roles}"
        if not self._ensure_db():
            return False, "DB not available; user creation requires MariaDB"
        try:
            conn = self._get_conn()
            hashed = _bcrypt_hash(password)
            email_val = email.strip() if email and email.strip() else None
            phone_val = phone.strip() if phone and phone.strip() else None
            name_val = name.strip() if name and name.strip() else None
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dashboard_users (username, password_hash, role, email, phone, name) VALUES (%s, %s, %s, %s, %s, %s);",
                    (username, hashed, role, email_val, phone_val, name_val)
                )
            conn.close()
            logger.info("DashAuthManager: created user '%s' role='%s'", username, role)
            return True, "User created successfully"
        except pymysql.err.IntegrityError as ie:
            if "uq_email" in str(ie):
                return False, "Email already exists"
            return False, "Username already exists"
        except Exception as e:
            logger.error("DashAuthManager.create_user error: %s", e)
            return False, "Internal error"

    def update_user(
        self,
        user_id: int,
        role: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[bool, str]:
        """Update an existing user's details."""
        if not self._ensure_db():
            return False, "DB not available"
        valid_roles = ("admin", "manager", "responder", "viewer")
        if role and role not in valid_roles:
            return False, f"Role must be one of {valid_roles}"
        try:
            conn = self._get_conn()
            fields = []
            params = []
            if role is not None:
                fields.append("role = %s")
                params.append(role)
            if email is not None:
                fields.append("email = %s")
                params.append(email.strip() if email.strip() else None)
            if phone is not None:
                fields.append("phone = %s")
                params.append(phone.strip() if phone.strip() else None)
            if name is not None:
                fields.append("name = %s")
                params.append(name.strip() if name.strip() else None)
            if is_active is not None:
                fields.append("is_active = %s")
                params.append(1 if is_active else 0)

            if not fields:
                conn.close()
                return True, "No fields to update"

            params.append(user_id)
            sql = f"UPDATE dashboard_users SET {', '.join(fields)} WHERE id = %s;"
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                updated = cur.rowcount
            conn.close()
            if updated:
                logger.info("DashAuthManager: updated user id=%d", user_id)
                return True, "User updated successfully"
            return False, "User not found"
        except pymysql.err.IntegrityError:
            return False, "Email already in use by another user"
        except Exception as e:
            logger.error("DashAuthManager.update_user error: %s", e)
            return False, "Internal error"

    def delete_user(self, username: str, requesting_user: str) -> Tuple[bool, str]:
        """Delete a user. Cannot delete yourself or the last admin."""
        if username == requesting_user:
            return False, "Cannot delete your own account"
        if not self._ensure_db():
            return False, "DB not available"
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                # Guard: ensure at least one active admin remains
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM dashboard_users WHERE role='admin' AND is_active=1 AND username != %s;",
                    (username,)
                )
                if cur.fetchone()["cnt"] == 0:
                    conn.close()
                    return False, "Cannot delete the last active admin account"
                cur.execute("DELETE FROM dashboard_users WHERE username=%s;", (username,))
                deleted = cur.rowcount
            conn.close()
            if deleted:
                logger.info("DashAuthManager: deleted user '%s' by '%s'", username, requesting_user)
                return True, "User deleted"
            return False, "User not found"
        except Exception as e:
            logger.error("DashAuthManager.delete_user error: %s", e)
            return False, "Internal error"

    def change_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """Change a user's password (admin operation)."""
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters"
        if not self._ensure_db():
            return False, "DB not available"
        try:
            conn = self._get_conn()
            hashed = _bcrypt_hash(new_password)
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE dashboard_users SET password_hash=%s, failed_attempts=0, locked_until=NULL "
                    "WHERE username=%s;",
                    (hashed, username)
                )
                updated = cur.rowcount
            conn.close()
            if updated:
                logger.info("DashAuthManager: password changed for user '%s'", username)
                return True, "Password updated"
            return False, "User not found"
        except Exception as e:
            logger.error("DashAuthManager.change_password error: %s", e)
            return False, "Internal error"

    @staticmethod
    def _env_users() -> Dict[str, str]:
        raw = os.environ.get("DASH_USERS", "").strip()
        users: Dict[str, str] = {}
        if raw:
            for pair in raw.split(","):
                pair = pair.strip()
                if ":" in pair:
                    u, p = pair.split(":", 1)
                    users[u.strip()] = p.strip()
        return users



# Singleton auth manager (initialized after store and config are ready)
dash_auth: DashAuthManager = DashAuthManager(config)



def _require_auth(f):
    """Decorator: redirect to /login if session not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("dash_user"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def _require_auth_api(f):
    """Decorator: return 401 JSON if session not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("dash_user"):
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def _require_admin_api(f):
    """Decorator: return 403 JSON if session user is not admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("dash_user"):
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        if session.get("dash_role") != "admin":
            return jsonify({"ok": False, "error": "Forbidden: admin role required"}), 403
        return f(*args, **kwargs)
    return decorated


def _require_roles(*allowed_roles):
    """Decorator: allow access if user's role is in allowed_roles OR is admin."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("dash_user"):
                return jsonify({"ok": False, "error": "Unauthorized"}), 401
            user_role = session.get("dash_role", "viewer")
            if user_role != "admin" and user_role not in allowed_roles:
                return jsonify({"ok": False, "error": f"Forbidden: role must be one of {list(allowed_roles)}"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator




# ============================================================
# SLACK USER HELPER WITH IN-MEMORY CACHING
# ============================================================

_user_cache: Dict[str, Tuple[str, float]] = {}
_user_cache_lock = threading.Lock()
USER_CACHE_TTL = 3600  # 1 hour cache


def get_slack_user_name(
    client: WebClient,
    user_id: str,
    fallback_hint: Optional[str] = None
) -> str:
    """
    Ultra-fast user name lookup with in-memory caching to eliminate Slack API roundtrips.
    """
    if not user_id:
        return "Unknown"

    now = time.time()
    with _user_cache_lock:
        cached = _user_cache.get(user_id)
        if cached and now < cached[1]:
            return cached[0]

    if fallback_hint:
        with _user_cache_lock:
            _user_cache[user_id] = (fallback_hint, now + USER_CACHE_TTL)
        return fallback_hint

    try:
        response = client.users_info(user=user_id)
        user = response.get("user", {})
        name = (
            user.get("real_name")
            or user.get("profile", {}).get("display_name")
            or user.get("name")
            or user_id
        )
        with _user_cache_lock:
            _user_cache[user_id] = (name, now + USER_CACHE_TTL)
        return name
    except Exception as e:
        logger.warning("Could not fetch Slack user %s: %s", user_id, e)
        return user_id


# ============================================================
# INCIDENT THREAD AUDIT LOGGER
# ============================================================

def post_incident_thread_update(
    client: WebClient,
    channel_id: str,
    message_ts: str,
    text: str
) -> None:
    if not channel_id or not message_ts:
        return

    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=message_ts,
            text=text
        )
    except Exception as e:
        logger.warning("Failed to post thread update to %s/%s: %s", channel_id, message_ts, e)


# ============================================================
# RESOLUTION HANDLER
# ============================================================

def handle_alert_resolution(
    alert: Dict[str, Any],
    occurrence_id: Optional[str] = None,
    resolution_time: Optional[datetime] = None,
    resolved_by: Optional[str] = None,
    slack_client: Optional[WebClient] = None
) -> bool:
    client = slack_client or slack

    res_time = (
        resolution_time
        or parse_alert_time(alert.get("endsAt"))
        or datetime.now(timezone.utc)
    )
    res_time_str = format_display_time(res_time)

    if not occurrence_id:
        fp = alert.get("fingerprint", "")
        starts_at = alert.get("startsAt", "")
        occurrence_id = build_occurrence_id(fp, starts_at)

    # Attribution: explicit override, else ack user, else assignee, else system
    prior = store.get(occurrence_id)
    resolved_by_final = resolve_by_from_record(prior, explicit=resolved_by)

    claimed_record = store.try_claim_resolution(
        occurrence_id,
        res_time_str,
        alert,
        resolved_by=resolved_by_final
    )

    if not claimed_record:
        logger.debug("Resolution for %s already claimed. Skipping.", occurrence_id)
        return False

    logger.info("Claimed resolution for occurrence %s. Processing Slack updates.", occurrence_id)

    # Delete any active silence in Alertmanager
    if claimed_record.get("silence_id"):
        silence_deleted = am_client.delete_silence(claimed_record["silence_id"])
        if silence_deleted:
            logger.info(
                "Deleted Alertmanager silence %s for occurrence %s",
                claimed_record.get("silence_id"),
                occurrence_id
            )

    all_messages = claimed_record.get("messages", [])
    if (
        not all_messages
        and claimed_record.get("channel_id")
        and claimed_record.get("message_ts")
    ):
        all_messages = [
            {
                "channel_id": claimed_record["channel_id"],
                "message_ts": claimed_record["message_ts"]
            }
        ]

    # Update original Slack firing messages: mark resolved and remove all action buttons
    for msg in all_messages:
        ch = msg.get("channel_id")
        ts = msg.get("message_ts")
        if not ch or not ts:
            continue

        try:
            old_alert = copy.deepcopy(
                claimed_record.get("alert_data", alert)
            )
            old_alert["endsAt"] = res_time.isoformat()

            _, clean_blocks = build_firing_blocks(
                old_alert,
                claimed_record,
                occurrence_id,
                is_resolved=False,
                hide_buttons=True
            )

            alert_title = claimed_record.get("alert", "Alert")
            update_text = f"🚨 {alert_title} [Resolved]"

            client.chat_update(
                channel=ch,
                ts=ts,
                text=update_text,
                blocks=clean_blocks
            )

            post_incident_thread_update(
                client,
                ch,
                ts,
                f"🟢 *Incident Resolved* at {res_time_str} by {resolved_by_final}."
            )
        except SlackApiError as e:
            logger.warning("Could not update message %s: %s", ts, e.response.get("error"))
        except Exception as e:
            logger.warning("Could not update message %s: %s", ts, e)

    # Post separate RESOLVED card to channel
    res_text, res_blocks = build_resolved_blocks(
        alert,
        claimed_record,
        res_time
    )

    try:
        client.chat_postMessage(
            channel=config.slack_channel,
            text=res_text,
            blocks=res_blocks
        )
        logger.info("Separate resolved message posted for occurrence %s", occurrence_id)
    except SlackApiError as e:
        logger.error("Failed to post separate resolved message: %s", e.response.get("error"))
    except Exception as e:
        logger.error("Failed to post separate resolved message: %s", e)

    return True


# ============================================================
>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
# BACKGROUND RESOLUTION MONITOR
# ============================================================

shutdown_event = threading.Event()


def resolved_alert_monitor_loop():
    logger.info("Background resolution monitor active.")
    last_prune = time.time()

    while not shutdown_event.is_set():
        try:
            if store.has_unresolved_active_alerts():
                active_fps = am_client.get_active_fingerprints()
                tracked_alerts = store.get_unresolved_active_alerts()

                for item in tracked_alerts:
                    fp = item.get("fingerprint")
                    occ_id = item.get("occurrence_id")

                    if fp and fp not in active_fps and occ_id:
                        logger.info(
                            "Alert occurrence %s recovered. Triggering atomic resolution.",
                            occ_id
                        )
                        handle_alert_resolution(
                            item.get("alert_data", {}),
                            occurrence_id=occ_id
                        )

            if time.time() - last_prune > 21600:
                store.prune_old_records()
                gc.collect()
                last_prune = time.time()

        except Exception as e:
            logger.warning("Monitor loop error: %s", e)

        shutdown_event.wait(config.resolve_monitor_interval)


# ============================================================
# REFER / ASSIGN TEAM MEMBER & DM NOTIFICATION
# ============================================================

def send_assignment_dm(
    client: WebClient,
    assignee_id: str,
    referrer_id: str,
    referrer_name: str,
    channel_id: str,
    message_ts: str,
    alert_data: Dict[str, Any],
    occurrence_id: str
) -> None:
    """
    Sends an instant direct message (DM) notification to the assigned team member.
    """
    if not assignee_id:
        return

    try:
        labels = alert_data.get("labels", {})
        annotations = alert_data.get("annotations", {})
        alertname = labels.get("alertname", "Unknown Alert")
        severity = labels.get("severity", "unknown").upper()
        instance = labels.get("instance", "Unknown")
        summary = annotations.get("summary", "")
        description = annotations.get("description", "")

        # Try to get permalink to the original incident message in the channel
        permalink = ""
        try:
            p_resp = client.chat_getPermalink(channel=channel_id, message_ts=message_ts)
            permalink = p_resp.get("permalink", "")
        except Exception:
            pass

        sev_emoji = (
            "🔴" if severity in ("CRITICAL", "PAGE", "FATAL")
            else "🟡" if severity in ("WARNING", "WARN")
            else "ℹ️"
        )

        dm_text = f"🚨 Incident Assigned to You: [{severity}] {alertname}"

        body_lines = [
            f"You have been assigned to this incident by <@{referrer_id}> ({referrer_name}):\n",
            f"• *Alert:* `{alertname}`",
            f"• *Severity:* `{severity}`",
            f"• *Instance:* `{instance}`",
            f"• *Channel:* <#{channel_id}>"
        ]
        if summary:
            body_lines.append(f"• *Summary:* {summary}")
        if description and description != summary:
            body_lines.append(f"• *Description:* {description[:300]}")

        dm_blocks: List[Dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{sev_emoji} Incident Assigned to You",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(body_lines)
                }
            }
        ]

        # Action buttons in DM
        action_elements: List[Dict[str, Any]] = []
        if permalink:
            action_elements.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔗 View in Channel",
                    "emoji": True
                },
                "url": permalink,
                "style": "primary"
            })

        if action_elements:
            dm_blocks.append({
                "type": "actions",
                "elements": action_elements
            })

        client.chat_postMessage(
            channel=assignee_id,
            text=dm_text,
            blocks=dm_blocks
        )
        logger.info(
            "Sent assignment DM to user %s for occurrence %s",
            assignee_id,
            occurrence_id
        )
    except Exception as e:
        logger.warning(
            "Could not send assignment DM to %s: %s",
            assignee_id,
            e
        )


@bolt_app.action("refer_user_action")
def on_refer_user(ack, body, client):
    ack()

    try:
        user_id = body["user"]["id"]
        caller_name_hint = body["user"].get("name") or body["user"].get("username")
        user_name = get_slack_user_name(client, user_id, fallback_hint=caller_name_hint)

        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        selected_user_id = body["actions"][0].get("selected_user")
        if not selected_user_id:
            return

        block_id = body["actions"][0].get("block_id", "")
        occurrence_id = block_id.replace("incident_select_block_", "")

        record = store.get(occurrence_id)
        if not record:
            return

        selected_user_name = get_slack_user_name(client, selected_user_id)
        now_str = format_display_time(datetime.now(timezone.utc))

        updated_record = store.update_assignment(
            occurrence_id=occurrence_id,
            assignee_id=selected_user_id,
            assignee_name=selected_user_name,
            referred_by_id=user_id,
            referred_by_name=user_name,
            action_at=now_str
        )

        if not updated_record:
            return

        alert_data = updated_record.get("alert_data", {})
        text, blocks = build_firing_blocks(
            alert_data,
            updated_record,
            occurrence_id
        )

        # Update the main card in the channel (all action buttons remain visible)
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text,
            blocks=blocks
        )

        # Post thread update in channel
        post_incident_thread_update(
            client,
            channel_id,
            message_ts,
            f"👤 <@{user_id}> ({user_name}) referred and assigned this incident to <@{selected_user_id}> ({selected_user_name})."
        )

        # Send instant Direct Message (DM) to the assigned team member
        send_assignment_dm(
            client=client,
            assignee_id=selected_user_id,
            referrer_id=user_id,
            referrer_name=user_name,
            channel_id=channel_id,
            message_ts=message_ts,
            alert_data=alert_data,
            occurrence_id=occurrence_id
        )

        logger.info(
            "Occurrence %s referred to %s by %s",
            occurrence_id,
            selected_user_name,
            user_name
        )
    except Exception as e:
        logger.exception("Error on refer_user_action: %s", e)


# ============================================================
# PAUSE / SNOOZE
# ============================================================

@bolt_app.action("pause_alert_dropdown")
def on_pause_alert_dropdown(ack, body, client):
    ack()

    try:
        user_id = body["user"]["id"]
        caller_name_hint = body["user"].get("name") or body["user"].get("username")
        user_name = get_slack_user_name(client, user_id, fallback_hint=caller_name_hint)

        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        selected_val = body["actions"][0].get("selected_option", {}).get("value", "")
        parts = selected_val.split(":", 2)

        if len(parts) < 3:
            return

        pause_key = parts[1]
        occurrence_id = parts[2]

        record = store.get(occurrence_id)
        fingerprint = (
            record.get("fingerprint")
            if record
            else occurrence_id.split("_")[0]
        )

        alert = am_client.get_alert_by_fingerprint(fingerprint)
        if not alert and record:
            alert = record.get("alert_data")

        if not alert:
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Alert is no longer active",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "⚠️ *Alert is no longer active in Alertmanager.*"
                        }
                    }
                ]
            )
            return

        now_dt = datetime.now(timezone.utc)
        ends_at, duration_label = calculate_pause_end_time(pause_key, now_dt)

        if record and record.get("silence_id"):
            am_client.delete_silence(record["silence_id"])

        silence_id = ""
        try:
            silence_id = am_client.create_silence(
                labels=alert.get("labels", {}),
                author=user_name,
                starts_at=now_dt,
                ends_at=ends_at,
                comment=f"Snoozed for {duration_label} via Slack by {user_name}"
            )
        except Exception as e:
            logger.warning("Could not create silence in Alertmanager: %s", e)

        now_str = format_display_time(now_dt)
        ends_at_str = format_display_time(ends_at)

        updated_record = store.update_action(
            occurrence_id=occurrence_id,
            action="paused",
            user_id=user_id,
            user_name=user_name,
            action_at=now_str,
            target_message_ts=message_ts,
            silence_id=silence_id or None,
            silence_ends_at=ends_at_str,
            silence_label=duration_label,
            timeline_entry=f"⏸️ Snoozed for {duration_label} (until {ends_at_str}) by <@{user_id}>"
        )

        if not updated_record:
            return

        text, blocks = build_firing_blocks(
            alert,
            updated_record,
            occurrence_id
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text,
            blocks=blocks
        )

        silence_note = f" (Silence ID: `{silence_id}`)" if silence_id else ""
        post_incident_thread_update(
            client,
            channel_id,
            message_ts,
            f"⏸️ Incident snoozed for *{duration_label}* (until `{ends_at_str}`) by <@{user_id}> ({user_name}).{silence_note}"
        )

        logger.info(
            "Occurrence %s snoozed for %s by %s",
            occurrence_id,
            duration_label,
            user_name
        )
    except Exception as e:
        logger.exception("Error on pause_alert_dropdown: %s", e)


# ============================================================
# ACCEPT / ACKNOWLEDGE
# ============================================================

@bolt_app.action("accept_alert")
def on_accept_alert(ack, body, client):
    ack()

    try:
        user_id = body["user"]["id"]
        caller_name_hint = body["user"].get("name") or body["user"].get("username")
        user_name = get_slack_user_name(client, user_id, fallback_hint=caller_name_hint)

        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        occurrence_id = body["actions"][0].get("value", "")

        record = store.get(occurrence_id)
        fingerprint = (
            record.get("fingerprint")
            if record
            else occurrence_id.split("_")[0]
        )

        alert = am_client.get_alert_by_fingerprint(fingerprint)
        if not alert and record:
            alert = record.get("alert_data")

        if not alert:
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Alert is no longer active",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "⚠️ *Alert is no longer active in Alertmanager.*"
                        }
                    }
                ]
            )
            return

        now_dt = datetime.now(timezone.utc)
        now_str = format_display_time(now_dt)
        ends_at = now_dt + timedelta(hours=config.silence_duration_hours)

        silence_id = ""
        try:
            silence_id = am_client.create_silence(
                labels=alert.get("labels", {}),
                author=user_name,
                starts_at=now_dt,
                ends_at=ends_at,
                comment=f"Acknowledged and silenced for {config.silence_duration_hours}h by {user_name}"
            )
        except Exception as e:
            logger.warning("Could not create silence in Alertmanager: %s", e)

        updated_record = store.update_action(
            occurrence_id=occurrence_id,
            action="accepted",
            user_id=user_id,
            user_name=user_name,
            action_at=now_str,
            target_message_ts=message_ts,
            silence_id=silence_id or None,
            silence_ends_at=format_display_time(ends_at),
            silence_label=f"{config.silence_duration_hours} Hours",
            timeline_entry=f"✅ Acknowledged and silenced ({config.silence_duration_hours}h) by <@{user_id}>"
        )

        if not updated_record:
            return

        # Auto-assign acknowledging user if unassigned
        if not updated_record.get("assignee_id"):
            updated_record = store.update_assignment(
                occurrence_id=occurrence_id,
                assignee_id=user_id,
                assignee_name=user_name,
                referred_by_id=user_id,
                referred_by_name=user_name,
                action_at=now_str
            ) or updated_record

        text, blocks = build_firing_blocks(
            alert,
            updated_record,
            occurrence_id
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text,
            blocks=blocks
        )

        silence_str = f" Silence active for {config.silence_duration_hours}h." if silence_id else ""
        post_incident_thread_update(
            client,
            channel_id,
            message_ts,
            f"✅ <@{user_id}> ({user_name}) acknowledged the incident.{silence_str}"
        )

        logger.info("Occurrence %s accepted by %s", occurrence_id, user_name)
    except Exception as e:
        logger.exception("Error on accept_alert: %s", e)


# ============================================================
# RESUME / UNPAUSE
# ============================================================

@bolt_app.action("resume_alert")
def on_resume_alert(ack, body, client):
    ack()

    try:
        user_id = body["user"]["id"]
        caller_name_hint = body["user"].get("name") or body["user"].get("username")
        user_name = get_slack_user_name(client, user_id, fallback_hint=caller_name_hint)

        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        occurrence_id = body["actions"][0].get("value", "")

        record = store.get(occurrence_id)
        if not record:
            return

        if record.get("silence_id"):
            am_client.delete_silence(record["silence_id"])

        now_str = format_display_time(datetime.now(timezone.utc))

        updated_record = store.update_action(
            occurrence_id=occurrence_id,
            action="not_acknowledged",
            user_id=user_id,
            user_name=user_name,
            action_at=now_str,
            target_message_ts=message_ts,
            silence_id=None,
            silence_ends_at=None,
            silence_label=None,
            timeline_entry=f"▶️ Resumed / Unsilenced by <@{user_id}> ({user_name})"
        )

        if not updated_record:
            return

        alert_data = updated_record.get("alert_data", {})
        text, blocks = build_firing_blocks(
            alert_data,
            updated_record,
            occurrence_id
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text,
            blocks=blocks
        )

        post_incident_thread_update(
            client,
            channel_id,
            message_ts,
            f"▶️ Alert resumed and unsilenced by <@{user_id}> ({user_name}). Active monitoring restored."
        )

        logger.info("Occurrence %s resumed by %s", occurrence_id, user_name)
    except Exception as e:
        logger.exception("Error on resume_alert: %s", e)


# ============================================================
# REJECT / ESCALATE
# - Name of who rejected is NOT displayed anywhere
# - All interactive buttons are removed from the rejected message
# - A fresh notification is immediately posted to the Slack channel
# ============================================================

@bolt_app.action("reject_alert")
def on_reject_alert(ack, body, client):
    ack()

    try:
        user_id = body["user"]["id"]
        caller_name_hint = body["user"].get("name") or body["user"].get("username")
        user_name = get_slack_user_name(client, user_id, fallback_hint=caller_name_hint)

        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        occurrence_id = body["actions"][0].get("value", "")

        record = store.get(occurrence_id)
        fingerprint = (
            record.get("fingerprint")
            if record
            else occurrence_id.split("_")[0]
        )

        alert = am_client.get_alert_by_fingerprint(fingerprint)
        if not alert and record:
            alert = record.get("alert_data")

        # 1. Remove any existing silence in Alertmanager
        if record and record.get("silence_id"):
            am_client.delete_silence(record["silence_id"])

        now_str = format_display_time(datetime.now(timezone.utc))

        # 2. Update record: mark action as 'rejected'
        # user details are NOT shown in user-facing fields
        updated_record = store.update_action(
            occurrence_id=occurrence_id,
            action="rejected",
            user_id=None,  # Keep anonymous
            user_name=None,  # Keep anonymous
            action_at=now_str,
            target_message_ts=message_ts,
            silence_id=None,
            silence_ends_at=None,
            silence_label=None,
            timeline_entry="⚠️ Rejected / Escalated"
        )

        if not updated_record:
            return

        # 3. Update the existing Slack message:
        # All buttons are removed! (hide_buttons=True, action='rejected')
        # NO user name is displayed on the card!
        alert_payload = alert or record.get("alert_data", {})
        text, blocks = build_firing_blocks(
            alert_payload,
            updated_record,
            occurrence_id,
            is_resolved=False,
            hide_buttons=True
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text,
            blocks=blocks
        )

        # Thread update: explicitly do NOT mention user name or user id!
        post_incident_thread_update(
            client,
            channel_id,
            message_ts,
            "⚠️ *Incident was rejected / escalated.* Escalation cycle active. Re-notifying team."
        )

        logger.info(
            "Occurrence %s rejected anonymously (invoked by user %s). Escalating with new notification.",
            occurrence_id,
            user_id
        )

        # 4. Reject Escalation Loop (Section 13)
        # Post a fresh actionable notification to the channel
        # with full interactive buttons active for other responders!
        def _execute_reject_escalation():
            try:
                # Re-check state: if resolved in the interim, do not re-alert!
                current_state = store.get(occurrence_id)
                if current_state and current_state.get("resolved_at"):
                    logger.info(
                        "Occurrence %s resolved before escalation check. Skipping re-alert.",
                        occurrence_id
                    )
                    return

                fresh_ack = None  # Fresh firing card with buttons
                fresh_text, fresh_blocks = build_firing_blocks(
                    alert_payload,
                    fresh_ack,
                    occurrence_id,
                    is_resolved=False,
                    hide_buttons=False
                )

                new_msg_resp = client.chat_postMessage(
                    channel=config.slack_channel,
                    text=f"🚨 [RE-NOTIFIED] {fresh_text}",
                    blocks=fresh_blocks
                )

                new_ts = new_msg_resp.get("ts")
                new_ch = new_msg_resp.get("channel", config.slack_channel)

                if new_ts:
                    starts_at = alert_payload.get("startsAt", "")
                    store.save_or_append_notification(
                        occurrence_id=occurrence_id,
                        fingerprint=fingerprint,
                        starts_at=starts_at,
                        channel_id=new_ch,
                        message_ts=new_ts,
                        alert_data=alert_payload
                    )

                    post_incident_thread_update(
                        client,
                        new_ch,
                        new_ts,
                        "🚨 *Re-notified Alert*: Incident was previously rejected/escalated and requires immediate attention."
                    )
            except Exception as esc_err:
                logger.exception("Error executing reject escalation: %s", esc_err)

        if config.reject_escalation_seconds > 0:
            logger.info(
                "Scheduling reject escalation for occurrence %s in %ds",
                occurrence_id,
                config.reject_escalation_seconds
            )
            timer = threading.Timer(config.reject_escalation_seconds, _execute_reject_escalation)
            timer.daemon = True
            timer.start()
        else:
            _execute_reject_escalation()

    except Exception as e:
        logger.exception("Error on reject_alert: %s", e)


# ============================================================
# MANUAL RESOLUTION — REMOVED
# Mark Resolved button is no longer shown. Resolution comes from
# Alertmanager (webhook / background monitor). Attribution:
# acknowledged user -> assignee -> System Auto-detect.
# Legacy action id kept as a no-op so old Slack messages do not error.
# ============================================================

@bolt_app.action("manual_resolve_alert")
def on_manual_resolve(ack, body, client):
    ack()
    logger.info(
        "manual_resolve_alert ignored (feature removed). occurrence=%s",
        (body.get("actions") or [{}])[0].get("value", "")
    )


# ============================================================
# ADD INCIDENT NOTE MODAL
# ============================================================

@bolt_app.action("open_note_modal")
def on_open_note_modal(ack, body, client):
    ack()

    try:
        trigger_id = body["trigger_id"]
        occurrence_id = body["actions"][0].get("value", "")
        channel_id = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "submit_incident_note",
                "private_metadata": json.dumps({
                    "occurrence_id": occurrence_id,
                    "channel_id": channel_id,
                    "message_ts": message_ts
                }),
                "title": {
                    "type": "plain_text",
                    "text": "Add Incident Note"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Post Note"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "note_input_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Investigation update or RCA note:"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "note_text",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "e.g. Investigating high CPU; restarting worker pool pod."
                            }
                        }
                    }
                ]
            }
        )
    except Exception as e:
        logger.exception("Error opening note modal: %s", e)


@bolt_app.view("submit_incident_note")
def on_submit_incident_note(ack, body, client, view):
    ack()

    try:
        user_id = body["user"]["id"]
        caller_name_hint = body["user"].get("name") or body["user"].get("username")
        user_name = get_slack_user_name(client, user_id, fallback_hint=caller_name_hint)

        meta = json.loads(view.get("private_metadata", "{}"))
        occurrence_id = meta.get("occurrence_id")
        channel_id = meta.get("channel_id")
        message_ts = meta.get("message_ts")

        note_text = (
            view["state"]["values"]["note_input_block"]["note_text"]["value"]
        )

        if not note_text:
            return

        store.add_timeline_note(
            occurrence_id=occurrence_id,
            user_id=user_id,
            user_name=user_name,
            note=note_text
        )

        post_incident_thread_update(
            client,
            channel_id,
            message_ts,
            f"💬 *Incident Note from <@{user_id}> ({user_name}):*\n>{note_text}"
        )

        logger.info("Added note to occurrence %s by %s", occurrence_id, user_name)
    except Exception as e:
        logger.exception("Error submitting incident note: %s", e)


# ============================================================
<<<<<<< HEAD
# FLASK HEALTH
# ============================================================

=======
# AUTH ROUTES
# ============================================================

@flask_app.route("/login", methods=["GET"])
def login_page():
    if session.get("dash_user"):
        return redirect("/")
    # Search for login.html in the same set of candidate dirs as dashboard.html
    here = os.path.dirname(os.path.abspath(__file__))
    candidate_dirs = [
        here,
        os.getcwd(),
        os.path.join(here, "templates"),
        os.path.join(here, "static"),
    ]
    for d in candidate_dirs:
        target = os.path.join(d, "login.html")
        if os.path.isfile(target):
            return send_from_directory(d, "login.html")
    return "<h1>login.html not found</h1><p>Place login.html next to app.py</p>", 404


@flask_app.route("/api/login", methods=["POST"])
def api_login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = (data.get("password") or "")

    # --- Brute-force gate ---
    remaining_lock = DashAuthManager._check_brute_force(ip)
    if remaining_lock is not None:
        mins = int(remaining_lock // 60) + 1
        return jsonify({"ok": False, "error": f"Too many failed attempts. Try again in {mins} minute(s)."}), 429

    if not username or not password:
        return jsonify({"ok": False, "error": "Username and password are required"}), 400

    user_info = dash_auth.authenticate(username, password) if dash_auth else None

    if user_info:
        DashAuthManager._clear_attempts(ip)
        session.permanent = True
        session["dash_user"] = user_info["username"]
        session["dash_role"] = user_info.get("role", "viewer")
        logger.info("Dashboard login: user=%s role=%s ip=%s", user_info["username"], user_info.get("role"), ip)
        return jsonify({"ok": True, "username": user_info["username"], "role": user_info.get("role", "viewer")}), 200

    remaining = DashAuthManager._record_failed_attempt(ip)
    logger.warning("Failed login: user=%s ip=%s remaining_attempts=%s", username, ip, remaining)
    msg = "Invalid username or password"
    if remaining == 0:
        msg = f"Too many failed attempts. Account locked for {_LOCKOUT_SECONDS // 60} minutes."
    return jsonify({"ok": False, "error": msg}), 401


@flask_app.route("/api/logout", methods=["POST"])
def api_logout():
    user = session.pop("dash_user", None)
    session.pop("dash_role", None)
    if user:
        logger.info("Dashboard logout: user=%s", user)
    return jsonify({"ok": True}), 200


@flask_app.route("/api/auth-check", methods=["GET"])
def api_auth_check():
    user = session.get("dash_user")
    return jsonify({
        "authenticated": bool(user),
        "username": user or "",
        "role": session.get("dash_role", "viewer") if user else "",
    }), 200


# ============================================================
# ON-CALL CALCULATION HELPER
# ============================================================

def get_current_oncall(schedule_id: int) -> Optional[Dict[str, Any]]:
    """
    Computes the current on-call user for a schedule taking into account:
    - rotation_type ('daily', 'weekly', 'custom')
    - custom_interval_days
    - start_time & timezone
    - position-ordered participants
    - active schedule_overrides
    """
    if not dash_auth._ensure_db():
        return None
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM schedules WHERE id = %s;", (schedule_id,))
            schedule = cur.fetchone()
            if not schedule:
                conn.close()
                return None

            cur.execute("""
                SELECT so.*, u.id as user_id, u.username, u.name, u.email, u.phone, u.role
                FROM schedule_overrides so
                JOIN dashboard_users u ON so.override_user_id = u.id
                WHERE so.schedule_id = %s AND so.start_time <= NOW() AND so.end_time >= NOW()
                ORDER BY so.id DESC LIMIT 1;
            """, (schedule_id,))
            override = cur.fetchone()
            if override:
                conn.close()
                return {
                    "user_id": override["user_id"],
                    "username": override["username"],
                    "name": override.get("name") or override["username"],
                    "email": override.get("email") or "",
                    "phone": override.get("phone") or "",
                    "role": override["role"],
                    "is_override": True,
                    "override_start": override["start_time"].isoformat() if override.get("start_time") else None,
                    "override_end": override["end_time"].isoformat() if override.get("end_time") else None
                }

            cur.execute("""
                SELECT sp.position, u.id as user_id, u.username, u.name, u.email, u.phone, u.role
                FROM schedule_participants sp
                JOIN dashboard_users u ON sp.user_id = u.id
                WHERE sp.schedule_id = %s AND u.is_active = 1
                ORDER BY sp.position ASC;
            """, (schedule_id,))
            participants = cur.fetchall()
            conn.close()

            if not participants:
                return None

            rot_type = schedule.get("rotation_type", "daily")
            custom_days = schedule.get("custom_interval_days", 1) or 1
            if rot_type == "daily":
                interval_days = 1
            elif rot_type == "weekly":
                interval_days = 7
            else:
                interval_days = max(1, custom_days)

            start_time = schedule.get("start_time")
            if not start_time:
                start_time = datetime.now(timezone.utc)
            elif isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)

            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

            now_dt = datetime.now(timezone.utc)
            delta = now_dt - start_time
            total_days = max(0, delta.total_seconds() / 86400.0)
            shift_index = int(total_days // interval_days) % len(participants)

            oncall_user = participants[shift_index]
            return {
                "user_id": oncall_user["user_id"],
                "username": oncall_user["username"],
                "name": oncall_user.get("name") or oncall_user["username"],
                "email": oncall_user.get("email") or "",
                "phone": oncall_user.get("phone") or "",
                "role": oncall_user["role"],
                "position": oncall_user["position"],
                "is_override": False
            }
    except Exception as e:
        logger.error("get_current_oncall error: %s", e)
        return None


# ============================================================
# USER MANAGEMENT API
# ============================================================

@flask_app.route("/api/users", methods=["GET"])
@_require_roles("admin", "manager")
def api_users_list():
    users = dash_auth.list_users() if dash_auth else []
    return jsonify({"ok": True, "users": users}), 200


@flask_app.route("/api/users", methods=["POST"])
@_require_admin_api
def api_users_create():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = (data.get("password") or "")
    role = (data.get("role") or "viewer").strip().lower()
    email = data.get("email")
    phone = data.get("phone")
    name = data.get("name")

    ok, msg = dash_auth.create_user(
        username=username,
        password=password,
        role=role,
        email=email,
        phone=phone,
        name=name
    )
    return jsonify({"ok": ok, "message": msg}), (201 if ok else 400)


@flask_app.route("/api/users/<int:user_id>", methods=["PUT"])
@_require_admin_api
def api_users_update(user_id: int):
    data = request.get_json(silent=True) or {}
    ok, msg = dash_auth.update_user(
        user_id=user_id,
        role=data.get("role"),
        email=data.get("email"),
        phone=data.get("phone"),
        name=data.get("name"),
        is_active=data.get("is_active")
    )
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 400)


@flask_app.route("/api/users/<string:username>", methods=["DELETE"])
@_require_admin_api
def api_users_delete(username: str):
    requesting = session["dash_user"]
    ok, msg = dash_auth.delete_user(username, requesting)
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 400)


@flask_app.route("/api/users/<string:username>/password", methods=["PUT"])
@_require_admin_api
def api_users_change_password(username: str):
    data = request.get_json(silent=True) or {}
    new_password = data.get("password") or ""
    ok, msg = dash_auth.change_password(username, new_password)
    return jsonify({"ok": ok, "message": msg}), (200 if ok else 400)


# ============================================================
# TEAMS MANAGEMENT API
# ============================================================

@flask_app.route("/api/teams", methods=["GET"])
@_require_auth_api
def api_teams_list():
    if not dash_auth._ensure_db():
        return jsonify({"ok": True, "teams": []}), 200
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, description, created_at, updated_at FROM teams ORDER BY id ASC;")
            teams = cur.fetchall()

            # Get member details for each team
            cur.execute("""
                SELECT tm.team_id, u.id as user_id, u.username, u.name, u.email, u.role
                FROM team_members tm
                JOIN dashboard_users u ON tm.user_id = u.id
                ORDER BY u.username ASC;
            """)
            members = cur.fetchall()
        conn.close()

        team_members_map: Dict[int, List[Dict[str, Any]]] = {}
        for m in members:
            tid = m["team_id"]
            team_members_map.setdefault(tid, []).append({
                "id": m["user_id"],
                "username": m["username"],
                "name": m.get("name") or m["username"],
                "email": m.get("email") or "",
                "role": m["role"]
            })

        result = []
        for t in teams:
            tid = t["id"]
            m_list = team_members_map.get(tid, [])
            result.append({
                "id": tid,
                "name": t["name"],
                "description": t.get("description") or "",
                "members": m_list,
                "member_count": len(m_list),
                "created_at": t["created_at"].isoformat() if t.get("created_at") else None
            })
        return jsonify({"ok": True, "teams": result}), 200
    except Exception as e:
        logger.error("api_teams_list error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/teams", methods=["POST"])
@_require_roles("admin", "manager")
def api_teams_create():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    member_ids = data.get("member_ids") or []

    if not name:
        return jsonify({"ok": False, "error": "Team name is required"}), 400

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teams (name, description) VALUES (%s, %s);",
                (name, description or None)
            )
            team_id = cur.lastrowid
            if member_ids and isinstance(member_ids, list):
                for uid in member_ids:
                    cur.execute(
                        "INSERT IGNORE INTO team_members (team_id, user_id) VALUES (%s, %s);",
                        (team_id, uid)
                    )
        conn.close()
        return jsonify({"ok": True, "team_id": team_id, "message": "Team created"}), 201
    except pymysql.err.IntegrityError:
        return jsonify({"ok": False, "error": "Team with this name already exists"}), 400
    except Exception as e:
        logger.error("api_teams_create error: %s", e)
        return jsonify({"ok": False, "error": "Internal error"}), 500


@flask_app.route("/api/teams/<int:team_id>", methods=["PUT"])
@_require_roles("admin", "manager")
def api_teams_update(team_id: int):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description")
    member_ids = data.get("member_ids")

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            if name is not None or description is not None:
                cur.execute(
                    "UPDATE teams SET name = COALESCE(%s, name), description = COALESCE(%s, description) WHERE id = %s;",
                    (name.strip() if name else None, description.strip() if description else None, team_id)
                )

            if member_ids is not None and isinstance(member_ids, list):
                cur.execute("DELETE FROM team_members WHERE team_id = %s;", (team_id,))
                for uid in member_ids:
                    cur.execute(
                        "INSERT IGNORE INTO team_members (team_id, user_id) VALUES (%s, %s);",
                        (team_id, uid)
                    )
        conn.close()
        return jsonify({"ok": True, "message": "Team updated"}), 200
    except pymysql.err.IntegrityError:
        return jsonify({"ok": False, "error": "Team name already in use"}), 400
    except Exception as e:
        logger.error("api_teams_update error: %s", e)
        return jsonify({"ok": False, "error": "Internal error"}), 500


@flask_app.route("/api/teams/<int:team_id>", methods=["DELETE"])
@_require_admin_api
def api_teams_delete(team_id: int):
    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM teams WHERE id = %s;", (team_id,))
            deleted = cur.rowcount
        conn.close()
        if deleted:
            return jsonify({"ok": True, "message": "Team deleted"}), 200
        return jsonify({"ok": False, "error": "Team not found"}), 404
    except Exception as e:
        logger.error("api_teams_delete error: %s", e)
        return jsonify({"ok": False, "error": "Internal error"}), 500


# ============================================================
# SERVICES MANAGEMENT API
# ============================================================

@flask_app.route("/api/services", methods=["GET"])
@_require_auth_api
def api_services_list():
    if not dash_auth._ensure_db():
        return jsonify({"ok": True, "services": []}), 200
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.id, s.name, s.team_id, t.name as team_name, s.description, s.created_at
                FROM services s
                LEFT JOIN teams t ON s.team_id = t.id
                ORDER BY s.name ASC;
            """)
            rows = cur.fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "name": r["name"],
                "team_id": r["team_id"],
                "team_name": r.get("team_name") or "Unassigned",
                "description": r.get("description") or "",
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None
            })
        return jsonify({"ok": True, "services": result}), 200
    except Exception as e:
        logger.error("api_services_list error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/services", methods=["POST"])
@_require_roles("admin", "manager")
def api_services_create():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    team_id = data.get("team_id")
    description = (data.get("description") or "").strip()

    if not name:
        return jsonify({"ok": False, "error": "Service name is required"}), 400

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO services (name, team_id, description) VALUES (%s, %s, %s);",
                (name, team_id or None, description or None)
            )
            svc_id = cur.lastrowid
        conn.close()
        return jsonify({"ok": True, "service_id": svc_id, "message": "Service created"}), 201
    except Exception as e:
        logger.error("api_services_create error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/services/<int:service_id>", methods=["PUT"])
@_require_roles("admin", "manager")
def api_services_update(service_id: int):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    team_id = data.get("team_id")
    description = data.get("description")

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE services SET name = COALESCE(%s, name), team_id = %s, description = COALESCE(%s, description) WHERE id = %s;",
                (name.strip() if name else None, team_id if team_id is not None else None, description.strip() if description else None, service_id)
            )
        conn.close()
        return jsonify({"ok": True, "message": "Service updated"}), 200
    except Exception as e:
        logger.error("api_services_update error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/services/<int:service_id>", methods=["DELETE"])
@_require_roles("admin", "manager")
def api_services_delete(service_id: int):
    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM services WHERE id = %s;", (service_id,))
            deleted = cur.rowcount
        conn.close()
        if deleted:
            return jsonify({"ok": True, "message": "Service deleted"}), 200
        return jsonify({"ok": False, "error": "Service not found"}), 404
    except Exception as e:
        logger.error("api_services_delete error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# SCHEDULES & ON-CALL MANAGEMENT API
# ============================================================

@flask_app.route("/api/schedules", methods=["GET"])
@_require_auth_api
def api_schedules_list():
    if not dash_auth._ensure_db():
        return jsonify({"ok": True, "schedules": []}), 200
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.id, s.name, s.team_id, t.name as team_name, s.rotation_type,
                       s.custom_interval_days, s.timezone, s.start_time, s.created_at
                FROM schedules s
                LEFT JOIN teams t ON s.team_id = t.id
                ORDER BY s.id ASC;
            """)
            schedules = cur.fetchall()

            # Get participants
            cur.execute("""
                SELECT sp.schedule_id, sp.position, u.id as user_id, u.username, u.name, u.email
                FROM schedule_participants sp
                JOIN dashboard_users u ON sp.user_id = u.id
                ORDER BY sp.position ASC;
            """)
            participants = cur.fetchall()
        conn.close()

        sched_parts_map: Dict[int, List[Dict[str, Any]]] = {}
        for p in participants:
            sid = p["schedule_id"]
            sched_parts_map.setdefault(sid, []).append({
                "position": p["position"],
                "user_id": p["user_id"],
                "username": p["username"],
                "name": p.get("name") or p["username"],
                "email": p.get("email") or ""
            })

        result = []
        for s in schedules:
            sid = s["id"]
            parts = sched_parts_map.get(sid, [])
            oncall = get_current_oncall(sid)
            result.append({
                "id": sid,
                "name": s["name"],
                "team_id": s["team_id"],
                "team_name": s.get("team_name") or "Unassigned",
                "rotation_type": s["rotation_type"],
                "custom_interval_days": s.get("custom_interval_days", 1),
                "timezone": s.get("timezone", "UTC"),
                "start_time": s["start_time"].isoformat() if s.get("start_time") else None,
                "participants": parts,
                "current_oncall": oncall,
                "created_at": s["created_at"].isoformat() if s.get("created_at") else None
            })
        return jsonify({"ok": True, "schedules": result}), 200
    except Exception as e:
        logger.error("api_schedules_list error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/schedules", methods=["POST"])
@_require_roles("admin", "manager")
def api_schedules_create():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    team_id = data.get("team_id")
    rotation_type = data.get("rotation_type") or "daily"
    custom_interval_days = data.get("custom_interval_days") or 1
    tz = data.get("timezone") or "UTC"
    start_time_raw = data.get("start_time")
    try:
        dt = datetime.fromisoformat(start_time_raw.replace('Z', '+00:00')) if start_time_raw else datetime.now(timezone.utc)
    except ValueError:
        dt = datetime.now(timezone.utc)
    start_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    participant_user_ids = data.get("participant_user_ids") or []

    if not name:
        return jsonify({"ok": False, "error": "Schedule name is required"}), 400

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO schedules (name, team_id, rotation_type, custom_interval_days, timezone, start_time)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (name, team_id or None, rotation_type, custom_interval_days, tz, start_time_str))
            sched_id = cur.lastrowid

            if participant_user_ids and isinstance(participant_user_ids, list):
                for pos, uid in enumerate(participant_user_ids):
                    cur.execute("""
                        INSERT INTO schedule_participants (schedule_id, user_id, position)
                        VALUES (%s, %s, %s);
                    """, (sched_id, uid, pos))
        conn.close()
        return jsonify({"ok": True, "schedule_id": sched_id, "message": "Schedule created"}), 201
    except Exception as e:
        logger.error("api_schedules_create error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/schedules/<int:schedule_id>", methods=["PUT"])
@_require_roles("admin", "manager")
def api_schedules_update(schedule_id: int):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    team_id = data.get("team_id")
    rotation_type = data.get("rotation_type")
    custom_interval_days = data.get("custom_interval_days")
    tz = data.get("timezone")
    start_time_raw = data.get("start_time")
    participant_user_ids = data.get("participant_user_ids")

    start_time_str = None
    if start_time_raw:
        try:
            dt = datetime.fromisoformat(start_time_raw.replace('Z', '+00:00'))
            start_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE schedules
                SET name = COALESCE(%s, name),
                    team_id = COALESCE(%s, team_id),
                    rotation_type = COALESCE(%s, rotation_type),
                    custom_interval_days = COALESCE(%s, custom_interval_days),
                    timezone = COALESCE(%s, timezone),
                    start_time = COALESCE(%s, start_time)
                WHERE id = %s;
            """, (name.strip() if name else None, team_id, rotation_type, custom_interval_days, tz, start_time_str, schedule_id))

            if participant_user_ids is not None and isinstance(participant_user_ids, list):
                cur.execute("DELETE FROM schedule_participants WHERE schedule_id = %s;", (schedule_id,))
                for pos, uid in enumerate(participant_user_ids):
                    cur.execute("""
                        INSERT INTO schedule_participants (schedule_id, user_id, position)
                        VALUES (%s, %s, %s);
                    """, (schedule_id, uid, pos))
        conn.close()
        return jsonify({"ok": True, "message": "Schedule updated"}), 200
    except Exception as e:
        logger.error("api_schedules_update error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
@_require_roles("admin", "manager")
def api_schedules_delete(schedule_id: int):
    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM schedules WHERE id = %s;", (schedule_id,))
            deleted = cur.rowcount
        conn.close()
        if deleted:
            return jsonify({"ok": True, "message": "Schedule deleted"}), 200
        return jsonify({"ok": False, "error": "Schedule not found"}), 404
    except Exception as e:
        logger.error("api_schedules_delete error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/schedules/<int:schedule_id>/oncall", methods=["GET"])
@_require_auth_api
def api_schedules_oncall(schedule_id: int):
    oncall = get_current_oncall(schedule_id)
    if not oncall:
        return jsonify({"ok": False, "error": "No on-call user configured or found"}), 404
    return jsonify({"ok": True, "oncall": oncall}), 200


@flask_app.route("/api/schedules/<int:schedule_id>/overrides", methods=["POST"])
@_require_roles("admin", "manager", "responder")
def api_schedules_add_override(schedule_id: int):
    data = request.get_json(silent=True) or {}
    override_user_id = data.get("override_user_id")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not override_user_id or not start_time or not end_time:
        return jsonify({"ok": False, "error": "override_user_id, start_time, and end_time are required"}), 400

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO schedule_overrides (schedule_id, override_user_id, start_time, end_time)
                VALUES (%s, %s, %s, %s);
            """, (schedule_id, override_user_id, start_time, end_time))
            override_id = cur.lastrowid
        conn.close()
        return jsonify({"ok": True, "override_id": override_id, "message": "Override created"}), 201
    except Exception as e:
        logger.error("api_schedules_add_override error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# ESCALATION POLICIES MANAGEMENT API
# ============================================================

@flask_app.route("/api/escalation-policies", methods=["GET"])
@_require_auth_api
def api_escalation_policies_list():
    if not dash_auth._ensure_db():
        return jsonify({"ok": True, "policies": []}), 200
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ep.id, ep.name, ep.service_id, s.name as service_name,
                       ep.team_id, t.name as team_name, ep.created_at
                FROM escalation_policies ep
                LEFT JOIN services s ON ep.service_id = s.id
                LEFT JOIN teams t ON ep.team_id = t.id
                ORDER BY ep.id ASC;
            """)
            policies = cur.fetchall()

            cur.execute("""
                SELECT eps.id, eps.policy_id, eps.step_order, eps.notify_type,
                       eps.schedule_id, sc.name as schedule_name,
                       eps.user_id, u.username, u.name as user_name, eps.delay_minutes
                FROM escalation_policy_steps eps
                LEFT JOIN schedules sc ON eps.schedule_id = sc.id
                LEFT JOIN dashboard_users u ON eps.user_id = u.id
                ORDER BY eps.step_order ASC;
            """)
            steps = cur.fetchall()
        conn.close()

        policy_steps_map: Dict[int, List[Dict[str, Any]]] = {}
        for step in steps:
            pid = step["policy_id"]
            policy_steps_map.setdefault(pid, []).append({
                "id": step["id"],
                "step_order": step["step_order"],
                "notify_type": step["notify_type"],
                "schedule_id": step["schedule_id"],
                "schedule_name": step.get("schedule_name") or "",
                "user_id": step["user_id"],
                "user_name": step.get("user_name") or step.get("username") or "",
                "delay_minutes": step["delay_minutes"]
            })

        result = []
        for p in policies:
            pid = p["id"]
            result.append({
                "id": pid,
                "name": p["name"],
                "service_id": p["service_id"],
                "service_name": p.get("service_name") or "Unassigned",
                "team_id": p["team_id"],
                "team_name": p.get("team_name") or "Unassigned",
                "steps": policy_steps_map.get(pid, []),
                "created_at": p["created_at"].isoformat() if p.get("created_at") else None
            })
        return jsonify({"ok": True, "policies": result}), 200
    except Exception as e:
        logger.error("api_escalation_policies_list error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/escalation-policies", methods=["POST"])
@_require_roles("admin", "manager")
def api_escalation_policies_create():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    service_id = data.get("service_id")
    team_id = data.get("team_id")
    steps = data.get("steps") or []

    if not name:
        return jsonify({"ok": False, "error": "Policy name is required"}), 400

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO escalation_policies (name, service_id, team_id)
                VALUES (%s, %s, %s);
            """, (name, service_id or None, team_id or None))
            policy_id = cur.lastrowid

            if steps and isinstance(steps, list):
                for st in steps:
                    cur.execute("""
                        INSERT INTO escalation_policy_steps (policy_id, step_order, notify_type, schedule_id, user_id, delay_minutes)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (
                        policy_id,
                        st.get("step_order", 1),
                        st.get("notify_type", "schedule"),
                        st.get("schedule_id"),
                        st.get("user_id"),
                        st.get("delay_minutes", 0)
                    ))
        conn.close()
        return jsonify({"ok": True, "policy_id": policy_id, "message": "Policy created"}), 201
    except Exception as e:
        logger.error("api_escalation_policies_create error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/escalation-policies/<int:policy_id>", methods=["PUT"])
@_require_roles("admin", "manager")
def api_escalation_policies_update(policy_id: int):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    service_id = data.get("service_id")
    team_id = data.get("team_id")
    steps = data.get("steps")

    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500

    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE escalation_policies
                SET name = COALESCE(%s, name),
                    service_id = %s,
                    team_id = %s
                WHERE id = %s;
            """, (name.strip() if name else None, service_id if service_id is not None else None, team_id if team_id is not None else None, policy_id))

            if steps is not None and isinstance(steps, list):
                cur.execute("DELETE FROM escalation_policy_steps WHERE policy_id = %s;", (policy_id,))
                for st in steps:
                    cur.execute("""
                        INSERT INTO escalation_policy_steps (policy_id, step_order, notify_type, schedule_id, user_id, delay_minutes)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (
                        policy_id,
                        st.get("step_order", 1),
                        st.get("notify_type", "schedule"),
                        st.get("schedule_id"),
                        st.get("user_id"),
                        st.get("delay_minutes", 0)
                    ))
        conn.close()
        return jsonify({"ok": True, "message": "Policy updated"}), 200
    except Exception as e:
        logger.error("api_escalation_policies_update error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@flask_app.route("/api/escalation-policies/<int:policy_id>", methods=["DELETE"])
@_require_roles("admin", "manager")
def api_escalation_policies_delete(policy_id: int):
    if not dash_auth._ensure_db():
        return jsonify({"ok": False, "error": "DB not available"}), 500
    try:
        conn = dash_auth._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM escalation_policies WHERE id = %s;", (policy_id,))
            deleted = cur.rowcount
        conn.close()
        if deleted:
            return jsonify({"ok": True, "message": "Policy deleted"}), 200
        return jsonify({"ok": False, "error": "Policy not found"}), 404
    except Exception as e:
        logger.error("api_escalation_policies_delete error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# MANUAL INCIDENT CREATION API
# ============================================================

@flask_app.route("/api/incidents/create", methods=["POST"])
@_require_roles("admin", "manager", "responder")
def api_incidents_create():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    service_id = data.get("service_id")
    urgency = (data.get("urgency") or "medium").lower()
    severity = (data.get("severity") or "warning").lower()
    server = (data.get("server") or "manual-trigger").strip()

    if not title:
        return jsonify({"ok": False, "error": "Incident title is required"}), 400

    creator_username = session.get("dash_user", "system")
    now_dt = datetime.now(timezone.utc)
    starts_at_str = format_display_time(now_dt)
    occ_id = f"manual_{int(now_dt.timestamp())}_{secrets.token_hex(4)}"
    fp = hashlib.md5(f"{title}_{occ_id}".encode()).hexdigest()[:16]

    alert_data = {
        "labels": {
            "alertname": title,
            "severity": severity,
            "instance": server,
            "source": "manual",
            "urgency": urgency
        },
        "annotations": {
            "summary": title,
            "description": description or f"Manually triggered incident by {creator_username}"
        },
        "startsAt": now_dt.isoformat(),
        "fingerprint": fp
    }

    # Save to state store
    store.save_or_append_notification(
        occurrence_id=occ_id,
        fingerprint=fp,
        starts_at=now_dt.isoformat(),
        channel_id=config.slack_channel,
        message_ts="",
        alert_data=alert_data
    )

    # If DB available, attach service_id, urgency, source, title, description
    if dash_auth._ensure_db():
        try:
            conn = dash_auth._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE acknowledgements
                    SET service_id = %s, urgency = %s, source = 'manual', title = %s, description = %s
                    WHERE occurrence_id = %s;
                """, (service_id or None, urgency, title, description, occ_id))
            conn.close()
        except Exception as e:
            logger.error("Error updating manual incident meta: %s", e)

    # Post firing notification to Slack if Slack is configured
    try:
        text, blocks = build_firing_blocks(alert_data, None, occ_id)
        resp = slack.chat_postMessage(channel=config.slack_channel, text=text, blocks=blocks)
        if resp and resp.get("ts"):
            store.save_or_append_notification(
                occurrence_id=occ_id,
                fingerprint=fp,
                starts_at=now_dt.isoformat(),
                channel_id=resp.get("channel", config.slack_channel),
                message_ts=resp["ts"],
                alert_data=alert_data
            )
    except Exception as e:
        logger.warning("Could not post manual incident to Slack: %s", e)

    logger.info("Manual incident created: occ_id=%s title='%s' by user=%s", occ_id, title, creator_username)
    return jsonify({
        "ok": True,
        "occurrence_id": occ_id,
        "message": "Incident created successfully"
    }), 201



# ============================================================
# FLASK HEALTH
# ============================================================

>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "unresolved_alerts": len(store.get_unresolved_active_alerts())
    }), 200
<<<<<<< HEAD
=======


# ============================================================
# DASHBOARD ROUTES & HELPERS
# ============================================================

@flask_app.after_request
def _dashboard_after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _parse_dash_iso(value: Any) -> Optional[datetime]:
    return parse_alert_time(value)


def _format_dash_duration(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _clean_user_name(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = str(val).strip()
    if "@" in val:
        val = val.split("@")[0]
    return val


def _serialise_dash_record(r: Dict[str, Any]) -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    action = r.get("action", "not_acknowledged")
    resolved_at = r.get("resolved_at")
    if resolved_at:
        status = "resolved"
    elif action == "accepted":
        status = "acknowledged"
    elif action == "paused":
        status = "snoozed"
    elif action == "rejected":
        status = "rejected"
    else:
        status = "firing"

    starts = _parse_dash_iso(r.get("starts_at") or r.get("created_at", ""))
    ends = _parse_dash_iso(resolved_at) if resolved_at else now_utc
    duration_secs = int((ends - starts).total_seconds()) if starts and ends else 0
    formatted_time = _format_dash_duration(max(0, duration_secs))
    sev = (r.get("severity") or "unknown").lower()

    return {
        "occurrence_id": r.get("occurrence_id", ""),
        "fingerprint": r.get("fingerprint", ""),
        "alert": r.get("alert", "Unknown"),
        "server": r.get("server", "Unknown"),
        "severity": sev,
        "status": status,
        "action": action,
        "assignee_name": _clean_user_name(r.get("assignee_name")),
        "assignee_id": r.get("assignee_id"),
        "user_name": _clean_user_name(r.get("user_name")),
        "user_id": r.get("user_id"),
        "starts_at": r.get("starts_at") or r.get("created_at", ""),
        "resolved_at": resolved_at,
        "updated_at": r.get("updated_at", ""),
        "downtime": formatted_time,
        "duration": formatted_time,
        "duration_seconds": max(0, duration_secs),
        "silence_ends_at": r.get("silence_ends_at"),
        "silence_label": r.get("silence_label"),
        "timeline": r.get("timeline", []),
        "notes": r.get("notes", []),
        "message_count": len(r.get("messages", [])),
        "alert_data": r.get("alert_data", {}),
    }


def _safe_int_param(val: Any, default: int) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


@flask_app.route("/", methods=["GET"])
@flask_app.route("/dashboard", methods=["GET"])
@flask_app.route("/dashboard/", methods=["GET"])
@flask_app.route("/dashboard.html", methods=["GET"])
@_require_auth
def dashboard_page():
    candidate_dirs = [
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
    ]
    for d in candidate_dirs:
        target = os.path.join(d, "dashboard.html")
        if os.path.isfile(target):
            return send_from_directory(d, "dashboard.html")
    return "<h1>dashboard.html not found</h1><p>Please place dashboard.html in the same directory as app.py</p>", 404


@flask_app.route("/api/stats", methods=["GET"])
@_require_auth_api
def dashboard_api_stats():
    records = store.get_all_records()
    total = len(records)
    active = [r for r in records if not r.get("resolved_at")]
    resolved = [r for r in records if r.get("resolved_at")]
    firing = [r for r in active if r.get("action") == "not_acknowledged"]
    acknowledged = [r for r in active if r.get("action") == "accepted"]
    snoozed = [r for r in active if r.get("action") == "paused"]
    rejected = [r for r in active if r.get("action") == "rejected"]
    critical = [r for r in active if (r.get("severity") or "").lower() in ("critical", "page", "fatal")]
    warning = [r for r in active if (r.get("severity") or "").lower() in ("warning", "warn")]

    now_utc = datetime.now(timezone.utc)
    mttr_list: List[float] = []
    for r in resolved:
        starts = _parse_dash_iso(r.get("starts_at") or r.get("created_at", ""))
        ends = _parse_dash_iso(r.get("resolved_at", ""))
        if starts and ends:
            diff = (ends - starts).total_seconds()
            if diff >= 0:
                mttr_list.append(diff)
    mttr_avg = int(sum(mttr_list) / len(mttr_list)) if mttr_list else 0

    oldest_active_secs = None
    for r in firing:
        starts = _parse_dash_iso(r.get("starts_at") or r.get("created_at", ""))
        if starts:
            secs = int((now_utc - starts).total_seconds())
            if oldest_active_secs is None or secs > oldest_active_secs:
                oldest_active_secs = secs

    return jsonify({
        "total": total,
        "active": len(active),
        "resolved": len(resolved),
        "firing": len(firing),
        "acknowledged": len(acknowledged),
        "snoozed": len(snoozed),
        "rejected": len(rejected),
        "critical": len(critical),
        "warning": len(warning),
        "mttr_avg_seconds": mttr_avg,
        "oldest_active_seconds": oldest_active_secs,
        "last_updated": now_utc.isoformat(),
    }), 200


@flask_app.route("/api/alerts", methods=["GET"])
@flask_app.route("/api/incidents", methods=["GET"])
@_require_auth_api
def dashboard_api_alerts():
    status = request.args.get("status", "all")
    severity = request.args.get("severity", "all")
    urgency = request.args.get("urgency", "all")
    service_id = request.args.get("service_id", "all")
    search = request.args.get("search", "").strip() or None
    sort_by = request.args.get("sort_by", "started").lower()
    sort_dir = request.args.get("sort_dir", "desc").lower()
    page = max(1, _safe_int_param(request.args.get("page"), 1))
    per_page = min(200, max(5, _safe_int_param(request.args.get("per_page"), 10)))

    records = store.get_all_records()

    if sort_by == "started":
        def _started_key(r: Dict[str, Any]):
            ts_str = r.get("starts_at") or r.get("created_at") or r.get("updated_at") or ""
            dt = _parse_dash_iso(ts_str)
            return dt.timestamp() if dt else 0.0
        records.sort(key=_started_key, reverse=(sort_dir != "asc"))
    else:
        def _default_sort_key(r: Dict[str, Any]):
            is_resolved = 1 if r.get("resolved_at") else 0
            ts_str = r.get("updated_at") or r.get("starts_at") or r.get("created_at") or ""
            dt = _parse_dash_iso(ts_str)
            ts = dt.timestamp() if dt else 0.0
            return (is_resolved, -ts)
        records.sort(key=_default_sort_key)

    if status and status != "all":
        if status == "active":
            records = [r for r in records if not r.get("resolved_at")]
        elif status == "resolved":
            records = [r for r in records if r.get("resolved_at")]
        elif status == "firing":
            records = [r for r in records if not r.get("resolved_at") and r.get("action") == "not_acknowledged"]
        elif status == "acknowledged":
            records = [r for r in records if not r.get("resolved_at") and r.get("action") == "accepted"]
        elif status == "snoozed":
            records = [r for r in records if not r.get("resolved_at") and r.get("action") == "paused"]
        elif status == "rejected":
            records = [r for r in records if not r.get("resolved_at") and r.get("action") == "rejected"]

    if severity and severity != "all":
        if severity == "critical":
            records = [r for r in records if (r.get("severity") or "").lower() in ("critical", "page", "fatal")]
        elif severity == "warning":
            records = [r for r in records if (r.get("severity") or "").lower() in ("warning", "warn")]
        elif severity == "info":
            records = [r for r in records if (r.get("severity") or "").lower() not in ("critical", "page", "fatal", "warning", "warn")]

    if urgency and urgency != "all":
        records = [r for r in records if (r.get("urgency") or "medium").lower() == urgency.lower()]

    if service_id and service_id != "all":
        try:
            svc_id_num = int(service_id)
            records = [r for r in records if r.get("service_id") == svc_id_num]
        except (ValueError, TypeError):
            pass

    if search:
        q = search.lower()
        records = [
            r for r in records
            if q in (r.get("alert") or "").lower()
            or q in (r.get("server") or "").lower()
            or q in (r.get("severity") or "").lower()
            or q in (r.get("assignee_name") or "").lower()
            or q in (r.get("fingerprint") or "").lower()
            or q in (r.get("occurrence_id") or "").lower()
            or q in (r.get("title") or "").lower()
        ]

    total_count = len(records)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total_count + per_page - 1) // per_page),
        "records": [_serialise_dash_record(r) for r in records[start:end]],
    }), 200



@flask_app.route("/api/alerts/<path:occurrence_id>", methods=["GET"])
@_require_auth_api
def dashboard_api_alert_detail(occurrence_id: str):
    rec = store.get(occurrence_id)
    if not rec:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_serialise_dash_record(rec)), 200


@flask_app.route("/api/alerts/<path:occurrence_id>/ack", methods=["POST"])
@_require_roles("admin", "manager", "responder")
def api_alert_ack(occurrence_id: str):
    rec = store.get(occurrence_id)
    if not rec:
        return jsonify({"ok": False, "error": "Incident not found"}), 404

    user = session.get("dash_user", "admin")
    now_str = format_display_time(datetime.now(timezone.utc))

    updated = store.update_action(
        occurrence_id=occurrence_id,
        action="accepted",
        user_id=user,
        user_name=user,
        action_at=now_str,
        timeline_entry=f"✅ Acknowledged in dashboard by {user}"
    )

    if not updated:
        return jsonify({"ok": False, "error": "Could not update incident"}), 500

    # Sync to Slack if active messages exist
    try:
        if rec.get("messages") and slack:
            for msg in rec.get("messages", []):
                ch = msg.get("channel_id")
                ts = msg.get("message_ts")
                if ch and ts:
                    text, blocks = build_firing_blocks(
                        rec.get("alert_data", {}),
                        updated,
                        occurrence_id
                    )
                    slack.chat_update(channel=ch, ts=ts, text=text, blocks=blocks)
    except Exception as e:
        logger.warning("Could not sync web ack to Slack: %s", e)

    return jsonify({"ok": True, "message": "Incident acknowledged", "record": _serialise_dash_record(updated)}), 200


@flask_app.route("/api/alerts/<path:occurrence_id>/snooze", methods=["POST"])
@_require_roles("admin", "manager", "responder")
def api_alert_snooze(occurrence_id: str):
    rec = store.get(occurrence_id)
    if not rec:
        return jsonify({"ok": False, "error": "Incident not found"}), 404

    data = request.get_json(silent=True) or {}
    minutes = int(data.get("minutes", 30))
    user = session.get("dash_user", "admin")
    now_utc = datetime.now(timezone.utc)
    now_str = format_display_time(now_utc)
    ends_at = now_utc + timedelta(minutes=minutes)

    silence_id = None
    try:
        silence_id = am_client.create_silence(
            labels=(rec.get("alert_data") or {}).get("labels", {}),
            author=user,
            ends_at=ends_at,
            comment=f"Snoozed for {minutes}m via Dashboard by {user}"
        )
    except Exception as e:
        logger.warning("Could not create Alertmanager silence: %s", e)

    snooze_label = f"{minutes}m" if minutes < 60 else f"{minutes//60}h"
    updated = store.update_action(
        occurrence_id=occurrence_id,
        action="paused",
        user_id=user,
        user_name=user,
        action_at=now_str,
        silence_id=silence_id,
        silence_ends_at=ends_at.isoformat(),
        silence_label=snooze_label,
        timeline_entry=f"⏸️ Snoozed for {snooze_label} in dashboard by {user}"
    )

    if not updated:
        return jsonify({"ok": False, "error": "Could not snooze incident"}), 500

    try:
        if rec.get("messages") and slack:
            for msg in rec.get("messages", []):
                ch = msg.get("channel_id")
                ts = msg.get("message_ts")
                if ch and ts:
                    text, blocks = build_firing_blocks(
                        rec.get("alert_data", {}),
                        updated,
                        occurrence_id
                    )
                    slack.chat_update(channel=ch, ts=ts, text=text, blocks=blocks)
    except Exception as e:
        logger.warning("Could not sync web snooze to Slack: %s", e)

    return jsonify({"ok": True, "message": f"Incident snoozed for {snooze_label}", "record": _serialise_dash_record(updated)}), 200


@flask_app.route("/api/alerts/<path:occurrence_id>/resolve", methods=["POST"])
@_require_roles("admin", "manager", "responder")
def api_alert_resolve(occurrence_id: str):
    rec = store.get(occurrence_id)
    if not rec:
        return jsonify({"ok": False, "error": "Incident not found"}), 404

    user = session.get("dash_user", "admin")
    handle_alert_resolution(
        alert=rec.get("alert_data", {}),
        occurrence_id=occurrence_id,
        resolved_by_override=f"{user} (Dashboard)"
    )

    updated = store.get(occurrence_id)
    return jsonify({
        "ok": True,
        "message": "Incident marked as resolved",
        "record": _serialise_dash_record(updated) if updated else None
    }), 200


@flask_app.route("/api/alerts/<path:occurrence_id>/reject", methods=["POST"])
@_require_roles("admin", "manager", "responder")
def api_alert_reject(occurrence_id: str):
    rec = store.get(occurrence_id)
    if not rec:
        return jsonify({"ok": False, "error": "Incident not found"}), 404

    user = session.get("dash_user", "admin")
    now_str = format_display_time(datetime.now(timezone.utc))

    updated = store.update_action(
        occurrence_id=occurrence_id,
        action="rejected",
        user_id=user,
        user_name=user,
        action_at=now_str,
        timeline_entry=f"\u26a0\ufe0f Rejected in dashboard by {user}"
    )
>>>>>>> 381d0a9 (update the alert-action dashboard add more features)

    if not updated:
        return jsonify({"ok": False, "error": "Could not reject incident"}), 500

    return jsonify({"ok": True, "message": "Incident rejected", "record": _serialise_dash_record(updated)}), 200


# ============================================================
# ALERTMANAGER WEBHOOK
# ============================================================

@flask_app.route("/alertmanager", methods=["POST"])
def alertmanager_webhook():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"ok": False, "error": "Empty body"}), 400

    status = payload.get("status", "firing")
    alerts = payload.get("alerts", [])
    processed = 0

    for alert in alerts:
        fp = alert.get("fingerprint")
        starts_at = alert.get("startsAt")
        if not fp:
            continue

        occurrence_id = build_occurrence_id(fp, starts_at)
        existing = store.get(occurrence_id)

        # ====================================================
        # FIRING
        # ====================================================
        if status == "firing":
            # If already acknowledged or snoozed, suppress duplicate spam
            if (
                existing
                and existing.get("action") in ("accepted", "paused")
                and not existing.get("resolved_at")
            ):
                logger.debug(
                    "Occurrence %s is %s; suppressing duplicate firing webhook.",
                    occurrence_id,
                    existing.get("action")
                )
                continue

            # If existing was rejected, treat new firing as re-notification with full buttons
            ack_for_build = existing
            if (
                existing
                and existing.get("action") == "rejected"
                and not existing.get("resolved_at")
            ):
                ack_for_build = None

            text, blocks = build_firing_blocks(
                alert,
                ack_for_build,
                occurrence_id
            )

            try:
                resp = slack.chat_postMessage(
                    channel=config.slack_channel,
                    text=text,
                    blocks=blocks
                )

                store.save_or_append_notification(
                    occurrence_id=occurrence_id,
                    fingerprint=fp,
                    starts_at=starts_at,
                    channel_id=resp.get("channel", config.slack_channel),
                    message_ts=resp["ts"],
                    alert_data=alert
                )

                processed += 1
            except SlackApiError as e:
                logger.error(
                    "Failed to post firing alert to Slack: %s",
                    e.response.get("error")
                )
            except Exception as e:
                logger.error("Failed to post firing alert to Slack: %s", e)

        # ====================================================
        # RESOLVED
        # ====================================================
        elif status == "resolved":
            target_occ_id = occurrence_id if existing else None
            if not target_occ_id:
                active_match = store.get_latest_active_by_fingerprint(fp)
                if active_match:
                    target_occ_id = active_match.get("occurrence_id")

            if handle_alert_resolution(alert, occurrence_id=target_occ_id):
                processed += 1

    return jsonify({"ok": True, "processed": processed}), 200


# ============================================================
# SOCKET MODE
# ============================================================

def run_socket_mode(handler: SocketModeHandler):
    try:
        handler.start()
    except Exception as e:
        logger.exception("Socket mode error: %s", e)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    logger.info("Starting Promax Incident Management Bot...")
    logger.info("Log file: %s", config.log_file)
<<<<<<< HEAD
    logger.info("State file: %s", config.ack_state_file)

    socket_handler = None

=======
    if isinstance(store, MariaDBStateStore):
        logger.info("Active Storage Backend: MariaDB Database (Host: %s, Database: %s)", config.db_host, config.db_name)
    else:
        logger.info("Active Storage Backend: JSON State File (%s)", config.ack_state_file)

    # Ensure DB-backed auth manager is connected
    dash_auth._ensure_db()
    logger.info("DashAuthManager initialised (db_available=%s)", dash_auth._db_available)

    socket_handler = None

>>>>>>> 381d0a9 (update the alert-action dashboard add more features)
    if config.slack_app_token:
        try:
            socket_handler = SocketModeHandler(bolt_app, config.slack_app_token)
            t_socket = threading.Thread(
                target=run_socket_mode,
                args=(socket_handler,),
                daemon=True
            )
            t_socket.start()
        except Exception as e:
            logger.warning("Could not start Socket Mode handler: %s", e)

    t_monitor = threading.Thread(
        target=resolved_alert_monitor_loop,
        daemon=True
    )
    t_monitor.start()

    def handle_sigterm(signum, frame):
        logger.info("Shutting down cleanly...")
        shutdown_event.set()
        if socket_handler:
            socket_handler.close()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    port = int(os.environ.get("PORT", "5000"))
    flask_app.run(
        host="0.0.0.0",
        port=port,
        threaded=True
    )
