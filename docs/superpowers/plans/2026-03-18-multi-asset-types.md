# Multi-Asset Types Connection Form Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the frontend ConnectionModal to support a two-level cascading taxonomy for various data center assets (OS, DB, Virtualization, Network, Monitoring, OOB) with dynamic form fields based on the selected asset type.

**Architecture:** The frontend modal state will be expanded to include `category` and `sub_type`. Based on these two variables, the UI will dynamically render specific input fields (like Kubeconfig textareas, SNMP dropdowns, or API token inputs). These dynamic values will be packed into the `extra_args` object to be sent to the backend. The backend `api/routes.py` will receive these safely. A masking/unmasking strategy will be implemented for sensitive fields.

**Tech Stack:** React, Tailwind CSS, TypeScript, FastAPI (Python)

---

### Task 1: Setup Taxonomy Data Structures in Frontend

**Files:**
- Modify: `frontend/src/components/modals/ConnectionModal.tsx`

- [ ] **Step 1: Define the taxonomy constants**
At the top of the file, define the categories and sub-types according to the spec.
```typescript
const ASSET_CATEGORIES = [
  { id: 'os', label: '操作系统与主机 (OS & Compute)' },
  { id: 'db', label: '数据库与缓存 (Database & Cache)' },
  { id: 'cloud', label: '虚拟化与云原生 (Virtualization)' },
  { id: 'network', label: '网络与安全 (Network & Security)' },
  { id: 'monitor', label: '监控与告警 (Monitoring & APM)' },
  { id: 'oob', label: '硬件动环 (Hardware & OOB)' },
]

const ASSET_SUB_TYPES: Record<string, { id: string, label: string, protocol: string, defaultPort: number }[]> = {
  os: [
    { id: 'linux', label: 'Linux / Unix (SSH)', protocol: 'ssh', defaultPort: 22 },
    { id: 'winrm', label: 'Windows Server (WinRM)', protocol: 'winrm', defaultPort: 5985 },
  ],
  db: [
    { id: 'mysql', label: 'MySQL', protocol: 'database', defaultPort: 3306 },
    { id: 'oracle', label: 'Oracle', protocol: 'database', defaultPort: 1521 },
    { id: 'postgresql', label: 'PostgreSQL', protocol: 'database', defaultPort: 5432 },
    { id: 'mssql', label: 'SQL Server', protocol: 'database', defaultPort: 1433 },
    { id: 'redis', label: 'Redis', protocol: 'database', defaultPort: 6379 },
    { id: 'mongodb', label: 'MongoDB', protocol: 'database', defaultPort: 27017 },
    { id: 'elasticsearch', label: 'ElasticSearch', protocol: 'database', defaultPort: 9200 },
  ],
  cloud: [
    { id: 'vmware', label: 'VMware vCenter/ESXi', protocol: 'api', defaultPort: 443 },
    { id: 'k8s', label: 'Kubernetes (K8s)', protocol: 'api', defaultPort: 6443 },
    { id: 'zstack', label: 'ZStack', protocol: 'api', defaultPort: 5000 },
  ],
  network: [
    { id: 'f5', label: 'F5 BIG-IP', protocol: 'api', defaultPort: 443 },
    { id: 'switch', label: 'Switch / Router', protocol: 'ssh', defaultPort: 22 },
  ],
  monitor: [
    { id: 'zabbix', label: 'Zabbix', protocol: 'api', defaultPort: 80 },
    { id: 'prometheus', label: 'Prometheus', protocol: 'api', defaultPort: 9090 },
  ],
  oob: [
    { id: 'snmp', label: 'SNMP', protocol: 'api', defaultPort: 161 },
    { id: 'redfish', label: 'Redfish/iLO/iDRAC', protocol: 'api', defaultPort: 443 },
  ]
}
```

- [ ] **Step 2: Update component state to include category and sub_type**
Modify the `form` initial state in `ConnectionModal` to include `category` (default `'os'`) and `sub_type` (default `'linux'`). Remove `PROTOCOL_OPTIONS` and `DB_TYPES` as they are now superseded.

- [ ] **Step 3: Commit**
```bash
git add frontend/src/components/modals/ConnectionModal.tsx
git commit -m "feat: setup asset taxonomy data structures in connection modal"
```

### Task 2: Implement Cascading Dropdowns & Basic Field Hiding

**Files:**
- Modify: `frontend/src/components/modals/ConnectionModal.tsx`

- [ ] **Step 1: Replace old protocol selector with Category/SubType dropdowns**
Replace the old `PROTOCOL_OPTIONS.map` rendering with two `<select>` inputs for Category and SubType.
When Category changes, automatically select the first SubType of that Category.
When SubType changes, automatically update `form.protocol` and `form.port` based on the mapped default values.
Update `form.extra_args.category` and `form.extra_args.sub_type` to preserve UI state for future editing.

- [ ] **Step 2: Hide Username/Password dynamically based on SubType**
Certain types (like Redis, K8s depending on auth mode, SNMPv3) don't use standard Username/Password. Wrap the Username and Password grid in conditional logic.
For now, hide Username if `sub_type === 'redis'`.

- [ ] **Step 3: Commit**
```bash
git add frontend/src/components/modals/ConnectionModal.tsx
git commit -m "feat: implement cascading category dropdowns in connection modal"
```

### Task 3: Implement Dynamic Custom Fields by SubType

**Files:**
- Modify: `frontend/src/components/modals/ConnectionModal.tsx`

