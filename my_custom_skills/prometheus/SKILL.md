---
name: prometheus
description: Expert guide for installing, configuring, querying, and managing Prometheus monitoring systems, including automated AI-driven analysis.
---

# Prometheus Expert & Analyzer

This comprehensive skill combines expert guidance for Prometheus management with powerful tools for automated system analysis.

## Capabilities

1.  **Installation**: Deploy Prometheus on Linux (Binary/Systemd) or Docker.
2.  **Deployment**: Automate Node Exporter installation and target configuration.
3.  **Configuration**: Manage `prometheus.yml`, scrape configs, and alerting rules.
4.  **Querying**: Construct complex PromQL queries for system and service metrics.
5.  **Automated Analysis**: Use the bundled Python script for health checks and performance analysis.
6.  **Troubleshooting**: Diagnose issues with targets, scrape failures, and high load.

## Automated Deployment (Node Exporter)

Quickly deploy Node Exporter to a new Linux host and add it to the Prometheus Server.

**Script Location:** `scripts/deploy_node_exporter.py`

### Usage

```bash
python .claude/skills/prometheus/scripts/deploy_node_exporter.py \
  --target-ip <NEW_HOST_IP> \
  --target-pass <NEW_HOST_PASS>
```

### Key Features
*   **Auto-Install**: Deploys Node Exporter binary and sets up Systemd service.
*   **Auto-Config**: Detects hostname (`hostname: <name>`) and adds it to Prometheus config.
*   **Auto-Verify**: Polls Prometheus API until the target is UP.

### Parameters
*   `--target-ip`: (Required) IP address of the new Linux host.
*   `--target-user` / `--target-pass`: SSH credentials for the new host (Default: root / cnChervon@123).
*   `--prom-ip`: Prometheus Server IP (Default: 192.168.130.45).
*   `--prom-user` / `--prom-pass`: SSH credentials for Prometheus Server.
*   `--job-name`: Job label for the target (Default: `linux`).
*   `--pkg`: Path to local `node_exporter` tarball (optional).

## Installation

### Linux (Systemd)

Use the provided helper script `scripts/install_linux.sh` or follow these manual steps:

1.  **Download**: Get the latest release from `https://prometheus.io/download/`.
2.  **Extract**: `tar xvf prometheus-*.tar.gz`
3.  **User**: `sudo useradd --no-create-home --shell /bin/false prometheus`
4.  **Directories**:
    ```bash
    sudo mkdir /etc/prometheus
    sudo mkdir /var/lib/prometheus
    sudo chown prometheus:prometheus /etc/prometheus /var/lib/prometheus
    ```
5.  **Binaries**: Move `prometheus` and `promtool` to `/usr/local/bin/`.
6.  **Config**: Move `prometheus.yml` and `consoles/` to `/etc/prometheus/`.
7.  **Service**: Create `/etc/systemd/system/prometheus.service`.

### Docker

Quick start with Docker:

```bash
docker run -d 
    --name prometheus 
    -p 9090:9090 
    -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml 
    prom/prometheus
```

## Configuration

The main configuration file is `prometheus.yml`.

### Basic Structure

```yaml
global:
  scrape_interval: 15s # Set the scrape interval to every 15 seconds.

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['<target_ip>:9100']
```

### Hot Reload

To reload configuration without restarting:
1.  **Process**: Send `SIGHUP` signal to the process ID.
    `kill -HUP <pid>`
2.  **API**: Send POST request to `/-/reload` endpoint (requires `--web.enable-lifecycle`).
    `curl -X POST http://localhost:9090/-/reload`

## Querying (PromQL) & Analysis

### Common Metrics

*   **CPU Usage**:
    `100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`

*   **Memory Usage**:
    `100 * (1 - ((node_memory_MemFree_bytes + node_memory_Buffers_bytes + node_memory_Cached_bytes) / node_memory_MemTotal_bytes))`

*   **Disk Usage**:
    `100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes)`

*   **Network Traffic (In/Out)**:
    `rate(node_network_receive_bytes_total[5m])`
    `rate(node_network_transmit_bytes_total[5m])`

### Aggregation

*   `sum(rate(http_requests_total[5m])) by (job)`: Total request rate per job.
*   `topk(3, sum(rate(process_cpu_seconds_total[5m])) by (job))`: Top 3 CPU consumers by job.

### Automated Analysis Script

Use the bundled Python script to execute PromQL queries or perform a health check.

**Location:** `scripts/query_prometheus.py`

#### Usage

1.  **Run a Custom Query**:
    ```bash
    python .claude/skills/prometheus/scripts/query_prometheus.py \
      --url http://localhost:9090 \
      --query "up == 0"
    ```

2.  **Auto-Analysis (Health Check)**:
    Automatically checks CPU, Memory, Disk, and Up status.
    ```bash
    python .claude/skills/prometheus/scripts/query_prometheus.py \
      --url http://localhost:9090 \
      --analyze
    ```

#### Parameters
- `--url`: Base URL (e.g., `http://localhost:9090`).
- `--query`: PromQL query string.
- `--analyze`: Run built-in health checks instead of a custom query.
- `--limit`: (Optional) Limit results.
- `--type`: `instant` (default) or `range`.
- `--start` / `--end`: Time range (e.g., `1h`, `now`).

#### Analysis Logic
- **Health & Availability**: Checks for dead targets (`up == 0`) and flapping (`min_over_time(up[24h]) == 0`).
- **OS Performance**: Evaluates CPU load and Disk usage (`free < 10%`).
- **VMware/Hardware**: Monitors datastore capacity.

## Alerting

Alerting rules are defined in separate YAML files and referenced in `prometheus.yml`.

### Example Rule

```yaml
groups:
- name: example
  rules:
  - alert: InstanceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Instance {{ $labels.instance }} down"
```

## Troubleshooting

1.  **Targets Down**: Check `http://<prometheus_host>:9090/targets`. Verify network connectivity and firewall rules (port 9100 for node_exporter).
2.  **Scrape Timeout**: Increase `scrape_timeout` in configuration or reduce metrics cardinality.
3.  **High Memory**: Reduce retention period (`--storage.tsdb.retention.time`) or check for high cardinality metrics.

## Tools

*   **Promtool**: Check configuration syntax. `promtool check config prometheus.yml`
*   **Amtool**: Alertmanager CLI tool.
