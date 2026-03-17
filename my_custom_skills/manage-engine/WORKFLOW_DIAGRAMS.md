# Configure Alarms API - Visual Workflow

## 🎯 Configuration Decision Tree

```
┌────────────────────────────────────────────────────────────┐
│           Configure Alarms API - Decision Flow             │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   What do you want to configure?      │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  Single Monitor  │                  │  Monitor Type    │
│  (resource_id)   │                  │  (resource_type) │
└──────────────────┘                  └──────────────────┘
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  Which alarm?    │                  │  Which alarm?    │
│  (attribute_id)  │                  │  (attribute_id)  │
└──────────────────┘                  └──────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   How to set threshold?               │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  Use Template    │                  │  Custom Values   │
│  (threshold_id)  │                  │  (critical_*)    │
│  ✅ RECOMMENDED  │                  │  (warning_*)     │
└──────────────────┘                  └──────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Add notifications?                  │
        │   (optional)                          │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  Yes             │                  │  No              │
│  (action_id)     │                  │  (skip)          │
└──────────────────┘                  └──────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Configure poll counts?              │
        │   (optional)                          │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  Availability    │                  │  Threshold       │
│  Attribute 700   │                  │  Metrics         │
│  availability_*  │                  │  consecutive_*   │
└──────────────────┘                  └──────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Execute Request                     │
        │   POST /xml/configurealarms           │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Response                            │
        │   4000 = Success                      │
        │   400x = Error                        │
        └───────────────────────────────────────┘
```

## 🔄 Configuration Modes

### Mode 1: Single Monitor with Template
```
User Input:
  resource_id = "10113263"
  attribute_id = "708"
  threshold_id = "1"

    │
    ▼
┌─────────────────────────────────┐
│  configure_alarm()              │
│  ├─ resource_id                 │
│  ├─ attribute_id                │
│  ├─ threshold_id                │
│  └─ request_type=1              │
└─────────────────────────────────┘
    │
    ▼
API Request:
  POST /xml/configurealarms
  resourceid=10113263
  attributeid=708
  thresholdid=1
  requesttype=1
  overrideConf=true

    │
    ▼
Result:
  ✅ Threshold profile applied
```

### Mode 2: Multiple Attributes
```
User Input:
  resource_id = "10113263"
  attribute_id = "708,685,711"  # CPU, Memory, Disk
  threshold_id = "1"

    │
    ▼
┌─────────────────────────────────┐
│  configure_alarm()              │
│  ├─ resource_id                 │
│  ├─ attribute_id (multi)        │
│  ├─ threshold_id                │
│  └─ request_type=1              │
└─────────────────────────────────┘
    │
    ▼
API Request:
  POST /xml/configurealarms
  resourceid=10113263
  attributeid=708,685,711
  thresholdid=1
  requesttype=1

    │
    ▼
Result:
  ✅ 3 attributes configured
```

### Mode 3: Monitor Type Template
```
User Input:
  resource_type = "servers"
  attribute_id = "708"
  threshold_id = "1"

    │
    ▼
┌─────────────────────────────────┐
│  configure_alarm()              │
│  ├─ resource_type               │
│  ├─ attribute_id                │
│  ├─ threshold_id                │
│  └─ override_conf=False         │
└─────────────────────────────────┘
    │
    ▼
API Request:
  POST /xml/configurealarms
  resourceType=servers
  attributeid=708
  thresholdid=1
  overrideConf=false

    │
    ▼
Result:
  ✅ All 'servers' type configured
```

### Mode 4: Custom Thresholds
```
User Input:
  resource_id = "10113263"
  attribute_id = "708"
  critical_threshold = 95
  warning_threshold = 85

    │
    ▼
┌─────────────────────────────────┐
│  configure_alarm()              │
│  ├─ resource_id                 │
│  ├─ attribute_id                │
│  ├─ critical_threshold          │
│  ├─ warning_threshold           │
│  ├─ critical_condition=">"      │
│  └─ consecutive_critical_polls  │
└─────────────────────────────────┘
    │
    ▼
API Request:
  POST /xml/configurealarms
  resourceid=10113263
  attributeid=708
  criticalthresholdvalue=95
  warningthresholdvalue=85
  criticalthresholdcondition=>
  consecutive_criticalpolls=3

    │
    ▼
Result:
  ✅ Custom thresholds set
```

## 📊 Data Flow Diagram

