import sys
import urllib.request
import urllib.parse

def get_weather(city):
    try:
        url = f"http://wttr.in/{urllib.parse.quote(city)}?format=3"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        response = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        print(response.strip())
    except Exception as e:
        print(f"获取气象数据失败: {e}")

if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Nanjing"
    get_weather(city)
