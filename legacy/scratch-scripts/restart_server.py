import urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:8000/")
    print("Server running on port 8000")
except Exception as e:
    print(f"Error checking 8000: {e}")

try:
    urllib.request.urlopen("http://127.0.0.1:5173/")
    print("Vite dev server running on port 5173")
except Exception as e:
    print(f"Error checking 5173: {e}")
