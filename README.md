# Promax Production Monitoring Stack

Centralized production monitoring, logging, alerting, and Slack notification system for Promax infrastructure.

---

## 1. Project Overview

This project provides a centralized monitoring platform for Promax production servers.

The monitoring server collects:

* Linux system metrics
* CPU usage
* Memory usage
* Disk/storage usage
* System load
* Network traffic
* Disk I/O
* MySQL metrics
* Nginx metrics
* Nginx access logs
* Nginx error logs
* System logs
* Authentication logs

Alerts are handled through Prometheus and Alertmanager and delivered to Slack through a custom Python Alert Action Service.

---

# 2. Architecture

```text
                         ┌─────────────────────────────┐
                         │       TBC-Monitoring        │
                         │                             │
                         │  Prometheus                 │
                         │  Grafana                    │
                         │  Alertmanager               │
                         │  Loki                       │
                         │  Alert Action Service       │
                         │  Ansible                    │
                         └──────────────┬──────────────┘
                                        │
                         Private Network│
                                        │
              ┌─────────────────────────┴─────────────────────┐
              │                                               │
              ▼                                               ▼
       Promax Server 1                                  Promax Server 2
       ┌────────────────┐                              ┌────────────────┐
       │ Grafana Alloy  │                              │ Grafana Alloy  │
       │ Node Metrics   │                              │ Node Metrics   │
       │ MySQL          │                              │ Nginx          │
       │ Nginx          │                              │ MySQL/etc.     │
       │ System Logs    │                              │ System Logs    │
       └───────┬────────┘                              └───────┬────────┘
               │                                               │
               │ Metrics                                       │ Metrics
               ├──────────────────────► Prometheus             │
               │                                               │
               │ Logs                                           │
               └──────────────────────► Loki                    │
                                                               │
                                                               └──► Prometheus/Loki
```

---

# 3. Components

| Component            | Location           | Purpose                                   |
| -------------------- | ------------------ | ----------------------------------------- |
| Prometheus           | TBC-Monitoring     | Metrics collection/storage/querying       |
| Grafana              | TBC-Monitoring     | Monitoring dashboards                     |
| Alertmanager         | TBC-Monitoring     | Alert routing and notification management |
| Loki                 | TBC-Monitoring     | Centralized log storage                   |
| Alert Action Service | TBC-Monitoring     | Slack interactive alert handling          |
| Ansible              | TBC-Monitoring     | Alloy deployment/automation               |
| Grafana Alloy        | Production servers | Metrics and log collection                |
| MySQL Exporter       | Production servers | MySQL metrics                             |
| Nginx Exporter       | Production servers | Nginx metrics                             |

---

# 4. Server Information

## Monitoring Server

Hostname:

```text
TBC-Monitoring
```

Private IP:

```text
<MONITORING_PRIVATE_IP>
```

Operating System:

```text
Ubuntu 26.04 LTS
```

Project directory:

```text
/opt/promax-monitoring
```

---

## Monitored AWS Lab Server

Private IP:

```text
<AWS_SERVER_PRIVATE_IP>
```

Public IP:

```text
<AWS_SERVER_PUBLIC_IP>
```

> Actual IP addresses are intentionally hidden from this README.

The AWS server was used as a testing environment before deploying the monitoring stack to Promax production servers.

---

# 5. Project Directory

Main directory:

```bash
/opt/promax-monitoring
```

Structure:

```text
/opt/promax-monitoring/
│
├── docker-compose.yml
│
├── prometheus/
│   ├── prometheus.yml
│   └── rules/
│       └── infrastructure.yml
│
├── alertmanager/
│   ├── alertmanager.yml
│   └── templates/
│       └── slack.tmpl
│
├── loki/
│   └── loki-config.yml
│
├── grafana/
│
├── alert-action/
│   ├── app.py
│   ├── .env
│   └── venv/
│
└── ansible/
    ├── ansible.cfg
    ├── inventory/
    │   └── production.ini
    ├── roles/
    │   └── alloy/
    │       ├── defaults/
    │       ├── handlers/
    │       ├── tasks/
    │       └── templates/
    │
    └── playbooks/
        └── install-alloy.yml
```

---

# 6. Docker Monitoring Stack

The following services run inside Docker on the monitoring server:

```text
Prometheus
Grafana
Alertmanager
Loki
```

Check containers:

```bash
cd /opt/promax-monitoring
docker compose ps
```

Check all containers:

```bash
docker ps
```

Start stack:

```bash
docker compose up -d
```

Stop stack:

