import re
import sys
from collections import Counter

def analyze_logs(log_file_path):
    """
    Analyzes a generic log file for common failure patterns.
    """
    print(f"Analyzing {log_file_path}...")
    
    error_patterns = [
        r"Exception",
        r"Error",
        r"Critical",
        r"Fail",
        r"Timeout",
        r"Connection refused"
    ]
    
    findings = Counter()
    
    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings[pattern] += 1
                        # Print first few occurrences
                        if findings[pattern] <= 3:
                            print(f"[Line {line_num}] Found {pattern}: {line.strip()[:100]}...")
                            
    except FileNotFoundError:
        print(f"File not found: {log_file_path}")
        return

    print("\n--- Summary ---")
    for pattern, count in findings.items():
        print(f"{pattern}: {count} occurrences")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python log_analyzer.py <log_file_path>")
        sys.exit(1)
        
    analyze_logs(sys.argv[1])
