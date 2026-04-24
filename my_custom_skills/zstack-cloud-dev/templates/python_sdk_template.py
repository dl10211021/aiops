# -*- coding: utf-8 -*-
import os
import hashlib
import zstacklib.utils.log as log
import apibinding.api_actions as api_actions
from apibinding import api

# =================CONFIGURATION=================
ZS_SERVER_IP = "192.168.0.1"  # Replace with your ZStack Management Node IP
ZS_PORT = "8080"
ACCOUNT_NAME = "admin"
PASSWORD = "password"         # Replace with your password
# ===============================================

# Setup Environment
os.environ['ZS_SERVER_IP'] = ZS_SERVER_IP
log.configure_log('./zstack-sdk.log', log_to_console=True)

class ZStackClient:
    def __init__(self, ip, port, account, password):
        self.ip = ip
        self.port = port
        self.account = account
        self.password = password
        self.session_uuid = None
        self.api_instance = api.Api(host=self.ip, port=self.port)

    def login(self):
        """Logs in and retrieves Session UUID."""
        print(f"Logging in as {self.account}...")
        action = api_actions.LogInByAccountAction()
        action.accountName = self.account
        # ZStack requires SHA-512 hashed password
        action.password = hashlib.sha512(self.password.encode('utf-8')).hexdigest()
        
        # Login is an Async call (returns a Job)
        evt = self.api_instance.async_call_wait_for_complete(action)
        
        if not evt.success:
            raise Exception(f"Login Error: {evt.error}")
        
        self.session_uuid = evt.inventory.uuid
        print(f"Login Successful. Session UUID: {self.session_uuid}")
        return self.session_uuid

    def logout(self):
        if not self.session_uuid:
            return
        
        print("Logging out...")
        action = api_actions.LogOutAction()
        action.sessionUuid = self.session_uuid
        self.api_instance.async_call_wait_for_complete(action)
        print("Logged out.")

    def query_vms(self, vm_name=None):
        """Query VM Instances."""
        print("Querying VMs...")
        action = api_actions.QueryVmInstanceAction()
        action.sessionUuid = self.session_uuid
        if vm_name:
            # Add query condition
            action.conditions = [f"name={vm_name}"]
            
        # Query is a Sync call
        result = self.api_instance.sync_call(action)
        
        if not result.success:
            raise Exception(f"Query Error: {result.error}")
            
        return result.inventories

    def start_vm(self, vm_uuid):
        """Start a VM Instance (Async Action)."""
        print(f"Starting VM {vm_uuid}...")
        action = api_actions.StartVmInstanceAction()
        action.uuid = vm_uuid
        action.sessionUuid = self.session_uuid
        
        # Async call - waits for completion
        evt = self.api_instance.async_call_wait_for_complete(action)
        
        if not evt.success:
            raise Exception(f"Start VM Error: {evt.error}")
            
        print("VM Started successfully.")
        return evt.inventory

# =================MAIN EXECUTION=================
if __name__ == "__main__":
    client = ZStackClient(ZS_SERVER_IP, ZS_PORT, ACCOUNT_NAME, PASSWORD)
    try:
        client.login()
        
        # Example: Query all VMs
        vms = client.query_vms()
        for vm in vms:
            print(f"VM: {vm.name}, UUID: {vm.uuid}, State: {vm.state}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.logout()