```bash
docker compose down
```

Restart stack:

```bash
docker compose restart
```

---

# 7. Prometheus

Prometheus image:

```text
prom/prometheus:v3.13.2
```

Port:

```text
9090
```

Prometheus configuration:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets:
          - 'prometheus:9090'
```

Prometheus is started with:

```text
--web.enable-remote-write-receiver
```

This allows Grafana Alloy to send metrics using Prometheus Remote Write.

---

## Prometheus Health Check

```bash
curl http://127.0.0.1:9090/-/healthy
```

Expected:

```text
Prometheus Server is Healthy.
```

---

## Check Prometheus Targets

```bash
curl -s http://127.0.0.1:9090/api/v1/targets
```

---

## Check Alertmanager Connection

```bash
curl -s http://127.0.0.1:9090/api/v1/alertmanagers
```

---

# 8. Grafana

Grafana image:

```text
grafana/grafana:11.2.0
```

Grafana is used for:

* Infrastructure monitoring
* Server health
* CPU monitoring
* Memory monitoring
* Disk monitoring
* Network monitoring
* MySQL monitoring
* Nginx monitoring
* Nginx logs
* System logs
* Authentication logs

Dashboard:

```text
🏢 Promax Production Dashboard
```

Dashboard UID:

```text
promax-production-dashboard
```

Refresh:

```text
10s
```

Default time range:

```text
now-30m → now
```

---

# 9. Prometheus Dashboard Queries

## Servers Online

```promql
count(up{job="node"} == 1)
```

## Average CPU

```promql
100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

## Average Memory

```promql
100 * (1 - avg(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

## CPU Usage by Server

```promql
100 * (
  1 -
  avg by(instance) (
    rate(node_cpu_seconds_total{mode="idle"}[5m])
  )
)
```

## Memory Usage by Server

```promql
100 * (
  1 -
  node_memory_MemAvailable_bytes
  /
  node_memory_MemTotal_bytes
)
```

## Disk Usage

```promql
100 * (
  1 -
  node_filesystem_avail_bytes{
    fstype!~"tmpfs|overlay",
    mountpoint="/"
  }
  /
  node_filesystem_size_bytes{
    fstype!~"tmpfs|overlay",
    mountpoint="/"
  }
)
```

## System Load

```promql
node_load1
```

## Network Receive

```promql
sum by(instance) (
  rate(node_network_receive_bytes_total{device!="lo"}[5m])
)
```

## Network Transmit

```promql
sum by(instance) (
  rate(node_network_transmit_bytes_total{device!="lo"}[5m])
)
```

## Disk Read

```promql
sum by(instance) (
  rate(node_disk_read_bytes_total[5m])
)
```

## Disk Write

```promql
sum by(instance) (
  rate(node_disk_written_bytes_total[5m])
)
```

---

# 10. MySQL Monitoring

A dedicated MySQL monitoring user was created.

```sql
CREATE USER 'alloy'@'localhost'
IDENTIFIED BY '<MYSQL_MONITOR_PASSWORD>';

GRANT PROCESS, REPLICATION CLIENT, SELECT
ON *.*
TO 'alloy'@'localhost';

FLUSH PRIVILEGES;
```

The real password is intentionally not stored in this README.

---

## Test MySQL Monitoring User

```bash
mysql -u alloy -p \
-h 127.0.0.1 \
-P 3306 \
-e "SELECT VERSION();"
```

---

## MySQL Connections

```promql
mysql_global_status_threads_connected
```

## MySQL Query Rate

```promql
rate(mysql_global_status_queries[5m])
```

## MySQL Slow Queries

```promql
rate(mysql_global_status_slow_queries[5m])
```

## MySQL Running Queries

```promql
mysql_global_status_threads_running
```

## MySQL Availability

```promql
mysql_up
```

---

# 11. Grafana Alloy

Grafana Alloy is installed directly on monitored servers.

It runs through systemd.

It is **not** running as a Docker container on the monitoring server.

---

## Alloy Status

```bash
sudo systemctl status alloy --no-pager
```

## Restart Alloy

```bash
sudo systemctl restart alloy
```

## Enable Alloy on Boot

```bash
sudo systemctl enable alloy
```

## Alloy Logs

```bash
sudo journalctl -u alloy -f
```

## Recent Alloy Logs

```bash
sudo journalctl -u alloy -n 100 --no-pager
```

---

# 12. Alloy Node Metrics

Node/system metrics are collected using the Unix exporter:

```alloy
prometheus.exporter.unix "node" {
}

