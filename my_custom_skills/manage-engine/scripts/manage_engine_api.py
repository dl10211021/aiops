import requests
import json
import logging
import os
import time
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.json or environment variables."""
    # Try environment variables first
    url = os.getenv("MANAGE_ENGINE_URL")
    key = os.getenv("MANAGE_ENGINE_API_KEY")
    
    if url and key:
        return url, key
        
    # Try config.json in parent directory or current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    config_paths = [
        os.path.join(parent_dir, "config.json"),
        os.path.join(script_dir, "config.json"),
        "config.json"
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                    return config.get("url"), config.get("api_key")
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")
                
    # Fallback to defaults
    return "https://192.168.129.132:8443", "9f6f30a5b2163fd920fea01e3d5d411f"

DEFAULT_URL, DEFAULT_API_KEY = load_config()

class Attributes:
    """Common Attribute IDs for ManageEngine AppManager."""
    AVAILABILITY = "17" # Standard Availability
    HEALTH = "18"       # Standard Health
    
    # System Metrics (Windows/Linux)
    CPU_UTILIZATION = "708" 
    PHYSICAL_MEMORY_UTILIZATION = "685" 
    DISK_UTILIZATION = "711" 
    
    # Process/Service Specific
    PROCESS_AVAILABILITY = "715"
    PROCESS_HEALTH = "716"
    PROCESS_INSTANCE_COUNT = "717"
    
    # Response Time
    RESPONSE_TIME = "16"

class AppManagerClient:
    """
    Optimized Client for ManageEngine Applications Manager (AppManager) REST API.
    Ref: https://www.manageengine.com/products/applications_manager/help/rest-apis.html
    """
    def __init__(self, base_url=DEFAULT_URL, api_key=DEFAULT_API_KEY, verify_ssl=False, retries=3):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        
        # Optimize: Use Session with Retries
        self.session = requests.Session()
        if not verify_ssl:
            requests.packages.urllib3.disable_warnings()
            self.session.verify = False
        
        retry_strategy = Retry(
            total=retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def request(self, endpoint, params=None, method="GET", format="json"):
        """
        Generic request handler for AppManager with improved error handling.
        """
        url = f"{self.base_url}/AppManager/{format}/{endpoint}"
        
        query_params = {}
        data_body = None
        
        if method == "GET":
            query_params = params if params else {}
            query_params['apikey'] = self.api_key
        else:
            data_body = params if params else {}
            data_body['apikey'] = self.api_key
        
        try:
            start_time = time.time()
            response = self.session.request(
                method, 
                url, 
                params=query_params,
                data=data_body,
                timeout=30
            )
            response.raise_for_status()
            
            if format == "json":
                # AppManager sometimes returns invalid JSON or empty responses
                if not response.text.strip():
                    return None
                data = response.json()
                
                # Check for AppManager logic errors
                if 'response' in data and 'result' in data['response']:
                    # Some endpoints might return error in result? Usually codes are in header but check logic
                    pass
                return data
            else:
                return response.text
                
        except requests.exceptions.HTTPError as errh:
            logger.error(f"Http Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            logger.error(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            logger.error(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            logger.error(f"OOps: Something Else: {err}")
        except ValueError as json_err:
             logger.error(f"JSON Decode Error: {json_err} - Body: {response.text[:100]}")
             
        return None

    def request_v3(self, endpoint, params=None, data=None, method="GET"):
        """
        Handle V3 API requests (Header-based Auth).
        Endpoint should be relative to /api/v3/, e.g., 'alarms'.
        Ref: https://www.manageengine.com/products/applications_manager/help/rest-apis.html (V3 Section)
        """
        # Construct V3 URL - Assuming /api/v3/ structure based on docs
        # Note: Adjust path if your instance uses /AppManager/api/v3/
        url = f"{self.base_url}/api/v3/{endpoint}"
        
        headers = {
            "Authorization": self.api_key,
            "Accept": "application/json"
        }
        
        try:
            response = self.session.request(
                method, 
                url, 
                headers=headers,
                params=params,
                json=data, # V3 typically uses JSON body
                timeout=30
            )
            response.raise_for_status()
            
            if not response.text.strip():
                return None
            return response.json()
                
        except Exception as e:
            logger.error(f"V3 Request Error [{method} {url}]: {e}")
            return None

    # --- Operations ---
    def poll_now(self, resource_id):
        """Trigger immediate poll for a resource."""
        return self.request("PollNow", params={"resourceid": resource_id}, method="GET", format="xml")

    def execute_action(self, action_id, resource_id):
        """Execute a predefined action on a resource."""
        params = {
            "actionid": action_id,
            "resourceid": resource_id
        }
        return self.request("ExecuteAction", params=params, method="POST")

    # --- Monitor Groups ---
    def add_monitor_group(self, group_name, description=None):
        """Create a new Monitor Group."""
        params = {"groupname": group_name}
        if description:
            params["description"] = description
        return self.request("AddMonitorGroup", params=params, method="GET", format="xml")

    def delete_monitor_group(self, group_id):
        """Delete a Monitor Group."""
        return self.request("DeleteMonitorGroup", params={"groupid": group_id}, method="GET", format="xml")

    def associate_monitor_to_group(self, resource_id, group_id):
        """Associate a monitor with a monitor group."""
        params = {
            "resourceid": resource_id,
            "groupid": group_id
        }
        return self.request("AssociateMonitorToMonitorGroup", params=params, method="GET", format="xml")
        
    def unassociate_monitor_from_group(self, resource_id, group_id):
        """Unassociate a monitor from a monitor group."""
        params = {
            "resourceid": resource_id,
            "groupid": group_id
        }
        return self.request("UnassociateMonitorFromMonitorGroup", params=params, method="GET", format="xml")

    def get_alarms_v3(self):
        """List alarms using V3 API (Example)."""
        return self.request_v3("alarms")

    def _get_result_list(self, response_data):
        """Helper to extract list of results, handling dict vs list inconsistency."""
        if not response_data or 'response' not in response_data or 'result' not in response_data['response']:
            return []
        
        result = response_data['response']['result']
        if isinstance(result, dict):
            return [result]
        return result

    # --- Monitors ---
    def list_monitors(self, **kwargs):
        """List all monitors or filter by parameters."""
        params = kwargs if kwargs else {"type": "all"}
        return self.request("ListMonitor", params=params)

    def get_monitor_data(self, resource_id):
        """Get latest poll data for a specific resource ID."""
        return self.request("GetMonitorData", params={"resourceid": resource_id})
        
    def get_monitor_details(self, resource_id):
        """Alias for get_monitor_data"""
        return self.request("GetMonitorData", params={"resourceid": resource_id})

    def get_history_data(self, resource_id, attribute_id, period=1):
        """
        Get historical polled data.
        period: 0=Today, 1=7Days, 2=30Days, 5=1Year
        """
        params = {
            "resourceid": resource_id,
            "attributeID": attribute_id,
            "period": period
        }
        return self.request("ShowPolledData", params=params, method="GET", format="xml")

    # --- Alarms ---
    def list_alarms(self, type="all"):
        """List alarms. type can be 'all', 'critical', 'warning', 'clear'."""
        return self.request("ListAlarms", params={"type": type})

    # --- Configuration ---
    def list_threshold_profiles(self):
        """Lists all available threshold profiles."""
        # Note: Some versions fail with JSON, XML might be safer if JSON fails
        # But for optimization, let's keep JSON default and handle error in caller or retry
        return self.request("ListThresholdProfiles")

    def configure_alarm(self, **kwargs):
        """Flexible alarm configuration wrapper."""
        # Defaults
        params = {
            "requesttype": "1",
            "overrideConf": "true"
        }
        
        # Flatten kwargs to params, converting types
        for k, v in kwargs.items():
            if v is None: continue
            if isinstance(v, bool):
                params[k] = "true" if v else "false"
            else:
                params[k] = str(v)
                
        return self.request("configurealarms", params=params, method="POST", format="xml")

    # --- Maintenance ---
    def manage_monitor(self, resource_id, action="manage"):
        endpoint = "ManageMonitor" if action.lower() == "manage" else "UnmanageMonitor"
        return self.request(endpoint, params={"resourceid": resource_id}, method="POST", format="xml")

    def create_maintenance_task(self, name, resource_id, start_time, end_time, method="daily", description="Created via API"):
        """
        Create a maintenance task (downtime schedule).
        method: once, daily, weekly, monthly
        """
        params = {
            "taskName": name,
            "resourceid": resource_id,
            "startTime": start_time,
            "endTime": end_time,
            "frequency": method,
            "description": description,
            "type": "1" # 1 for Maintenance
        }
        return self.request("CreateMaintenanceTask", params=params, method="POST")

    def get_downtime_details(self, resource_id):
        """Get maintenance tasks for a specific resource."""
        # Note: API might not support filtering by resourceid directly in ListMaintenanceTask
        # We might need to fetch all and filter, or use a specific endpoint if available.
        # For now, trying ListMaintenanceTask with resourceid param
        return self.request("ListMaintenanceTask", params={"resourceid": resource_id})

    # --- Add/Delete Monitors ---
    def add_linux_monitor(self, ip, user, password, display_name=None, group_id=None, poll_interval=300, managed_server_id=None, label=None):
        """Add a Linux monitor."""
        params = {
            "type": "Linux",
            "hostName": ip,
            "userName": user,
            "password": password,
            "os": "Linux",
            "pollInterval": str(poll_interval)
        }
        if display_name:
            params["displayname"] = display_name
        
        # Distributed Setup (Central/Probe)
        if managed_server_id:
            params["ManagedServerID"] = managed_server_id

        # Resource Label
        if label:
            params["label"] = label

        # Attempt to pass group_id directly (if supported by specific API version)
        if group_id:
            params["monitorGroup"] = group_id
            
        response = self.request("AddMonitor", params=params, method="POST")
        
        # Robust Group Association:
        # If group_id was provided, verify if we need to manually associate.
        # This handles cases where 'monitorGroup' param is ignored or fails silently.
        if group_id and response:
            # Extract resource ID and Success Code from response
            # Structure varies: {"response": {"resourceid": "...", "response-code": "4000"}}
            # Or sometimes flat if custom parser used. Assuming standard JSON.
            res_data = response.get('response', response) # Handle nested or flat
            
            res_code = res_data.get('response-code')
            new_resource_id = res_data.get('resourceid')
            
            if str(res_code) == '4000' and new_resource_id:
                try:
                    # Explicitly associate to ensure membership
                    self.associate_monitor_to_group(new_resource_id, group_id)
                except Exception as e:
                    logger.warning(f"Auto-association to group {group_id} failed: {e}")
             
        return response

    def add_windows_monitor(self, host, user, password, mode="WMI", display_name=None, group_id=None, poll_interval=300, snmp_community="public", snmp_port="161", managed_server_id=None, label=None):
        """
        Add a Windows monitor.
        mode: WMI (default) or SNMP
        """
        params = {
            "type": "Server", # Or "Windows" depending on exact API, but "Server" is common base, often needs OS specified
            "displayname": display_name if display_name else host,
            "host": host,
            "os": "Windows2012", # Defaulting to a modern Windows OS, API might require specific string like WindowsXP/2003/2008/2012
            "mode": mode,
            "username": user,
            "password": password,
            "pollInterval": str(poll_interval)
        }
        
        if mode.upper() == "SNMP":
            params["snmpCommunityString"] = snmp_community
            params["snmptelnetport"] = snmp_port
        
        # Distributed Setup (Central/Probe)
        if managed_server_id:
            params["ManagedServerID"] = managed_server_id

        # Resource Label
        if label:
            params["label"] = label
        
        # Attempt to pass group_id directly
        if group_id:
            params["monitorGroup"] = group_id
            
        response = self.request("AddMonitor", params=params, method="POST")

        # Robust Group Association (Same as Linux)
        if group_id and response:
            res_data = response.get('response', response)
            res_code = res_data.get('response-code')
            new_resource_id = res_data.get('resourceid')
            
            if str(res_code) == '4000' and new_resource_id:
                try:
                    self.associate_monitor_to_group(new_resource_id, group_id)
                except Exception as e:
                    logger.warning(f"Auto-association to group {group_id} failed: {e}")
                    
        return response

    # --- Cloud Monitors ---
    def add_aws_monitor(self, display_name, access_key, secret_key, services="EC2,RDS,S3", account_type="AwsGlobal", poll_interval=300, group_id=None):
        """
        Add Amazon AWS Monitor.
        services: Comma separated list (e.g., 'EC2,RDS,S3')
        """
        params = {
            "type": "Amazon",
            "displayname": display_name,
            "accessKey": access_key,
            "SecretAccessKey": secret_key,
            "AccountType": account_type,
            "AmazonServices": services,
            "pollInterval": str(poll_interval)
        }

        if group_id:
            params["monitorGroup"] = group_id

        response = self.request("AddMonitor", params=params, method="POST")
        
        # Group Association Logic
        if group_id and response:
            res_data = response.get('response', response)
            if str(res_data.get('response-code')) == '4000' and res_data.get('resourceid'):
                try:
                    self.associate_monitor_to_group(res_data.get('resourceid'), group_id)
                except Exception as e:
                    logger.warning(f"Auto-association to group {group_id} failed: {e}")
        return response

    def add_office365_monitor(self, display_name, tenant_name, client_id, client_secret, tenant_id, services="ExchangeOnline,SharepointOnline,MicrosoftTeams", poll_interval=300, group_id=None):
        """
        Add Office 365 Monitor.
        services: Comma separated list (e.g., 'ExchangeOnline,SharepointOnline')
        """
        params = {
            "type": "Office365",
            "displayname": display_name,
            "Office365TenantName": tenant_name,
            "ClientID": client_id,
            "ClientSecret": client_secret,
            "TenantID": tenant_id,
            "Office365Services": services,
            "pollInterval": str(poll_interval),
            "UsePowerShell": "False" # Default to False to rely on Graph API where possible or simple auth
        }

        if group_id:
            params["monitorGroup"] = group_id

        response = self.request("AddMonitor", params=params, method="POST")

        # Group Association Logic
        if group_id and response:
            res_data = response.get('response', response)
            if str(res_data.get('response-code')) == '4000' and res_data.get('resourceid'):
                try:
                    self.associate_monitor_to_group(res_data.get('resourceid'), group_id)
                except Exception as e:
                    logger.warning(f"Auto-association to group {group_id} failed: {e}")
        return response

    def add_process_monitor(self, resource_id, process_name, display_name=None):
        """Add a process monitor to a server."""
        params = {
            "resourceid": resource_id,
            "name": process_name
        }
        if display_name:
            params["displayname"] = display_name
        return self.request("process/add", params=params, method="POST", format="xml")

    def delete_monitor(self, resource_id):
        """Delete a monitor."""
        return self.request("DeleteMonitor", params={"resourceid": resource_id}, method="POST")
        
    # --- Groups ---
    def create_monitor_group(self, name, description=""):
        """Create a new monitor group."""
        params = {
            "groupname": name,
            "description": description
        }
        return self.request("CreateGroup", params=params, method="POST")

    def list_groups(self):
        """List all monitor groups."""
        return self.request("ListGroup")

    def associate_monitor_to_group(self, resource_id, group_id):
        """Associate a monitor with a monitor group."""
        params = {
            "resourceid": resource_id,
            "groupid": group_id
        }
        return self.request("AssociateMonitorToGroup", params=params, method="POST")

if __name__ == "__main__":
    # Self-test
    client = AppManagerClient()
    print("Testing connection...")
    try:
        monitors = client.list_monitors(type="server")
        if monitors:
            count = len(client._get_result_list(monitors))
            print(f"Successfully connected. Found {count} server monitors.")
        else:
            print("Connected but no monitors found or empty response.")
    except Exception as e:
        print(f"Connection failed: {e}")
