#!/usr/bin/env python3
"""
Migrate acknowledgements.json data into MariaDB.
Usage:
    python migrate_json_to_db.py [/path/to/acknowledgements.json]
"""
import os
import sys
import json
import pymysql

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "promax_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "promax_secure_pass")
DB_NAME = os.environ.get("DB_NAME", "promax_alerts")

def migrate():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "/var/lib/alert-action/acknowledgements.json"
    if not os.path.exists(json_path):
        # Check current dir fallback
        if os.path.exists("acknowledgements.json"):
            json_path = "acknowledgements.json"
        else:
            print(f"[ERROR] File not found: {json_path}")
            sys.exit(1)

    print(f"[*] Reading JSON file: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Connecting to MariaDB at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=True
    )

    insert_sql = """
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
    )
    ON DUPLICATE KEY UPDATE
        action = VALUES(action),
        assignee_id = VALUES(assignee_id),
        assignee_name = VALUES(assignee_name),
        user_id = VALUES(user_id),
        user_name = VALUES(user_name),
        resolved_at = VALUES(resolved_at),
        record_data = VALUES(record_data),
        updated_at = CURRENT_TIMESTAMP
    """

    count = 0
    with conn.cursor() as cursor:
        for occ_id, item in data.items():
            labels = (item.get("alert_data") or {}).get("labels") or {}
            alert_name = item.get("alert") or labels.get("alertname") or "Unknown"
            server = item.get("server") or labels.get("instance") or ""
            severity = item.get("severity") or labels.get("severity") or "info"

            cursor.execute(insert_sql, (
                str(occ_id),
                str(item.get("fingerprint") or occ_id),
                str(alert_name),
                str(server),
                str(severity),
                str(item.get("action") or "not_acknowledged"),
                str(item.get("assignee_id") or ""),
                str(item.get("assignee_name") or ""),
                str(item.get("user_id") or ""),
                str(item.get("user_name") or ""),
                str(item.get("channel_id") or ""),
                str(item.get("message_ts") or ""),
                str(item.get("starts_at") or (item.get("alert_data") or {}).get("startsAt") or ""),
                str(item.get("ends_at") or (item.get("alert_data") or {}).get("endsAt") or ""),
                str(item.get("resolved_at") or ""),
                str(item.get("silence_id") or ""),
                json.dumps(item, ensure_ascii=False),
            ))
            count += 1

    conn.close()
    print(f"[SUCCESS] Migrated {count} records into MariaDB 'acknowledgements' table successfully!")

if __name__ == "__main__":
    migrate()
