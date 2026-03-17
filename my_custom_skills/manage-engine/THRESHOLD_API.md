# ManageEngine Applications Manager - Threshold Configuration APIs

These APIs allow an admin user to configure thresholds in Applications Manager. Supports GET and POST requests.

## 🔗 API Endpoints
- **List Thresholds (GET)**: `/AppManager/json/threshold?apikey=[API Key]`
- **Create Threshold (POST)**: `/AppManager/json/threshold?apikey=[API Key]&...params...`
- **Update Threshold (POST)**: `/AppManager/json/threshold?apikey=[API Key]&thresholdid=[ID]&...params...`
- **Delete Threshold (POST)**: `/AppManager/json/threshold?apikey=[API Key]&thresholdid=[ID]&TO_DELETE=true`

## 📋 Key Request Parameters

| Field | Description |
| :--- | :--- |
| `thresholdname` | Display name of the threshold profile. |
| `type` | 1 (Numeric), 4 (Float), 3 (String) |
| `criticalcondition` | GT, LT, EQ, NE, LE, GE |
| `criticalvalue` | The threshold value for critical status. |
| `criticalmessage` | Notification message for critical condition. |
| `warningcondition` | GT, LT, EQ, NE, LE, GE |
| `warningvalue` | The threshold value for warning status. |
| `warningmessage` | Notification message for warning condition. |
| `thresholdType` | 0 (Standard), 1 (Adaptive) |

## 📊 Common Threshold Profiles (Discovered)

| ID | Name | Critical | Warning |
| :--- | :--- | :--- | :--- |
| 10000099 | CPU 70%报警 90%警告 | > 90 | >= 70 |
| 10000092 | CPU大于80%提醒 | >= 90 | >= 80 |
| 10000110 | 磁盘使用率大于90% | >= 95 | >= 90 |
| 10000087 | 磁盘空间使用超过70% | > 80 | >= 70 |
| 10000093 | 内存使用率80%报警 | > 90 | > 80 |
| 10000090 | Network Interface Status | equals down | - |

## 💡 Example: List via Python
```python
client.request("threshold", format="json")
```
