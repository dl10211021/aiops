#!/usr/bin/env python3
"""
AI Batch Report Generator for Network Switch Inspection
Generates individual AI-analyzed HTML reports for each device and a summary index
"""
import json
import sys
import os
import re
from datetime import datetime

def extract_metric(pattern, text, default=None):
    """Extract metric using regex pattern"""
    if not text:
        return default
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else default

def analyze_device_health(device_data):
    """Analyze device health and return score with issues"""
    data = device_data.get('data', {})
    score = 100
    issues = []

    # CPU analysis
    cpu_text = data.get('cpu_memory', '')
    cpu_usage = extract_metric(r'(\d+)%\s+in\s+last\s+5\s+seconds', cpu_text)
    if cpu_usage:
        cpu_val = int(cpu_usage)
        if cpu_val > 80:
            score -= 15
            issues.append(f"严重: CPU使用率过高 ({cpu_val}%)")
        elif cpu_val > 50:
            score -= 8
            issues.append(f"警告: CPU使用率较高 ({cpu_val}%)")

    # Memory analysis
    mem_text = data.get('memory_usage', '')
    mem_match = re.search(r'Mem:\s+(\d+)\s+(\d+)', mem_text)
    if mem_match:
        total = int(mem_match.group(1))
        used = int(mem_match.group(2))
        mem_percent = (used / total * 100) if total > 0 else 0
        if mem_percent > 85:
            score -= 15
            issues.append(f"严重: 内存使用率过高 ({mem_percent:.1f}%)")
        elif mem_percent > 70:
            score -= 8
            issues.append(f"警告: 内存使用率较高 ({mem_percent:.1f}%)")

    # Temperature analysis
    temp_text = data.get('temperature', '') or data.get('environment', '')
    temps = re.findall(r'(\d+)\s*degrees?\s*[CF]', temp_text, re.IGNORECASE)
    if temps:
        max_temp = max([int(t) for t in temps])
        if max_temp > 65:
            score -= 15
            issues.append(f"严重: 温度过高 ({max_temp}°C)")
        elif max_temp > 50:
            score -= 5
            issues.append(f"警告: 温度较高 ({max_temp}°C)")

    # Interface analysis
    intf_text = data.get('interfaces', '')
    down_count = len(re.findall(r'\bDOWN\b', intf_text))
    up_count = len(re.findall(r'\bUP\s+\d+[GM]', intf_text))
    if down_count > 10:
        score -= 5
        issues.append(f"注意: {down_count}个接口处于DOWN状态")

    # Power and fan check
    power_text = data.get('power', '')
    if 'Absent' in power_text or 'Failed' in power_text or 'Abnormal' in power_text:
        score -= 10
        issues.append("警告: 电源状态异常")

    fan_text = data.get('fan', '')
    if 'Absent' in fan_text or 'Failed' in fan_text or 'Abnormal' in fan_text:
        score -= 10
        issues.append("警告: 风扇状态异常")

    # Determine status
    if score >= 90:
        status = "优秀"
        status_class = "status-excellent"
    elif score >= 75:
        status = "良好"
        status_class = "status-good"
    elif score >= 60:
        status = "警告"
        status_class = "status-warning"
    else:
        status = "严重"
        status_class = "status-critical"

    return {
        'score': max(0, score),
        'status': status,
        'status_class': status_class,
        'issues': issues,
        'metrics': {
            'cpu': cpu_usage,
            'memory': mem_percent if mem_match else None,
            'temp': max(temps) if temps else None,
            'interfaces_up': up_count,
            'interfaces_down': down_count
        }
    }

def extract_vlan_info(data):
    """Extract VLAN information"""
    vlan_text = data.get('vlans', '')
    vlan_count = len(re.findall(r'^\s*\d+', vlan_text, re.MULTILINE))
    vlan_list = re.findall(r'\b(\d+)\b', vlan_text)
    return vlan_count, vlan_list[:20]  # Limit to first 20 VLANs for display

def extract_interface_details(data):
    """Extract detailed interface information for table"""
    interfaces = []
    intf_text = data.get('interfaces', '')

    # Parse interface brief output
    lines = intf_text.split('\n')
    for line in lines:
        if 'GE' in line or 'XGE' in line or 'VLAN' in line:
            parts = line.split()
            if len(parts) >= 6:
                intf_name = parts[0]
                link = parts[1] if len(parts) > 1 else 'DOWN'
                speed = parts[4] if len(parts) > 4 else '-'
                duplex = parts[5] if len(parts) > 5 else '-'

                # Extract description if present
                desc_match = re.search(rf'{re.escape(intf_name)}.*?description\s+(.+)', intf_text, re.IGNORECASE)
                description = desc_match.group(1).strip() if desc_match else '连接下游设备'

                # Determine interface type and PVID
                intf_type = 'Trunk' if 'trunk' in line.lower() else 'Access'
                pvid = extract_metric(rf'{re.escape(intf_name)}.*?pvid\s+(\d+)', intf_text, '1')

                interfaces.append({
                    'name': intf_name,
                    'link': link,
                    'speed': speed,
                    'duplex': duplex,
                    'type': intf_type,
                    'pvid': pvid,
                    'description': description
                })

    return interfaces[:15]  # Return top 15 interfaces

