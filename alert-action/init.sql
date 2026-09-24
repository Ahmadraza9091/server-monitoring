-- Create database if not exists
CREATE DATABASE IF NOT EXISTS proxmox_alerts CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE proxmox_alerts;

-- Dashboard users table for web UI authentication
CREATE TABLE IF NOT EXISTS dashboard_users (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    email VARCHAR(255) NULL,
    phone VARCHAR(32) NULL,
    name VARCHAR(128) NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'viewer',   -- 'admin' | 'manager' | 'responder' | 'viewer'
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    last_login TIMESTAMP NULL DEFAULT NULL,
    failed_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_username (username),
    UNIQUE KEY uq_email (email),
    INDEX idx_is_active (is_active),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_team_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Team Members join table
CREATE TABLE IF NOT EXISTS team_members (
    team_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, user_id),
    CONSTRAINT fk_tm_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT fk_tm_user FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Services table
CREATE TABLE IF NOT EXISTS services (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    team_id INT UNSIGNED NULL,
    description TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_services_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Schedules table for On-Call rotations
CREATE TABLE IF NOT EXISTS schedules (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    team_id INT UNSIGNED NULL,
    rotation_type VARCHAR(32) NOT NULL DEFAULT 'daily', -- 'daily', 'weekly', 'custom'
    custom_interval_days INT UNSIGNED NOT NULL DEFAULT 1,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_schedules_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Schedule Participants table
CREATE TABLE IF NOT EXISTS schedule_participants (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    schedule_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    position INT UNSIGNED NOT NULL DEFAULT 0,
    CONSTRAINT fk_sp_schedule FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
    CONSTRAINT fk_sp_user FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_schedule_position (schedule_id, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Schedule Overrides table
CREATE TABLE IF NOT EXISTS schedule_overrides (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    schedule_id INT UNSIGNED NOT NULL,
    override_user_id INT UNSIGNED NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_so_schedule FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
    CONSTRAINT fk_so_user FOREIGN KEY (override_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Escalation Policies table
CREATE TABLE IF NOT EXISTS escalation_policies (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    service_id INT UNSIGNED NULL,
    team_id INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ep_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL,
    CONSTRAINT fk_ep_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Escalation Policy Steps table
CREATE TABLE IF NOT EXISTS escalation_policy_steps (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    policy_id INT UNSIGNED NOT NULL,
    step_order INT UNSIGNED NOT NULL DEFAULT 1,
    notify_type VARCHAR(32) NOT NULL DEFAULT 'schedule', -- 'schedule' or 'user'
    schedule_id INT UNSIGNED NULL,
    user_id INT UNSIGNED NULL,
    delay_minutes INT UNSIGNED NOT NULL DEFAULT 0,
    CONSTRAINT fk_eps_policy FOREIGN KEY (policy_id) REFERENCES escalation_policies(id) ON DELETE CASCADE,
    CONSTRAINT fk_eps_schedule FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
    CONSTRAINT fk_eps_user FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Acknowledgements table storing alert incidents and actions
CREATE TABLE IF NOT EXISTS acknowledgements (
    occurrence_id VARCHAR(128) NOT NULL PRIMARY KEY,
    fingerprint VARCHAR(64) NOT NULL,
    alert_name VARCHAR(128) NOT NULL,
    server VARCHAR(128) DEFAULT '',
    severity VARCHAR(32) DEFAULT 'info',
    urgency VARCHAR(32) DEFAULT 'medium',
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
    service_id INT UNSIGNED NULL,
    source VARCHAR(32) DEFAULT 'alertmanager',
    created_by INT UNSIGNED NULL,
    title VARCHAR(255) NULL,
    description TEXT NULL,
    record_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fingerprint (fingerprint),
    INDEX idx_alert_name (alert_name),
    INDEX idx_server (server),
    INDEX idx_severity (severity),
    INDEX idx_action (action),
    INDEX idx_updated_at (updated_at),
    INDEX idx_service_id (service_id),
    CONSTRAINT fk_ack_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL,
    CONSTRAINT fk_ack_creator FOREIGN KEY (created_by) REFERENCES dashboard_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