prometheus.scrape "node" {
  targets    = prometheus.exporter.unix.node.targets
  forward_to = [prometheus.remote_write.local.receiver]
}
```

This provides metrics such as:

```text
CPU
Memory
Disk
Filesystem
Network
Load
Processes
System uptime
```

---

# 13. Alloy MySQL Metrics

```alloy
prometheus.exporter.mysql "mysql" {
  data_source_name = "alloy:<MYSQL_MONITOR_PASSWORD>@tcp(127.0.0.1:3306)/"
}

prometheus.scrape "mysql" {
  targets    = prometheus.exporter.mysql.mysql.targets
  forward_to = [prometheus.remote_write.local.receiver]
}
```

---

# 14. Nginx Monitoring

Nginx `stub_status` was configured:

```nginx
location /nginx_status {
    stub_status;
    allow 127.0.0.1;
    deny all;
}
```

This means only localhost can access the status endpoint.

Test:

```bash
curl http://127.0.0.1/nginx_status
```

Example:

```text
Active connections: 1
server accepts handled requests
 2 2 2
Reading: 0 Writing: 1 Waiting: 0
```

---

# 15. Nginx Exporter

Nginx exporter is used to convert Nginx statistics into Prometheus metrics.

Expected exporter port:

```text
9113
```

Test:

```bash
curl http://127.0.0.1:9113/metrics
```

Alloy scrape:

```alloy
prometheus.scrape "nginx" {
  targets = [{
    "__address__" = "127.0.0.1:9113",
    "job"         = "nginx",
  }]

  forward_to      = [prometheus.remote_write.local.receiver]
  scrape_interval = "15s"
}
```

---

# 16. Loki

Loki image:

```text
grafana/loki:3.5.0
```

Port:

```text
3100
```

Loki stores centralized logs received from Grafana Alloy.

---

## Loki Health Check

```bash
curl http://127.0.0.1:3100/ready
```

Expected:

```text
ready
```

---

## Loki Storage

Loki uses a Docker volume:

```text
loki_data
```

Filesystem storage is configured for chunks.

Retention:

```text
168 hours
```

which is:

```text
7 days
```

---

# 17. Nginx Log Collection

Alloy collects:

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

Configuration:

```alloy
local.file_match "nginx_logs" {
  path_targets = [
    {
      __path__ = "/var/log/nginx/*.log",
      job      = "nginx",
    },
  ]
}

loki.source.file "nginx_logs" {
  targets    = local.file_match.nginx_logs.targets
  forward_to = [loki.write.local.receiver]
}
```

---

# 18. Test Nginx Logs

Generate a request:

```bash
curl http://127.0.0.1/nginx_status
```

Check local Nginx logs:

```bash
tail -5 /var/log/nginx/access.log
```

Check Alloy:

```bash
sudo journalctl -u alloy -n 100 --no-pager
```

---

# 19. Loki Nginx Query

```bash
curl -sG \
'http://127.0.0.1:3100/loki/api/v1/query_range' \
--data-urlencode 'query={job="nginx"}' \
--data-urlencode 'limit=20'
```

---

# 20. Nginx Grafana LogQL

## Live Nginx Logs

```logql
{job="nginx"}
```

## Access Logs

```logql
{job="nginx", filename=~".*access.*"}
```

## Error Logs

```logql
{job="nginx", filename=~".*error.*"}
```

## Nginx Log Volume

```logql
sum(count_over_time({job="nginx"}[5m]))
```

## HTTP Errors

```logql
sum(count_over_time({job="nginx"} |~ " 4[0-9][0-9] "[5m]))
```

```logql
sum(count_over_time({job="nginx"} |~ " 5[0-9][0-9] "[5m]))
```

## HTTP 4xx / 5xx Details

```logql
{job="nginx"} |~ " 4[0-9][0-9] | 5[0-9][0-9] "
```

---

# 21. HTTP Status Summary

The Grafana dashboard categorizes HTTP responses:

```text
2xx → Successful requests
3xx → Redirects
4xx → Client errors
5xx → Server errors
```

Examples:

```text
200 → OK
301/302 → Redirect
400 → Bad Request
401 → Unauthorized
403 → Forbidden
404 → Not Found
500 → Internal Server Error
502 → Bad Gateway
503 → Service Unavailable
```

---

# 22. System Logs

System logs are collected into Loki with:

```text
job="system"
```

Authentication logs use:

```text
service="auth"
```

For systems that provide traditional log files:

```alloy
local.file_match "system_logs" {
  path_targets = [
    {
      __path__ = "/var/log/syslog",
      job      = "system",
      service  = "syslog",
    },
    {
      __path__ = "/var/log/auth.log",
      job      = "system",
      service  = "auth",
    },
  ]
}

