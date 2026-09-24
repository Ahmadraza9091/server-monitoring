#!/usr/bin/env python3
"""
Schema migration script for Promax Incident Management.
Safely applies all schema changes needed for:
  - Extended user fields (email, phone, name, expanded roles)
  - Teams & team membership
  - Services & escalation policies
  - On-call schedules, participants, overrides
  - Incident enhancements (service_id, urgency, source, created_by, title, description)

This script is idempotent — safe to run multiple times.

Usage:
    python migrate_schema.py [--db-host HOST] [--db-port PORT] ...
"""

import os
import sys
import argparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("ERROR: pymysql is required. Run: pip install pymysql")
    sys.exit(1)


def _col_exists(cur, table, column):
    """Check if a column exists in a table."""
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s;",
        (table, column)
    )
    return cur.fetchone()["cnt"] > 0


def _table_exists(cur, table):
    """Check if a table exists."""
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s;",
        (table,)
    )
    return cur.fetchone()["cnt"] > 0


def migrate(cur):
    """Apply all schema migrations."""

    # ================================================================
    # 1. Extend dashboard_users table
    # ================================================================
    print("[1/10] Extending dashboard_users...")

    if not _col_exists(cur, "dashboard_users", "email"):
        cur.execute(
            "ALTER TABLE dashboard_users ADD COLUMN email VARCHAR(255) NULL AFTER username;"
        )
        cur.execute(
            "ALTER TABLE dashboard_users ADD UNIQUE KEY uq_email (email);"
        )
        print("  + Added email column")

    if not _col_exists(cur, "dashboard_users", "name"):
        cur.execute(
            "ALTER TABLE dashboard_users ADD COLUMN name VARCHAR(128) NULL AFTER username;"
        )
        print("  + Added name column")

    if not _col_exists(cur, "dashboard_users", "phone"):
        cur.execute(
            "ALTER TABLE dashboard_users ADD COLUMN phone VARCHAR(32) NULL AFTER email;"
        )
        print("  + Added phone column")

    # Expand role column to support new roles
    cur.execute(
        "ALTER TABLE dashboard_users MODIFY COLUMN role VARCHAR(32) NOT NULL DEFAULT 'viewer';"
    )
    print("  + Ensured role column supports all role values")

    # ================================================================
    # 2. Create teams table
    # ================================================================
    print("[2/10] Creating teams table...")
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
    print("  + teams table ready")

    # ================================================================
    # 3. Create team_members join table
    # ================================================================
    print("[3/10] Creating team_members table...")
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
    print("  + team_members table ready")

    # ================================================================
    # 4. Create services table
    # ================================================================
    print("[4/10] Creating services table...")
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
    print("  + services table ready")

    # ================================================================
    # 5. Create escalation_policies table
    # ================================================================
    print("[5/10] Creating escalation_policies table...")
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
    print("  + escalation_policies table ready")

    # ================================================================
    # 6. Create escalation_policy_steps table
    # ================================================================
    print("[6/10] Creating escalation_policy_steps table...")
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
    print("  + escalation_policy_steps table ready")

    # ================================================================
    # 7. Create schedules table
    # ================================================================
    print("[7/10] Creating schedules table...")
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
    print("  + schedules table ready")

    # Now add FK for escalation_policy_steps -> schedules
    # (schedule table must exist first)
    try:
        cur.execute("""
            ALTER TABLE escalation_policy_steps
            ADD CONSTRAINT fk_eps_schedule FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE SET NULL;
        """)
    except Exception:
        pass  # FK may already exist

    try:
        cur.execute("""
            ALTER TABLE escalation_policy_steps
            ADD CONSTRAINT fk_eps_user FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE SET NULL;
        """)
    except Exception:
        pass

    # ================================================================
    # 8. Create schedule_participants table
    # ================================================================
    print("[8/10] Creating schedule_participants table...")
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
    print("  + schedule_participants table ready")

    # ================================================================
    # 9. Create schedule_overrides table
    # ================================================================
    print("[9/10] Creating schedule_overrides table...")
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
    print("  + schedule_overrides table ready")

    # ================================================================
    # 10. Extend acknowledgements table for manual incidents
    # ================================================================
    print("[10/10] Extending acknowledgements table...")

    if not _col_exists(cur, "acknowledgements", "service_id"):
        cur.execute(
            "ALTER TABLE acknowledgements ADD COLUMN service_id INT UNSIGNED NULL AFTER record_data;"
        )
        print("  + Added service_id column")

    if not _col_exists(cur, "acknowledgements", "urgency"):
        cur.execute(
            "ALTER TABLE acknowledgements ADD COLUMN urgency VARCHAR(16) NOT NULL DEFAULT 'medium' AFTER service_id;"
        )
        print("  + Added urgency column")

    if not _col_exists(cur, "acknowledgements", "source"):
        cur.execute(
            "ALTER TABLE acknowledgements ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'alertmanager' AFTER urgency;"
        )
        print("  + Added source column")

    if not _col_exists(cur, "acknowledgements", "created_by"):
        cur.execute(
            "ALTER TABLE acknowledgements ADD COLUMN created_by INT UNSIGNED NULL AFTER source;"
        )
        print("  + Added created_by column")

    if not _col_exists(cur, "acknowledgements", "title"):
        cur.execute(
            "ALTER TABLE acknowledgements ADD COLUMN title VARCHAR(255) NULL AFTER created_by;"
        )
        print("  + Added title column")

    if not _col_exists(cur, "acknowledgements", "description"):
        cur.execute(
            "ALTER TABLE acknowledgements ADD COLUMN description TEXT NULL AFTER title;"
        )
        print("  + Added description column")

    # Add indexes for new columns
    try:
        cur.execute("CREATE INDEX idx_source ON acknowledgements (source);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX idx_urgency ON acknowledgements (urgency);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX idx_service_id ON acknowledgements (service_id);")
    except Exception:
        pass

    print("\n[✓] All migrations completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Apply Promax schema migrations.")
    parser.add_argument("--db-host", default=os.environ.get("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.environ.get("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.environ.get("DB_USER", "proxmox_user"))
    parser.add_argument("--db-password", default=os.environ.get("DB_PASSWORD", "tbcadmin123@"))
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", "proxmox_alerts"))
    args = parser.parse_args()

    print(f"[*] Connecting to MariaDB at {args.db_host}:{args.db_port}/{args.db_name}...")
    try:
        conn = pymysql.connect(
            host=args.db_host,
            port=args.db_port,
            user=args.db_user,
            password=args.db_password,
            database=args.db_name,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        sys.exit(1)

    with conn.cursor() as cur:
        migrate(cur)

    conn.close()
    print("[✓] Migration complete. You may now start the application.")


if __name__ == "__main__":
    main()
