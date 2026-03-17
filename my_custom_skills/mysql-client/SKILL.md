---
name: mysql-client
description: MySQL Client for database connectivity, querying, and data export.
---

# MySQL Client Skill

You are an expert MySQL Database Administrator and Developer.
Use this skill to connect to MySQL databases, execute SQL queries, list tables, and export data.

## Capabilities

1.  **Execute SQL Queries**: Run `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `SHOW`, etc.
2.  **List Tables**: Get a list of all tables in a database.
3.  **Describe Table**: Get the schema/structure of a specific table.
4.  **Export Data**: Export table content to CSV or JSON.

## Usage

### 1. Execute SQL Query (`query`)
```bash
python .claude/skills/mysql-client/scripts/mysql_tool.py query 
  --host <HOST> --port <PORT> --user <USER> --password <PASS> --database <DB> 
  --sql "SELECT * FROM users LIMIT 10"
```

### 2. List Tables (`list-tables`)
```bash
python .claude/skills/mysql-client/scripts/mysql_tool.py list-tables 
  --host <HOST> --port <PORT> --user <USER> --password <PASS> --database <DB>
```

### 3. Describe Table (`describe`)
```bash
python .claude/skills/mysql-client/scripts/mysql_tool.py describe 
  --host <HOST> --port <PORT> --user <USER> --password <PASS> --database <DB> 
  --table users
```

### 4. Export Table (`export`)
```bash
python .claude/skills/mysql-client/scripts/mysql_tool.py export 
  --host <HOST> --port <PORT> --user <USER> --password <PASS> --database <DB> 
  --table users --format csv
```

## Safety Guidelines

1.  **Read-Before-Write**: Always `SELECT` data before `UPDATE` or `DELETE` to verify the target set.
2.  **Use Transactions**: For critical updates, wrap operations in `START TRANSACTION` and `COMMIT` if running manually (tool auto-commits single statements).
3.  **Confirm Dangerous Operations**: Ask for user confirmation before dropping tables or deleting large datasets.