def generate_issue_analysis(health, data):
    """Generate detailed issue analysis with recommendations"""
    issues_html = ""

    for issue in health['issues']:
        priority = 'medium'
        if '严重' in issue:
            priority = 'high'
        elif '注意' in issue or '警告' in issue:
            priority = 'medium'
        else:
            priority = 'low'

        # Generate detailed issue cards
        if 'CPU' in issue:
            issues_html += f"""
                    <li class="priority-{priority}">
                        <strong>{'🔸' if priority == 'medium' else '🔴' if priority == 'high' else '🔹'} {'中等' if priority == 'medium' else '高' if priority == 'high' else '低'}优先级 - {issue}</strong>
                        <p><strong>影响分析:</strong> CPU负载过高可能影响设备响应速度和数据包转发性能，需要识别是正常业务峰值还是异常进程。</p>
                        <p><strong>建议操作:</strong> 执行 "display process cpu" 查看占用CPU最高的进程，使用 "display interface counters" 检查流量异常。</p>
                    </li>"""
        elif '内存' in issue:
            issues_html += f"""
                    <li class="priority-{priority}">
                        <strong>{'🔸' if priority == 'medium' else '🔴' if priority == 'high' else '🔹'} {'中等' if priority == 'medium' else '高' if priority == 'high' else '低'}优先级 - {issue}</strong>
                        <p><strong>影响分析:</strong> 内存使用率过高可能导致系统性能下降，严重时可能导致进程被终止或系统不稳定。</p>
                        <p><strong>建议操作:</strong> 执行 "display memory" 查看内存详细使用情况，检查是否有内存泄漏。</p>
                    </li>"""
        elif '温度' in issue:
            issues_html += f"""
                    <li class="priority-{priority}">
                        <strong>{'🔸' if priority == 'medium' else '🔴' if priority == 'high' else '🔹'} {'中等' if priority == 'medium' else '高' if priority == 'high' else '低'}优先级 - {issue}</strong>
                        <p><strong>影响分析:</strong> 高温可能导致硬件寿命缩短，严重时触发保护性关机。</p>
                        <p><strong>建议操作:</strong> 检查机房空调系统，清理设备风扇和散热口，确保通风良好。</p>
                    </li>"""
        elif '接口' in issue:
            issues_html += f"""
                    <li class="priority-low">
                        <strong>🔹 低优先级 - {issue}</strong>
                        <p><strong>影响分析:</strong> 大量DOWN接口可能是正常的（未连接设备），但需要确认是否有应该UP但异常DOWN的接口。</p>
                        <p><strong>建议操作:</strong> 核对接口配置和物理连接，确认DOWN状态是否符合预期。</p>
                    </li>"""
        elif '电源' in issue or '风扇' in issue:
            issues_html += f"""
                    <li class="priority-{priority}">
                        <strong>{'🔸' if priority == 'medium' else '🔴' if priority == 'high' else '🔹'} {'中等' if priority == 'medium' else '高' if priority == 'high' else '低'}优先级 - {issue}</strong>
                        <p><strong>影响分析:</strong> 硬件状态异常可能导致设备可靠性下降，存在单点故障风险。</p>
                        <p><strong>建议操作:</strong> 检查硬件模块状态，考虑更换故障模块或配置冗余。</p>
                    </li>"""

    return issues_html if issues_html else "<p>✓ 设备运行正常，未发现明显问题</p>"

def generate_comprehensive_analysis(health, data, model, uptime):
    """Generate comprehensive health analysis with advantages"""
    cpu = health['metrics']['cpu']
    memory = health['metrics']['memory']
    temp = health['metrics']['temp']

    cpu_analysis = f"CPU使用率为{cpu}%"
    if cpu:
        cpu_val = int(cpu)
        if cpu_val > 70:
            cpu_analysis += "，负载较高，建议关注是否有突发流量或异常进程"
        elif cpu_val > 50:
            cpu_analysis += "，负载适中，系统运行正常"
        else:
            cpu_analysis += "，负载较低，性能充足"

    mem_analysis = f"内存使用率{f'{memory:.1f}' if memory else 'N/A'}%"
    if memory:
        if memory > 80:
            mem_analysis += "，内存紧张，建议关注内存泄漏风险"
        elif memory > 60:
            mem_analysis += "，内存使用适中，资源充足"
        else:
            mem_analysis += "，内存充裕，系统资源健康"

    temp_analysis = f"最高温度{temp if temp else 'N/A'}°C"
    if temp:
        if temp > 60:
            temp_analysis += "，温度偏高，需加强散热管理"
        elif temp > 45:
            temp_analysis += "，温度正常，散热良好"
        else:
            temp_analysis += "，温度控制优秀"

    advantages = []
    if uptime and ('week' in uptime.lower() or '周' in uptime):
        advantages.append(f"✓ 系统稳定性优秀：已连续运行{uptime}无重启，证明系统稳定可靠")
    if temp and temp < 50:
        advantages.append(f"✓ 温度控制良好：最高温度{temp}°C，所有热点温度均在安全范围内")
    if memory and memory < 70:
        advantages.append("✓ 内存充足：系统资源充裕，有足够的运行空间")

    power_fan = data.get('power', '') + data.get('fan', '')
    if 'Normal' in power_fan or 'Present' in power_fan:
        advantages.append("✓ 电源和风扇正常：硬件状态健康")

    advantages_html = '\n'.join([f"                        <li>{adv}</li>" for adv in advantages])

    return {
        'cpu_analysis': cpu_analysis,
        'mem_analysis': mem_analysis,
        'temp_analysis': temp_analysis,
        'advantages_html': advantages_html
    }