loki.source.file "system_logs" {
  targets    = local.file_match.system_logs.targets
  forward_to = [loki.write.local.receiver]
}
```

---

# 23. Check System Log Files

Before enabling file-based collection:

```bash
ls -l /var/log/syslog /var/log/auth.log
```

If the files do not exist, check systemd journal:

```bash
sudo journalctl -n 20 --no-pager
```

Modern Ubuntu systems may rely heavily on journald, so journal-based Alloy collection may be preferable depending on the server configuration.

---

# 24. Test System Logs

Generate a test message:

```bash
logger "PROMAX SYSTEM LOG TEST"
```

Check:

```bash
sudo tail -20 /var/log/syslog
```

Restart Alloy:

```bash
sudo systemctl restart alloy
```

Check Alloy:

```bash
sudo journalctl -u alloy -n 100 --no-pager
```

---

# 25. System Log Grafana Queries

## Live System Logs

```logql
{job="system"}
```

## System Log Volume

```logql
sum(count_over_time({job="system"}[5m]))
```

## Authentication Logs

```logql
{job="system", service="auth"}
```

## System Errors

```logql
{job="system"} |~ "(?i)error|failed|failure|critical"
```

## Warnings

```logql
{job="system"} |~ "(?i)warning|warn"
```

## Errors + Warnings

```logql
{job="system"} |~ "(?i)error|failed|failure|critical|warning|warn"
```

---

# 26. Prometheus Remote Write

Alloy sends metrics to Prometheus using:

```alloy
prometheus.remote_write "local" {
  endpoint {
    url = "http://<MONITORING_PRIVATE_IP>:9090/api/v1/write"
  }
}
```

In the AWS lab, private connectivity was unavailable, so a reverse SSH tunnel was used instead.

---

# 27. Loki Write

Production configuration:

```alloy
loki.write "local" {
  endpoint {
    url = "http://<MONITORING_PRIVATE_IP>:3100/loki/api/v1/push"
  }
}
```

---

# 28. AWS Lab Reverse SSH Tunnel

AWS and the on-premises monitoring server did not have direct private-network connectivity.

Therefore, reverse SSH tunneling was used only for lab testing.

---

## Prometheus Tunnel

Run from TBC-Monitoring:

```bash
ssh -i /root/.ssh/id_ed25519 -N \
-R 19090:127.0.0.1:9090 \
ubuntu@<AWS_SERVER_PUBLIC_IP>
```

AWS Alloy then uses:

```text
http://127.0.0.1:19090/api/v1/write
```

Test from AWS:

```bash
curl -v http://127.0.0.1:19090/-/healthy
```

Expected:

```text
Prometheus Server is Healthy.
```

---

## Loki Tunnel

Run from TBC-Monitoring:

```bash
ssh -i /root/.ssh/id_ed25519 -N \
-R 13100:127.0.0.1:3100 \
ubuntu@<AWS_SERVER_PUBLIC_IP>
```

AWS Alloy uses:

```text
http://127.0.0.1:13100/loki/api/v1/push
```

Test from AWS:

```bash
curl -v http://127.0.0.1:13100/ready
```

Expected:

```text
ready
```

---

# 29. Important Reverse SSH Detail

The reverse tunnel:

```bash
-R 19090:127.0.0.1:9090
```

means:

```text
AWS localhost:19090
        ↓
SSH tunnel
        ↓
Monitoring server localhost:9090
```

Similarly:

```bash
-R 13100:127.0.0.1:3100
```

means:

```text
AWS localhost:13100
        ↓
SSH tunnel
        ↓
Monitoring server localhost:3100
```

Therefore:

```bash
ss -lntp | grep 19090
```

and:

```bash
ss -lntp | grep 13100
```

should be checked on the AWS server.

---

# 30. Alerting Architecture

```text
Prometheus
     │
     │ Alert Rules
     ▼
Alertmanager
     │
     ▼
Python Alert Action Service
     │
     ▼
Slack
     │
     ├── #warning-alerts
     │
     └── #critical-alters
```

---

# 31. Alert Rules

Rules file:

```text
/opt/promax-monitoring/prometheus/rules/infrastructure.yml
```

Configured alerts:

```text
HighCPUUsage
CriticalCPUUsage

HighMemoryUsage
CriticalMemoryUsage

HighDiskUsage
CriticalDiskUsage

