---
name: linux
description: Expert guide for Linux system administration, shell scripting, and troubleshooting.
---

# Linux System Administration Skill

## Overview
This skill provides expert capabilities for managing Linux environments (Ubuntu, CentOS/RHEL, Debian). It covers command-line operations, system monitoring, security management, and advanced shell scripting.

## Core Capabilities

### 1. System Monitoring & Performance
- **CPU/Memory**: `top`, `htop`, `vmstat 1`, `free -h`
- **Disk I/O**: `iostat -xz 1`, `iotop`
- **Network**: `iftop`, `nethogs`, `ss -tulpn`, `netstat -anp`
- **Logs**: `journalctl -xe`, `tail -f /var/log/syslog`, `dmesg -T`

### 2. File Operations
- **Search**: `find . -name "*.log" -mtime +7`, `grep -r "error" /var/log`
- **Archives**: 
  - Compress: `tar -czvf archive.tar.gz /path/to/dir`
  - Extract: `tar -xzvf archive.tar.gz`
- **Permissions**: `chmod 755 script.sh`, `chown user:group file`

### 3. Networking
- **Check Ports**: `nc -zv host port`, `telnet host port`
- **Transfer**: `rsync -avz source/ user@host:/dest/`, `scp file user@host:~`
- **Firewall**: 
  - UFW: `ufw allow 80/tcp`, `ufw status`
  - Firewalld: `firewall-cmd --permanent --add-port=80/tcp`, `firewall-cmd --reload`

### 4. Package Management
- **Debian/Ubuntu**: `apt update && apt upgrade`, `apt install package`
- **RHEL/CentOS**: `dnf update`, `dnf install package`

## Batch Operations (New!)

This skill now includes a powerful **Batch Ops Toolkit** for managing multiple servers simultaneously.

### 1. Health Inspector (`batch_health_inspector.py`)
Deep scans servers for critical errors, resource exhaustion, and kernel parameter issues.
```bash
python scripts/batch_runner/batch_health_inspector.py --ips 192.168.1.10 192.168.1.11 --user root
```

### 2. System Optimizer (`batch_optimizer.py`)
Applies performance tuning (sysctl, limits) and fixes common issues.
- **Standard Optimization**: `python scripts/batch_runner/batch_optimizer.py --ips 192.168.1.10`
- **Deep Slim (Remove GUI)**: `python scripts/batch_runner/batch_optimizer.py --ips 192.168.1.10 --slim` (Disables GNOME, Tracker, PackageKit, etc.)

### 3. Service Manager (`batch_service_manager.py`)
Bulk start/stop/enable/disable/mask services.
```bash
python scripts/batch_runner/batch_service_manager.py --ips 192.168.1.10 --action disable --services collectd
```

### 4. Network Configurator (`batch_network_config.py`)
Batch configure static IPs and DNS on RHEL/CentOS systems.
```bash
python scripts/batch_runner/batch_network_config.py --hosts 192.168.1.10 --dns 8.8.8.8
```

## Available Resources
- `scripts/ssh_runner.py`: Single-host remote command execution.
- `scripts/batch_runner/`: Directory containing all batch operation scripts.
- `templates/bash_robust_template.sh`: Production-ready Bash script template.
- `cheatsheets/performance_tuning.md`: Quick reference for Linux performance tuning.