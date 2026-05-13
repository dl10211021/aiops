from __future__ import annotations

from typing import Any

GENERIC_HTTP_API_PARAMETERS = [
    {
        "field": "scheme",
        "label": "访问协议",
        "type": "select",
        "required": False,
        "defaultValue": "http",
        "options": [
            {"label": "HTTP", "value": "http"},
            {"label": "HTTPS", "value": "https"},
        ],
        "group": "http_api",
    },
    {
        "field": "base_path",
        "label": "API 基础路径",
        "type": "text",
        "required": False,
        "group": "http_api",
    },
    {
        "field": "api_token",
        "label": "API Token",
        "type": "password",
        "required": False,
        "group": "http_api",
    },
]


def _text_parameter(
    field: str,
    label: str,
    *,
    group: str,
    default: str | None = None,
    placeholder: str | None = None,
    required: bool = False,
) -> dict[str, Any]:
    parameter: dict[str, Any] = {
        "field": field,
        "label": label,
        "type": "text",
        "required": required,
        "group": group,
    }
    if default is not None:
        parameter["defaultValue"] = default
    if placeholder is not None:
        parameter["placeholder"] = placeholder
    return parameter


def _password_parameter(
    field: str,
    label: str,
    *,
    group: str,
    default: str | None = None,
    placeholder: str | None = None,
    required: bool = False,
) -> dict[str, Any]:
    parameter = _text_parameter(
        field,
        label,
        group=group,
        default=default,
        placeholder=placeholder,
        required=required,
    )
    parameter["type"] = "password"
    return parameter


def _number_parameter(
    field: str,
    label: str,
    *,
    group: str,
    default: int,
    required: bool = False,
) -> dict[str, Any]:
    return {
        "field": field,
        "label": label,
        "type": "number",
        "required": required,
        "defaultValue": default,
        "group": group,
    }


def _boolean_parameter(
    field: str,
    label: str,
    *,
    group: str,
    default: bool = False,
    required: bool = False,
) -> dict[str, Any]:
    return {
        "field": field,
        "label": label,
        "type": "boolean",
        "required": required,
        "defaultValue": default,
        "group": group,
    }


def _select_parameter(
    field: str,
    label: str,
    *,
    group: str,
    options: list[tuple[str, str]],
    default: str | None = None,
    required: bool = False,
) -> dict[str, Any]:
    parameter: dict[str, Any] = {
        "field": field,
        "label": label,
        "type": "select",
        "required": required,
        "options": [{"label": option_label, "value": value} for option_label, value in options],
        "group": group,
    }
    if default is not None:
        parameter["defaultValue"] = default
    return parameter