HighSystemLoad
HighSwapUsage
```

---

## Alert Thresholds

| Alert           |   Threshold |   Duration |
| --------------- | ----------: | ---------: |
| High CPU        |        >80% | 10 minutes |
| Critical CPU    |        >90% |  5 minutes |
| High Memory     |        >80% | 10 minutes |
| Critical Memory |        >90% |  5 minutes |
| High Disk       |        >80% | 10 minutes |
| Critical Disk   |        >90% |  5 minutes |
| High Load       | > CPU cores | 10 minutes |
| High Swap       |        >80% | configured |

---

# 32. CPU Testing

Check CPU cores:

```bash
nproc
```

CPU stress test used in the lab:

```bash
stress-ng --cpu 2 --timeout 12m
```

After testing:

```bash
sudo pkill stress-ng
```

Verify:

```bash
ps aux | grep stress-ng
```

Do not run stress tests on production systems without approval.

---

# 33. Memory Monitoring

Memory usage query:

```promql
100 * (1 - avg(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

This calculates system memory utilization using `MemAvailable`.

Memory stress testing should not be performed on a production server because low-memory systems can trigger the Linux OOM killer and terminate services.

---

# 34. Alertmanager

Alertmanager is responsible for:

* Grouping alerts
* Routing alerts
* Warning/critical separation
* Repeat notifications
* Resolved notifications
* Alert silencing

Current routing:

```text
severity="critical"
        ↓
alert-action-critical

other alerts
        ↓
alert-action-warning
```

---

## Alertmanager Timing

```yaml
group_wait: 30s
group_interval: 5m
repeat_interval: 5m
```

Resolved notifications:

```yaml
send_resolved: true
```

---

## Alertmanager Status

```bash
curl -s http://127.0.0.1:9093/api/v2/status
```

Current alerts:

```bash
curl -s http://127.0.0.1:9093/api/v2/alerts
```

Current silences:

```bash
curl -s http://127.0.0.1:9093/api/v2/silences
```

---

# 35. Alert Action Service

Directory:

```text
/opt/promax-monitoring/alert-action
```

Virtual environment:

```text
/opt/promax-monitoring/alert-action/venv
```

Systemd service:

```text
alert-action.service
```

---

## Check Service

```bash
sudo systemctl status alert-action --no-pager
```

## Restart

```bash
sudo systemctl restart alert-action
```

## Enable on Boot

```bash
sudo systemctl enable alert-action
```

## Logs

```bash
sudo journalctl -u alert-action -f
```

---

# 36. Alert Action Environment

The service uses:

```text
/opt/promax-monitoring/alert-action/.env
```

Required variables:

```env
SLACK_BOT_TOKEN=<SECRET>
SLACK_SIGNING_SECRET=<SECRET>
ALERTMANAGER_URL=http://127.0.0.1:9093
SLACK_APP_TOKEN=<SECRET>
```

Secure permissions:

```bash
chmod 600 /opt/promax-monitoring/alert-action/.env
```

Never commit this file to Git.

---

# 37. Verify Slack Environment Safely

```bash
PID=$(systemctl show -p MainPID --value alert-action)

sudo tr '\0' '\n' < /proc/$PID/environ |
grep '^SLACK_' |
sed 's/=.*$/=<SET>/'
```

Expected:

```text
SLACK_BOT_TOKEN=<SET>
SLACK_SIGNING_SECRET=<SET>
SLACK_APP_TOKEN=<SET>
```

---

# 38. Slack Socket Mode

Slack Socket Mode was selected because no public HTTPS endpoint/domain was available.

Architecture:

```text
Alertmanager
      │
      ▼
Alert Action Service
      │
      │ Socket Mode
      ▼
Slack
```

Channels:

```text
#warning-alerts
#critical-alters
```

---

# 39. Slack Alert Behaviour

A firing alert appears as:

```text
🚨 ALERT FIRING
```

with information such as:

```text
Alert
Severity
Server
Summary
Description
Status
```

Interactive buttons:

```text
ACCEPT
REJECT
```

---

# 40. ACCEPT Workflow

When ACCEPT is clicked:

```text
Slack
  ↓
Alert Action Service
  ↓
Read alert labels
  ↓
Create Alertmanager silence
  ↓
Silence for 4 hours
  ↓
Update Slack message
```

The silence uses the alert labels so the firing alert is suppressed.

Comment format:

```text
Alert acknowledged by <Slack user> via Slack
```

The alert remains unresolved, but repeated notifications stop while the silence is active.

After four hours:

```text
If alert is still firing
        ↓
Silence expires
        ↓
Alert can notify again
```

---

# 41. REJECT Workflow

When REJECT is clicked:

```text
Slack
  ↓
Alert Action Service
  ↓
No silence
  ↓
Alert remains active
  ↓
Normal Alertmanager notifications continue
```

The rejector name is intentionally not displayed.

---

# 42. Alertmanager Silence Verification

List silences:

```bash
curl -s http://127.0.0.1:9093/api/v2/silences
```

Check alerts:

```bash
curl -s http://127.0.0.1:9093/api/v2/alerts
```

A successfully acknowledged alert should show that it is suppressed by the relevant silence.

---

# 43. Ansible

Ansible runs on:

```text
TBC-Monitoring
```

Project:

```text
/opt/promax-monitoring/ansible
```

Configuration:

```text
ansible.cfg
```

Inventory:

```text
inventory/production.ini
```

Playbook:

```text
playbooks/install-alloy.yml
```

Role:

```text
roles/alloy
```

---

# 44. Ansible Inventory

Example:

```ini
[ecommerce]
ecommerce-server ansible_host=<AWS_SERVER_PUBLIC_IP>

[webservers]
web-server ansible_host=<SERVER2_PUBLIC_IP>

[all:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=/root/.ssh/id_ed25519
```

Replace placeholders with actual private production values.

---

# 45. Ansible Connectivity

```bash
cd /opt/promax-monitoring/ansible
```

Test:

```bash
ansible all -m ping
```

Only ecommerce:

```bash
ansible ecommerce -m ping
```

Deploy Alloy:

```bash
ansible-playbook playbooks/install-alloy.yml
```

---

# 46. Alloy Ansible Role

The Alloy role automates:

1. Alloy installation
2. Alloy configuration
3. Configuration deployment
4. Systemd enablement
5. Alloy restart
6. Configuration updates

Structure:

```text
roles/alloy/
├── defaults/
│   └── main.yml
├── handlers/
│   └── main.yml
├── tasks/
│   └── main.yml
└── templates/
    └── config.alloy.j2
```

---

# 47. Production vs AWS Lab

## AWS Lab

```text
AWS Server
    │
    │ Alloy
    │
    ├── localhost:19090
    │        ↓
    │     SSH Tunnel
    │        ↓
    │   Prometheus :9090
    │
    └── localhost:13100
             ↓
          SSH Tunnel
             ↓
          Loki :3100
```

## Production

```text
Promax Server
      │
      │ Private Network
      ▼
TBC-Monitoring
      │
      ├── Prometheus :9090
      │
      └── Loki :3100
```

Reverse SSH tunnels are therefore a **lab workaround**, not the preferred production architecture.

---

# 48. Why AWS Private IP Did Not Work

The AWS VPC and on-premises network are separate networks.

The AWS server could not directly reach:

```text
<MONITORING_PRIVATE_IP>:9090
```

because there was no:

```text
VPN
Direct Connect
Site-to-Site private routing
```

between the networks.

Opening TCP 9090 in the AWS Security Group does not create connectivity to an on-premises private IP.

For production, Promax servers should be on the same reachable private network as the monitoring server or connected through appropriate private networking.

---

# 49. Monitoring Server Health Checks

Run:

```bash
docker compose ps
```

Prometheus:

```bash
curl http://127.0.0.1:9090/-/healthy
```

Loki:

```bash
curl http://127.0.0.1:3100/ready
```

Alertmanager:

```bash
curl -s http://127.0.0.1:9093/api/v2/status
```

Grafana:

```bash
curl -I http://127.0.0.1:3000
```

Alert Action:

```bash
sudo systemctl status alert-action --no-pager
```

---

# 50. Monitored Server Health Checks

Alloy:

```bash
sudo systemctl status alloy --no-pager
```

Nginx:

```bash
sudo systemctl status nginx --no-pager
```

Nginx status:

```bash
curl http://127.0.0.1/nginx_status
```

MySQL:

```bash
sudo systemctl status mysql --no-pager
```

MySQL port:

```bash
ss -lntp | grep 3306
```

Nginx logs:

```bash
ls -lh /var/log/nginx/
```

System logs:

```bash
ls -lh /var/log/syslog /var/log/auth.log
```

---

# 51. Troubleshooting

## Alloy Failed

```bash
sudo systemctl status alloy --no-pager
```

```bash
sudo journalctl -u alloy -n 100 --no-pager
```

Restart:

```bash
sudo systemctl restart alloy
```

---

## Prometheus Not Receiving Metrics

Check:

```bash
curl http://127.0.0.1:9090/-/healthy
```

Targets:

```bash
curl -s http://127.0.0.1:9090/api/v1/targets
```

Container logs:

```bash
docker logs prometheus --tail 100
```

---

## Loki Not Receiving Logs

```bash
curl http://127.0.0.1:3100/ready
```

```bash
docker logs loki --tail 100
```

```bash
sudo journalctl -u alloy -n 100 --no-pager
```

---

## Nginx Logs Missing

Check:

```bash
ls -lh /var/log/nginx/
```

Generate request:

```bash
curl http://127.0.0.1/nginx_status
```

Check:

```bash
tail -5 /var/log/nginx/access.log
```

Then Grafana:

```logql
{job="nginx"}
```

---

## System Logs Missing

Check:

```bash
ls -l /var/log/syslog /var/log/auth.log
```

If missing:

```bash
sudo journalctl -n 30 --no-pager
```

Use Alloy journal collection where appropriate.

---

## MySQL Metrics Missing

Check:

```bash
sudo systemctl status mysql --no-pager
```

Check port:

```bash
ss -lntp | grep 3306
```

Test:

```bash
mysql -u alloy -p \
-h 127.0.0.1 \
-P 3306 \
-e "SELECT VERSION();"
```

Check Alloy:

```bash
sudo journalctl -u alloy -n 100 --no-pager
```

---

# 52. Production Security

Before production deployment:

* Use private IPs.
* Do not expose Prometheus publicly.
* Do not expose Loki publicly.
* Do not expose Alertmanager publicly.
* Protect Grafana with HTTPS.
* Use strong Grafana credentials.
* Restrict firewall rules.
* Use SSH keys.
* Store secrets securely.
* Do not commit `.env`.
* Do not commit PEM/private keys.
* Use least-privilege MySQL monitoring permissions.
* Configure monitoring-server backups.
* Configure Loki persistent storage.
* Monitor monitoring-server disk usage.
* Enable Alloy at boot.
* Use a production WSGI server for the Alert Action Service.
* Add duplicate webhook/idempotency handling before production.
* Review Slack tokens and rotate any credentials that were exposed during testing.

---

# 53. Important Ports

## Monitoring Server

| Port | Service              | Purpose          |
| ---: | -------------------- | ---------------- |
| 3000 | Grafana              | Dashboard        |
| 9090 | Prometheus           | Metrics          |
| 9093 | Alertmanager         | Alert management |
| 3100 | Loki                 | Logs             |
| 5000 | Alert Action Service | Alert webhook    |

## Monitored Servers

| Port | Service        |
| ---: | -------------- |
|   22 | SSH            |
|   80 | HTTP           |
|  443 | HTTPS          |
| 3306 | MySQL          |
| 9113 | Nginx Exporter |

Only required internal access should be allowed.

---

# 54. Complete Restart Procedure

Monitoring server:

```bash
cd /opt/promax-monitoring
docker compose restart
```

Check:

```bash
docker compose ps
```

Alloy:

```bash
sudo systemctl restart alloy
```

Alert Action:

```bash
sudo systemctl restart alert-action
```

Verify:

```bash
curl http://127.0.0.1:9090/-/healthy
curl http://127.0.0.1:3100/ready
curl -s http://127.0.0.1:9093/api/v2/status
```

---

# 55. Full Production Deployment Process

When Promax production server IPs are available:

### Step 1 — Add servers

Edit:

```bash
nano /opt/promax-monitoring/ansible/inventory/production.ini
```

Add:

```ini
[ecommerce]
promax-ecommerce ansible_host=<PROMAX_SERVER_IP>

[webservers]
promax-web ansible_host=<PROMAX_SERVER_IP>
```

---

### Step 2 — Test Ansible

```bash
cd /opt/promax-monitoring/ansible
ansible all -m ping
```

---

### Step 3 — Deploy Alloy

```bash
ansible-playbook playbooks/install-alloy.yml
```

---

### Step 4 — Verify Alloy

On each production server:

```bash
sudo systemctl status alloy --no-pager
```

---

### Step 5 — Verify Metrics

Open Prometheus and verify:

```promql
up
```

Then:

```promql
node_cpu_seconds_total
```

and:

```promql
node_memory_MemAvailable_bytes
```

---

### Step 6 — Verify MySQL

```promql
mysql_up
```

Expected:

```text
1
```

---

### Step 7 — Verify Nginx

```bash
curl http://127.0.0.1/nginx_status
```

Then verify:

```promql
nginx_up
```

if the Nginx exporter exposes that metric.

---

### Step 8 — Verify Logs

Nginx:

```logql
{job="nginx"}
```

System:

```logql
{job="system"}
```

Authentication:

```logql
{job="system", service="auth"}
```

---

### Step 9 — Open Grafana

Open:

```text
🏢 Promax Production Dashboard
```

Verify:

```text
Servers
CPU
Memory
Disk
Network
Load
MySQL
Nginx
Nginx Logs
System Logs
```

---

### Step 10 — Test Alerts

Generate a controlled CPU/memory condition on a test server.

Verify:

```text
Prometheus
    ↓
Alertmanager
    ↓
Alert Action Service
    ↓
Slack
```

---

### Step 11 — Test ACCEPT

Click:

```text
ACCEPT
```

Verify Alertmanager silence:

```bash
curl -s http://127.0.0.1:9093/api/v2/silences
```

---

### Step 12 — Test REJECT

Click:

```text
REJECT
```

Verify no silence is created.

---

# 56. Final Production Architecture

```text
                         TBC-Monitoring
                    ┌──────────────────────┐
                    │                      │
                    │     Prometheus       │
                    │     Grafana          │
                    │     Alertmanager     │
                    │     Loki             │
                    │     Alert Action     │
                    │     Ansible          │
                    │                      │
                    └──────────┬───────────┘
                               │
                       Private Network
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    Promax Server 1      Promax Server 2      Promax Server N
          │                    │                    │
        Alloy                Alloy                Alloy
          │                    │                    │
     ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
     │         │          │         │          │         │
  Metrics    Logs      Metrics    Logs      Metrics    Logs
     │         │          │         │          │         │
     └────┬────┘          └────┬────┘          └────┬────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
             Prometheus                    Loki
                 │                           │
                 └────────────┬──────────────┘
                              ▼
                           Grafana
                              │
                              ▼
                         Alertmanager
                              │
                              ▼
                     Alert Action Service
                              │
                              ▼
                            Slack
```

---

# 57. Project Status

## Completed

* [x] Monitoring server
* [x] Prometheus
* [x] Grafana
* [x] Alertmanager
* [x] Loki
* [x] Prometheus → Alertmanager integration
* [x] Grafana Alloy
* [x] Node/system metrics
* [x] MySQL monitoring
* [x] Nginx stub_status
* [x] Nginx log collection
* [x] Loki log ingestion
* [x] Nginx Grafana panels
* [x] System log Grafana panels
* [x] Infrastructure alert rules
* [x] Slack warning alerts
* [x] Slack critical alerts
* [x] Slack Socket Mode
* [x] Slack ACCEPT button
* [x] Slack REJECT button
* [x] Alertmanager silence on ACCEPT
* [x] Four-hour acknowledgement silence
* [x] Ansible Alloy deployment structure
* [x] AWS lab testing
* [x] Reverse SSH lab connectivity

## Remaining for Production

* [ ] Add actual Promax production IPs
* [ ] Deploy Alloy to all Promax servers
* [ ] Install/configure Nginx exporter on required servers
* [ ] Confirm system-log collection method per server
* [ ] Replace AWS reverse SSH with direct private connectivity
* [ ] Secure/rotate all secrets
* [ ] Configure HTTPS for Grafana
* [ ] Configure monitoring-server backups
* [ ] Harden firewall rules
* [ ] Productionize Alert Action Service with WSGI
* [ ] Add webhook idempotency/duplicate protection
* [ ] Finalize production alert escalation policy

---

# 58. Git Security

Before pushing this project to GitHub:

```bash
git status
```

Search for IP addresses:

```bash
git grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}'
```

Search for possible Slack credentials:

```bash
git grep -nE 'xoxb-|xapp-|SLACK_SIGNING_SECRET'
```

Never commit:

```text
.env
*.pem
*.key
id_rsa
id_ed25519
private keys
database passwords
Slack tokens
API secrets
production credentials
```

Recommended `.gitignore`:

```gitignore
.env
*.pem
*.key
id_rsa
id_ed25519
__pycache__/
venv/
*.log
```

---

# 59. Final Notes

The AWS environment was used only as a lab/testing environment.

The preferred production architecture is:

```text
Promax Servers
      ↓
Grafana Alloy
      ↓
Prometheus + Loki
      ↓
Grafana
      ↓
Alertmanager
      ↓
Alert Action Service
      ↓
Slack

Reverse SSH tunnels should not be required in the final production architecture.