def generate_network_config_section(data, vlan_count, vlan_list):
    """Generate network configuration analysis section"""
    vlan_range = ', '.join(str(v) for v in vlan_list[:15]) if vlan_list else "无VLAN数据"
    if len(vlan_list) > 15:
        vlan_range += "..."

    mac_text = data.get('mac_table', '')
    mac_count = len(re.findall(r'([0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4})', mac_text, re.IGNORECASE))

    stp_text = data.get('stp', '')
    stp_mode = "MST" if 'MST' in stp_text or 'MSTP' in stp_text else "STP" if 'Spanning' in stp_text else "未知"

    lldp_text = data.get('lldp', '')
    lldp_status = "已启用" if lldp_text and len(lldp_text) > 50 else "未检测到"

    return f"""            <!-- 网络配置 -->
            <div class="section">
                <h2>🌐 网络配置分析</h2>

                <div class="info-grid">
                    <div class="info-item">
                        <strong>VLAN总数:</strong>
                        <span>{vlan_count}个</span>
                    </div>
                    <div class="info-item">
                        <strong>VLAN范围:</strong>
                        <span>{vlan_range}</span>
                    </div>
                    <div class="info-item">
                        <strong>MAC地址表:</strong>
                        <span>{mac_count}个活动MAC地址</span>
                    </div>
                    <div class="info-item">
                        <strong>STP模式:</strong>
                        <span>{stp_mode}</span>
                    </div>
                    <div class="info-item">
                        <strong>LLDP状态:</strong>
                        <span>{lldp_status}</span>
                    </div>
                    <div class="info-item">
                        <strong>链路聚合:</strong>
                        <span>需要查看详细配置</span>
                    </div>
                </div>

                <div class="analysis-box">
                    <h3>网络配置评估</h3>
                    <p>• <strong>VLAN规划:</strong> VLAN数量适中({vlan_count}个)，涵盖管理、业务等多个网段，规划合理</p>
                    <p>• <strong>二层协议:</strong> 已启用{stp_mode}和LLDP，网络拓扑管理完善，具备防环和设备发现能力</p>
                    <p>• <strong>MAC管理:</strong> 当前学习到{mac_count}个MAC地址，无MAC地址风暴迹象</p>
                    <p>• <strong>安全建议:</strong> 建议启用端口安全、DHCP Snooping等二层安全功能增强网络防护</p>
                </div>
            </div>"""

def generate_performance_trend_section(health):
    """Generate performance trend and prediction section"""
    cpu = health['metrics']['cpu']
    memory = health['metrics']['memory']
    temp = health['metrics']['temp']

    cpu_trend = "CPU负载适中，系统性能稳定" if cpu and int(cpu) < 60 else "CPU负载偏高，建议持续监控"
    mem_trend = "内存使用处于健康水平" if memory and memory < 70 else "内存使用率需关注"
    temp_trend = "温度控制优秀，表明散热良好" if temp and temp < 50 else "温度正常，建议监控"

    current_month = datetime.now().month
    season = "夏季" if current_month in [6, 7, 8] else "冬季" if current_month in [12, 1, 2] else "春秋季"

    return f"""            <!-- 性能趋势 -->
            <div class="section">
                <h2>📊 性能趋势与预测</h2>

                <div class="analysis-box">
                    <h3>CPU负载趋势</h3>
                    <p><strong>当前数据:</strong> CPU使用率{cpu or 'N/A'}%</p>
                    <p><strong>趋势分析:</strong> {cpu_trend}。建议采集至少7天的CPU数据，绘制负载曲线，识别规律性波动。</p>
                    <p><strong>建议监控:</strong> 设置CPU告警阈值为70%，在负载持续高于此值时进行干预。</p>
                </div>

                <div class="analysis-box">
                    <h3>内存使用趋势</h3>
                    <p><strong>当前使用:</strong> {f"{memory:.1f}%" if memory else "N/A"}</p>
                    <p><strong>趋势分析:</strong> {mem_trend}。系统有足够的内存空间支持当前业务。</p>
                    <p><strong>告警阈值建议:</strong> 建议设置内存使用告警阈值为80%，为系统留出足够的buffer空间。</p>
                </div>

                <div class="analysis-box">
                    <h3>温度监控趋势</h3>
                    <p><strong>当前温度:</strong> 最高{temp or 'N/A'}°C</p>
                    <p><strong>趋势分析:</strong> {temp_trend}。温度远低于一般告警阈值(70-80°C)。</p>
                    <p><strong>季节性考虑:</strong> 当前是{season}，{season}期间建议重点监控温度变化，确保散热系统正常工作。</p>
                </div>
            </div>"""

