import requests
import time
import subprocess
import sys

# Create the server completely asynchronously
import threading


def run_server():
    subprocess.run([sys.executable, "run_test.py"])


thread = threading.Thread(target=run_server)
thread.daemon = True
thread.start()

time.sleep(5)

try:
    print("Testing read-only session...")
    resp_ro = requests.post(
        "http://127.0.0.1:8088/api/v1/connect",
        json={
            "host": "127.0.0.1",
            "username": "test",
            "allow_modifications": False,
            "protocol": "virtual",
            "lazy": True,
        },
    ).json()
    print("Connect RO:", resp_ro)

    # Try mock command
    ro_cmd = requests.post(
        "http://127.0.0.1:8088/api/v1/execute",
        json={"session_id": resp_ro["data"]["session_id"], "command": "mkdir test"},
    ).json()
    print("Execute RO:", ro_cmd)

    print("\nTesting write session...")
    resp_rw = requests.post(
        "http://127.0.0.1:8088/api/v1/connect",
        json={
            "host": "127.0.0.1",
            "username": "test",
            "allow_modifications": True,
            "protocol": "virtual",
            "lazy": True,
        },
    ).json()
    print("Connect RW:", resp_rw)

    # Try mock command
    rw_cmd = requests.post(
        "http://127.0.0.1:8088/api/v1/execute",
        json={"session_id": resp_rw["data"]["session_id"], "command": "mkdir test"},
    ).json()
    print("Execute RW:", rw_cmd)

except Exception as e:
    print("Error:", e)
finally:
    import os

    os.system("taskkill /f /im run_test.py /t")
