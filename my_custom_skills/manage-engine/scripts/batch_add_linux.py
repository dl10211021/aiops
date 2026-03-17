import csv
import sys
import time
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def batch_add_monitors(csv_file="servers.csv"):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print(f"--- 正在从 {csv_file} 批量读取服务器 ---")
    
    try:
        with open(csv_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total = len(rows)
            
            print(f"✅ 成功读取 {total} 条记录。开始处理...")
            print("-" * 60)
            
            success_count = 0
            fail_count = 0
            
            for i, row in enumerate(rows, 1):
                ip = row.get('IP Address', '').strip()
                user = row.get('Username', 'root').strip()
                pwd = row.get('Password', 'cnChervon@123').strip()
                name = row.get('Display Name', '').strip()
                group_id = row.get('Group ID', '').strip()
                
                if not ip:
                    print(f"⚠️  跳过第 {i} 行: IP 为空")
                    continue
                    
                if not name:
                    name = f"Linux_{ip}"
                
                print(f"[{i}/{total}] 添加: {name} ({ip}) -> Group: {group_id if group_id else 'None'} ...", end="", flush=True)
                
                # 调用 API
                try:
                    res = client.add_linux_monitor(ip, user, pwd, display_name=name, group_id=group_id)
                    
                    # 检查结果
                    if res and ('4000' in str(res) or 'success' in str(res).lower()):
                        print(" ✅ 成功")
                        success_count += 1
                    elif "4444" in str(res):
                        print(" ⚠️ 已存在")
                        # 视为成功或忽略
                    else:
                        print(f" ❌ 失败 ({str(res)[:100]})")
                        fail_count += 1
                        
                except Exception as e:
                    print(f" ❌ 异常: {e}")
                    fail_count += 1
                    
                # 稍微暂停，避免 API 限流
                time.sleep(1)

            print("-" * 60)
            print(f"🏁 批量处理完成！成功: {success_count}, 失败: {fail_count}")

    except FileNotFoundError:
        print(f"❌ 找不到文件: {csv_file}")
        print("请创建一个 CSV 文件，包含表头: IP Address, Username, Password, Display Name, Group ID")

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "servers.csv"
    batch_add_monitors(file_path)
