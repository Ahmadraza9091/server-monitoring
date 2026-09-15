# Promax Production Monitoring System

[![Status](https://img.shields.io/badge/status-production-green?style=for-the-badge)](https://github.com)
[![License](https://img.shields.io/badge/license-proprietary-blue?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux-orange?style=for-the-badge)](https://www.linux.org)
[![Docker](https://img.shields.io/badge/docker-enabled-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com)

A **production-grade, centralized monitoring and alerting platform** for Promax on-premises servers with real-time dashboards, intelligent alerting, and interactive incident management via Slack.

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Deployment](#deployment) • [Troubleshooting](#troubleshooting)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Components](#components)
- [Complete Workflow](#complete-workflow)
- [System Diagrams (DFD / ERD / Use Case)](#system-diagrams-dfd--erd--use-case)
- [Deployment Guide](#deployment-guide)
- [Configuration](#configuration)
- [Monitoring & Dashboards](#monitoring--dashboards)
- [Alert Management](#alert-management)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Quick Reference](#quick-reference)

---

## 📌 Overview

> **Purpose:** A production-style, centralized monitoring and alerting platform for Promax/on-premises servers.
>
> This document is written so that a **new engineer can understand the system from zero**, deploy it, test it, and troubleshoot it **without needing to know the original implementation history**.

The Promax Monitoring System continuously watches:
- 🖥️ Servers
- 🐳 Containers & applications  
- 💾 Databases & system resources
- 📝 Logs & events

When something goes wrong, the system automatically detects, alerts, and enables engineers to manage incidents directly from Slack.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **🔍 Real-time Monitoring** | Continuous collection of metrics, logs, and system telemetry |
| **📊 Rich Dashboards** | Pre-built Grafana dashboards for servers, containers, databases, and applications |
| **🚨 Intelligent Alerting** | Rule-based alert evaluation with configurable thresholds and routing |
| **🎯 Interactive Incidents** | Acknowledge, assign, pause, or resolve alerts directly from Slack |
| **📱 Slack Integration** | Native Slack workflow with buttons, notes, and incident tracking |
| **🤖 Automated Actions** | Convert alert signals into actionable Slack notifications |
| **🔐 Enterprise Security** | Role-based access, token protection, and audit-ready logs |
| **⚙️ Infrastructure as Code** | Ansible-driven deployment for consistency and repeatability |

---

## 📐 System Architecture

```
                         ┌─────────────────────────┐
                         │   Promax Servers        │
                         │                         │
                         │ Metrics + Logs          │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │   Grafana Alloy         │
                         │  (Collection Agent)     │
                         └────────────┬────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
           ┌──────────────────────┐    ┌──────────────────────┐
           │    Prometheus        │    │       Loki           │
           │    Metrics Store     │    │    Log Storage       │
           │    Alert Evaluator   │    │                      │
           └──────────┬───────────┘    └──────────┬───────────┘
                      │                           │
                      └────────────┬──────────────┘
                                   ▼
                        ┌──────────────────────┐
                        │      Grafana         │
                        │    Dashboards        │
                        └──────────────────────┘

                   ALERT FLOW (Detection → Action)

                      Prometheus
                           │
                           ▼
                      Alertmanager
                           │
                           ▼
                  Alert Action Service
                           │
                           ▼
                         Slack
                  ┌────────┼────────┐
                  ▼        ▼        ▼
            Engineer   Actions   Resolution
```

### 🖼️ Visual System Diagram (AWS Servers → Monitoring Stack → Slack)

```mermaid
flowchart TB
    subgraph AWS["☁️ AWS Production Servers"]
        direction LR
        S1["🖥️ EC2 Server 1<br/>Grafana Alloy Agent"]
        S2["🖥️ EC2 Server 2<br/>Grafana Alloy Agent"]
        S3["🖥️ EC2 Server 3<br/>Grafana Alloy Agent"]
    end

    subgraph MON["🖥️ Monitoring Server (On-Prem / EC2)"]
        direction TB
        PROM["⚙️ Prometheus<br/>Metrics Store + Alert Evaluator<br/>:9090"]
        LOKI["📝 Loki<br/>Log Storage<br/>:3100"]
        GRAF["📊 Grafana<br/>Dashboards<br/>:3000"]
        AM["🚨 Alertmanager<br/>Routing & Grouping<br/>:9093"]
        AAS["🤖 Alert Action Service<br/>Flask Webhook Handler<br/>:5000"]
        STATE[("Alert State<br/>JSON File")]
    end

    subgraph SLACKBOX["💬 Slack"]
        direction TB
        MSG["Incident Message<br/>+ Action Buttons"]
        RESMSG["✅ Resolved<br/>Notification"]
    end

    ENG(["🧑‍💻 On-Call Engineer"])

    %% Metrics/logs flow
    S1 -- "metrics (remote_write)" --> PROM
    S2 -- "metrics (remote_write)" --> PROM
    S3 -- "metrics (remote_write)" --> PROM
    S1 -- "logs" --> LOKI
    S2 -- "logs" --> LOKI
    S3 -- "logs" --> LOKI

    %% Grafana reads
    PROM -- "query" --> GRAF
    LOKI -- "query" --> GRAF
    GRAF -- "dashboards / drill-down" --> ENG

    %% Alert flow
    PROM -- "evaluate rules<br/>fire alert (severity)" --> AM
    AM -- "webhook POST /alertmanager" --> AAS
    AAS -- "read/write" --> STATE
    AAS -- "post enriched message" --> MSG
    MSG --> ENG
    ENG -- "Ack / Assign / Note /<br/>Pause / Reject / Resolve" --> MSG
    MSG -- "action payload" --> AAS

    %% Resolution flow
    PROM -- "condition clears<br/>send RESOLVED" --> AM
    AM -- "resolved webhook" --> AAS
    AAS -- "separate message<br/>(original not edited)" --> RESMSG
    RESMSG --> ENG

    classDef aws fill:#FF9900,stroke:#232F3E,color:#232F3E
    classDef mon fill:#1f77b4,stroke:#0d3a5c,color:#fff
    classDef slack fill:#4A154B,stroke:#2c0e2d,color:#fff
    class S1,S2,S3 aws
    class PROM,LOKI,GRAF,AM,AAS,STATE mon
    class MSG,RESMSG slack
```

### Monitoring Flow Overview

```
Production Servers
       ↓ (Metrics + Logs)
Grafana Alloy
       ├──→ Prometheus (Metrics)
       └──→ Loki (Logs)
           ↓
       Grafana (UI)

Alert Path:
Prometheus → Alertmanager → Alert Action Service → Slack → Engineer Actions
```

---

## 🏗️ Components

| Component | Purpose | Port | Runs On |
|-----------|---------|------|---------|
| **Grafana Alloy** | Collects metrics and logs from monitored servers | `12345` | Monitored servers |
| **Prometheus** | Stores and evaluates metrics; fires alerts | `9090` | Monitoring server |
| **Loki** | Centralizes and stores logs | `3100` | Monitoring server |
| **Grafana** | Web dashboards and visualizations | `3000` | Monitoring server |
| **Alertmanager** | Groups, routes, fires, and resolves alerts | `9093` | Monitoring server |
| **Alert Action Service** | Converts alerts into interactive Slack workflows | `5000` | Monitoring server |
| **Slack** | Incident notification and operator interaction | N/A | Cloud |
| **Ansible** | Installs and configures Alloy on servers | N/A | Admin machine |

---

## 🔄 Complete Monitoring Workflow

### **Step 1: Server Produces Telemetry**

Production servers generate metrics and logs:

```
CPU = 96%
Memory = 82%  
Disk = 91%
Network Traffic = 850 Mbps
```

### **Step 2: Alloy Collects Data**

Grafana Alloy runs on each server and collects:

```
Linux Server
     ├─→ CPU/Memory/Disk metrics → Alloy
     ├─→ Docker container metrics → Alloy
     ├─→ Application metrics → Alloy
     └─→ System logs → Alloy
```

### **Step 3: Data Reaches Monitoring Server**

Metrics are sent to Prometheus and logs to Loki via remote_write:

```
Alloy → Prometheus (metrics)
Alloy → Loki (logs)
```

### **Step 4: Grafana Visualizes Data**

Grafana reads both datasources and displays dashboards:

```
Prometheus ┐
           ├─→ Grafana Dashboard
Loki ──────┘
```

### **Step 5: Prometheus Evaluates Alert Rules**

Example alert rule:

```yaml
CPU > 90% for 5 minutes → FIRING
Memory > 85% for 10 minutes → FIRING
Disk > 90% for 15 minutes → FIRING
```

### **Step 6: Alertmanager Receives Alert**

Prometheus sends firing alerts to Alertmanager:

```
Prometheus → Alertmanager
             (severity: critical/warning)
```

### **Step 7: Alertmanager Routes Alert**

Routing rules determine destination:

```
if severity == "critical" → Critical Receiver (Slack)
if severity == "warning"  → Warning Receiver (Slack)
```

### **Step 8: Alert Action Service Processes**

Custom Flask service receives webhook from Alertmanager:

```
Alertmanager → Alert Action Service (http://localhost:5000/alertmanager)
```

### **Step 9: Create Interactive Slack Incident**

Service creates enriched Slack message with:

- ✅ Alert name and severity
- 📍 Affected server/instance
- 📊 Metric value and threshold
- ⏱️ Duration and start time
- 🔗 Grafana dashboard link
- 🔗 Prometheus graph link
- 📋 Runbook link (if available)
- 🎯 Action buttons (below)

### **Step 10: Engineer Handles Incident**

Available actions in Slack:

```
[Acknowledge]  [Pause/Silence]  [Reject]  [Add Note]  [Assign]  [Mark Resolved]
```

Actions are stored in a JSON state file so context is preserved.

### **Step 11: Problem is Fixed**

Server metric returns to normal:

```
CPU: 96% → 78% → 45%
(no longer triggers alert condition)
```

### **Step 12: Alertmanager Sends Resolved Event**

Prometheus evaluates alert as resolved and notifies Alertmanager:

```
Prometheus → Alertmanager: "Alert is now RESOLVED"
```

### **Step 13: Separate Resolution Notification**

Original firing message is **not** rewritten. Instead, a separate message is posted:

```
✅ RESOLVED: High CPU Usage
   Server: prod-app-01
   Duration: 8 minutes 32 seconds
   Timestamp: 2024-01-15 14:23:15 UTC
```

This keeps incident history clean and easy to understand.

---

## 📊 System Diagrams (DFD / ERD / Use Case)

### 1️⃣ Data Flow Diagram (DFD)

Shows how telemetry and alert data move between external entities, processes, and data stores.

```mermaid
flowchart TB
    %% External Entities
    SRV([Production Servers])
    ENG([Engineer])
    ADM([Administrator])
    SLK([Slack Platform])

    %% Processes
    P1(("1.0<br/>Collect Metrics & Logs<br/>Grafana Alloy"))
    P2(("2.0<br/>Store & Evaluate Metrics<br/>Prometheus"))
    P3(("2.1<br/>Store Logs<br/>Loki"))
    P4(("3.0<br/>Visualize Data<br/>Grafana"))
    P5(("4.0<br/>Route Alerts<br/>Alertmanager"))
    P6(("5.0<br/>Process & Notify<br/>Alert Action Service"))
    P7(("6.0<br/>Manage Incident<br/>Slack Interaction"))
    P8(("7.0<br/>Deploy & Configure<br/>Ansible"))

    %% Data Stores
    D1[(D1: Prometheus TSDB)]
    D2[(D2: Loki Log Store)]
    D3[(D3: Alert State JSON File)]
    D4[(D4: Alert Rules Config)]

    %% Flows
    SRV -- "CPU / Mem / Disk / Container / App metrics" --> P1
    SRV -- "System & app logs" --> P1

    P1 -- "remote_write metrics" --> P2
    P1 -- "log streams" --> P3

    P2 -- "write metrics" --> D1
    P3 -- "write logs" --> D2

    D1 -- "query metrics" --> P4
    D2 -- "query logs" --> P4
    P4 -- "dashboards" --> ENG

    D4 -- "alert rules" --> P2
    P2 -- "firing/resolved alerts" --> P5
    P5 -- "webhook: alert payload" --> P6

    P6 -- "read/write state" --> D3
    P6 -- "enriched incident message" --> P7
    P7 -- "post message / buttons" --> SLK
    SLK -- "interactive message" --> ENG
    ENG -- "Ack / Assign / Note / Pause / Reject / Resolve" --> SLK
    SLK -- "action payload" --> P7
    P7 -- "update state" --> D3
    P7 -- "resolution notice" --> SLK
    SLK -- "resolved notification" --> ENG

    ADM -- "SSH / playbook run" --> P8
    P8 -- "install & configure Alloy" --> SRV
    ADM -- "define thresholds" --> D4
    ADM -- "manage inventory" --> P8
```

### 2️⃣ Entity Relationship Diagram (ERD)

Logical data model for servers, metrics, alerts, alert state, engineers, and Slack notifications.

```mermaid
erDiagram
    SERVER ||--o{ METRIC : generates
    SERVER ||--o{ LOG_ENTRY : generates
    SERVER ||--o{ ALERT : triggers
    SERVER {
        string instance_id PK
        string hostname
        string ip_address
        string environment
        string role
        boolean alloy_installed
    }

    METRIC {
        string metric_id PK
        string server_id FK
        string metric_name
        float value
        datetime timestamp
    }

    LOG_ENTRY {
        string log_id PK
        string server_id FK
        string source
        string message
        datetime timestamp
    }

    ALERT_RULE ||--o{ ALERT : defines
    ALERT_RULE {
        string rule_id PK
        string alert_name
        string expr
        string severity
        string for_duration
        string summary_template
    }

    ALERT ||--|| ALERT_STATE : has
    ALERT ||--o{ SLACK_NOTIFICATION : produces
    ALERT {
        string alert_id PK
        string rule_id FK
        string server_id FK
        string status
        float metric_value
        datetime started_at
        datetime resolved_at
    }

    ALERT_STATE {
        string alert_id PK, FK
        string status
        string acknowledged_by FK
        datetime acknowledged_at
        string assigned_to FK
        string notes
        datetime silenced_until
    }

    ENGINEER ||--o{ ALERT_STATE : acknowledges
    ENGINEER ||--o{ ALERT_STATE : assigned_to
    ENGINEER ||--o{ SLACK_NOTIFICATION : receives
    ENGINEER {
        string engineer_id PK
        string username
        string slack_user_id
        string team
    }

    SLACK_NOTIFICATION {
        string notification_id PK
        string alert_id FK
        string message_ts
        string channel
        string type
        datetime sent_at
    }

    DASHBOARD {
        string dashboard_id PK
        string name
        string datasource
    }

    DASHBOARD ||--o{ SERVER : visualizes
```

### 3️⃣ Use Case Diagram

Actors and their interactions with the monitoring platform.

```mermaid
flowchart LR
    Engineer(["🧑‍💻 Engineer"])
    Admin(["🛠️ Administrator"])
    Prometheus(["⚙️ Prometheus<br/>(system actor)"])
    Slack(["💬 Slack<br/>(system actor)"])

    subgraph SYS["Promax Monitoring System"]
        UC1(["View Dashboards"])
        UC2(["Explore Logs"])
        UC3(["Check Alert History"])
        UC4(["Receive Slack Incident Notification"])
        UC5(["Acknowledge Alert"])
        UC6(["Assign Alert"])
        UC7(["Add Note to Incident"])
        UC8(["Pause / Silence Alert"])
        UC9(["Reject Alert"])
        UC10(["Mark Alert Resolved"])
        UC11(["Receive Resolved Notification"])
        UC12(["Configure Alert Rules"])
        UC13(["Configure Alertmanager Routing"])
        UC14(["Deploy Grafana Alloy via Ansible"])
        UC15(["Add Server to Inventory"])
        UC16(["Configure Slack App / Tokens"])
        UC17(["Create Custom Dashboard"])
        UC18(["Evaluate Alert Rule"])
        UC19(["Fire / Resolve Alert"])
    end

    Engineer --> UC1
    Engineer --> UC2
    Engineer --> UC3
    Engineer --> UC4
    Engineer --> UC5
    Engineer --> UC6
    Engineer --> UC7
    Engineer --> UC8
    Engineer --> UC9
    Engineer --> UC10
    Engineer --> UC11
    Engineer --> UC17

    Admin --> UC12
    Admin --> UC13
    Admin --> UC14
    Admin --> UC15
    Admin --> UC16
    Admin --> UC1
    Admin --> UC17

    Prometheus --> UC18
    Prometheus --> UC19

    UC19 -.include.-> UC4
    UC10 -.include.-> UC11
    Slack --> UC4
    Slack --> UC11
    UC5 -.extend.-> UC7
    UC6 -.extend.-> UC7
```

---

## 🚀 Deployment Guide

### **Prerequisites**

- Monitoring server: Ubuntu/Debian 20.04+, 4GB RAM minimum
- Monitored servers: Linux (Ubuntu/Debian/CentOS/RHEL)
- Docker & Docker Compose installed
- Ansible 2.9+
- Slack workspace with admin access

### **Deployment Order (From Zero)**

```
1. Prepare monitoring server
       ↓
2. Install Docker
       ↓
3. Deploy Prometheus
       ↓
4. Deploy Grafana
       ↓
5. Deploy Loki
       ↓
6. Deploy Alertmanager
       ↓
7. Configure Prometheus alert rules
       ↓
8. Configure Alertmanager routes/webhooks
       ↓
9. Configure Alert Action Service
       ↓
10. Configure Slack application
       ↓
11. Start Alert Action Service
       ↓
12. Configure Ansible
       ↓
13. Add monitored servers to inventory
       ↓
14. Install Grafana Alloy on servers
       ↓
15-21. Verify and test
```

### **Quick Start with Docker Compose**

```bash
# 1. Clone repository
git clone https://github.com/promax-tech/monitoring.git
cd monitoring

# 2. Copy example files
cp .env.example .env
cp prometheus/prometheus.yml.example prometheus/prometheus.yml
cp alertmanager/alertmanager.yml.example alertmanager/alertmanager.yml

# 3. Edit .env with your Slack tokens
# SLACK_BOT_TOKEN=xoxb-...
# SLACK_APP_TOKEN=xapp-...
# SLACK_SIGNING_SECRET=...

# 4. Start all services
docker-compose up -d

# 5. Verify
curl http://localhost:9090     # Prometheus
curl http://localhost:3000     # Grafana (admin/admin)
curl http://localhost:9093     # Alertmanager
curl http://localhost:5000/health  # Alert Action Service
```

---

## ⚙️ Configuration

### **Prometheus Alert Rules**

File: `prometheus/rules/alerts.yml`

```yaml
groups:
  - name: server_alerts
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: node_cpu_usage > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU is {{ $value }}% for more than 5 minutes"
          
      - alert: HighMemoryUsage
        expr: node_memory_usage > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory is {{ $value }}% for more than 10 minutes"
          
      - alert: DiskSpaceRunningOut
        expr: node_disk_usage > 90
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Disk space critical on {{ $labels.instance }}"
          description: "Disk usage is {{ $value }}%"
```

### **Alertmanager Routing**

File: `alertmanager/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

  routes:
    - match:
        severity: critical
      receiver: critical
      repeat_interval: 5m
      
    - match:
        severity: warning
      receiver: warning
      repeat_interval: 1h

receivers:
  - name: default
    webhook_configs:
      - url: http://alert-action-service:5000/alertmanager
        send_resolved: true
        
  - name: critical
    webhook_configs:
      - url: http://alert-action-service:5000/alertmanager
        send_resolved: true
        
  - name: warning
    webhook_configs:
      - url: http://alert-action-service:5000/alertmanager
        send_resolved: true
```

### **Ansible Playbook for Alloy Installation**

File: `ansible/playbooks/install-alloy.yml`

```yaml
---
- hosts: all
  become: yes
  roles:
    - alloy
  vars:
    prometheus_server: "monitoring.internal:9090"
    loki_server: "monitoring.internal:3100"
    alloy_config: "/etc/alloy/config.alloy"
```

---

## 📊 Monitoring & Dashboards

### **Pre-built Dashboards**

Grafana includes dashboards for:

- 📈 Server Overview (CPU, memory, disk, network)
- 🐳 Docker Containers
- 🗄️ MySQL/Database metrics
- 🔗 Application metrics
- 📝 Logs exploration
- 🚨 Alert history
- 🔄 System uptime

### **Creating Custom Dashboards**

1. Open Grafana: `http://monitoring-server:3000`
2. Login with admin credentials
3. Click "+" → "Dashboard" → "Add Panel"
4. Select datasource (Prometheus or Loki)
5. Write query: `up{job="node-exporter"}`
6. Visualize and save

### **Example Queries**

```promql
# CPU usage per server
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory available percentage
(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# Disk usage percentage
(node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100

# Network throughput
rate(node_network_transmit_bytes_total[5m])
```

---

## 🚨 Alert Management

### **Alert Lifecycle**

```
PENDING → FIRING → (Engineer action) → ACKNOWLEDGED → RESOLVED
```

### **Alert Actions (Slack)**

| Action | Effect |
|--------|--------|
| **Acknowledge** | Marks alert as acknowledged, updates state |
| **Pause/Silence** | Silences alert for 1 hour (configurable) |
| **Reject** | Dismisses alert, marks as rejected |
| **Add Note** | Adds context/notes to incident |
| **Assign** | Assigns to team member, notifies them |
| **Mark Resolved** | Manually closes incident |

### **State File**

Alert states are persisted in JSON:

```json
{
  "alert_123": {
    "status": "acknowledged",
    "acknowledged_at": "2024-01-15T14:20:00Z",
    "acknowledged_by": "john.doe",
    "notes": "Restarted app server",
    "assigned_to": "ops-team"
  }
}
```

---

## 🔧 Troubleshooting

### **Grafana Alloy is not running**

```bash
sudo systemctl status alloy --no-pager
sudo journalctl -u alloy -f
sudo systemctl restart alloy
```

### **Prometheus is not receiving metrics**

Check targets page:

```bash
# Visit:
http://MONITORING_SERVER_IP:9090/targets

# Verify Alloy configuration:
sudo systemctl status alloy
sudo cat /etc/alloy/config.alloy

# Check network connectivity:
telnet MONITORING_SERVER_IP 9090
```

### **Grafana has no data**

Verify:

1. ✅ Prometheus is running: `curl http://localhost:9090`
2. ✅ Prometheus has data: `http://localhost:9090/graph`
3. ✅ Grafana datasource URL is correct
4. ✅ Time range in Grafana is not in the future

### **Alertmanager is not receiving alerts**

Check Alertmanager UI:

```bash
http://MONITORING_SERVER_IP:9093
```

Then verify Prometheus alert rules:

```bash
curl http://localhost:9090/api/v1/rules
```

### **Slack alert is not appearing**

Check Alert Action Service:

```bash
sudo systemctl status alert-action.service --no-pager
sudo journalctl -u alert-action.service -n 100
curl http://127.0.0.1:5000/health
```

Verify Alertmanager webhook is configured:

```bash
curl http://MONITORING_SERVER_IP:9093/api/v1/status
```

### **Alert Action Service fails to start**

Validate Python syntax:

```bash
cd /opt/promax-monitoring/alert-action
sudo /opt/promax-monitoring/alert-action/venv/bin/python -m py_compile app.py
```

Check systemd unit:

```bash
systemctl cat alert-action.service
systemctl daemon-reload
sudo systemctl restart alert-action.service
```

### **Slack action does not work**

Verify:

- ✅ Slack bot token is valid
- ✅ Slack signing secret matches
- ✅ Slack app token is correct
- ✅ Socket Mode is enabled in Slack app config
- ✅ Channel permissions allow bot to post
- ✅ Interactive action handling is configured

---


### **`.gitignore` Template**

```gitignore
# Environment
.env
.env.local

# SSH/Keys
*.pem
*.key
*.pub

# Python
venv/
__pycache__/
*.pyc
*.egg-info/

# Logs
*.log
logs/

# Sensitive data
passwords.txt
secrets/
```

### **Do Not Commit**

```
SLACK_BOT_TOKEN
SLACK_APP_TOKEN
SLACK_SIGNING_SECRET
SSH private keys
Database passwords
API keys
```

---

## 📁 Repository Structure

```
promax-monitoring/
│
├── README.md
├── docker-compose.yml
├── .env.example
│
├── prometheus/
│   ├── prometheus.yml
│   └── rules/
│       └── alerts.yml
│
├── alertmanager/
│   └── alertmanager.yml
│
├── loki/
│   └── loki-config.yml
│
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       └── dashboards/
│
├── ansible/
│   ├── inventory/
│   │   ├── production.ini.example
│   │   └── test.ini.example
│   ├── playbooks/
│   │   └── install-alloy.yml
│   └── roles/
│       └── alloy/
│           ├── defaults/
│           ├── handlers/
│           ├── tasks/
│           └── templates/
│
└── alert-action/
    ├── app.py
    ├── requirements.txt
    ├── .env.example
    └── alert-action.service.example
```

---

## ⚡ Quick Reference

| Task | Command |
|------|---------|
| **Check Alloy** | `sudo systemctl status alloy --no-pager` |
| **Alloy logs** | `sudo journalctl -u alloy -f` |
| **Restart Alloy** | `sudo systemctl restart alloy` |
| **Alert Action status** | `sudo systemctl status alert-action.service --no-pager` |
| **Alert Action logs** | `sudo journalctl -u alert-action.service -f` |
| **Health check** | `curl http://127.0.0.1:5000/health` |
| **Python syntax** | `python -m py_compile app.py` |
| **Prometheus UI** | `http://MONITORING_SERVER_IP:9090` |
| **Prometheus targets** | `http://MONITORING_SERVER_IP:9090/targets` |
| **Alertmanager UI** | `http://MONITORING_SERVER_IP:9093` |
| **Grafana UI** | `http://MONITORING_SERVER_IP:3000` |
| **CPU stress test** | `stress-ng --cpu 0 --timeout 5m --metrics-brief` |
| **Stop stress test** | `pkill stress-ng` |
| **Ansible ping** | `ansible all -i inventory/production.ini -m ping` |
| **Ansible syntax check** | `ansible-playbook playbooks/install-alloy.yml --syntax-check` |

---

## ✅ Production Readiness Checklist

Before marking as production-ready:

- [ ] Monitoring server has sufficient CPU/RAM/storage (4GB+ RAM, 50GB+ disk)
- [ ] Docker containers use pinned versions (not `latest`)
- [ ] Prometheus retention is configured (30+ days recommended)
- [ ] Loki retention/storage is configured
- [ ] Grafana authentication is secured (strong password, LDAP/OAuth if available)
- [ ] Prometheus/Alertmanager are **not** publicly exposed
- [ ] Alloy is managed by systemd on all monitored servers
- [ ] Alloy configuration is managed by Ansible (Infrastructure as Code)
- [ ] Production inventory is separated from test inventory
- [ ] Alert rules are documented and reviewed
- [ ] Critical and warning routes are tested with real traffic
- [ ] Slack firing notification is tested end-to-end
- [ ] Slack interactive actions (acknowledge, assign, resolve) are tested
- [ ] Pause/silence behavior is tested and timed correctly
- [ ] Resolution notifications appear separately (not overwrites)
- [ ] Logs are available and queryable in Loki
- [ ] All dashboards are available in Grafana
- [ ] Secrets are excluded from Git (verify `.gitignore`)
- [ ] Configuration backups exist and are tested
- [ ] Engineering team is trained on troubleshooting procedures
- [ ] On-call runbooks are documented and accessible
- [ ] Monitoring of the monitoring system itself is in place

---

## 📚 For New Engineers

> **If you only remember one thing, remember this:**
>
> **Alloy collects data → Prometheus/Loki store it → Grafana shows it → Prometheus detects problems → Alertmanager routes them → Alert Action Service turns them into interactive Slack incidents → engineers handle them → the system sends a separate resolved notification when the problem is fixed.**

### **You will interact with three places:**

1. **Grafana** (`http://monitoring:3000`)
   - Investigate what's happening
   - View dashboards and drill down

2. **Prometheus/Alertmanager** (`http://monitoring:9090` / `http://monitoring:9093`)
   - Verify metric and alert state
   - Test alert rules
   - Check alert history

3. **Slack**
   - Acknowledge, assign, pause, reject
   - Add notes and context
   - Follow the incident to resolution

### **Administrators use Ansible:**

- Add or configure monitored servers
- Install Alloy uniformly across fleet
- Avoid manual repetition

---

## 📞 Support & Contribution

For issues, improvements, or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `journalctl -u [service] -f`
3. Create an issue in the repository
4. Contact the platform engineering team

---

## 📄 License & Ownership

This repository is intended for **Tech Bridge monitoring infrastructure**.

Add your organization's preferred license and operational ownership information before making public.

---

**Last Updated:** 15 sept 2026  
**Version:** 1.0  
**Maintained by:** Ahmad Raza 
