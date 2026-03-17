import csv
import sys
import datetime
import math
import argparse
import os

def get_business_tag(server_name):
    s = server_name.lower()
    if 'mes' in s: return '🏭 工厂生产系统 (MES)', 'tag-prod'
    if 'erp' in s: return '💰 企业核心资源 (ERP)', 'tag-core'
    if 'srm' in s: return '📦 供应链系统 (SRM)', 'tag-core'
    if 'plm' in s: return '📐 研发设计 (PLM)', 'tag-core'
    if 'db' in s or 'oracle' in s or 'sql' in s: return '🗄️ 核心数据库', 'tag-db'
    if 'ad' in s and 'cad' not in s: return '🔑 身份认证 (AD)', 'tag-infra'
    if 'k8s' in s: return '⚓ 容器集群 (K8s)', 'tag-infra'
    if 'sap' in s: return '💰 SAP核心', 'tag-core'
    return '🖥️ 通用应用服务器', 'tag-normal'

def is_ignored_partition(metric_name):
    """
    Check if partition is a read-only ISO/Image mount or system temp.
    """
    m = metric_name.lower()
    
    # 1. ISO/Image mounts
    if '/redhat' in m or '/centos' in m or '/ubuntu' in m or '/iso' in m or '/media' in m:
        return True
        
    # 2. Virtual/System filesystems
    if '/sys/fs' in m or '/dev/shm' in m or '/run' in m or '/boot' in m or '/overlay' in m:
        return True
        
    # 3. Docker internal mounts
    if 'docker' in m and 'overlay' in m:
        return True
        
    return False

