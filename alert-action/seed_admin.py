#!/usr/bin/env python3
"""
Seed or reset dashboard admin user in MariaDB.
Usage:
    python seed_admin.py [--username admin] [--password admin123] [--role admin]
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

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt is required. Run: pip install bcrypt")
    sys.exit(1)


TABLE_DDL = """
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
"""


def main():
    parser = argparse.ArgumentParser(description="Seed or reset a dashboard user.")
    parser.add_argument("--username", default=os.environ.get("DASH_DEFAULT_USER", "admin"), help="Username (default: admin)")
    parser.add_argument("--password", default=os.environ.get("DASH_DEFAULT_PASSWORD", "admin123"), help="Password (default: admin123)")
    parser.add_argument("--role", default="admin", choices=["admin", "manager", "responder", "viewer"], help="Role (default: admin)")
    parser.add_argument("--db-host", default=os.environ.get("DB_HOST", "mariadb"), help="DB host (default: mariadb or from DB_HOST)")
    parser.add_argument("--db-port", type=int, default=int(os.environ.get("DB_PORT", "3306")), help="DB port (default: 3306)")
    parser.add_argument("--db-user", default=os.environ.get("DB_USER", "proxmox_user"), help="DB user")
    parser.add_argument("--db-password", default=os.environ.get("DB_PASSWORD", "tbcadmin123@"), help="DB password")
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", "proxmox_alerts"), help="DB name")
    args = parser.parse_args()

    username = args.username.strip().lower()
    password = args.password
    role = args.role

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters long.")
        sys.exit(1)

    print(f"[*] Connecting to MariaDB at {args.db_host}:{args.db_port}/{args.db_name} as '{args.db_user}'...")
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
        print("    Tip: If running outside Docker, try --db-host 127.0.0.1")
        sys.exit(1)

    with conn.cursor() as cur:
        # 1. Ensure table exists
        cur.execute(TABLE_DDL)

        # 2. Hash password with bcrypt
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

        # 3. Insert or update user
        sql = """
        INSERT INTO dashboard_users (username, password_hash, role, is_active, failed_attempts, locked_until)
        VALUES (%s, %s, %s, 1, 0, NULL)
        ON DUPLICATE KEY UPDATE
            password_hash = VALUES(password_hash),
            role = VALUES(role),
            is_active = 1,
            failed_attempts = 0,
            locked_until = NULL;
        """
        cur.execute(sql, (username, hashed, role))

    conn.close()
    print(f"[+] Successfully seeded user '{username}' (role: {role}) with bcrypt password hash!")
    print(f"    Password: {password}")
    print("[!] Remember to change default credentials in production.")


if __name__ == "__main__":
    main()
