# Configure Alarms API - Quick Reference Guide

## 📋 Overview

The Configure Alarms API allows administrators to configure alarm thresholds for monitors in ManageEngine Applications Manager. It supports both individual monitor configuration and bulk configuration via monitor type templates.

## 🔑 Key Features

- ✅ Apply existing threshold profiles (recommended)
- ✅ Create custom threshold values
- ✅ Configure multiple attributes in one call
- ✅ Associate action notifications (Email, WeChat, etc.)
- ✅ Apply templates to monitor types
- ✅ Remove/delete configurations

## 🚀 Quick Start Examples

### 1️⃣ Simple Template Application (Recommended)

```python
from manage_engine_api import AppManagerClient

client = AppManagerClient("https://server:8443", "your_api_key")

# Apply default threshold to CPU
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    threshold_id="1",
    request_type=1
)
```

### 2️⃣ With Action Notifications

```python
# Configure CPU alarm with WeChat notification
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    threshold_id="3",
    critical_action_id="10000003",  # WeChat robot
    availability_critical_poll_count=3,
    request_type=1
)
```

### 3️⃣ Multiple Attributes

```python
# Configure CPU, Memory, Disk together
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708,685,711",  # CPU, Memory, Disk
    threshold_id="1",
    request_type=1
)
```

### 4️⃣ Custom Thresholds

```python
# Custom CPU threshold values
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    critical_threshold=95,
    warning_threshold=85,
    consecutive_critical_polls=3,
    request_type=1
)
```

### 5️⃣ Monitor Type Template

```python
# Apply to all Linux servers
result = client.configure_alarm(
    resource_type="servers",
    attribute_id="708",
    threshold_id="1",
    override_conf=False
)
```

## 📊 Common Attribute IDs

| Metric | ID | Description |
|--------|------|-------------|
| **Availability** | 700 | Server up/down detection |
| **Health Status** | 701 | Overall health |
| **CPU** | 708 | CPU utilization % |
| **Memory** | 685, 702 | Memory utilization % |
| **Disk** | 711, 761 | Disk utilization % |

## 🎯 Request Types

| Value | Action | Description |
|-------|--------|-------------|
| **1** | Save | Save and apply configuration |
| **2** | Save & Continue | Save and configure another |
| **3** | Remove | Remove configuration |
| **8** | Delete Template | Delete and disassociate |

## ⚙️ Configuration Approaches

### Approach A: Threshold Profile (Simple)

```python
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    threshold_id="1",        # Use existing profile
    request_type=1
)
```

**Pros:**
- ✅ Simple and reliable
- ✅ Reusable profiles
- ✅ Recommended method

**Cons:**
- ❌ Limited customization

### Approach B: Custom Thresholds (Advanced)

```python
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    critical_threshold=95,      # Custom values
    warning_threshold=85,
    critical_condition=">",
    consecutive_critical_polls=3,
    request_type=1
)
```

**Pros:**
- ✅ Full customization
- ✅ Specific threshold values

**Cons:**
- ❌ More complex
- ❌ API limitations (use Web UI for advanced cases)

## 🔔 Action Association

```python
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    threshold_id="1",
    critical_action_id="10000003",    # Critical alerts
    warning_action_id="10000003",     # Warning alerts
    clear_action_id="10000003",       # Clear alerts
    request_type=1
)
```

## 📈 Poll Count Configuration

### Availability Polls (for attribute 700)

```python
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="700",
    availability_critical_poll_count=3,  # Alert after 3 failures
    availability_clear_poll_count=2,     # Clear after 2 successes
    request_type=1
)
```

### Threshold Polls (for metrics)

```python
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    consecutive_critical_polls=3,  # Threshold-level setting
    consecutive_warning_polls=2,
    consecutive_clear_polls=1,
    request_type=1
)
```

## 🗑️ Remove Configuration

```python
# Remove CPU alarm
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    request_type=3  # Remove
)
```

## 🎨 Complete Server Setup

```python
def setup_server_alarms(resource_id, action_id):
    """Configure all essential alarms for a server"""

    # 1. Availability alarm
    client.configure_alarm(
        resource_id=resource_id,
        attribute_id="700",
        threshold_id="1",
        critical_action_id=action_id,
        availability_critical_poll_count=3
    )

    # 2. Health status
    client.configure_alarm(
        resource_id=resource_id,
        attribute_id="701",
        threshold_id="1",
        critical_action_id=action_id
    )

    # 3. CPU, Memory, Disk
    client.configure_alarm(
        resource_id=resource_id,
        attribute_id="708,685,711",
        threshold_id="1",
        critical_action_id=action_id
    )
```

## 🛠️ Helper Scripts