- [ ] **Step 1: Implement Database Fields (MySQL, Oracle, PG, MSSQL, Redis, Mongo)**
If `category === 'db'`, show a generic "Database Name / SID" input mapped to `extra_args.db_name` (or `extra_args.database`). Add a "Use SSL" checkbox mapped to `extra_args.use_ssl`.
Remove the old `form.protocol === 'database'` block. Ensure the new backend DB type mapper uses the `sub_type`. Set `extra_args.db_type = form.sub_type`.

- [ ] **Step 2: Implement K8s Auth Toggle and Kubeconfig Area**
If `sub_type === 'k8s'`, show a radio group: [Token, Kubeconfig].
If Token, show a Bearer Token input (`type="password"`) mapped to `extra_args.bearer_token`.
If Kubeconfig, show a `<textarea>` mapped to `extra_args.kubeconfig`.

- [ ] **Step 3: Implement SNMPv2/v3 Fields**
If `sub_type === 'snmp'`, show a version select [v2c, v3] mapped to `extra_args.snmp_version` (default v2c).
If v2c, show Community String input (`type="password"`) mapped to `extra_args.community_string`.
If v3, hide standard user/pass, show:
- Auth User (`extra_args.v3_auth_user`)
- Auth Protocol select [MD5, SHA] (`extra_args.v3_auth_protocol`)
- Auth Pass (`type="password"`, `extra_args.v3_auth_pass`)
- Priv Protocol select [DES, AES] (`extra_args.v3_priv_protocol`)
- Priv Pass (`type="password"`, `extra_args.v3_priv_pass`)

- [ ] **Step 4: Implement generic Token inputs for Zabbix/ElasticSearch/F5**
If `sub_type` in `['zabbix', 'elasticsearch', 'f5']`, add a generic "API Token (Optional)" input (`type="password"`) mapped to `extra_args.api_token`.

- [ ] **Step 5: Implement Switch / Router fields**
If `sub_type === 'switch'`, add a generic "Enable Password" input (`type="password"`) mapped to `extra_args.enable_pass`.

- [ ] **Step 6: State Cleanup on Category Change**
Add an effect or handler when `category` or `sub_type` changes to clear out irrelevant `extra_args` to prevent saving orphan secrets.

- [ ] **Step 7: Commit**
```bash
git add frontend/src/components/modals/ConnectionModal.tsx
git commit -m "feat: add dynamic custom fields for k8s, snmp, databases, and switches"
```

### Task 4: Fix State Hydration (Edit Mode)

**Files:**
- Modify: `frontend/src/components/modals/ConnectionModal.tsx`

- [ ] **Step 1: Read UI state from `extra_args`**
In the `useEffect` that checks `sessionStorage.getItem('prefill_asset')`, update the parsing logic to extract `category` and `sub_type` from `a.extra_args.category` and `a.extra_args.sub_type`.
If not present, gracefully fallback to inferring it based on `protocol` (e.g. `protocol: ssh` -> `os/linux`).

- [ ] **Step 2: Test rendering**
Run `npm run build` in the frontend directory to ensure no TypeScript compilation errors.

- [ ] **Step 3: Commit**
```bash
git add frontend/src/components/modals/ConnectionModal.tsx
git commit -m "fix: hydrate connection modal state correctly in edit mode"
```

### Task 5: Backend Compatibility Updates (Reachability Test)

**Files:**
- Modify: `api/routes.py`

- [ ] **Step 1: Update `/connect/test` logic**
In `test_connection`, if `protocol == 'api'`, implement a basic TCP socket connect check instead of trying to invoke SSH or DB drivers, because we won't implement all the specific API SDKs right now (they go in Skills).
```python
        if req.protocol == "api":
            import socket
            try:
                with socket.create_connection((req.host, req.port), timeout=3):
                    pass
                return ResponseModel(
                    status="success",
                    message=f"[OK] Port {req.port} is reachable. (Auth testing deferred to execution agent)",
                )
            except Exception as e:
                return ResponseModel(status="error", message=f"[FAIL] TCP Connect Failed: {str(e)}")
```

- [ ] **Step 2: Ensure DB tester uses `extra_args.db_type`**
Verify the DB testing block correctly extracts `req.extra_args.get("db_type")` since we changed the frontend payload.

- [ ] **Step 3: Commit**
```bash
git add api/routes.py
git commit -m "feat: support basic api protocol tcp reachability testing"
```

### Task 6: Backend Security & Encryption

**Files:**
- Modify: `core/memory.py`
- Modify: `api/routes.py`

- [ ] **Step 1: Implement encryption for sensitive extra_args fields**
In `core/memory.py`, create a list of sensitive keys: `['bearer_token', 'kubeconfig', 'api_token', 'v3_auth_pass', 'v3_priv_pass', 'community_string', 'enable_pass']`.
When saving an asset (`save_asset` and `save_assets_batch`), iterate through `extra_args` and if a key is sensitive, encrypt it using `self._fernet.encrypt()`.
When loading assets (`get_all_assets`), decrypt these sensitive fields before returning them.

- [ ] **Step 2: Implement Masking Strategy**
In `api/routes.py` for endpoints that list assets (e.g. `get_saved_assets`), modify the returned payload to mask sensitive fields in `extra_args` as `********` to prevent leakage.
*Note: Because the UI needs Kubeconfigs for the textarea, we might just mask tokens/passwords, but for security, it is best to mask all secrets sent back.*

- [ ] **Step 3: Handle Masked Updates**
In `api/routes.py` and `core/memory.py` update logic, if the incoming payload has `********` for a sensitive field, pop it from the update dictionary so the original encrypted value remains in the database.

- [ ] **Step 4: Commit**
```bash
git add core/memory.py api/routes.py
git commit -m "feat: implement JSON-level encryption and masking for sensitive asset fields"
```