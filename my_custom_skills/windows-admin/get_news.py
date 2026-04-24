import argparse
import base64
import re
import winrm # pywinrm

def get_news(target, user, password):
    # Establish WinRM connection
    sess = winrm.Session(
        f"http://{target}:5985/wsman", 
        auth=(user, password), 
        transport='ntlm'
    )
    
    # PowerShell command: Fetch content, convert to Base64 (to bypass WinRM/Console encoding issues)
    # Fixed: Explicitly convert String content to Byte[] before Base64 encoding
    ps_command = """
    $ProgressPreference = 'SilentlyContinue'
    try {
        $resp = Invoke-WebRequest -Uri "https://top.baidu.com/board?tab=realtime" -UseBasicParsing -TimeoutSec 10
        
        if ($resp.Content -is [byte[]]) {
            [Convert]::ToBase64String($resp.Content)
        } else {
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($resp.Content)
            [Convert]::ToBase64String($bytes)
        }
    } catch {
        Write-Error $_.Exception.Message
    }
    """
    
    # Execute
    result = sess.run_ps(ps_command)
    
    if result.status_code != 0:
        print(f"Error fetching news: {result.std_err.decode('utf-8', errors='ignore')}")
        return

    # Decode Output
    try:
        b64_str = result.std_out.strip()
        if not b64_str:
            print("No data received.")
            return
            
        html_content = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Decoding failed: {e}")
        return

    # Parse HTML with Regex (Lightweight, no need for bs4)
    # Target: <div class="c-single-text-ellipsis">  News Title  </div>
    # Note: Baidu's structure might change, but this class is relatively stable for the board
    pattern = re.compile(r'<div class="c-single-text-ellipsis">\s*(.*?)\s*</div>')
    matches = pattern.findall(html_content)
    
    if not matches:
        print("Could not find news items. The page structure might have changed or access was denied.")
    else:
        print(f"=== 百度实时热搜 (Source: {target}) ===")
        # Usually the first item is the top pinned one, followed by the list
        for i, item in enumerate(matches[:15], 1):
            print(f"{i}. {item.strip()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    
    get_news(args.target, args.user, args.password)
