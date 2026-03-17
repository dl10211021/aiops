# Data Center Full-Stack Asset Management Design

## 1. Overview
The current platform primarily supports SSH (Linux/Unix), WinRM (Windows), and generic Databases. To serve a modern data center, the connection matrix must be expanded to cover monitoring systems, hardware/OOB management, NoSQL, virtualization, and network appliances. The frontend Connection Modal needs a dynamic hierarchical UI to accommodate the varied authentication mechanisms (Passwords vs. API Tokens vs. Community Strings vs. Kubeconfigs) while maintaining a clean user experience. All these extra credentials will be seamlessly stored in the existing `extra_args` JSON schema in the backend.

## 2. Asset Classification Taxonomy (The Hierarchy)

We will introduce a two-level cascading selector in the frontend.

### Level 1 & Level 2 Mapping

*   **1. 操作系统与主机 (OS & Compute)**
    *   Linux / Unix (SSH) -> `protocol: ssh` *[host, port: 22, user, pass/key]*
    *   Windows Server (WinRM) -> `protocol: winrm` *[host, port: 5985, user, pass]*
*   **2. 数据库与缓存 (Database & Cache)**
    *   MySQL -> `protocol: database`, `extra_args.db_type: mysql` *[host, port: 3306, user, pass, db_name]*
    *   Oracle -> `protocol: database`, `extra_args.db_type: oracle` *[host, port: 1521, user, pass, sid]*
    *   PostgreSQL -> `protocol: database`, `extra_args.db_type: postgresql` *[host, port: 5432, user, pass, db_name]*
    *   SQL Server (MSSQL) -> `protocol: database`, `extra_args.db_type: mssql` *[host, port: 1433, user, pass, db_name]*
    *   Redis -> `protocol: database`, `extra_args.db_type: redis` *[host, port: 6379, pass, db_name (mapped as db_index), use_ssl]* 
    *   MongoDB -> `protocol: database`, `extra_args.db_type: mongodb` *[host, port: 27017, user, pass, db_name (auth_db), use_ssl]*
    *   ElasticSearch -> `protocol: database`, `extra_args.db_type: elasticsearch` *[host, port: 9200, user/pass or api_token, use_ssl]*
*   **3. 虚拟化与云原生 (Virtualization & Cloud Native)**
    *   VMware vCenter/ESXi -> `protocol: api`, `extra_args.sub_type: vmware` *[host, port: 443, user, pass]*
    *   Kubernetes (K8s) -> `protocol: api`, `extra_args.sub_type: k8s` *[host, port: 6443, auth_type (token/kubeconfig), bearer_token or kubeconfig]*
    *   ZStack -> `protocol: api`, `extra_args.sub_type: zstack` *[host, port: 5000, user, pass]*
*   **4. 网络与安全 (Network & Security)**
    *   F5 BIG-IP -> `protocol: api`, `extra_args.sub_type: f5` *[host, port: 443, user, pass]*
    *   Switch / Router (SSH) -> `protocol: ssh`, `extra_args.sub_type: switch` *[host, port: 22, user, pass, enable_pass]*
*   **5. 监控与告警 (Monitoring & APM)**
    *   Zabbix -> `protocol: api`, `extra_args.sub_type: zabbix` *[host, port: 80/443, api_token or user/pass]*
    *   Prometheus -> `protocol: api`, `extra_args.sub_type: prometheus` *[host, port: 9090, basic_auth (user/pass)]*
*   **6. 硬件动环 (Hardware & OOB)**
    *   SNMP -> `protocol: api`, `extra_args.sub_type: snmp` *[host, port: 161, snmp_version (v2c/v3), community_string, v3_auth_user, v3_auth_protocol (MD5/SHA), v3_auth_pass, v3_priv_protocol (DES/AES), v3_priv_pass]*
    *   Redfish/iLO/iDRAC -> `protocol: api`, `extra_args.sub_type: redfish` *[host, port: 443, user, pass]*

## 3. Frontend Architecture Changes (`ConnectionModal.tsx`)

### 3.1 Form State Updates
We will introduce `category` and `sub_type` state variables to power the cascading dropdowns.
To ensure the frontend can reverse-map an edited asset back to its correct category, we will strictly save the UI state (`category` and `sub_type`) inside the `extra_args` JSON blob.

### 3.2 Dynamic Field Rendering
Based on the `category` and `sub_type`, the form will dynamically hide or show standard inputs (like username) and inject extra fields stored in `extra_args`.

*   **Auth Type Toggles**: For assets with variable authentication (like K8s or Zabbix), we will provide a radio toggle (e.g., "Use Token" vs "Use Kubeconfig YAML").
*   **Kubeconfig**: Rendered as a `<textarea>` to paste the YAML. Saved as a plain string inside `extra_args.kubeconfig`.
*   **SNMPv3**: When SNMP version is toggled to v3, standard `user`/`pass` inputs are re-purposed or replaced by Auth Password / Priv Password fields along with Protocol dropdowns (MD5/SHA, DES/AES).

### 3.3 Default Port Mapping
When a `sub_type` is selected, the `port` input will automatically default to the industry standard for that asset (e.g., K8s -> 6443, Redis -> 6379, SNMP -> 161).

## 4. Backend Compatibility (`api/routes.py`, `ssh_manager.py` & `db_manager.py`)

No database schema changes are required for the `assets` table. The `assets` table already uses `protocol` (string) and `extra_args_json` (JSON blob). We simply allow new protocols (e.g., `api`) to pass through.

*   `ssh_manager.py` currently attempts SSH for everything except `is_virtual`. For these new protocols (where `protocol == 'api'`), the connection is fundamentally "virtual/agent-based". The core system will create a virtual session representing this endpoint.
*   **Connection Testing**: The `/connect/test` endpoint must be extended to support basic reachability checks for the new types using standard Python networking (e.g. TCP ping to the port, or simple HTTP GET for APIs) before falling back to full authentication tests. We will NOT use AI to perform these basic connectivity tests as it is slow and non-deterministic.
*   **Security/Encryption (Backend)**: To address critical security concerns, we must introduce JSON-level encryption in the backend. In `api/routes.py` and `memory.py`, any incoming payload with known sensitive keys in `extra_args` (such as `bearer_token`, `kubeconfig`, `api_token`, `v3_auth_pass`, `v3_priv_pass`) **MUST** be encrypted using the platform's symmetric key before saving to the SQLite database. When the backend feeds these credentials to the AI execution context, it decrypts them in memory.
*   **Proxy Execution**: Long-term, raw tokens should not be handed directly to the LLM to prevent prompt injection leaks. Currently, skills use Python scripts that extract tokens from the session context. This is acceptable for now, provided the LLM itself doesn't actively print the credentials in its markdown output.

## 5. Security Considerations
*   Tokens and Kubeconfigs stored in `extra_args` are sent securely over HTTPS.
*   Frontend will use `type="password"` for Token, Auth Pass, and Priv Pass fields to prevent shoulder-surfing. 
*   **Masking**: When editing an existing asset, the backend MUST return masked strings (e.g., `********`) for all sensitive `extra_args` keys. If the user submits the form with the `********` placeholder, the backend will ignore that specific key update to preserve the original encrypted secret.

## 6. Scope
This design implements the frontend UI taxonomy, connection state setup, and cascading form rendering in React. It does NOT include writing the backend Python execution scripts/skills for each of the 20+ protocols to actually monitor or manage them; those are handled within individual "Skills" loaded into the AI agent later.