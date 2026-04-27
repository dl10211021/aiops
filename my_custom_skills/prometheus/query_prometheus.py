# -*- coding: utf-8 -*-
import requests
import sys
import argparse
import json
import time

def check_prometheus_status(url):
    endpoints = {
        'Health': f'{url}/-/healthy',
        'Readiness': f'{url}/-/ready',
        'Targets': f'{url}/api/v1/targets',
        'Config': f'{url}/api/v1/status/config',
        'Uptime': f'{url}/api/v1/status/uptime',
    }
    results = {}
    for name, endpoint in endpoints.items():
        try:
            r = requests.get(endpoint, timeout=5)
            if r.status_code == 200:
                results[name] = {'status': 'OK', 'data': r.text[:500]}
            else:
                results[name] = {'status': 'FAILED', 'code': r.status_code}
        except Exception as e:
            results[name] = {'status': 'ERROR', 'error': str(e)}
    return results

def analyze_health(url):
    targets_url = f'{url}/api/v1/targets'
    try:
        r = requests.get(targets_url, timeout=10)
        r.raise_for_status()
        data = r.json()
        targets = data.get('data', {}).get('activeTargets', [])
        
        down_targets = []
        up_targets = []
        for t in targets:
            if t.get('health') != 'up':
                down_targets.append({
                    'job': t.get('labels', {}).get('job'),
                    'instance': t.get('labels', {}).get('instance'),
                    'health': t.get('health'),
                    'lastError': t.get('lastError', 'N/A')
                })
            else:
                up_targets.append({
                    'job': t.get('labels', {}).get('job'),
                    'instance': t.get('labels', {}).get('instance')
                })
        
        # Quick CPU check
        cpu_url = f'{url}/api/v1/query?query=100-(avg(irate(node_cpu_seconds_total{{mode="idle"}}[5m]))*100)'
        cpu_r = requests.get(cpu_url, timeout=10)
        cpu_data = {'status': 'N/A', 'error': 'No data'}
        if cpu_r.status_code == 200:
            cpu_vals = cpu_r.json().get('data', {}).get('result', [])
            if cpu_vals:
                cpu_data = {v['metric']['instance']: v['value'][1] for v in cpu_vals}
        
        # Quick Memory check
        mem_url = f'{url}/api/v1/query?query=100*(1-(node_memory_MemFree_bytes+node_memory_Buffers_bytes+node_memory_Cached_bytes)/node_memory_MemTotal_bytes)'
        mem_r = requests.get(mem_url, timeout=10)
        mem_data = {'status': 'N/A', 'error': 'No data'}
        if mem_r.status_code == 200:
            mem_vals = mem_r.json().get('data', {}).get('result', [])
            if mem_vals:
                mem_data = {v['metric']['instance']: v['value'][1] for v in mem_vals}

        return {
            'down_targets': down_targets,
            'up_targets_count': len(up_targets),
            'cpu_usage': cpu_data,
            'memory_usage': mem_data
        }
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--mode', choices=['status', 'analyze'], default='status')
    args = parser.parse_args()
    
    if args.mode == 'status':
        print(json.dumps(check_prometheus_status(args.url), indent=2))
    else:
        print(json.dumps(analyze_health(args.url), indent=2))