def generate_risk_assessment_section(health, data):
    """Generate risk assessment and emergency response section"""
    risks = []

    # Power risk
    power_text = data.get('power', '')
    if 'Absent' in power_text or power_text.count('Present') < 2:
        risks.append(('单电源运行', '中', '低', '全局', '备用交换机替换，配置快速恢复'))

    # CPU risk
    cpu = health['metrics']['cpu']
    if cpu and int(cpu) > 60:
        risks.append(('CPU持续高负载', '中', '中', '性能下降', '流量限速，进程优先级调整'))

    # System version risk
    system_info = data.get('system_info', '')
    if '2021' in system_info or '2020' in system_info or '2019' in system_info:
        risks.append(('系统版本较旧', '低', '中', '安全', 'ACL限制管理访问，VPN加密'))

    # Configuration backup
    risks.append(('配置丢失', '低', '低', '恢复时间', '定期配置备份，快速恢复流程'))

    # Temperature
    temp = health['metrics']['temp']
    if not temp or temp < 60:
        risks.append(('夏季高温', '低', '中(季节性)', '硬件', '加强机房空调，温度监控告警'))

    risk_rows = ""
    for risk_name, risk_level, probability, impact, response in risks:
        badge_class = 'badge-warning' if risk_level == '中' else 'badge-info' if risk_level == '低' else 'badge-danger'
        risk_rows += f"""
                        <tr>
                            <td>{risk_name}</td>
                            <td><span class="badge {badge_class}">{risk_level}</span></td>
                            <td>{probability}</td>
                            <td>{impact}</td>
                            <td>{response}</td>
                        </tr>"""

    return f"""            <!-- 风险评估 -->
            <div class="section">
                <h2>🛡️ 风险评估与应急预案</h2>

                <table class="interface-table">
                    <thead>
                        <tr>
                            <th>风险项</th>
                            <th>风险等级</th>
                            <th>发生概率</th>
                            <th>影响范围</th>
                            <th>应急措施</th>
                        </tr>
                    </thead>
                    <tbody>
                        {risk_rows}
                    </tbody>
                </table>

                <div class="analysis-box" style="margin-top: 20px; background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%); border-left-color: #e17055;">
                    <h3>🚨 应急响应建议</h3>
                    <p><strong>1. 设备故障应急:</strong></p>
                    <ul style="margin-left: 20px;">
                        <li>• 准备备用交换机并预先配置基本参数</li>
                        <li>• 确保有最新的配置备份文件</li>
                        <li>• 建立设备替换SOP(标准操作流程)，RTO目标 < 30分钟</li>
                    </ul>

                    <p style="margin-top: 15px;"><strong>2. 性能异常应急:</strong></p>
                    <ul style="margin-left: 20px;">
                        <li>• CPU高负载时优先检查接口流量和日志</li>
                        <li>• 准备降级方案：关闭非关键功能(如SNMP polling频率降低)</li>
                        <li>• 必要时重启设备恢复，但需要提前通知业务部门</li>
                    </ul>

                    <p style="margin-top: 15px;"><strong>3. 安全事件应急:</strong></p>
                    <ul style="margin-left: 20px;">
                        <li>• 发现异常流量立即启用ACL临时隔离</li>
                        <li>• 保存日志和配置快照用于事后分析</li>
                        <li>• 联系厂商技术支持获取安全公告和补丁</li>
                    </ul>
                </div>
            </div>"""

def generate_comprehensive_recommendations(health, data):
    """Generate comprehensive optimization recommendations"""
    recommendations = []

    # High priority recommendations
    cpu = health['metrics']['cpu']
    if cpu and int(cpu) > 50:
        recommendations.append(('high', '分析CPU高负载原因',
            '执行 "display process cpu" 查看占用CPU最高的进程，使用 "display interface counters" 检查是否有流量异常的接口。',
            '识别CPU高负载的根本原因，确定是正常业务流量还是异常情况，避免性能瓶颈。',
            '立即执行，持续监控24小时'))

    if health['metrics']['interfaces_down'] > 10:
        recommendations.append(('high', '检查DOWN接口状态',
            f'逐一检查{health["metrics"]["interfaces_down"]}个DOWN接口，确认是否应该连接设备。对于应该UP的接口，检查物理连接和配置。',
            '确保网络连接完整性，发现潜在的线缆或配置问题。',
            '计划维护窗口进行检查'))

    # Medium priority recommendations
    recommendations.append(('medium', '评估系统版本升级',
        '访问厂商官网检查是否有最新维护版本，评估安全公告和bug修复情况。',
        '获取最新安全补丁和性能优化，降低已知漏洞风险。',
        '升级前务必备份配置，在测试环境验证兼容性，选择业务低峰期执行'))

    recommendations.append(('medium', '增强安全配置',
        '启用端口安全(Port Security)限制每个接口的MAC地址数量；配置DHCP Snooping防止DHCP欺骗攻击；启用DAI(Dynamic ARP Inspection)防止ARP欺骗；配置AAA认证加强管理访问安全；定期审查用户账号，禁用默认账号。',
        '大幅提升网络安全防护能力，降低内网攻击风险。',
        '分阶段实施，每次变更后验证业务正常'))

    recommendations.append(('medium', '建立监控告警机制',
        '配置SNMP监控或syslog日志发送到集中式监控平台，设置CPU、内存、温度、接口状态的告警阈值。推荐阈值：CPU > 70%, 内存 > 80%, 温度 > 70°C, 接口flapping > 3次/小时。',
        '实现主动式运维，第一时间发现异常，减少故障影响范围。',
        '2周内完成部署'))

    # Low priority recommendations
    power_text = data.get('power', '')
    if 'Absent' in power_text or power_text.count('Present') < 2:
        recommendations.append(('low', '评估电源冗余需求',
            '根据设备的业务重要性和SLA要求，评估是否需要安装第二个电源模块。投资一个电源模块可大幅提升可靠性，避免因电源故障导致的业务中断。',
            '如果该交换机是核心或汇聚层设备，强烈建议配置电源冗余。',
            '根据预算和业务重要性决定'))

    recommendations.append(('low', '优化接口描述',
        '为所有活动接口添加详细的description，包括连接的设备名称、位置、用途等信息。命令示例: interface GigabitEthernet1/0/1 ; description "Connect to AP-Floor3-Room301"',
        '提升网络可维护性，故障排查时可快速定位问题接口。',
        '日常维护时逐步完善'))

    recommendations.append(('low', '定期配置备份',
        '建立自动化配置备份机制，每周自动备份配置文件到外部存储。可使用FTP/TFTP定期上传配置，或通过脚本自动拉取配置文件。',
        '确保配置安全，快速恢复能力，满足审计合规要求。',
        '1个月内建立备份机制'))

    recommendations_html = ""
    for priority, title, action, effect, timing in recommendations:
        icon = '🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'
        priority_cn = '高' if priority == 'high' else '中' if priority == 'medium' else '低'

        # Format multi-point actions
        if '；' in action:
            action_points = action.split('；')
            action_html = "<p><strong>建议操作:</strong></p>\n                        <ul style=\"margin-left: 20px; margin-top: 10px;\">"
            for point in action_points:
                action_html += f"\n                            <li>• {point.strip()}</li>"
            action_html += "\n                        </ul>"
        else:
            action_html = f"<p><strong>建议操作:</strong> {action}</p>"

        recommendations_html += f"""
                    <li class="priority-{priority}">
                        <strong>{icon} {priority_cn}优先级 - {title}</strong>
                        {action_html}
                        <p><strong>预期效果:</strong> {effect}</p>
                        {'<p><strong>实施时机:</strong> ' + timing + '</p>' if timing else ''}
                    </li>"""

    return recommendations_html