### Script 1: Advanced Examples
```bash
# Run interactive examples
python configure_alarms_advanced.py <example_number> <resource_id> [action_id]

# Example: Simple template
python configure_alarms_advanced.py 1 10113263

# Example: With actions
python configure_alarms_advanced.py 2 10113263 10000003

# Example: Comprehensive setup
python configure_alarms_advanced.py 10 10113263 10000003
```

### Script 2: Quick CPU Setup
```bash
# Configure CPU alarm with defaults (90% critical, 80% warning)
python set_cpu_alarm.py 10113263

# Custom thresholds
python set_cpu_alarm.py 10113263 95 85
```

### Script 3: Full Server Setup
```bash
# Setup all alarms (availability, health, CPU)
python setup_alarms.py 10113263 10000003
```

## 📝 API Parameters Reference

### Core Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `apikey` | String | Yes | API authentication key |
| `resourceid` | String | Yes* | Monitor resource ID |
| `attributeid` | String | Yes | Attribute ID(s), comma-separated |
| `requesttype` | Integer | Yes | 1=Save, 2=Continue, 3=Remove, 8=Delete |

*Or use `monitor_name` or `resource_type`

### Threshold Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `threshold_id` | String | Existing threshold profile ID |
| `critical_threshold` | Number | Critical threshold value |
| `warning_threshold` | Number | Warning threshold value |
| `info_threshold` | Number | Clear threshold value |
| `critical_condition` | String | `>`, `<`, `=`, `>=`, `<=` |
| `consecutive_critical_polls` | Integer | Polls before critical alert |

### Action Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `critical_action_id` | String | Action for critical alerts |
| `warning_action_id` | String | Action for warning alerts |
| `clear_action_id` | String | Action for clear alerts |

### Advanced Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `resource_type` | String | Monitor type (for templates) |
| `override_conf` | Boolean | Override existing config |
| `availability_critical_poll_count` | Integer | Polls before availability alert |
| `availability_clear_poll_count` | Integer | Polls before clear |
| `remove_rca` | Boolean | Remove RCA message |

## 🎯 Best Practices

### ✅ DO

1. **Use threshold profiles** - Simpler and more maintainable
2. **Configure multiple attributes** - Use comma-separated IDs
3. **Set appropriate poll counts** - Avoid false positives
4. **Associate actions** - Enable notifications
5. **Test incrementally** - Start with one alarm

### ❌ DON'T

1. **Don't skip override_conf** - May not apply changes
2. **Don't use API for complex thresholds** - Use Web UI instead
3. **Don't set poll counts too low** - Causes alert storms
4. **Don't forget action IDs** - No notifications otherwise

## 🔍 Troubleshooting

### Issue: Configuration not applying

```python
# Solution: Set override_conf=True
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    threshold_id="1",
    override_conf=True  # ← Important!
)
```

### Issue: Too many alerts

```python
# Solution: Increase poll counts
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="700",
    availability_critical_poll_count=5,  # Increase from 1-2
    availability_clear_poll_count=3
)
```

### Issue: Custom thresholds not working

```python
# Solution: Use Web UI or ensure all parameters are set
# For complex custom thresholds, Web UI is recommended
```

## 📚 Related Documentation

- **API Reference**: `API_REFERENCE.md` (Section 3)
- **Skill Guide**: `skill.md` (Section 4)
- **Learning Summary**: `LEARNING_SUMMARY.md`
- **Official Docs**: https://www.manageengine.com/products/applications_manager/help/configure-alarms.html

## 🚀 Quick Command Reference

```bash
# List available examples
python configure_alarms_advanced.py

# Simple template (Example 1)
python configure_alarms_advanced.py 1 <resource_id>

# With actions (Example 2)
python configure_alarms_advanced.py 2 <resource_id> <action_id>

# Multiple attributes (Example 3)
python configure_alarms_advanced.py 3 <resource_id>

# Custom thresholds (Example 4)
python configure_alarms_advanced.py 4 <resource_id>

# Monitor type (Example 5)
python configure_alarms_advanced.py 5 <monitor_type>

# Remove config (Example 6)
python configure_alarms_advanced.py 6 <resource_id>

# Availability alarm (Example 7)
python configure_alarms_advanced.py 7 <resource_id> <action_id>

# Health alarm (Example 8)
python configure_alarms_advanced.py 8 <resource_id> <action_id>

# Memory & Disk (Example 9)
python configure_alarms_advanced.py 9 <resource_id>

# Comprehensive (Example 10)
python configure_alarms_advanced.py 10 <resource_id> <action_id>
```

---

**Last Updated**: 2026-02-09
**Version**: 1.0
**Author**: ManageEngine Integration Team
