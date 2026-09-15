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

from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


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
        val_str = str(value).strip()
        if val_str.startswith("0001-01-01"):
            return None

        if val_str.endswith("Z"):
            val_str = val_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(val_str)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc)
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
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
                with open(self.filepath, "r", encoding="utf-8") as f:
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


store = JsonStateStore(
    config.ack_state_file,
    retention_days=config.retention_days
)


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
# FLASK HEALTH
# ============================================================

@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "unresolved_alerts": len(store.get_unresolved_active_alerts())
    }), 200


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
    logger.info("State file: %s", config.ack_state_file)

    socket_handler = None

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
