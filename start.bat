@echo off
start /B python main.py > backend.log 2>&1
echo "Started backend on port 8000"