def generate_report(csv_file, output_file):
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
    except FileNotFoundError:
        print(f"Error: File {csv_file} not found.")
        return

    # Categories
    critical_disk = []
    critical_mem = []
    critical_cpu = []
    
    # Statistics
    total_servers = set()
    os_counts = {'windows': 0, 'linux': 0, 'other': 0}
    ignored_count = 0
    
    # Pre-scan for server counts
    for row in data:
        sname = row['Server Name']
        if sname not in total_servers:
            total_servers.add(sname)
            os_type = row.get('OS', 'other').lower()
            if 'windows' in os_type: os_counts['windows'] += 1
            elif 'linux' in os_type: os_counts['linux'] += 1
            else: os_counts['other'] += 1

    stats = {
        'total_analyzed': len(total_servers),
        'risk_disk': 0,
        'risk_mem': 0,
        'risk_cpu': 0,
        'days_to_full_alert': 0,
        'total_risks': 0
    }

    for row in data:
        metric = row['Metric']
        
        # --- FILTERING LOGIC ---
        if 'Disk' in metric and is_ignored_partition(metric):
            ignored_count += 1
            continue
        # -----------------------

        try:
            curr_avg = float(row.get('Current Avg (%)', 0))
            pred_peak = float(row.get('Predicted Peak (%)', 0))
            pred_avg = float(row.get('Predicted Avg (%)', 0))
            current_max = float(row.get('Current Max (%)', 0))
        except:
            continue

        # Logic
        daily_growth = (pred_avg - curr_avg) / 7.0
        volatility = current_max - curr_avg
        
        days_to_full = 999
        logic_explanation = []
        
        # Human Readable Logic
        if daily_growth > 0.1:
            remaining = 100.0 - curr_avg
            days_to_full = remaining / daily_growth
            logic_explanation.append(f"<span style='color:#e74c3c'>🔥 持续增长</span>：每天上涨约 {daily_growth:.1f}%")
            if days_to_full < 30:
                logic_explanation.append(f"⏳ <span style='font-weight:bold'>倒计时</span>：按此速度，预计 <strong>{int(days_to_full)}天后</strong> 空间耗尽")
        elif daily_growth < -0.1:
             logic_explanation.append("📉 趋势下降：负载正在降低")
        else:
            logic_explanation.append("➖ 趋势平稳：无明显增长")

        if volatility > 15:
            logic_explanation.append(f"🌊 <span style='color:#f39c12'>剧烈波动</span>：业务高峰期比平时高出 {volatility:.0f}%")
            
        # Tag
        analysis_tag = ""
        if days_to_full < 7:
            analysis_tag = f"🚨 极度危险 (不足{int(days_to_full)}天)"
            stats['days_to_full_alert'] += 1
        elif days_to_full < 30:
            analysis_tag = f"⚠️ 严重警告 (不足{int(days_to_full)}天)"
        elif pred_peak > 100:
            analysis_tag = "💥 容量溢出"
        elif volatility > 20:
            analysis_tag = "📉 不稳定/抖动"
        else:
            analysis_tag = "➖ 持续高负载"

        item = {
            'server': row['Server Name'],
            'os': row['OS'],
            'metric': row['Metric'],
            'curr': curr_avg,
            'peak': pred_peak,
            'days': days_to_full,
            'analysis': analysis_tag,
            'logic': "<br>".join(logic_explanation),
            'biz_label': get_business_tag(row['Server Name'])[0],
            'biz_class': get_business_tag(row['Server Name'])[1]
        }

        # Filter: Only Critical/Warning with high peak
        if row['Status'] in ['CRITICAL', 'WARNING'] and pred_peak > 80:
            stats['total_risks'] += 1
            metric_type = row['Metric']
            if 'Disk' in metric_type:
                critical_disk.append(item)
                stats['risk_disk'] += 1
            elif 'Memory' in metric_type:
                critical_mem.append(item)
                stats['risk_mem'] += 1
            elif 'CPU' in metric_type:
                critical_cpu.append(item)
                stats['risk_cpu'] += 1

    # Sorting
    critical_disk.sort(key=lambda x: (x['days'] if x['days'] < 365 else 999, -x['peak']))
    critical_mem.sort(key=lambda x: -x['peak'])
    critical_cpu.sort(key=lambda x: -x['peak'])

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Auto-generate Conclusion Text
    conclusion_text = f"""
    <ul style="margin:0; padding-left:20px;">
        <li><strong>巡检范围：</strong> 本次共对全网 <strong>{stats['total_analyzed']}</strong> 台服务器进行了深度体检（包含 {os_counts['windows']} 台 Windows 和 {os_counts['linux']} 台 Linux）。</li>
        <li><strong>智能过滤：</strong> AI 自动识别并过滤了 <strong>{ignored_count}</strong> 个只读镜像挂载点（如 /redhat7.6, /iso 等）和系统临时分区，确保障碍聚焦于真实业务。</li>
        <li><strong>核心发现：</strong> 剔除误报后，我们识别出 <strong>{stats['total_risks']}</strong> 个真实的潜在风险点。</li>
        <li style="color:#c0392b"><strong>紧急预警：</strong> 发现 <strong>{stats['days_to_full_alert']}</strong> 个关键业务节点的磁盘空间将在 <strong>7天内完全耗尽</strong>。如果不立即采取措施（清理或扩容），将直接导致业务中断。</li>
    </ul>
    """

    # --- HTML Generator ---
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>IT 基础设施容量健康度报告 (精简版)</title>
        <style>
            :root {{ --primary: #2c3e50; --bg: #f0f2f5; --danger: #e74c3c; --warning: #f1c40f; --info: #3498db; --success: #27ae60; }}
            body {{ font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: var(--bg); margin: 0; padding: 40px; color: #333; line-height: 1.6; }}
            
            .container {{ max-width: 1200px; margin: 0 auto; }}
            
            h1 {{ text-align: center; color: var(--primary); margin-bottom: 10px; font-weight: 800; font-size: 32px; }}
            .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 40px; font-size: 16px; }}
            
            /* Algorithm Explanation Box */
            .algo-box {{ background: #e8f4fd; border: 1px solid #b6e0fe; padding: 20px; border-radius: 8px; margin-bottom: 30px; font-size: 14px; color: #2c3e50; }}
            .algo-title {{ font-weight: bold; font-size: 16px; margin-bottom: 10px; display: flex; align-items: center; color: #0984e3; }}
            .algo-steps {{ display: flex; gap: 20px; justify-content: space-around; text-align: center; }}
            .step {{ flex: 1; position: relative; }}
            .step-icon {{ font-size: 24px; display: block; margin-bottom: 5px; }}
            .step:not(:last-child)::after {{ content: '➜'; position: absolute; right: -15px; top: 15px; color: #bdc3c7; font-size: 20px; }}
            
            /* Summary Box */
            .summary-card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; border-top: 5px solid var(--primary); }}
            .summary-title {{ font-size: 20px; font-weight: 700; color: var(--primary); margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            
            /* KPI Grid */
            .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
            .kpi-card {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border-bottom: 4px solid #ddd; }}
            .kpi-num {{ display: block; font-size: 32px; font-weight: 800; color: var(--primary); }}
            .kpi-label {{ font-size: 13px; color: #7f8c8d; font-weight: 600; }}
            
            .kpi-danger {{ border-color: var(--danger); }}
            .kpi-danger .kpi-num {{ color: var(--danger); }}
            .kpi-warning {{ border-color: var(--warning); }}
            .kpi-warning .kpi-num {{ color: #f39c12; }}
            
            /* Navigation */
            .nav {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; position: sticky; top: 20px; z-index: 100; }}
            .nav-btn {{ padding: 12px 25px; border: none; border-radius: 50px; font-weight: bold; cursor: pointer; transition: transform 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.15); text-decoration: none; color: white; display: flex; align-items: center; gap: 8px; font-size: 15px; }}
            .nav-btn:hover {{ transform: scale(1.05); }}
            
            .btn-disk {{ background: linear-gradient(135deg, #e74c3c, #c0392b); }}
            .btn-mem {{ background: linear-gradient(135deg, #3498db, #2980b9); }}
            .btn-cpu {{ background: linear-gradient(135deg, #27ae60, #2ecc71); }}
            
            /* Tables */
            .section-header {{ display: flex; align-items: center; margin-top: 40px; margin-bottom: 15px; background: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .section-icon {{ font-size: 24px; margin-right: 15px; }}
            .section-title {{ font-size: 20px; font-weight: 800; color: var(--primary); }}
            .section-count {{ background: #f1f2f6; padding: 4px 12px; border-radius: 20px; font-size: 13px; margin-left: auto; color: #666; font-weight: bold; }}
            
            .data-table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }}
            .data-table th {{ background: #f8f9fa; color: #7f8c8d; font-weight: 700; padding: 15px; text-align: left; font-size: 14px; border-bottom: 2px solid #eee; }}
            .data-table td {{ padding: 15px; border-bottom: 1px solid #f1f1f1; vertical-align: top; font-size: 14px; }}
            .data-table tr:hover {{ background-color: #fcfcfc; }}
            
            /* Tags */
            .tag {{ padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; display: inline-block; }}
            .tag-prod {{ background: #ffebee; color: #c62828; }}
            .tag-core {{ background: #e3f2fd; color: #1565c0; }}
            .tag-db {{ background: #fff3e0; color: #e67e22; }}
            .tag-infra {{ background: #f3e5f5; color: #8e44ad; }}
            .tag-normal {{ background: #f5f5f5; color: #7f8c8d; }}
            
            .analysis-bad {{ color: #c0392b; font-weight: 800; background: #ffebee; padding: 5px 10px; border-radius: 4px; display:inline-block; margin-bottom: 5px; }}
            .analysis-warn {{ color: #d35400; font-weight: 700; background: #fff3e0; padding: 5px 10px; border-radius: 4px; display:inline-block; margin-bottom: 5px; }}
            
            .logic-text {{ font-size: 13px; color: #555; line-height: 1.6; background: #f9f9f9; padding: 8px; border-radius: 4px; border-left: 3px solid #ddd; }}
            
            .progress-bg {{ background: #eee; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 8px; width: 100%; }}
            .progress-bar {{ height: 100%; border-radius: 4px; }}
            
            .footer {{ text-align: center; margin-top: 60px; font-size: 12px; color: #bdc3c7; border-top: 1px solid #e0e0e0; padding-top: 20px; }}
        </style>
    </head>
    <body>

    <div class="container">
        <h1>📊 IT 基础设施健康度体检报告</h1>
        <div class="subtitle">生成日期: {today_str} &emsp;|&emsp; 编制: AI 智能容量规划助手</div>

        <!-- 1. 算法说明 (让领导看懂怎么算的) -->
        <div class="algo-box">
            <div class="algo-title">💡 我们的 AI 预测模型是如何工作的？(算法原理)</div>
            <div class="algo-steps">
                <div class="step">
                    <span class="step-icon">📅</span>
                    <strong>1. 采集历史</strong><br>
                    回溯过去 30 天的 CPU、内存、磁盘使用记录。
                </div>
                <div class="step">
                    <span class="step-icon">🧹</span>
                    <strong>2. 智能降噪</strong><br>
                    自动剔除 ISO 镜像挂载、系统临时目录等无效告警。
                </div>
                <div class="step">
                    <span class="step-icon">📈</span>
                    <strong>3. 趋势推演</strong><br>
                    计算日均增长率，结合波动峰值，推算未来 7 天的使用情况。
                </div>
            </div>
        </div>

        <!-- 2. 核心结论 -->
        <div class="summary-card">
            <div class="summary-title">📝 总结汇报 (Executive Summary)</div>
            {conclusion_text}
        </div>

        <!-- 3. KPI 看板 -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <span class="kpi-num">{stats['total_analyzed']}</span>
                <span class="kpi-label">服务器巡检总数</span>
            </div>
            <div class="kpi-card kpi-danger">
                <span class="kpi-num">{stats['days_to_full_alert']}</span>
                <span class="kpi-label">🚨 7天内即将耗尽</span>
            </div>
            <div class="kpi-card kpi-warning">
                <span class="kpi-num">{stats['risk_disk']}</span>
                <span class="kpi-label">磁盘严重告警</span>
            </div>
            <div class="kpi-card kpi-warning">
                <span class="kpi-num">{stats['risk_mem'] + stats['risk_cpu']}</span>
                <span class="kpi-label">性能(CPU/内存)瓶颈</span>
            </div>
        </div>

        <!-- 4. 导航 -->
        <div class="nav">
            <a href="#disk-section" class="nav-btn btn-disk">💾 磁盘风险 ({len(critical_disk)})</a>
            <a href="#mem-section" class="nav-btn btn-mem">🧠 内存/CPU 风险 ({len(critical_mem) + len(critical_cpu)})</a>
        </div>

        <!-- DISK SECTION -->
        <div id="disk-section">
            <div class="section-header">
                <span class="section-icon">💾</span>
                <div class="section-title">磁盘空间风险 (已剔除镜像挂载)</div>
                <div class="section-count">共 {len(critical_disk)} 条</div>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th width="20%">业务系统 / 服务器</th>
                        <th width="25%">风险位置 (磁盘分区)</th>
                        <th width="35%">AI 诊断依据 (人话版)</th>
                        <th width="20%">最终建议</th>
                    </tr>
                </thead>
                <tbody>
    """

    def render_row(item, type_icon=""):
        metric_clean = item['metric'].replace('Disk ', '').replace('(', '').replace(')', '')
        
        peak_val = min(item['peak'], 100)
        bar_color = "#e74c3c" if peak_val > 90 else "#f39c12"
        
        return f"""
        <tr>
            <td>
                <div style="font-weight:bold; font-size:15px; margin-bottom:5px; color:#2c3e50;">{item['server']}</div>
                <span class="tag {item['biz_class']}">{item['biz_label']}</span>
                <span class="tag tag-normal">{item['os'].upper()}</span>
            </td>
            <td>
                <div style="background:#f1f2f6; padding:5px 8px; border-radius:4px; font-family:monospace; font-weight:bold; color:#555; display:inline-block; margin-bottom:5px;">{metric_clean}</div>
                <div style="font-size:13px; color:#777;">当前使用率: <strong>{item['curr']:.1f}%</strong></div>
                <div class="progress-bg">
                    <div class="progress-bar" style="width:{peak_val}%; background:{bar_color};"></div>
                </div>
            </td>
            <td>
                <div class="logic-text">
                    {item['logic']}
                </div>
            </td>
            <td>
                <div class="{ 'analysis-bad' if '极度' in item['analysis'] or '溢出' in item['analysis'] else 'analysis-warn' }">
                    {item['analysis']}
                </div>
            </td>
        </tr>
        """

    for item in critical_disk[:50]: 
        html += render_row(item)

    html += """
            </tbody>
        </table>
    </div>

    <!-- MEMORY/CPU SECTION -->
    <div id="mem-section">
        <div class="section-header">
            <span class="section-icon">🧠</span>
            <div class="section-title">性能瓶颈 (CPU & 内存)</div>
            <div class="section-count">共 {len(critical_mem) + len(critical_cpu)} 条</div>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th width="20%">业务系统 / 服务器</th>
                    <th width="25%">风险指标</th>
                    <th width="35%">AI 诊断依据 (人话版)</th>
                    <th width="20%">最终建议</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Merge Mem & CPU
    perf_items = critical_mem + critical_cpu
    perf_items.sort(key=lambda x: -x['peak'])
    
    for item in perf_items[:30]:
        html += render_row(item)

    html += """
            </tbody>
        </table>
    </div>

    <div class="footer">
        Generated by <strong>Gemini AI Capacity Planner</strong> &bull; 基于线性回归与波动率混合预测模型
    </div>

    </div> <!-- Container -->
    </body>
    </html>
    """

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", nargs='?', default="capacity_forecast.csv")
    args = parser.parse_args()
    generate_report(args.csv_file, "capacity_report.html")
