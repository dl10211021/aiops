---
name: zstack-cloud-dev
description: Expert guidance and code templates for developing with ZStack Cloud V4.8.10 using the Python SDK.
---

# ZStack Cloud Developer Skill

## Overview
This skill provides expert guidance and code templates for developing with ZStack Cloud V4.8.10 using the Python SDK. It covers authentication, resource management (VMs, Volumes), and handling asynchronous API operations.

## Prerequisites
- **Python 2.7** (Compatible version as per manual)
- **ZStack Cloud SDK**: Must be installed or available in the path.
- **Network Access**: Connectivity to the ZStack Cloud Management Node (default port 8080).

## Core Concepts

### 1. Authentication
All API calls require a `sessionUuid`. You obtain this by logging in with an account name and a SHA-512 hashed password.

### 2. Sync vs Async APIs
- **Sync APIs** (mostly `GET`): Return results immediately.
- **Async APIs** (Create/Update/Delete): Return a Job UUID. You must poll the job status or wait for completion. The SDK helper `async_call_wait_for_complete` handles this automatically.

### 3. Action-Based Architecture
ZStack APIs are modeled as "Actions".
- Query VM -> `QueryVmInstanceAction`
- Start VM -> `StartVmInstanceAction` (via `actions` endpoint)

## Usage Guide

### Step 1: Initialize
Set the target server IP and configure logging.

```python
import os
import zstacklib.utils.log as log
from apibinding import api

# Set server IP
os.environ['ZS_SERVER_IP'] = '192.168.1.100' 

# Configure logging
log.configure_log('/var/log/zstack/zstack-sdk.log', log_to_console=True)
```

### Step 2: Login
```python
import hashlib
import apibinding.api_actions as api_actions

def login(account, password):
    login_action = api_actions.LogInByAccountAction()
    login_action.accountName = account
    # Password must be SHA-512 hashed
    login_action.password = hashlib.sha512(password.encode('utf-8')).hexdigest()
    
    api_instance = api.Api(host=os.environ['ZS_SERVER_IP'], port='8080')
    result = api_instance.async_call_wait_for_complete(login_action)
    
    if not result.success:
        raise Exception(f"Login failed: {result.error}")
        
    return result.inventory.uuid
```

### Step 3: Execute Action (e.g., Query VM)
```python
def query_vm(session_uuid, vm_name=None):
    action = api_actions.QueryVmInstanceAction()
    action.sessionUuid = session_uuid
    if vm_name:
        action.conditions = [f"name={vm_name}"]
    
    api_instance = api.Api(host=os.environ['ZS_SERVER_IP'], port='8080')
    # Sync call for Query
    result = api_instance.sync_call(action)
    
    if not result.success:
        raise Exception(f"Query failed: {result.error}")
        
    return result.inventories
```

## Available Resources
- `templates/python_sdk_template.py`: A complete, runnable script skeleton for ZStack automation.
