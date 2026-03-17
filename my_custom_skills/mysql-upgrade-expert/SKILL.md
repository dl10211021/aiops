---
name: mysql-upgrade-expert
description: Automated tool for assessing MySQL 8.0 to 8.4 upgrade readiness, focusing on deprecated authentication, charsets, and replication settings.
---

# MySQL Upgrade Expert Skill

This skill provides an automated assessment for upgrading from MySQL 8.0 to MySQL 8.4. It checks for critical blockers, deprecated features, and configuration risks that could impact the upgrade process or post-upgrade stability.

## Features

1.  **Authentication Audit:** Detects users still using `mysql_native_password` (removed in 8.4) and generates migration SQL.
2.  **Charset Check:** Scans for deprecated `utf8mb3` (aliased as `utf8`) usage in user schemas.
3.  **Replication Health:** verifies `GTID_MODE` and `BINLOG_FORMAT` for safer failover and data consistency.
4.  **Remediation Generation:** Outputs a SQL script with recommended fixes.

## Usage

### Run Assessment

```bash
python .claude/skills/mysql-upgrade-expert/scripts/assess_upgrade.py 
  --host <HOST> 
  --port <PORT> 
  --user <USER> 
  --password <PASSWORD>
```

### Example Output

```text
============================================================
 UPGRADE ASSESSMENT REPORT 
============================================================

Found 2 potential blocking issues or warnings:
1. User 'app_user'@'%' uses deprecated plugin.
2. Table 'sales.orders' uses collation utf8_general_ci.

============================================================
 GENERATED REMEDIATION SCRIPT (Review carefully!) 
============================================================
-- ACTION REQUIRED: Update password for 'app_user'@'%'
ALTER USER 'app_user'@'%' IDENTIFIED WITH caching_sha2_password BY 'replace_with_password';
ALTER TABLE sales.orders CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

## Prerequisites

- Python 3.x
- `pymysql` library installed (`pip install pymysql`)
- Connectivity to the target MySQL instance.
