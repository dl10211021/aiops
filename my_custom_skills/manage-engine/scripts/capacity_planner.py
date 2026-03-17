
import argparse
import logging
import concurrent.futures
import csv
import sys
import os
import statistics
import datetime
import xml.etree.ElementTree as ET

# Add ManageEngine skill scripts to path to import api
skill_path = os.path.dirname(os.path.abspath(__file__))
if skill_path not in sys.path:
    sys.path.append(skill_path)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('capacity_planner')

def run_forecast():
    """Step 1: Fetch Data and Forecast"""
    logger.info("Starting Capacity Forecasting...")
    
    # We will invoke the forecast_capacity.py logic directly or via subprocess
    # To keep it simple and robust within skill context, let's execute the script we just created.
    # But wait, we can just import the main function or replicate the logic if we want a single entry point.
    # The best practice for this 'skill' environment is to use run_shell_command to chain them 
    # OR just import the main function if designed as module.
    
    # Let's use subprocess to call the script we just saved, ensuring clean separation.
    import subprocess
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    forecast_script = os.path.join(script_dir, "forecast_capacity.py")
    output_csv = "capacity_forecast.csv"
    
    cmd = [sys.executable, forecast_script, "--limit", "1000", "--output", output_csv]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False) # Let it print to stdout
    
    if result.returncode != 0:
        logger.error("Forecasting failed.")
        sys.exit(1)
        
    return output_csv

def generate_report(csv_file):
    """Step 2: Generate Report"""
    logger.info("Generating HTML Report...")
    
    # We need the logic from generate_report_v4.py which is now our 'best practice' report generator.
    # Let's save that logic as 'generate_forecast_report.py' first.
    # Actually, I haven't saved 'generate_forecast_report.py' yet in the thought process I just said I would.
    # I will save generate_report_v4 logic as scripts/generate_forecast_report.py in the NEXT tool call.
    
    # For now, let's assume it exists.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_script = os.path.join(script_dir, "generate_forecast_report.py")
    
    cmd = [sys.executable, report_script, csv_file]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    import subprocess
    csv_path = run_forecast()
    generate_report(csv_path)
