import subprocess
import time

p = subprocess.Popen(["python", "main.py"])
print("Started backend with PID:", p.pid)