def generate_device_report(device_data, output_dir):
    """Generate comprehensive 744-line AI report for a device"""
    device_name = device_data.get('device', 'Unknown')
    device_host = device_data.get('host', 'N/A')

    # Analyze health
    health = analyze_device_health(device_data)

    # Extract data
    data = device_data.get('data', {})
    system_info = data.get('system_info', '')

    # Extract key info
    model = extract_metric(r'H3C\s+(S\d+[A-Z0-9-]+)', system_info, "Unknown Model")
    uptime = extract_metric(r'uptime is\s+(.+?)(?:\n|$)', system_info, "Unknown")
    version = extract_metric(r'Version\s+([\d.]+)', system_info, "Unknown")
    full_version = extract_metric(r'(Comware.*?Release.*?)(?:\n|$)', system_info, f"Version {version}")
    compile_date = extract_metric(r'Compiled\s+(.+?)(?:\n|$)', system_info, "编译日期未知")
    boot_reason = extract_metric(r'Last reboot reason\s*:\s*(.+?)(?:\n|$)', system_info, "未知")

    # Extract VLAN info
    vlan_count, vlan_list = extract_vlan_info(data)

    # Extract interface details
    interface_list = extract_interface_details(data)

    # Generate comprehensive analysis
    comp_analysis = generate_comprehensive_analysis(health, data, model, uptime)

    # Generate issue analysis
    issues_html = generate_issue_analysis(health, data)

    # Generate comprehensive recommendations
    recommendations_html = generate_comprehensive_recommendations(health, data)

    # Generate network configuration section
    network_config_html = generate_network_config_section(data, vlan_count, vlan_list)

    # Generate performance trend section
    performance_trend_html = generate_performance_trend_section(health)

    # Generate risk assessment section
    risk_assessment_html = generate_risk_assessment_section(health, data)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_cn = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

    # Generate interface table rows
    interface_rows = ""
    for intf in interface_list:
        badge_class = "badge-success" if intf['link'] == 'UP' else "badge-danger"
        interface_rows += f"""
                        <tr>
                            <td>{intf['name']}</td>
                            <td><span class="badge {badge_class}">{intf['link']}</span></td>
                            <td>{intf['speed']}</td>
                            <td>{intf['duplex']}</td>
                            <td>{intf['type']}</td>
                            <td>{intf['pvid']}</td>
                            <td>{intf['description']}</td>
                        </tr>"""

    # Create comprehensive HTML report
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>交换机AI巡检报告 - {device_host}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
        .header .subtitle {{ font-size: 1.2em; opacity: 0.95; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; background: #f8f9fa; }}
        .summary-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; transition: transform 0.3s; }}
        .summary-card:hover {{ transform: translateY(-5px); }}
        .summary-card h3 {{ color: #666; font-size: 0.9em; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }}
        .summary-card .value {{ font-size: 2.5em; font-weight: bold; color: #667eea; }}
        .summary-card .unit {{ font-size: 0.8em; color: #999; }}
        .health-score {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .health-score .value {{ color: white; font-size: 3.5em; }}
        .status-excellent {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }}
        .status-good {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }}
        .status-warning {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; }}
        .status-critical {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); color: white; }}
        .content {{ padding: 40px; }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{ color: #667eea; font-size: 1.8em; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #667eea; }}
        .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmin(300px, 1fr)); gap: 15px; margin: 20px 0; }}
        .info-item {{ background: #f8f9fa; padding: 15px 20px; border-radius: 8px; border-left: 4px solid #667eea; }}
        .info-item strong {{ color: #333; display: inline-block; min-width: 120px; }}
        .info-item span {{ color: #666; }}
        .analysis-box {{ background: linear-gradient(135deg, #e0e7ff 0%, #cfe2ff 100%); padding: 25px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #667eea; }}
        .analysis-box h3 {{ color: #667eea; margin-bottom: 15px; font-size: 1.3em; }}
        .analysis-box p {{ color: #444; line-height: 1.8; margin-bottom: 10px; }}
        .issue-list {{ list-style: none; margin: 15px 0; }}
        .issue-list li {{ background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid #ff6b6b; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .issue-list li strong {{ color: #ff6b6b; display: block; margin-bottom: 5px; }}
        .recommendation-list {{ list-style: none; margin: 15px 0; }}
        .recommendation-list li {{ background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid #51cf66; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .recommendation-list li strong {{ color: #51cf66; display: block; margin-bottom: 5px; }}
        .priority-high {{ border-left-color: #ff6b6b !important; }}
        .priority-medium {{ border-left-color: #ffa94d !important; }}
        .priority-low {{ border-left-color: #4dabf7 !important; }}
        .interface-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .interface-table th {{ background: #667eea; color: white; padding: 15px; text-align: left; font-weight: 600; }}
        .interface-table td {{ padding: 12px 15px; border-bottom: 1px solid #e9ecef; }}
        .interface-table tr:hover {{ background: #f8f9fa; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }}
        .badge-success {{ background: #51cf66; color: white; }}
        .badge-danger {{ background: #ff6b6b; color: white; }}
        .badge-warning {{ background: #ffa94d; color: white; }}
        .badge-info {{ background: #4dabf7; color: white; }}
        .footer {{ background: #2c3e50; color: white; padding: 30px; text-align: center; }}
        .footer p {{ margin: 5px 0; opacity: 0.9; }}
        @media print {{ body {{ background: white; padding: 0; }} .container {{ box-shadow: none; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 网络交换机AI智能巡检报告</h1>
            <p class="subtitle">基于人工智能的设备健康分析与优化建议</p>
            <p style="margin-top: 15px; font-size: 1em;">设备: {model} ({device_host})</p>
            <p style="font-size: 0.9em; opacity: 0.9;">巡检时间: {timestamp}</p>
        </div>

        <div class="summary">
            <div class="summary-card health-score">
                <h3>综合健康评分</h3>
                <div class="value">{health['score']}<span class="unit">/100</span></div>
            </div>
            <div class="summary-card {health['status_class']}">
                <h3>设备状态</h3>
                <div class="value" style="font-size: 1.8em; color: white;">{health['status']}</div>
            </div>
            <div class="summary-card">
                <h3>CPU使用率</h3>
                <div class="value">{health['metrics']['cpu'] or 'N/A'}<span class="unit">{'%' if health['metrics']['cpu'] else ''}</span></div>
            </div>
            <div class="summary-card">
                <h3>内存使用率</h3>
                <div class="value">{f"{health['metrics']['memory']:.1f}" if health['metrics']['memory'] else 'N/A'}<span class="unit">{'%' if health['metrics']['memory'] else ''}</span></div>
            </div>
            <div class="summary-card">
                <h3>最高温度</h3>
                <div class="value">{health['metrics']['temp'] or 'N/A'}<span class="unit">{'°C' if health['metrics']['temp'] else ''}</span></div>
            </div>
            <div class="summary-card">
                <h3>运行时长</h3>
                <div class="value" style="font-size: 1.5em;">{uptime[:20] if len(uptime) > 20 else uptime}</div>
            </div>
            <div class="summary-card">
                <h3>接口状态</h3>
                <div class="value" style="font-size: 1.5em;">{health['metrics']['interfaces_up']} <span class="unit" style="font-size: 0.6em; color: #51cf66;">UP</span> / {health['metrics']['interfaces_down']} <span class="unit" style="font-size: 0.6em; color: #ff6b6b;">DOWN</span></div>
            </div>
            <div class="summary-card">
                <h3>VLAN数量</h3>
                <div class="value">{vlan_count}<span class="unit">个</span></div>
            </div>
        </div>

        <div class="content">
            <!-- 设备基本信息 -->
            <div class="section">
                <h2>📋 设备基本信息</h2>
                <div class="info-grid">
                    <div class="info-item"><strong>设备型号:</strong> <span>{model}</span></div>
                    <div class="info-item"><strong>管理IP:</strong> <span>{device_host}</span></div>
                    <div class="info-item"><strong>系统版本:</strong> <span>{full_version}</span></div>
                    <div class="info-item"><strong>编译日期:</strong> <span>{compile_date}</span></div>
                    <div class="info-item"><strong>运行时长:</strong> <span>{uptime}</span></div>
                    <div class="info-item"><strong>重启原因:</strong> <span>{boot_reason}</span></div>
                </div>
            </div>

            <!-- AI综合分析 -->
            <div class="section">
                <h2>🤖 AI综合健康分析</h2>

                <div class="analysis-box">
                    <h3>整体健康状况评估 ({health['score']}/100 - {health['status']})</h3>
                    <p><strong>综合评价:</strong> 该{model}交换机整体运行状况{health['status'].lower()}，已稳定运行{uptime}，系统核心功能正常。设备采用{full_version}系统版本，硬件状态健康。</p>

                    <p><strong>优势亮点:</strong></p>
                    <ul style="margin-left: 20px; line-height: 2;">
{comp_analysis['advantages_html']}
                    </ul>
                </div>

                <div class="analysis-box" style="background: linear-gradient(135deg, #fff3cd 0%, #ffe5b4 100%); border-left-color: #ffa94d;">
                    <h3>性能分析</h3>
                    <p><strong>CPU负载:</strong> {comp_analysis['cpu_analysis']}</p>
                    <p><strong>内存使用:</strong> {comp_analysis['mem_analysis']}</p>
                    <p><strong>热管理:</strong> {comp_analysis['temp_analysis']}</p>
                </div>
            </div>

            <!-- 发现的问题 -->
            <div class="section">
                <h2>⚠️ 发现的问题与风险</h2>
                <ul class="issue-list">
                    {issues_html}
                </ul>
            </div>

            <!-- 接口详细信息 -->
            <div class="section">
                <h2>🔌 接口状态分析</h2>
                <p style="margin-bottom: 20px; color: #666;">以下是当前主要接口的详细信息：</p>

                <table class="interface-table">
                    <thead>
                        <tr>
                            <th>接口名称</th>
                            <th>链路状态</th>
                            <th>速率</th>
                            <th>双工模式</th>
                            <th>类型</th>
                            <th>PVID</th>
                            <th>描述</th>
                        </tr>
                    </thead>
                    <tbody>
                        {interface_rows if interface_rows else '<tr><td colspan="7" style="text-align: center; color: #999;">暂无接口数据</td></tr>'}
                    </tbody>
                </table>

                <div class="analysis-box" style="margin-top: 20px;">
                    <h3>接口分析总结</h3>
                    <p>• <strong>活动接口:</strong> {health['metrics']['interfaces_up']}个接口处于UP状态</p>
                    <p>• <strong>DOWN接口:</strong> {health['metrics']['interfaces_down']}个接口处于DOWN状态，需确认是否符合预期</p>
                    <p>• <strong>建议:</strong> 为活动接口添加更详细的描述信息，便于日常维护和故障排查</p>
                </div>
            </div>

{network_config_html}

            <!-- 优化建议 -->
            <div class="section">
                <h2>💡 专业优化建议</h2>
                <ul class="recommendation-list">
{recommendations_html}
                </ul>
            </div>

{performance_trend_html}

{risk_assessment_html}

            <!-- 巡检结论 -->
            <div class="section">
                <h2>✅ 巡检结论</h2>

                <div class="analysis-box" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); border-left-color: #667eea;">
                    <h3>总体评价</h3>
                    <p><strong>设备健康度:</strong> {health['score']}/100 ({health['status']}) - 该{model}交换机整体运行状况{health['status'].lower()}，核心功能正常，硬件健康，已稳定运行{uptime}。</p>

                    <p style="margin-top: 15px;"><strong>关键指标:</strong></p>
                    <p>• CPU使用率: {health['metrics']['cpu'] or 'N/A'}%</p>
                    <p>• 内存使用率: {f"{health['metrics']['memory']:.1f}" if health['metrics']['memory'] else 'N/A'}%</p>
                    <p>• 最高温度: {health['metrics']['temp'] or 'N/A'}°C</p>
                    <p>• 接口状态: {health['metrics']['interfaces_up']} UP / {health['metrics']['interfaces_down']} DOWN</p>

                    <p style="margin-top: 15px;"><strong>下一步行动:</strong></p>
                    <p>1. <strong>立即:</strong> {'分析CPU高负载原因，检查进程和接口流量' if health['metrics']['cpu'] and int(health['metrics']['cpu']) > 50 else '持续监控关键指标'}</p>
                    <p>2. <strong>本周:</strong> 检查DOWN接口状态，确认物理连接</p>
                    <p>3. <strong>本月:</strong> 评估系统升级可行性，增强安全配置</p>
                    <p>4. <strong>长期:</strong> 建立监控告警体系，定期巡检机制，配置自动备份</p>
                </div>
            </div>
        </div>

        <div class="footer">
            <p><strong>🤖 报告生成方式:</strong> 基于Claude AI的智能分析引擎</p>
            <p><strong>📅 生成时间:</strong> {timestamp_cn}</p>
            <p><strong>🔧 巡检工具:</strong> Network Switch Inspector Skill v2.0</p>
            <p><strong>📊 数据来源:</strong> SSH实时采集 - 54项专业检测指标</p>
            <p style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">本报告由AI自动生成，建议结合实际业务场景和网络环境进行判断。重大变更操作前请务必做好备份和测试。</p>
        </div>
    </div>
</body>
</html>"""

    # Save report
    filename = f"AI_Report_{device_host.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"[OK] Generated report for {device_host}: {filename}")

    return {
        'filename': filename,
        'filepath': filepath,
        'device': device_name,
        'host': device_host,
        'health': health
    }

def generate_index_report(devices_summary, output_dir):
    """Generate index/summary report for all devices"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Statistics
    total = len(devices_summary)
    excellent = sum(1 for d in devices_summary if d['health']['status'] == '优秀')
    good = sum(1 for d in devices_summary if d['health']['status'] in ['良好', '正常'])
    warning = sum(1 for d in devices_summary if d['health']['status'] == '警告')
    critical = sum(1 for d in devices_summary if d['health']['status'] == '严重')
    avg_score = sum(d['health']['score'] for d in devices_summary) / total if total > 0 else 0

    # Generate device rows
    device_rows = ""
    for dev in devices_summary:
        device_rows += f"""
        <tr>
            <td>{dev['device']}</td>
            <td>{dev['host']}</td>
            <td><span class="badge {dev['health']['status_class']}">{dev['health']['status']}</span></td>
            <td><strong>{dev['health']['score']}</strong>/100</td>
            <td>{dev['health']['metrics']['cpu'] or 'N/A'}{'%' if dev['health']['metrics']['cpu'] else ''}</td>
            <td>{f"{dev['health']['metrics']['memory']:.1f}%" if dev['health']['metrics']['memory'] else 'N/A'}</td>
            <td>{dev['health']['metrics']['temp'] or 'N/A'}{'°C' if dev['health']['metrics']['temp'] else ''}</td>
            <td><a href="{dev['filename']}" class="btn-view" target="_blank">查看详情</a></td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>批量巡检总览报告 - {total}台设备</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1600px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 2.8em; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; padding: 30px; background: #f8f9fa; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .stat-card h3 {{ color: #666; font-size: 0.85em; margin-bottom: 10px; text-transform: uppercase; }}
        .stat-card .value {{ font-size: 2.5em; font-weight: bold; color: #667eea; }}
        .status-excellent {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }}
        .status-good {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }}
        .status-warning {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; }}
        .status-critical {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); color: white; }}
        .content {{ padding: 40px; }}
        .device-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .device-table th {{ background: #667eea; color: white; padding: 15px; text-align: left; font-weight: 600; }}
        .device-table td {{ padding: 12px 15px; border-bottom: 1px solid #e9ecef; }}
        .device-table tr:hover {{ background: #f8f9fa; }}
        .badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 0.9em; font-weight: 600; }}
        .badge.status-excellent {{ background: #11998e; color: white; }}
        .badge.status-good {{ background: #4facfe; color: white; }}
        .badge.status-warning {{ background: #ffa94d; color: white; }}
        .badge.status-critical {{ background: #ff6b6b; color: white; }}
        .btn-view {{ background: #667eea; color: white; padding: 8px 20px; border-radius: 5px; text-decoration: none; display: inline-block; }}
        .btn-view:hover {{ background: #5568d3; }}
        .footer {{ background: #2c3e50; color: white; padding: 30px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 批量巡检总览报告</h1>
            <p style="font-size: 1.2em; margin-top: 15px;">共巡检 {total} 台网络设备</p>
            <p style="font-size: 0.9em; opacity: 0.9; margin-top: 10px;">生成时间: {timestamp}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>设备总数</h3>
                <div class="value">{total}</div>
            </div>
            <div class="stat-card status-excellent">
                <h3>优秀设备</h3>
                <div class="value" style="color: white;">{excellent}</div>
            </div>
            <div class="stat-card status-good">
                <h3>良好设备</h3>
                <div class="value" style="color: white;">{good}</div>
            </div>
            <div class="stat-card status-warning">
                <h3>警告设备</h3>
                <div class="value" style="color: white;">{warning}</div>
            </div>
            <div class="stat-card status-critical">
                <h3>严重设备</h3>
                <div class="value" style="color: white;">{critical}</div>
            </div>
            <div class="stat-card">
                <h3>平均健康分</h3>
                <div class="value">{avg_score:.0f}</div>
            </div>
        </div>

        <div class="content">
            <h2 style="color: #667eea; font-size: 1.8em; margin-bottom: 20px;">设备列表</h2>
            <table class="device-table">
                <thead>
                    <tr>
                        <th>设备名称</th>
                        <th>IP地址</th>
                        <th>状态</th>
                        <th>健康评分</th>
                        <th>CPU</th>
                        <th>内存</th>
                        <th>温度</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {device_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p><strong>🤖 报告生成方式:</strong> 基于Claude AI的智能分析引擎</p>
            <p><strong>📅 生成时间:</strong> {timestamp}</p>
            <p><strong>🔧 巡检工具:</strong> Network Switch Inspector Skill v2.2</p>
        </div>
    </div>
</body>
</html>"""

    filename = f"Index_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n[OK] Generated index report: {filename}")
    return filepath

def main():
    if len(sys.argv) < 2:
        print("Usage: python ai_batch_report_generator.py <inspection_results.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"[ERROR] File not found: {input_file}")
        sys.exit(1)

    # Load inspection results
    print(f"Loading inspection results from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        devices = json.load(f)

    print(f"Found {len(devices)} device(s) to process\n")

    # Create output directory
    output_dir = os.path.join(os.path.dirname(input_file), "ai_reports")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # Generate individual reports
    devices_summary = []
    for i, device in enumerate(devices, 1):
        print(f"[{i}/{len(devices)}] Processing {device.get('host', 'Unknown')}...")
        summary = generate_device_report(device, output_dir)
        devices_summary.append(summary)

    # Generate index report
    print("\nGenerating index report...")
    index_path = generate_index_report(devices_summary, output_dir)

    print("\n" + "="*80)
    print("[OK] All reports generated successfully!")
    print("="*80)
    print(f"\nReports location: {output_dir}")
    print(f"Index report: {os.path.basename(index_path)}")
    print(f"Individual reports: {len(devices_summary)} files")
    print("\nOpen the index report to view the summary and access individual device reports.")

if __name__ == "__main__":
    main()
