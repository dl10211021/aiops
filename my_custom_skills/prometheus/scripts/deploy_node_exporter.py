#!/usr/bin/env python3
"""
Prometheus Node Exporter Deployment Tool

This script automates the deployment of Node Exporter on a Linux target
and configures the Prometheus server to scrape it.

Features:
- Deploys Node Exporter binary via SSH.
- Configures Systemd service with auto-start.
- Auto-detects target hostname for labeling.
- Updates Prometheus configuration (file_sd_configs) on the monitoring server.
- Verifies target UP status via Prometheus API.
- Handles 'job' label consistency (default: linux).

Usage:
    python deploy_node_exporter.py 
        --target-ip <IP> --target-user <USER> --target-pass <PASS> 
        --prom-ip <IP> --prom-user <USER> --prom-pass <PASS> 
        [--node-exporter-pkg <PATH>]
"""

import argparse
import paramiko
import time
import sys
import os
import requests

# Default Configuration
DEFAULT_PROM_IP = "192.168.130.45"
DEFAULT_PROM_USER = "root"
DEFAULT_PROM_PASS = "cnChervon@123"
DEFAULT_TARGET_USER = "root"
DEFAULT_TARGET_PASS = "cnChervon@123"
DEFAULT_INSTALL_DIR = "/usr/local/prometheus"
DEFAULT_PKG_PATH = "node_exporter-1.8.1.linux-amd64.tar.gz"  # Assumes local or on Prom server
REMOTE_PKG_PATH_ON_PROM = "/opt/node_exporter-1.8.1.linux-amd64.tar.gz" # Backup location