```
┌──────────────┐
│  Python App  │
└──────┬───────┘
       │ client.configure_alarm(...)
       ▼
┌─────────────────────────────────────────────┐
│  AppManagerClient                           │
│  ┌───────────────────────────────────────┐  │
│  │ configure_alarm()                     │  │
│  │ ├─ Build params dict                 │  │
│  │ ├─ Convert types                     │  │
│  │ ├─ Map Python → API parameters       │  │
│  │ └─ Call request()                    │  │
│  └───────────────┬───────────────────────┘  │
└──────────────────┼──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  request()                                  │
│  ├─ Method: POST                            │
│  ├─ Format: xml                             │
│  ├─ Endpoint: configurealarms               │
│  └─ Add apikey                              │
└──────────────────┬──────────────────────────┘
                   │
                   │ HTTPS POST
                   ▼
┌─────────────────────────────────────────────┐
│  ManageEngine Applications Manager         │
│  https://server:8443                        │
│  /AppManager/xml/configurealarms            │
│  ┌───────────────────────────────────────┐  │
│  │ Validate parameters                   │  │
│  │ Apply configuration                   │  │
│  │ Associate actions                     │  │
│  │ Save to database                      │  │
│  │ Return XML response                   │  │
│  └───────────────┬───────────────────────┘  │
└──────────────────┼──────────────────────────┘
                   │
                   │ XML Response
                   ▼
┌─────────────────────────────────────────────┐
│  Response XML                               │
│  <AppManager-response>                      │
│    <result>                                 │
│      <response response-code="4000">        │
│        <message>成功</message>              │
│      </response>                            │
│    </result>                                │
│  </AppManager-response>                     │
└──────────────────┬──────────────────────────┘
                   │
                   │ return response.text
                   ▼
┌──────────────┐
│  Python App  │  ← Process result
└──────────────┘
```

## 🎯 Parameter Flow

```
Python Code:
┌───────────────────────────────────────────────────────┐
│  client.configure_alarm(                              │
│      resource_id="10113263",                          │
│      attribute_id="708",                              │
│      threshold_id="1",                                │
│      critical_action_id="10000003",                   │
│      availability_critical_poll_count=3,              │
│      override_conf=True                               │
│  )                                                    │
└───────────────────────┬───────────────────────────────┘
                        │
                        ▼ Parameter Mapping
┌───────────────────────────────────────────────────────┐
│  params = {                                           │
│      "resourceid": "10113263",         ← str(...)     │
│      "attributeid": "708",             ← str(...)     │
│      "thresholdid": "1",               ← str(...)     │
│      "criticalactionid": "10000003",   ← str(...)     │
│      "availabilityCriticalPollCount": "3", ← str(...) │
│      "overrideConf": "true",           ← "true"       │
│      "requesttype": "1",               ← str(default) │
│      "apikey": "xxx"                   ← auto         │
│  }                                                    │
└───────────────────────┬───────────────────────────────┘
                        │
                        ▼ HTTP POST
┌───────────────────────────────────────────────────────┐
│  POST /AppManager/xml/configurealarms                 │
│  Data:                                                │
│      resourceid=10113263&                             │
│      attributeid=708&                                 │
│      thresholdid=1&                                   │
│      criticalactionid=10000003&                       │
│      availabilityCriticalPollCount=3&                 │
│      overrideConf=true&                               │
│      requesttype=1&                                   │
│      apikey=xxx                                       │
└───────────────────────┬───────────────────────────────┘
                        │
                        ▼ Server Processing
                     ✅ Applied
```

## 🔔 Action Association Flow

```
┌─────────────────────────────────────────────────┐
│  Alarm Configuration                            │
│  ├─ Threshold: CPU > 90%                        │
│  ├─ Critical Action: WeChat Robot (10000003)    │
│  ├─ Warning Action: Email (10000004)            │
│  └─ Clear Action: WeChat Robot (10000003)       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼ Monitor State Change
           ┌───────┴───────┐
           │               │
    Normal │               │ Threshold Breach
           ▼               ▼
    ┌─────────┐     ┌──────────────┐
    │ CLEAR   │     │  WARNING     │
    │ (<80%)  │     │  (80-90%)    │
    └────┬────┘     └──────┬───────┘
         │                  │
         │ Clear            │ Warning
         │ Action           │ Action
         ▼                  ▼
    ┌─────────┐     ┌──────────────┐
    │ WeChat  │     │  Email       │
    │ Notify  │     │  Notify      │
    └─────────┘     └──────┬───────┘
                           │
                           │ Continues
                           ▼
                    ┌──────────────┐
                    │  CRITICAL    │
                    │  (>90%)      │
                    └──────┬───────┘
                           │ Critical
                           │ Action
                           ▼
                    ┌──────────────┐
                    │  WeChat      │
                    │  Notify      │
                    └──────────────┘
```

