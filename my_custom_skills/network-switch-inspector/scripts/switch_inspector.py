#!/usr/bin/env python3
"""
Network Switch Inspector
Supports H3C and Huawei switches via SSH
"""

import paramiko
import time
import yaml
import json
import sys
from typing import Dict, List, Optional
from datetime import datetime


class SwitchInspector:
    """SSH-based network switch inspector for H3C and Huawei devices"""

    # Vendor-specific command mappings - Comprehensive professional inspection
    COMMANDS = {
        'h3c': {
            # 基础系统信息
            'system_info': 'display version',
            'device_info': 'display device',
            'cpu_memory': 'display cpu-usage',
            'memory_usage': 'display memory',
            'bootrom_info': 'display boot-loader',
            'flash_info': 'display flash',

            # 接口和链路状态
            'interfaces': 'display interface brief',
            'interface_status': 'display interface',
            'interface_counters': 'display interface counters',
            'interface_errors': 'display interface | include error',
            'link_flap': 'display interface | include Last link flapping',
            'transceiver': 'display transceiver diagnosis interface',
            'transceiver_info': 'display transceiver interface',

            # 二层网络
            'vlan': 'display vlan',
            'vlan_all': 'display vlan all',
            'mac_table': 'display mac-address',
            'mac_statistics': 'display mac-address statistics',
            'stp': 'display stp',
            'stp_brief': 'display stp brief',
            'lacp': 'display link-aggregation summary',
            'lldp_neighbor': 'display lldp neighbor-information',

            # 三层网络
            'arp_table': 'display arp',
            'arp_statistics': 'display arp statistics',
            'routing_table': 'display ip routing-table',
            'routing_statistics': 'display ip routing-table statistics',
            'ospf_peer': 'display ospf peer',
            'bgp_peer': 'display bgp peer',

            # 性能和资源
            'qos_policy': 'display qos policy interface',
            'acl': 'display acl all',
            'cpu_history': 'display cpu-usage history',
            'process': 'display process cpu',

            # 安全和认证
            'users': 'display users',
            'ssh_status': 'display ssh server status',
            'ssh_session': 'display ssh server session',
            'dot1x': 'display dot1x',
            'port_security': 'display port-security',

            # 环境监控
            'temperature': 'display environment',
            'power': 'display power',
            'fan': 'display fan',
            'alarm': 'display alarm',

            # 日志和诊断
            'logs': 'display logbuffer',
            'logs_reverse': 'display logbuffer reverse',
            'diagnostic': 'display diagnostic-information',
            'ntp': 'display ntp status',
            'clock': 'display clock',

            # 配置和备份
            'current_config': 'display current-configuration',
            'saved_config': 'display saved-configuration',
            'config_diff': 'display configuration changes',
            'startup_info': 'display startup',

            # 堆叠和虚拟化
            'irf': 'display irf',
            'irf_link': 'display irf link',
            'mad': 'display mad',

            # 可靠性
            'transceiver_alarm': 'display transceiver alarm',
            'device_manuinfo': 'display device manuinfo'
        },
        'huawei': {
            # 基础系统信息
            'system_info': 'display version',
            'device_info': 'display device',
            'cpu_memory': 'display cpu-usage',
            'memory_usage': 'display memory-usage',
            'bootrom_info': 'display boot-loader',
            'flash_info': 'display flash',

            # 接口和链路状态
            'interfaces': 'display interface brief',
            'interface_status': 'display interface',
            'interface_counters': 'display interface counters',
            'interface_errors': 'display interface | include error',
            'optical_module': 'display transceiver',
            'optical_diagnosis': 'display transceiver diagnosis',

            # 二层网络
            'vlan': 'display vlan',
            'vlan_all': 'display vlan all',
            'mac_table': 'display mac-address',
            'mac_statistics': 'display mac-address count',
            'stp': 'display stp',
            'stp_brief': 'display stp brief',
            'eth_trunk': 'display eth-trunk',
            'lldp_neighbor': 'display lldp neighbor brief',

            # 三层网络
            'arp_table': 'display arp',
            'arp_statistics': 'display arp statistics',
            'routing_table': 'display ip routing-table',
            'routing_statistics': 'display ip routing-table statistics',
            'ospf_peer': 'display ospf peer',
            'bgp_peer': 'display bgp peer',

            # 性能和资源
            'qos_policy': 'display qos policy interface',
            'acl': 'display acl all',
            'cpu_history': 'display cpu-usage history',
            'process': 'display process cpu',

            # 安全和认证
            'users': 'display users',
            'ssh_status': 'display ssh server status',
            'ssh_session': 'display ssh server session',
            'dot1x': 'display dot1x',
            'port_security': 'display port-security',

            # 环境监控
            'temperature': 'display temperature',
            'power': 'display power',
            'fan': 'display fan',
            'alarm': 'display alarm all',

            # 日志和诊断
            'logs': 'display logbuffer',
            'logs_reverse': 'display logbuffer reverse',
            'diagnostic': 'display diagnostic-information',
            'ntp': 'display ntp status',
            'clock': 'display clock',

            # 配置和备份
            'current_config': 'display current-configuration',
            'saved_config': 'display saved-configuration',
            'startup_info': 'display startup',

            # 堆叠和虚拟化
            'stack': 'display stack',
            'stack_port': 'display stack port',
            'css': 'display css',

            # 可靠性
            'elabel': 'display elabel',
            'device_manufacture': 'display device manufacture-info'
        }
    }

    # Inspection modes - predefined command sets for different inspection levels
    INSPECTION_MODES = {
        'quick': [
            'system_info', 'cpu_memory', 'memory_usage', 'interfaces',
            'temperature', 'power', 'fan', 'logs'
        ],
        'standard': [
            'system_info', 'device_info', 'cpu_memory', 'memory_usage',
            'interfaces', 'interface_status', 'vlan', 'mac_table',
            'arp_table', 'routing_table', 'temperature', 'power', 'fan',
            'logs', 'alarm', 'stp_brief', 'lldp_neighbor'
        ],
        'full': 'all',  # All available commands
        'health': [
            'system_info', 'cpu_memory', 'memory_usage', 'cpu_history',
            'process', 'interfaces', 'interface_counters', 'interface_errors',
            'temperature', 'power', 'fan', 'alarm', 'logs'
        ],
        'network': [
            'interfaces', 'interface_status', 'vlan', 'vlan_all',
            'mac_table', 'mac_statistics', 'arp_table', 'routing_table',
            'stp', 'lacp', 'lldp_neighbor', 'ospf_peer', 'bgp_peer'
        ],
        'security': [
            'users', 'ssh_status', 'ssh_session', 'dot1x', 'port_security',
            'acl', 'logs', 'alarm'
        ]
    }

    def __init__(self, host: str, username: str, password: str, vendor: str,
                 port: int = 22, timeout: int = 10):
        """
        Initialize switch inspector

        Args:
            host: Switch IP address
            username: SSH username
            password: SSH password
            vendor: Switch vendor ('h3c' or 'huawei')
            port: SSH port (default 22)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.username = username
        self.password = password
        self.vendor = vendor.lower()
        self.port = port
        self.timeout = timeout
        self.client = None
        self.shell = None

        if self.vendor not in self.COMMANDS:
            raise ValueError(f"Unsupported vendor: {vendor}. Supported: h3c, huawei")

    def connect(self) -> bool:
        """
        Establish SSH connection to switch

        Returns:
            bool: True if connection successful
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            print(f"Connecting to {self.host}...")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )

            # Start interactive shell
            self.shell = self.client.invoke_shell()
            time.sleep(1)

            # Clear initial output
            if self.shell.recv_ready():
                self.shell.recv(65535)

            # Disable pagination
            self._disable_pagination()

            print(f"[OK] Connected to {self.host}")
            return True

        except Exception as e:
            print(f"[ERROR] Connection failed to {self.host}: {str(e)}")
            return False

    def _disable_pagination(self):
        """Disable pagination on the switch console"""
        if self.vendor == 'h3c':
            self._send_command('screen-length disable')
        elif self.vendor == 'huawei':
            self._send_command('screen-length 0 temporary')

    def _send_command(self, command: str, wait_time: float = 2.0, stream_output: bool = False) -> str:
        """
        Send command to switch and return output

        Args:
            command: Command to execute
            wait_time: Time to wait for output (seconds)
            stream_output: If True, print output to stdout as it arrives

        Returns:
            str: Command output
        """
        if not self.shell:
            raise RuntimeError("Not connected to switch")

        # Send command
        self.shell.send(command + '\n')
        
        # Wait for initial data
        time.sleep(0.5)
        
        # Dynamic wait for command completion
        max_retries = int(wait_time * 10) + 10  # Base wait + buffer
        if wait_time > 5:
             max_retries = int(wait_time * 5) # Longer commands check less frequently

        output = ""
        last_data_time = time.time()
        
        while True:
            if self.shell.recv_ready():
                chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                output += chunk
                if stream_output:
                    print(chunk, end='', flush=True)
                last_data_time = time.time()
            else:
                # Break if no data for 2 seconds (command likely finished)
                if time.time() - last_data_time > 2.0:
                    break
                # Break if total time exceeded massive limit (safety net)
                if time.time() - last_data_time > wait_time and len(output) == 0:
                     break
            
            time.sleep(0.1)

        return output

    def execute_raw_commands(self, commands: List[str], stream_output: bool = True) -> Dict[str, str]:
        """
        Execute a list of raw commands directly
        
        Args:
            commands: List of command strings
            stream_output: Whether to print output to console
            
        Returns:
            dict: Results {command: output}
        """
        results = {}
        if stream_output:
            print(f"\\n[INFO] Executing {len(commands)} raw commands on {self.host}...")
            
        for cmd in commands:
            if stream_output:
                print(f"\\n> {cmd}")
            try:
                # Use longer timeout for raw commands as they might be complex
                output = self._send_command(cmd, wait_time=5.0, stream_output=stream_output)
                results[cmd] = output
            except Exception as e:
                err_msg = f"ERROR: {str(e)}"
                if stream_output:
                    print(err_msg)
                results[cmd] = err_msg
                
        return results

    def execute_inspection(self, items: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Execute inspection commands

        Args:
            items: List of inspection items to check. If None, check all.
                   Options: system_info, cpu_memory, memory_usage, interfaces,
                           interface_status, vlan, mac_table, arp_table,
                           routing_table, logs, temperature, power, fan

        Returns:
            dict: Inspection results {item: output}
        """
        if not self.shell:
            raise RuntimeError("Not connected to switch")

        # If no items specified, check all
        if items is None:
            items = list(self.COMMANDS[self.vendor].keys())

        results = {}
        vendor_commands = self.COMMANDS[self.vendor]

        for item in items:
            if item not in vendor_commands:
                print(f"[WARNING] Unknown inspection item: {item}")
                continue

            command = vendor_commands[item]
            print(f"  Executing: {command}")

            try:
                output = self._send_command(command)
                results[item] = output
            except Exception as e:
                print(f"  [ERROR] Failed: {str(e)}")
                results[item] = f"ERROR: {str(e)}"

        return results

    def disconnect(self):
        """Close SSH connection"""
        if self.shell:
            self.shell.close()
        if self.client:
            self.client.close()
        print(f"[OK] Disconnected from {self.host}")


def load_devices(config_file: str) -> List[Dict]:
    """
    Load device list from YAML configuration file

    Args:
        config_file: Path to YAML config file

    Returns:
        list: List of device configurations
    """
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config.get('devices', [])


def inspect_device(device_config: Dict, items: Optional[List[str]] = None, raw_commands: Optional[List[str]] = None) -> Dict:
    """
    Inspect a single device or run raw commands

    Args:
        device_config: Device configuration dict
        items: Optional list of inspection items
        raw_commands: Optional list of raw commands to execute

    Returns:
        dict: Inspection results
    """
    inspector = SwitchInspector(
        host=device_config['host'],
        username=device_config['username'],
        password=device_config['password'],
        vendor=device_config['vendor'],
        port=device_config.get('port', 22),
        timeout=device_config.get('timeout', 10)
    )

    result = {
        'device': device_config.get('name', device_config['host']),
        'host': device_config['host'],
        'vendor': device_config['vendor'],
        'timestamp': datetime.now().isoformat(),
        'connection_status': 'failed',
        'data': {}
    }

    try:
        if inspector.connect():
            result['connection_status'] = 'success'
            if raw_commands:
                result['data'] = inspector.execute_raw_commands(raw_commands, stream_output=True)
            else:
                result['data'] = inspector.execute_inspection(items)
    finally:
        inspector.disconnect()

    return result


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Network Switch Inspector - Professional Network Equipment Inspection Tool')
    parser.add_argument('target', nargs='+', help='Device config file (YAML) or IP address(es)')
    parser.add_argument('-u', '--username', help='SSH username')
    parser.add_argument('-p', '--password', help='SSH password')
    parser.add_argument('-v', '--vendor', choices=['h3c', 'huawei'], help='Switch vendor')
    parser.add_argument('-P', '--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('-t', '--timeout', type=int, default=15, help='Connection timeout (default: 15)')
    parser.add_argument('-m', '--mode',
                       choices=['quick', 'standard', 'full', 'health', 'network', 'security'],
                       default='standard',
                       help='Inspection mode (ignored if -c is used)')
    parser.add_argument('-i', '--items', nargs='*', help='Specific inspection items (overrides mode)')
    parser.add_argument('-c', '--command', nargs='+', help='Execute raw commands (semicolon separated allowed). Enclose in quotes.')

    args = parser.parse_args()
    
    # Check for raw commands
    raw_commands = None
    items = None
    
    if args.command:
        # Process raw commands
        raw_commands = []
        for cmd_str in args.command:
            # Support semicolon separation for multiple commands in one string
            if ';' in cmd_str:
                raw_commands.extend([c.strip() for c in cmd_str.split(';') if c.strip()])
            else:
                raw_commands.append(cmd_str)
        print(f"[INFO] Custom Command Mode: {len(raw_commands)} commands queued\\n")
    else:
        # Normal inspection mode logic
        if args.items:
            items = args.items
            print(f"[INFO] Using custom inspection items: {len(items)} items\\n")
        else:
            mode_items = SwitchInspector.INSPECTION_MODES.get(args.mode)
            if mode_items == 'all':
                items = None
                print("[INFO] Inspection mode: FULL (all available commands)\\n")
            else:
                items = mode_items
                print(f"[INFO] Inspection mode: {args.mode.upper()} ({len(items)} items)\\n")

    # Check if target is a YAML file or IP addresses
    if len(args.target) == 1 and (args.target[0].endswith('.yaml') or args.target[0].endswith('.yml')):
        # Load from YAML file
        print(f"Loading devices from {args.target[0]}...")
        devices = load_devices(args.target[0])
        print(f"Found {len(devices)} device(s)\\n")
    else:
        # Direct IP mode - require username, password, vendor
        if not all([args.username, args.password, args.vendor]):
            print("[ERROR] When using IP address, you must specify: -u username -p password -v vendor")
            print("\\nExample:")
            print("  python switch_inspector.py 192.168.46.30 -u admin -p pass -v h3c")
            print("  python switch_inspector.py 192.168.46.30 -u admin -p pass -v h3c -c 'display interface brief'")
            sys.exit(1)

        # Create device configs from IP addresses
        devices = []
        for ip in args.target:
            device = {
                'name': f"{args.vendor.upper()}-{ip}",
                'host': ip,
                'username': args.username,
                'password': args.password,
                'vendor': args.vendor,
                'port': args.port,
                'timeout': args.timeout
            }
            devices.append(device)

        if not raw_commands:
            print(f"Batch inspecting {len(devices)} device(s)...\\n")

    # Inspect each device
    results = []
    for i, device in enumerate(devices, 1):
        if not raw_commands:
            print(f"[{i}/{len(devices)}] Inspecting {device.get('name', device['host'])}...")
            
        result = inspect_device(device, items, raw_commands)
        results.append(result)
        print()

    # Save results
    output_file = f"inspection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if not raw_commands:
        print(f"[OK] Results saved to {output_file}")
        success_count = sum(1 for r in results if r['connection_status'] == 'success')
        print(f"\\nSummary: {success_count}/{len(results)} devices inspected successfully")
    else:
        print(f"[OK] Command execution log saved to {output_file}")


if __name__ == '__main__':
    main()
