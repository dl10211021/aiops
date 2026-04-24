
import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('add_cloud_monitor')

def main():
    parser = argparse.ArgumentParser(description="Add Cloud Monitor (AWS, Office365) to AppManager")
    subparsers = parser.add_subparsers(dest="cloud_type", required=True, help="Cloud Provider Type")

    # --- AWS ---
    aws_parser = subparsers.add_parser("aws", help="Add Amazon AWS Monitor")
    aws_parser.add_argument("name", help="Display Name for the Monitor")
    aws_parser.add_argument("--access-key", required=True, help="AWS Access Key ID")
    aws_parser.add_argument("--secret-key", required=True, help="AWS Secret Access Key")
    aws_parser.add_argument("--services", default="EC2,RDS,S3", help="Comma-separated list of services (Default: EC2,RDS,S3)")
    aws_parser.add_argument("--account-type", default="AwsGlobal", help="Account Type (Default: AwsGlobal)")
    aws_parser.add_argument("--group", help="Monitor Group ID to associate with")
    aws_parser.add_argument("--poll", type=int, default=300, help="Polling Interval in seconds")

    # --- Office 365 ---
    o365_parser = subparsers.add_parser("o365", help="Add Office 365 Monitor")
    o365_parser.add_argument("name", help="Display Name for the Monitor")
    o365_parser.add_argument("--tenant-name", required=True, help="Office 365 Tenant Name (e.g., mycompany.onmicrosoft.com)")
    o365_parser.add_argument("--client-id", required=True, help="Azure App Client ID")
    o365_parser.add_argument("--client-secret", required=True, help="Azure App Client Secret")
    o365_parser.add_argument("--tenant-id", required=True, help="Azure Tenant ID")
    o365_parser.add_argument("--services", default="ExchangeOnline,SharepointOnline,MicrosoftTeams", help="Comma-separated services")
    o365_parser.add_argument("--group", help="Monitor Group ID to associate with")
    o365_parser.add_argument("--poll", type=int, default=300, help="Polling Interval in seconds")

    args = parser.parse_args()
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    response = None

    try:
        if args.cloud_type == "aws":
            logger.info(f"Adding AWS Monitor: {args.name}")
            response = client.add_aws_monitor(
                display_name=args.name,
                access_key=args.access_key,
                secret_key=args.secret_key,
                services=args.services,
                account_type=args.account_type,
                poll_interval=args.poll,
                group_id=args.group
            )
        
        elif args.cloud_type == "o365":
            logger.info(f"Adding Office 365 Monitor: {args.name}")
            response = client.add_office365_monitor(
                display_name=args.name,
                tenant_name=args.tenant_name,
                client_id=args.client_id,
                client_secret=args.client_secret,
                tenant_id=args.tenant_id,
                services=args.services,
                poll_interval=args.poll,
                group_id=args.group
            )

        # Parse Response
        logger.info(f"API Response: {response}")
        
        res_data = response.get('response', response)
        res_code = res_data.get('response-code')
        res_msg = res_data.get('message', 'Unknown status')
        
        if str(res_code) == '4000':
            new_id = res_data.get('resourceid', 'N/A')
            print(f"[SUCCESS] {args.cloud_type.upper()} Monitor added. ID: {new_id}")
            print(f"          Message: {res_msg}")
        else:
            print(f"[ERROR] Failed to add monitor. Code: {res_code}")
            print(f"        Message: {res_msg}")

    except Exception as e:
        logger.error(f"Error adding cloud monitor: {e}")
        print(f"[CRITICAL] Script Error: {e}")

if __name__ == "__main__":
    main()