## 📈 Poll Count Logic

### Availability Polls (Attribute 700)
```
Poll Results: DOWN DOWN DOWN UP DOWN
              │    │    │    │   │
              ▼    ▼    ▼    ▼   ▼
Poll Count:   1    2    3    0   1
              │    │    │    │   │
              │    │    │    │   └─ Count resets
              │    │    │    └───── Success: Reset counter
              │    │    └────────── Poll 3: ALERT! (if critical_count=3)
              │    └─────────────── Poll 2: Increment
              └──────────────────── Poll 1: Start counting

availabilityCriticalPollCount = 3
  → Alert triggered on 3rd consecutive DOWN

availabilityClearPollCount = 2
  → Alert cleared on 2nd consecutive UP
```

### Consecutive Polls (Metric Attributes)
```
CPU Values: 92% 94% 95% 88% 91%
            │   │   │   │   │
Threshold:  90% 90% 90% 90% 90%
            │   │   │   │   │
Status:     C   C   C   N   C
            │   │   │   │   │
            ▼   ▼   ▼   ▼   ▼
Count:      1   2   3   0   1
            │   │   │   │   │
            │   │   │   └───┴─ Below threshold: Reset
            │   │   └───────── Poll 3: ALERT! (if consecutive_critical=3)
            │   └───────────── Poll 2: Increment
            └───────────────── Poll 1: Start counting

consecutive_criticalpolls = 3
  → Critical alert on 3rd consecutive breach
```

## 🎨 Complete Example Flow

```
Goal: Configure server monitoring with all alarms

Step 1: Initialize Client
┌────────────────────────────────────┐
│  client = AppManagerClient(...)   │
└────────────┬───────────────────────┘
             │
Step 2: Configure Availability       ▼
┌────────────────────────────────────────────┐
│  client.configure_alarm(                   │
│      resource_id="10113263",               │
│      attribute_id="700",  # Availability   │
│      threshold_id="1",                     │
│      critical_action_id="10000003",        │
│      availability_critical_poll_count=3    │
│  )                                         │
└────────────┬───────────────────────────────┘
             │ ✅ Server down detection
Step 3: Configure Health             ▼
┌────────────────────────────────────────────┐
│  client.configure_alarm(                   │
│      resource_id="10113263",               │
│      attribute_id="701",  # Health         │
│      threshold_id="1",                     │
│      critical_action_id="10000003"         │
│  )                                         │
└────────────┬───────────────────────────────┘
             │ ✅ Health status monitoring
Step 4: Configure Metrics            ▼
┌────────────────────────────────────────────┐
│  client.configure_alarm(                   │
│      resource_id="10113263",               │
│      attribute_id="708,685,711",  # Multi  │
│      threshold_id="1",                     │
│      critical_action_id="10000003",        │
│      consecutive_critical_polls=3          │
│  )                                         │
└────────────┬───────────────────────────────┘
             │ ✅ CPU, Memory, Disk alarms
             ▼
Result: Complete server monitoring setup
┌────────────────────────────────────────────┐
│  ✅ Availability: 3 poll retry             │
│  ✅ Health: Action associated              │
│  ✅ CPU: Threshold + action                │
│  ✅ Memory: Threshold + action             │
│  ✅ Disk: Threshold + action               │
└────────────────────────────────────────────┘
```

## 📝 Success Response Flow

```
API Response:
<?xml version="1.0" encoding="UTF-8"?>
<AppManager-response uri="/AppManager/xml/configurealarms">
  <result>
    <response response-code="4000">
      <message>已成功创建动作</message>
    </response>
  </result>
</AppManager-response>

         │
         ▼ Parse
┌────────────────────┐
│  response-code     │
│  = "4000"          │
│  ✅ Success        │
└────────────────────┘

Error Response:
<?xml version="1.0" encoding="UTF-8"?>
<AppManager-response>
  <result>
    <response response-code="4001">
      <message>参数错误</message>
    </response>
  </result>
</AppManager-response>

         │
         ▼ Parse
┌────────────────────┐
│  response-code     │
│  = "4001"          │
│  ❌ Error          │
└────────────────────┘
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-09
**Purpose**: Visual reference for Configure Alarms API workflow
