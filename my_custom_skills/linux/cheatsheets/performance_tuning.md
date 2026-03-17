# Linux Performance Tuning & Monitoring Cheatsheet

## CPU
- `top`: Real-time view of running processes. Press `1` to see per-CPU usage.
- `htop`: Interactive process viewer (easier to read than top).
- `vmstat 1`: Report virtual memory statistics. Look at `r` (runnable) and `b` (blocked) columns.
- `mpstat -P ALL 1`: Report processors related statistics.
- `sar -u 1`: Report CPU utilization.

## Memory
- `free -m`: Display amount of free and used memory in MB.
- `vmstat -s`: Display memory statistics.
- `slabtop`: Display kernel slab cache information.
- `ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head`: Top memory consuming processes.

## Disk I/O
- `iostat -xz 1`: Extended statistics for devices. Look at `%util` (utilization) and `await` (average wait time).
- `iotop`: Top disk I/O usage by process.
- `df -h`: Disk space usage.
- `du -sh *`: Disk usage of current directory contents.

## Network
- `iftop`: Display bandwidth usage on an interface.
- `nethogs`: Monitor bandwidth usage by process.
- `ss -s`: Socket summary.
- `netstat -i`: Network interface statistics (errors/drops).
- `tcpdump -i eth0`: Capture packets on interface eth0.

## Kernel Parameters (sysctl)
- `sysctl -a`: List all kernel parameters.
- `sysctl -w net.ipv4.ip_forward=1`: Enable IP forwarding temporarily.
- Edit `/etc/sysctl.conf` for permanent changes.