class Deployer:
    def __init__(self, args):
        self.args = args
        self.ssh_target = None
        self.ssh_prom = None

    def connect_ssh(self, host, user, password):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, username=user, password=password, timeout=10)
            return client
        except Exception as e:
            print(f"❌ SSH Connection failed to {host}: {e}")
            return None

    def run_cmd(self, client, cmd):
        stdin, stdout, stderr = client.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        return exit_status, stdout.read().decode().strip(), stderr.read().decode().strip()

    def step1_prepare_target(self):
        print(f"\n=== [1/4] Preparing Target {self.args.target_ip} ===")
        self.ssh_target = self.connect_ssh(self.args.target_ip, self.args.target_user, self.args.target_pass)
        if not self.ssh_target: return False

        # Get Hostname
        _, hostname, _ = self.run_cmd(self.ssh_target, "hostname")
        self.target_hostname = hostname
        print(f"  Hostname detected: {self.target_hostname}")

        # Create Install Dir
        self.run_cmd(self.ssh_target, f"mkdir -p {DEFAULT_INSTALL_DIR}")
        
        # Check if already installed
        code, out, _ = self.run_cmd(self.ssh_target, "systemctl is-active node_exporter")
        if out == "active":
            print("  ⚠️ Node Exporter service is already active.")
            if not self.args.force:
                print("  Skipping installation (use --force to reinstall).")
                return True
        
        return True

    def step2_transfer_and_install(self):
        print(f"\n=== [2/4] Installing Node Exporter on {self.args.target_ip} ===")
        
        # 1. Transfer File
        # Logic: If local file exists, upload it. 
        # If not, try to scp from Prometheus server (if accessible) or download.
        # Here we assume the file is on the machine running this script OR on the Prometheus server.
        
        local_pkg = self.args.pkg
        remote_pkg = f"{DEFAULT_INSTALL_DIR}/{os.path.basename(local_pkg)}"
        
        sftp = self.ssh_target.open_sftp()
        
        if os.path.exists(local_pkg):
            print(f"  Uploading local package {local_pkg}...")
            sftp.put(local_pkg, remote_pkg)
        else:
            print(f"  ⚠️ Local package {local_pkg} not found.")
            print(f"  Trying to download from Prometheus server {self.args.prom_ip}...")
            # This requires an SSH connection to Prom server to fetch file
            self.ssh_prom = self.connect_ssh(self.args.prom_ip, self.args.prom_user, self.args.prom_pass)
            if self.ssh_prom:
                sftp_prom = self.ssh_prom.open_sftp()
                try:
                    # Try common locations
                    possible_paths = [
                        f"/root/{os.path.basename(local_pkg)}",
                        f"/opt/{os.path.basename(local_pkg)}",
                        f"/usr/local/src/{os.path.basename(local_pkg)}"
                    ]
                    found_path = None
                    for path in possible_paths:
                        try:
                            sftp_prom.stat(path)
                            found_path = path
                            break
                        except FileNotFoundError:
                            continue
                    
                    if found_path:
                        print(f"  Found on Prom server: {found_path}")
                        # Download to temp then upload
                        temp_local = "temp_node_exporter.tar.gz"
                        sftp_prom.get(found_path, temp_local)
                        sftp.put(temp_local, remote_pkg)
                        os.remove(temp_local)
                        print("  Transfer successful via local relay.")
                    else:
                        print("  ❌ Could not find package on Prometheus server.")
                        return False
                except Exception as e:
                    print(f"  ❌ Failed to transfer from Prom server: {e}")
                    return False
            else:
                 print("  ❌ Cannot connect to Prometheus server to fetch package.")
                 return False

        # 2. Extract and Install
        print("  Extracting...")
        self.run_cmd(self.ssh_target, f"tar -xf {remote_pkg} -C {DEFAULT_INSTALL_DIR}")
        
        # Find extracted dir
        code, out, _ = self.run_cmd(self.ssh_target, f"find {DEFAULT_INSTALL_DIR} -maxdepth 1 -type d -name 'node_exporter-*' | head -n 1")
        extracted_dir = out
        if not extracted_dir:
            print("  ❌ Extraction failed, directory not found.")
            return False
            
        # Link
        link_path = f"{DEFAULT_INSTALL_DIR}/node_exporter"
        self.run_cmd(self.ssh_target, f"ln -sfn {extracted_dir} {link_path}")
        
        # Service
        service_content = f"""[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=root
Group=root
Type=simple
ExecStart={link_path}/node_exporter --web.listen-address=:9100

[Install]
WantedBy=multi-user.target
"""
        with sftp.file("/etc/systemd/system/node_exporter.service", 'w') as f:
            f.write(service_content)
            
        # Start
        print("  Starting service...")
        self.run_cmd(self.ssh_target, "systemctl daemon-reload && systemctl enable node_exporter && systemctl restart node_exporter")
        
        code, out, _ = self.run_cmd(self.ssh_target, "systemctl is-active node_exporter")
        if out == "active":
            print("  ✅ Service is ACTIVE.")
        else:
            print(f"  ❌ Service failed to start. Status: {out}")
            return False
            
        return True

    def step3_configure_prometheus(self):
        print(f"\n=== [3/4] Configuring Prometheus Server {self.args.prom_ip} ===")
        if not self.ssh_prom:
            self.ssh_prom = self.connect_ssh(self.args.prom_ip, self.args.prom_user, self.args.prom_pass)
            if not self.ssh_prom: return False
            
        sftp = self.ssh_prom.open_sftp()
        
        # 1. Identify Config File
        # We look for linux_hosts.yml or linux.yml in targets/
        targets_dir = "/usr/local/prometheus/prometheus/targets"
        config_file = f"{targets_dir}/linux_hosts.yml"
        
        try:
            sftp.stat(config_file)
        except FileNotFoundError:
            # Try fallback
            config_file = f"{targets_dir}/linux.yml"
            try:
                sftp.stat(config_file)
            except FileNotFoundError:
                print(f"  ❌ Could not find linux_hosts.yml or linux.yml in {targets_dir}")
                # Create one?
                config_file = f"{targets_dir}/linux_hosts.yml"
                print(f"  Creating new config file: {config_file}")
                self.run_cmd(self.ssh_prom, f"touch {config_file}")

        print(f"  Target Config File: {config_file}")
        
        # 2. Check content
        with sftp.file(config_file, 'r') as f:
            content = f.read().decode('utf-8')
            
        full_target = f"{self.args.target_ip}:9100"
        
        if full_target in content:
            print(f"  ⚠️ Target {full_target} already exists in config.")
            # We could update it, but for now skip
            # return True
        
        # 3. Append Config
        # Using the standardized format we discovered
        new_block = f"""
- labels:
    hostname: {self.target_hostname}
    instance: {self.args.target_ip}
    job: {self.args.job_name}
    os: linux
  targets:
  - {full_target}
"""
        print(f"  Appending new target configuration (Job: {self.args.job_name})...")
        
        # Append safely using temp file
        temp_remote = "/tmp/new_target_block.yml"
        with sftp.file(temp_remote, 'w') as f:
            f.write(new_block)
            
        self.run_cmd(self.ssh_prom, f"cat {temp_remote} >> {config_file}")
        self.run_cmd(self.ssh_prom, f"rm {temp_remote}")
        
        # 4. Reload
        print("  Reloading Prometheus...")
        self.run_cmd(self.ssh_prom, "killall -HUP prometheus")
        
        return True

    def step4_verify(self):
        print("\n=== [4/4] Verifying Target Status ===")
        url = f"http://{self.args.prom_ip}:9090/api/v1/targets"
        print(f"  Polling API: {url}")
        
        for i in range(10):
            try:
                response = requests.get(url, timeout=5)
                data = response.json().get('data', {}).get('activeTargets', [])
                
                for t in data:
                    labels = t.get('labels', {})
                    if self.args.target_ip in labels.get('instance', ''):
                        health = t.get('health')
                        print(f"  Attempt {i+1}: Status = {health.upper()}")
                        if health == 'up':
                            print(f"  ✅ SUCCESS: Target {self.args.target_ip} ({self.target_hostname}) is UP.")
                            return True
                        elif health == 'down':
                             print(f"  ⚠️ Target is DOWN. Error: {t.get('lastError')}")
            except Exception as e:
                print(f"  API Check Failed: {e}")
            
            time.sleep(3)
            
        print("  ❌ Verification timed out.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Deploy Node Exporter & Configure Prometheus")
    
    # Target Args
    parser.add_argument("--target-ip", required=True, help="Target Linux IP")
    parser.add_argument("--target-user", default=DEFAULT_TARGET_USER, help="Target SSH User")
    parser.add_argument("--target-pass", default=DEFAULT_TARGET_PASS, help="Target SSH Password")
    
    # Prom Args
    parser.add_argument("--prom-ip", default=DEFAULT_PROM_IP, help="Prometheus Server IP")
    parser.add_argument("--prom-user", default=DEFAULT_PROM_USER, help="Prometheus SSH User")
    parser.add_argument("--prom-pass", default=DEFAULT_PROM_PASS, help="Prometheus SSH Password")
    
    # Config Args
    parser.add_argument("--pkg", default=DEFAULT_PKG_PATH, help="Path to node_exporter tarball (local or on Prom server)")
    parser.add_argument("--job-name", default="linux", help="Prometheus Job Name (default: linux)")
    parser.add_argument("--force", action="store_true", help="Force reinstall even if service is active")
    
    args = parser.parse_args()
    
    deployer = Deployer(args)
    
    if not deployer.step1_prepare_target(): sys.exit(1)
    if not deployer.step2_transfer_and_install(): sys.exit(1)
    if not deployer.step3_configure_prometheus(): sys.exit(1)
    if not deployer.step4_verify(): sys.exit(1)
    
    print("\n✅ Deployment Completed Successfully!")

if __name__ == "__main__":
    main()