SHARED_PARAMETER_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "ssh_shell": [
        _select_parameter(
            "shell",
            "命令环境",
            group="ssh",
            default="bash",
            options=[
                ("Bash", "bash"),
                ("Sh", "sh"),
                ("Zsh", "zsh"),
                ("Ksh", "ksh"),
                ("Csh", "csh"),
            ],
        ),
        _select_parameter(
            "sudo_method",
            "提权方式",
            group="ssh",
            default="none",
            options=[
                ("不提权", "none"),
                ("sudo", "sudo"),
                ("su", "su"),
            ],
        ),
        _text_parameter("become_user", "提权用户", group="ssh", default="root"),
    ],
    "ssh_network_cli": [
        {
            "field": "enable_pass",
            "label": "Enable 密码",
            "type": "password",
            "required": False,
            "group": "network_cli",
        },
        _select_parameter(
            "terminal_type",
            "终端类型",
            group="network_cli",
            default="vt100",
            options=[
                ("VT100（推荐）", "vt100"),
                ("xterm", "xterm"),
                ("xterm-256color", "xterm-256color"),
                ("ansi", "ansi"),
            ],
        ),
        _boolean_parameter(
            "allow_agent",
            "启用 SSH Agent",
            group="network_cli",
            default=False,
        ),
        _boolean_parameter(
            "look_for_keys",
            "搜索本机默认密钥",
            group="network_cli",
            default=False,
        ),
    ],
    "virtualization_shell": [
        _select_parameter(
            "shell",
            "命令环境",
            group="virtualization_shell",
            default="sh",
            options=[
                ("ESXi Shell", "sh"),
                ("Bash", "bash"),
            ],
        ),
        _text_parameter("default_cli", "默认 CLI", group="virtualization_shell", default="esxcli"),
    ],
    "winrm_powershell": [
        {
            "field": "transport",
            "label": "认证方式",
            "type": "select",
            "required": False,
            "defaultValue": "ntlm",
            "options": [
                {"label": "NTLM", "value": "ntlm"},
                {"label": "Basic", "value": "basic"},
                {"label": "Kerberos", "value": "kerberos"},
            ],
            "group": "winrm",
        },
        {
            "field": "shell",
            "label": "命令环境",
            "type": "select",
            "required": False,
            "defaultValue": "powershell",
            "options": [
                {"label": "PowerShell", "value": "powershell"},
                {"label": "CMD", "value": "cmd"},
            ],
            "group": "winrm",
        },
    ],
    "native_sql": [],
    "database_jdbc": [
        {
            "field": "db_name",
            "label": "数据库名",
            "type": "text",
            "required": False,
            "group": "jdbc",
        },
        {
            "field": "jdbc_jar",
            "label": "JDBC 驱动 Jar 路径",
            "type": "text",
            "required": False,
            "group": "jdbc",
        },
        {
            "field": "jdbc_url",
            "label": "JDBC URL",
            "type": "text",
            "required": False,
            "group": "jdbc",
        },
        {
            "field": "jdbc_driver_class",
            "label": "JDBC 驱动类",
            "type": "text",
            "required": False,
            "group": "jdbc",
        },
    ],
    "native_kv": [],
    "native_document": [],
    "container_shell": [
        _text_parameter("runtime_socket", "运行时 Socket", group="container", placeholder="/var/run/docker.sock"),
        _text_parameter("namespace", "命名空间", group="container"),
    ],
    "middleware_shell": [
        _text_parameter("service_name", "服务名", group="middleware_shell"),
        _text_parameter("config_path", "配置路径", group="middleware_shell"),
        _text_parameter("log_path", "日志路径", group="middleware_shell"),
    ],
    "storage_shell": [
        _select_parameter(
            "shell",
            "命令环境",
            group="storage_shell",
            default="sh",
            options=[
                ("Sh", "sh"),
                ("Bash", "bash"),
                ("专用存储 CLI", "storage_cli"),
            ],
        ),
        _text_parameter("management_cli", "管理 CLI", group="storage_shell", placeholder="synoservice / storage / isi"),
        _text_parameter("volume_name", "默认卷/池名称", group="storage_shell"),
        _text_parameter("health_command", "健康检查命令", group="storage_shell", placeholder="只读命令，例如 df -h 或厂商 CLI show status"),
    ],
    "ai_compute_shell": [
        _text_parameter("gpu_vendor", "GPU 厂商", group="ai_compute", default="nvidia"),
        _text_parameter("driver_check_command", "驱动检查命令", group="ai_compute", default="nvidia-smi"),
    ],
    "database_http": [
        {
            "field": "database",
            "label": "数据库/索引/Space",
            "type": "text",
            "required": False,
            "group": "database_http",
        },
        {
            "field": "scheme",
            "label": "访问协议",
            "type": "select",
            "required": False,
            "defaultValue": "http",
            "options": [
                {"label": "HTTP", "value": "http"},
                {"label": "HTTPS", "value": "https"},
            ],
            "group": "database_http",
        },
        {
            "field": "api_token",
            "label": "API Token",
            "type": "password",
            "required": False,
            "group": "database_http",
        },
    ],
    "http_api": GENERIC_HTTP_API_PARAMETERS,
    "custom_api": GENERIC_HTTP_API_PARAMETERS,
    "redfish_api": GENERIC_HTTP_API_PARAMETERS,
    "kubernetes_api": [],
    "middleware_api": GENERIC_HTTP_API_PARAMETERS,
    "bigdata_api": GENERIC_HTTP_API_PARAMETERS,
    "monitoring_api": GENERIC_HTTP_API_PARAMETERS,
    "container_api": GENERIC_HTTP_API_PARAMETERS,
    "network_api": GENERIC_HTTP_API_PARAMETERS,
    "security_api": GENERIC_HTTP_API_PARAMETERS,
    "oob_api": GENERIC_HTTP_API_PARAMETERS,
    "discovery_api": GENERIC_HTTP_API_PARAMETERS,
    "ai_platform_api": GENERIC_HTTP_API_PARAMETERS,
    "cicd_api": GENERIC_HTTP_API_PARAMETERS,
    "virtualization_api": [
        {
            "field": "api_token",
            "label": "API Token",
            "type": "password",
            "required": False,
            "group": "virtualization",
        },
        {
            "field": "project_name",
            "label": "OpenStack 项目名",
            "type": "text",
            "required": False,
            "group": "openstack",
        },
        {
            "field": "project_id",
            "label": "OpenStack 项目 ID",
            "type": "text",
            "required": False,
            "group": "openstack",
        },
        {
            "field": "domain_name",
            "label": "OpenStack Domain",
            "type": "text",
            "required": False,
            "defaultValue": "Default",
            "group": "openstack",
        },
        {
            "field": "compute_base_path",
            "label": "Nova API 路径",
            "type": "text",
            "required": False,
            "defaultValue": "/compute/v2.1",
            "group": "openstack",
        },
        {
            "field": "volume_base_path",
            "label": "Cinder API 路径",
            "type": "text",
            "required": False,
            "defaultValue": "/volume/v3",
            "group": "openstack",
        },
        {
            "field": "network_base_path",
            "label": "Neutron API 路径",
            "type": "text",
            "required": False,
            "defaultValue": "/network/v2.0",
            "group": "openstack",
        },
    ],
    "snmp": [
        _select_parameter(
            "snmp_version",
            "SNMP 版本",
            group="snmp",
            default="v2c",
            options=[
                ("v2c", "v2c"),
                ("v3", "v3"),
            ],
        ),
        _password_parameter("community_string", "Community 字符串", group="snmp", default="public"),
        _text_parameter("v3_auth_user", "v3 认证用户", group="snmp"),
        _select_parameter(
            "v3_auth_protocol",
            "v3 认证协议",
            group="snmp",
            default="SHA",
            options=[
                ("SHA", "SHA"),
                ("MD5", "MD5"),
            ],
        ),
        _password_parameter("v3_auth_pass", "v3 认证密码", group="snmp"),
        _select_parameter(
            "v3_priv_protocol",
            "v3 加密协议",
            group="snmp",
            default="AES",
            options=[
                ("AES", "AES"),
                ("DES", "DES"),
            ],
        ),
        _password_parameter("v3_priv_pass", "v3 加密密码", group="snmp"),
        _text_parameter("oid_profile", "OID 模板", group="snmp"),
    ],
    "storage_api": [
        {
            "field": "api_token",
            "label": "API Token",
            "type": "password",
            "required": False,
            "group": "storage_api",
        },
        {
            "field": "base_path",
            "label": "API 基础路径",
            "type": "text",
            "required": False,
            "group": "storage_api",
        },
        {
            "field": "health_path",
            "label": "健康检查路径",
            "type": "text",
            "required": False,
            "defaultValue": "/health",
            "group": "storage_api",
        },
        {
            "field": "jobs_path",
            "label": "任务列表路径",
            "type": "text",
            "required": False,
            "defaultValue": "/api/v1/jobs",
            "group": "storage_api",
        },
        {
            "field": "repositories_path",
            "label": "仓库/介质路径",
            "type": "text",
            "required": False,
            "defaultValue": "/api/v1/repositories",
            "group": "storage_api",
        },
        {
            "field": "policies_path",
            "label": "策略路径",
            "type": "text",
            "required": False,
            "defaultValue": "/api/v1/policies",
            "group": "storage_api",
        },
    ],
    "object_storage_api": [
        {
            "field": "endpoint_url",
            "label": "Endpoint URL",
            "type": "text",
            "required": False,
            "placeholder": "https://s3.amazonaws.com 或 http://minio.local:9000",
            "group": "object_storage",
        },
        {
            "field": "access_key",
            "label": "Access Key",
            "type": "password",
            "required": False,
            "group": "object_storage",
        },
        {
            "field": "secret_key",
            "label": "Secret Key",
            "type": "password",
            "required": False,
            "group": "object_storage",
        },
        {
            "field": "bucket",
            "label": "默认 Bucket",
            "type": "text",
            "required": False,
            "group": "object_storage",
        },
        {
            "field": "region",
            "label": "Region",
            "type": "text",
            "required": False,
            "group": "object_storage",
        },
        {
            "field": "use_ssl",
            "label": "启用 HTTPS",
            "type": "boolean",
            "required": False,
            "defaultValue": True,
            "group": "object_storage",
        },
    ],
}
