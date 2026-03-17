
import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_v3')

def main():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    logger.info("Testing V3 API Connectivity...")
    
    try:
        alarms = client.get_alarms_v3()
        if alarms:
            logger.info("V3 API Success!")
            print(alarms)
        else:
            logger.info("V3 API returned empty response or failed.")
            
    except Exception as e:
        logger.error(f"V3 Test Failed: {e}")

if __name__ == "__main__":
    main()
