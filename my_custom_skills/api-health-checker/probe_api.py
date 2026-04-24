import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress only the single InsecureRequestWarning from urllib3
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def probe_api_health(target_ip: str, target_ports: list, auth_header_value: str = None, common_endpoints: list = None) -> dict:
    """
    Probes a VIRTUAL API service for health and status using HTTPS.
    Attempts multiple common health endpoints and handles JSON/non-JSON responses.

    Args:
        target_ip (str): The IP address of the API service.
        target_ports (list): A list of ports to try (e.g., [9090, 443]).
        auth_header_value (str, optional): The value for the Authorization header (e.g., "Bearer your_token").
        common_endpoints (list, optional): A list of API paths to check (e.g., ["/health", "/status"]).
                                            Defaults to ["/health", "/status", "/api/health", "/"].

    Returns:
        dict: A structured result containing status, messages, data, and error details.
    """
    
    result = {
        "overall_status": "failure",
        "messages": [],
        "successful_data": None,
        "error_summary": None,
        "attempts": []
    }

    if common_endpoints is None:
        common_endpoints = ["/health", "/status", "/api/health", "/"]

    headers = {}
    if auth_header_value:
        headers["Authorization"] = auth_header_value
        result["messages"].append("Authorization header will be used.")
    else:
        result["messages"].append("Warning: No Authorization header value provided. Proceeding without authentication.")

    for port in target_ports:
        for endpoint in common_endpoints:
            url = f"https://{target_ip}:{port}{endpoint}"
            local_attempt = {
                "url": url,
                "status": "failure",
                "message": [],
                "data": None,
                "error_details": None
            }
            result["attempts"].append(local_attempt)
            local_attempt["message"].append(f"Attempting to connect to: {url}")

            try:
                response = requests.get(url, timeout=10, verify=False, headers=headers)
                response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
                
                local_attempt["status"] = "success"
                local_attempt["message"].append(f"API endpoint {url} is reachable. Status Code: {response.status_code}")
                
                try:
                    json_data = response.json()
                    local_attempt["message"].append("Response JSON (parsed):")
                    local_attempt["data"] = json_data
                    result["successful_data"] = json_data # Capture first successful data
                    result["overall_status"] = "success" # Mark overall success
                    
                    # Deep Discovery and Diagnosis - Example analysis
                    if isinstance(json_data, dict):
                        if 'status' in json_data and json_data['status'].upper() != 'UP':
                            local_attempt["message"].append(f"ALERT: API reported status is not 'UP': {json_data.get('status')}")
                            result["overall_status"] = "warning" # Downgrade if status not UP
                        if 'health' in json_data and json_data['health'].lower() != 'ok':
                            local_attempt["message"].append(f"ALERT: API reported health is not 'ok': {json_data.get('health')}")
                            result["overall_status"] = "warning" # Downgrade if health not ok
                        if 'errors' in json_data and len(json_data['errors']) > 0:
                            local_attempt["message"].append(f"CRITICAL: API reported errors: {json.dumps(json_data['errors'], indent=2)}")
                            result["overall_status"] = "critical" # Critical if errors
                    
                    return result # Return immediately on first success with data
                    
                except json.JSONDecodeError:
                    local_attempt["message"].append("Response is not JSON. Raw content (first 1024 characters):")
                    local_attempt["data"] = response.text[:1024]
                    result["successful_data"] = response.text[:1024] # Capture first successful data
                    result["overall_status"] = "success_non_json" # Mark success but non-json

            except requests.exceptions.Timeout:
                local_attempt["error_details"] = f"Connection to {url} timed out after 10 seconds. The service might be down or heavily loaded."
            except requests.exceptions.ConnectionError as e:
                local_attempt["error_details"] = f"Could not connect to {url}. This might be due to incorrect IP/port, network issues, or the service not running. Details: {e}"
            except requests.exceptions.HTTPError as e:
                local_attempt["error_details"] = f"HTTP request failed with status code {e.response.status_code}. Details: {e}"
                if e.response.status_code == 401 or e.response.status_code == 403:
                    local_attempt["message"].append("AUTHENTICATION REQUIRED: The API requires authentication. Please provide the correct account and password/token for the 'Authorization' header.")
            except Exception as e:
                local_attempt["error_details"] = f"An unexpected error occurred: {e}"
    
    # If we reach here, no attempt was fully successful or returned valid data
    # Aggregate error messages for summary
    error_messages = [attempt["error_details"] for attempt in result["attempts"] if attempt["error_details"]]
    if error_messages:
        result["error_summary"] = "\n".join(list(set(error_messages))) # Use set to avoid duplicate errors
    else:
        result["error_summary"] = "No specific error details captured, but no successful connection."

    result["messages"].append("All probing attempts failed to establish a successful connection or retrieve meaningful data.")
    return result

# Example usage (will be called by local_execute_script or another skill)
# if __name__ == "__main__":
#     ip = "192.168.130.45"
#     ports = [9090, 443]
#     auth_token = None # Or "Bearer YOUR_TOKEN"
#     
#     health_check_result = probe_api_health(ip, ports, auth_token)
#     print(json.dumps(health_check_result, indent=2))
