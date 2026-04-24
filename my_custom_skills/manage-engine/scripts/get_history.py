
import argparse
import xml.etree.ElementTree as ET
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('get_history')

ATTR_MAP = {
    "cpu": "708",
    "win_cpu": "41005",
    "mem": "709",
    "disk": "711",
    "response": "16"
}

def parse_xml_history(xml_string):
    """Parse the XML response from ShowPolledData."""
    try:
        # Check if it's a raw string error
        if not xml_string or not isinstance(xml_string, str):
            return []
            
        root = ET.fromstring(xml_string)
        data_points = []
        
        # Structure usually: <result><response><HistoryData><Data><Time>...</Time><Value>...</Value></Data>...</HistoryData></response></result>
        # Or <Monitorinfo ...><ArchiveData DateTime="..." AvgValue="..." .../></Monitorinfo>
        
        # 1. Try Standard Data/Time nodes
        for data in root.findall(".//Data"):
            time_val = data.find("Time")
            value_val = data.find("Value")
            if time_val is not None and value_val is not None:
                data_points.append({
                    "time": time_val.text,
                    "value": value_val.text
                })
        
        # 2. Try ArchiveData attributes (Historical reports)
        if not data_points:
            for archive in root.findall(".//ArchiveData"):
                time_val = archive.get("DateTime")
                value_val = archive.get("AvgValue")
                if time_val and value_val:
                    data_points.append({
                        "time": time_val,
                        "value": value_val
                    })
                    
        return data_points
    except Exception as e:
        logger.error(f"XML Parsing Error: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Get Historical Data (CPU/Mem/etc)")
    parser.add_argument("resource_id", help="Resource ID")
    parser.add_argument("--metric", choices=["cpu", "mem", "disk", "response"], default="cpu", help="Metric to fetch")
    parser.add_argument("--attr", help="Specific Attribute ID (overrides --metric)")
    parser.add_argument("--period", choices=["0", "1", "2", "3", "4"], default="1", help="Period (0=Today, 1=7Days, 2=30Days)")
    
    args = parser.parse_args()
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    attr_id = args.attr if args.attr else ATTR_MAP.get(args.metric, "708")
    
    logger.info(f"Fetching history for {args.resource_id} (Attr: {attr_id}, Period: {args.period})...")
    
    response = client.get_history_data(args.resource_id, attr_id, args.period)
    
    # logger.info(f"Raw Response: {response}") # Debug only
    
    if response:
        points = parse_xml_history(response)
        if points:
            print(f"--- History Data ({len(points)} points) ---")
            print(f"{'Time':<25} | {'Value':<10}")
            print("-" * 40)
            for p in points:
                print(f"{p['time']:<25} | {p['value']:<10}")
        else:
            print("No data points found or XML parsing failed.")
            print("Raw response start:", str(response)[:1000])
    else:
        print("No response from API.")

if __name__ == "__main__":
    main()
