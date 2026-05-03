from __future__ import annotations

import re
import shlex


_SHELL_NOOP_REDIRECTION_RE = re.compile(
    r"(?:(?<=\s)|^)(?:[0-9]?>>?|&>)\s*/dev/null\b"
    r"|(?:(?<=\s)|^)[0-9]?>&[0-9]\b"
)


def _strip_noop_redirections(command: str) -> str:
    return _SHELL_NOOP_REDIRECTION_RE.sub(" ", str(command or ""))


def _cmd_root(command: str) -> str:
    stripped = command.strip()
    if not stripped:
        return ""
    return stripped.split()[0].strip().lower()


def _compact_sql(sql: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", str(sql or ""), flags=re.DOTALL)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(re.sub(r"--.*$", "", line))
    return re.sub(r"\s+", " ", " ".join(lines)).strip().lower()


def _sql_actions(sql: str) -> list[str]:
    text = _compact_sql(sql)
    if not text:
        return []
    root = text.split(None, 1)[0]
    actions: list[str] = []

    if root in {"select", "show", "describe", "desc", "explain", "with"}:
        actions.append("sql.read")
    if root in {"insert", "update", "delete", "merge", "replace", "call"}:
        actions.append("sql.data_write")
    if root in {"create", "alter", "drop", "truncate", "rename"}:
        actions.append("sql.schema_change")
    if root in {"grant", "revoke"} or re.search(r"\b(create|alter|drop)\s+user\b", text):
        actions.append("sql.privilege_change")
    if re.search(r"\balter\s+system\b|\bswitch\s+logfile\b|\bshutdown\b|\bstartup\b|\bcheckpoint\b", text):
        actions.append("sql.instance_admin")
    if root in {"commit", "rollback"}:
        actions.append("sql.transaction")
    if re.search(r"\bdrop\s+(database|schema|user|tablespace)\b|\btruncate\s+table\b", text):
        actions.append("sql.dangerous_drop")
    return actions


def _sql_action_summary(sql: str) -> tuple[str, str]:
    actions = set(_sql_actions(sql))
    if "sql.dangerous_drop" in actions:
        return "数据库高危删除", "检测到删库、删用户、删表空间或清表动作，属于高危不可逆操作。"
    if "sql.instance_admin" in actions:
        return "数据库实例管理", "检测到数据库实例级管理动作，例如日志切换、实例启停或检查点，需要人工确认。"
    if "sql.privilege_change" in actions:
        return "数据库账号权限变更", "检测到数据库账号或权限变更动作，需要人工确认影响范围。"
    if "sql.schema_change" in actions:
        return "数据库结构变更", "检测到数据库表结构、对象或索引变更动作，需要人工确认。"
    if "sql.data_write" in actions:
        return "数据库数据写入", "检测到 INSERT、UPDATE、DELETE、MERGE 或过程调用等数据写入动作，需要人工确认。"
    if "sql.transaction" in actions:
        return "数据库事务控制", "检测到 COMMIT 或 ROLLBACK 等事务控制动作，需要确认当前事务上下文。"
    return "数据库变更", "检测到数据库数据修改或结构变更操作。"


def _strip_sudo(tokens: list[str]) -> list[str]:
    if tokens and tokens[0] == "sudo":
        return tokens[1:]
    return tokens


def _command_segments(command: str) -> list[str]:
    return [
        segment.strip()
        for segment in re.split(r"\s*(?:&&|\|\||;|\|)\s*", _strip_noop_redirections(command))
        if segment.strip()
    ]


def _has_file_write_redirect(command: str) -> bool:
    text = _strip_noop_redirections(command)
    return bool(re.search(r"(?:(?<=\s)|^)(?:[0-9]?>>?|&>)\s*(?!/dev/null\b)\S+", text))


def _contains_sensitive_path(command: str) -> bool:
    lower = command.lower()
    sensitive_markers = (
        "/etc/shadow",
        "/etc/gshadow",
        "/root/.ssh",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        ".pem",
        ".key",
    )
    return any(marker in lower for marker in sensitive_markers)


def _contains_filesystem_read_path(command: str) -> bool:
    lower = command.lower()
    markers = (
        "/etc/fstab",
        "/proc/mounts",
        "/proc/self/mounts",
        "/proc/swaps",
        "/sys/block/",
        "/sys/class/block/",
    )
    return any(marker in lower for marker in markers)


def _tokenize_segment(segment: str) -> list[str]:
    try:
        return [token.lower() for token in shlex.split(segment, posix=True)]
    except ValueError:
        return segment.lower().split()


def classify_linux_actions(command: str) -> list[str]:
    actions: list[str] = []
    if not str(command or "").strip():
        return actions

    if _has_file_write_redirect(command):
        actions.append("linux.file.write")

    for segment in _command_segments(command):
        tokens = _strip_sudo(_tokenize_segment(segment))
        if not tokens:
            continue
        root = tokens[0].split("/")[-1]

        if root in {"reboot", "shutdown", "poweroff", "halt"} or (root == "init" and len(tokens) > 1 and tokens[1] in {"0", "6"}):
            actions.append("linux.system.power")
            continue

        if root == "systemctl":
            verb = next((token for token in tokens[1:] if not token.startswith("-")), "")
            if verb in {"status", "show", "cat", "list-units", "list-unit-files", "is-active", "is-enabled", "is-failed"}:
                actions.append("linux.read.service")
            elif verb in {"start", "stop", "restart", "reload", "enable", "disable", "mask", "unmask", "daemon-reload"}:
                actions.append("linux.service.change")
            continue

        if root == "service":
            verb = tokens[2] if len(tokens) > 2 else ""
            if verb in {"status", "--status-all"}:
                actions.append("linux.read.service")
            elif verb in {"start", "stop", "restart", "reload"}:
                actions.append("linux.service.change")
            continue

        if root in {"free", "df", "du", "lscpu", "lsmem", "uptime", "top", "vmstat", "iostat", "mpstat", "sar", "uname", "hostname", "date", "id", "whoami", "who", "env", "printenv"}:
            actions.append("linux.read.resource")
            continue

        if root in {"lsblk", "blkid", "findmnt"}:
            actions.append("linux.read.filesystem")
            continue

        if root == "mount":
            option_tokens = [token for token in tokens[1:] if token.startswith("-")]
            positional_tokens = [token for token in tokens[1:] if not token.startswith("-")]
            read_only_options = {"-l", "-v", "-h", "--help", "--version", "--show-labels"}
            if not tokens[1:] or (option_tokens and all(token in read_only_options for token in option_tokens) and not positional_tokens):
                actions.append("linux.read.filesystem")
            else:
                actions.append("linux.disk.change")
            continue

        if root == "swapon" and any(token in {"--show", "-s", "--summary"} for token in tokens[1:]):
            actions.append("linux.read.filesystem")
            continue

        if root in {"journalctl", "dmesg"}:
            actions.append("linux.read.logs")
            continue

        if root in {"cat", "tail", "head", "less", "grep", "awk", "sed", "find", "stat"}:
            if _contains_sensitive_path(segment):
                actions.append("linux.sensitive.read")
            elif _contains_filesystem_read_path(segment):
                actions.append("linux.read.filesystem")
            elif "/var/log" in segment.lower():
                actions.append("linux.read.logs")
            else:
                actions.append("linux.read.file")
            continue

        if root == "crontab":
            if any(token in {"-e", "-r"} for token in tokens[1:]):
                actions.append("linux.file.write")
            else:
                actions.append("linux.read.cron")
            continue

        if root == "last":
            actions.append("linux.read.history")
            continue

        if root == "ip":
            if any(token in {"add", "del", "delete", "replace", "set", "flush"} for token in tokens[1:]):
                actions.append("linux.network.change")
            else:
                actions.append("linux.read.network")
            continue

        if root == "route":
            if any(token in {"add", "del", "delete", "change"} for token in tokens[1:]):
                actions.append("linux.network.change")
            else:
                actions.append("linux.read.network")
            continue

        if root == "ifconfig":
            if any(token in {"up", "down", "netmask", "broadcast", "mtu"} for token in tokens[1:]):
                actions.append("linux.network.change")
            else:
                actions.append("linux.read.network")
            continue

        if root == "firewall-cmd":
            if any(token.startswith("--list") or token in {"--state", "--get-active-zones", "--get-default-zone"} for token in tokens[1:]):
                actions.append("linux.read.network")
            else:
                actions.append("linux.network.change")
            continue

        if root == "nft":
            if any(token in {"list", "show"} for token in tokens[1:]):
                actions.append("linux.read.network")
            else:
                actions.append("linux.network.change")
            continue

        if root in {"ss", "netstat", "lsof", "dig", "nslookup", "host"}:
            actions.append("linux.read.network")
            continue

        if root in {"ping", "curl", "wget", "nc", "ncat", "netcat", "nmap", "telnet", "traceroute", "tracepath", "ssh", "scp", "sftp", "rsync"}:
            actions.append("linux.network.probe")
            continue

        if root in {"rm", "rmdir", "unlink"}:
            actions.append("linux.file.delete")
            continue
        if root in {"touch", "mkdir", "mv", "cp", "tee", "vi", "vim", "nano"}:
            actions.append("linux.file.write")
            continue
        if root in {"chmod", "chown", "chgrp", "setfacl"}:
            actions.append("linux.permission.change")
            continue
        if root in {"useradd", "userdel", "usermod", "groupadd", "groupdel", "groupmod", "passwd"}:
            actions.append("linux.user.change")
            continue
        if root in {"yum", "dnf", "apt", "apt-get", "zypper", "rpm"} and any(token in {"install", "remove", "erase", "update", "upgrade", "purge", "-e", "-u", "-i"} for token in tokens[1:]):
            actions.append("linux.package.change")
            continue
        if root in {"dd", "mkfs", "fdisk", "parted", "umount", "swapon", "swapoff"}:
            actions.append("linux.disk.change")
            continue
        if root in {"iptables"}:
            actions.append("linux.network.change")
            continue

    seen: set[str] = set()
    return [action for action in actions if not (action in seen or seen.add(action))]


def _contains_windows_sensitive_path(command: str) -> bool:
    lower = command.lower()
    sensitive_markers = (
        r"\windows\system32\config\sam",
        r"\windows\system32\config\system",
        r"\windows\system32\config\security",
        r"\ntds\ntds.dit",
        "ntds.dit",
        "lsass.dmp",
        "unattend.xml",
        "sysprep.inf",
        r"\microsoft\crypto\rsa\machinekeys",
        r"\appdata\roaming\microsoft\protect",
        r"\appdata\roaming\microsoft\crypto",
    )
    return any(marker in lower for marker in sensitive_markers)


def classify_windows_actions(command: str) -> list[str]:
    """Classify high-confidence PowerShell/CMD actions for WinRM sessions."""
    text = re.sub(r"\s+", " ", str(command or "")).strip()
    lower = text.lower()
    if not lower:
        return []

    actions: list[str] = []

    def add(action: str) -> None:
        actions.append(action)

    if re.search(r"\b(get-ciminstance|get-wmiobject|get-computerinfo|systeminfo|get-hotfix|hostname|whoami)\b", lower):
        add("windows.read.info")
    if re.search(r"\b(get-service)\b|\bsc(?:\.exe)?\s+query\b", lower):
        add("windows.read.service")
    if re.search(r"\b(get-winevent|get-eventlog)\b", lower):
        add("windows.read.eventlog")
    if re.search(r"\b(get-process|tasklist)\b", lower):
        add("windows.read.process")
    if re.search(r"\b(get-net\w*|get-dnsclient\w*|get-nettcpconnection|get-netroute|get-netip\w*|ipconfig|netstat)\b|\broute\s+print\b", lower):
        add("windows.read.network")
    if re.search(r"\b(get-content|type|cat)\b", lower):
        add("windows.read.file")
        if _contains_windows_sensitive_path(lower):
            add("windows.sensitive.read")
    if re.search(r"\b(get-vm|get-vmhost|get-vmswitch|get-vmnetworkadapter|get-vmharddiskdrive|get-vmreplication|get-vmsnapshot)\b", lower):
        add("windows.read.virtualization")

    if re.search(r"\b(test-netconnection|tnc|invoke-webrequest|iwr|invoke-restmethod|irm|ping|curl|wget|nslookup|tracert|resolve-dnsname)\b", lower):
        add("windows.network.probe")

    if re.search(r"\b(restart-computer|stop-computer|shutdown)\b", lower):
        add("windows.system.power")
    if re.search(r"\b(start-service|stop-service|restart-service|set-service|new-service|remove-service)\b|\bsc(?:\.exe)?\s+(start|stop|delete|config)\b", lower):
        add("windows.service.change")
    if re.search(r"\b(stop-process)\b|\btaskkill\b", lower):
        add("windows.process.stop")
    if re.search(r"\b(remove-item)\b|(?:^|[\s;&|])(?:del|erase|rmdir|rd)(?:\s|$)", lower):
        add("windows.file.delete")
    if re.search(r"\b(new-item|set-content|add-content|clear-content|out-file|copy-item|move-item|rename-item)\b", lower):
        add("windows.file.write")
    if re.search(r"\b(set-acl|get-acl\s*\|\s*set-acl|icacls)\b", lower):
        add("windows.permission.change")
    if re.search(r"\b(new-localuser|set-localuser|remove-localuser|new-localgroup|set-localgroup|remove-localgroup|add-localgroupmember|remove-localgroupmember)\b|\bnet\s+(user|localgroup)\b", lower):
        add("windows.user.change")
    if re.search(r"\b(new-itemproperty|set-itemproperty|remove-itemproperty|set-executionpolicy)\b|\breg(?:\.exe)?\s+(add|delete|import)\b", lower):
        add("windows.registry.change")
    if re.search(r"\b(new-netfirewallrule|set-netfirewallrule|remove-netfirewallrule|enable-netfirewallrule|disable-netfirewallrule)\b|\bnetsh\s+advfirewall\b", lower):
        add("windows.firewall.change")
    if re.search(r"\b(install-windowsfeature|uninstall-windowsfeature|install-module|uninstall-module|install-package|uninstall-package|winget|choco|msiexec)\b", lower):
        add("windows.package.change")

    if re.search(r"\b(start-vm|stop-vm|restart-vm|suspend-vm|resume-vm|save-vm)\b", lower):
        add("hyperv.vm.power")
    if re.search(r"\b(new-vm|set-vm|checkpoint-vm|restore-vmsnapshot|move-vm|set-vmnetworkadapter|set-vmharddiskdrive)\b", lower):
        add("hyperv.vm.change")
    if re.search(r"\b(remove-vm)\b", lower):
        add("hyperv.vm.delete")

    seen: set[str] = set()
    return [action for action in actions if not (action in seen or seen.add(action))]


def _datastore_root(command: str) -> str:
    try:
        parts = shlex.split(str(command or "").strip(), posix=True)
    except ValueError:
        parts = str(command or "").strip().split()
    return parts[0].lower() if parts else ""


def classify_redis_actions(command: str) -> list[str]:
    root = _datastore_root(command)
    if not root:
        return []
    if root in {"get", "mget", "hget", "hgetall", "hmget", "lrange", "llen", "smembers", "scard", "zrange", "zcard", "scan", "sscan", "hscan", "zscan", "info", "dbsize", "ttl", "pttl", "exists", "type", "keys", "client", "cluster", "memory", "slowlog", "monitor"}:
        return ["redis.read"]
    if root in {"flushall", "flushdb"}:
        return ["redis.flush"]
    if root == "acl":
        return ["redis.acl_change"]
    if root == "config" or root in {"module", "script"}:
        return ["redis.config_change"]
    if root in {"save", "bgsave", "bgrewriteaof"}:
        return ["redis.persistence_change"]
    if root in {"replicaof", "slaveof"}:
        return ["redis.replication_change"]
    if root in {"del", "unlink", "rename", "renamenx"}:
        return ["redis.key_delete"]
    if root in {"expire", "pexpire", "expireat", "pexpireat", "persist", "touch"}:
        return ["redis.expire"]
    if root in {"incr", "incrby", "incrbyfloat", "decr", "decrby"}:
        return ["redis.counter_change"]
    if root in {"set", "setex", "psetex", "setnx", "mset", "msetnx", "append", "getset", "hset", "hmset", "hdel", "hincrby", "hincrbyfloat", "lpush", "rpush", "lpop", "rpop", "lset", "ltrim", "sadd", "srem", "spop", "smove", "zadd", "zrem", "zincrby", "restore"}:
        return ["redis.key_write"]
    return []


def classify_memcached_actions(command: str) -> list[str]:
    root = _datastore_root(command)
    if not root:
        return []
    if root in {"version", "stats", "get", "gets"}:
        return ["memcached.read"]
    if root == "flush_all":
        return ["memcached.flush"]
    if root == "delete":
        return ["memcached.key_delete"]
    if root in {"incr", "decr", "touch", "gat", "gats"}:
        return ["memcached.counter_change"]
    if root in {"set", "add", "replace", "append", "prepend", "cas"}:
        return ["memcached.key_write"]
    return []


def classify_mongodb_actions(command: str = "", *, operation: str = "find") -> list[str]:
    root = _datastore_root(operation or command)
    if not root:
        return []
    if root in {"find", "count", "distinct", "listcollections", "listindexes", "stats", "ping"}:
        return ["mongodb.find"]
    if root == "aggregate":
        return ["mongodb.aggregate"]
    if root in {"dropdatabase", "dropcollection", "drop"}:
        return ["mongodb.drop"]
    if root in {"createindex", "dropindex", "createindexes", "dropindexes"}:
        return ["mongodb.index_change"]
    if root in {"createuser", "dropuser", "grantroles", "replset", "sh", "setparameter"}:
        return ["mongodb.admin"]
    if root in {"insert", "insertone", "insertmany", "update", "updateone", "updatemany", "replace", "replaceone", "delete", "deleteone", "deletemany"}:
        return ["mongodb.write"]
    return []


def classify_network_actions(command: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(command or "")).strip()
    lower = text.lower()
    if not lower:
        return []

    actions: list[str] = []

    def add(action: str) -> None:
        if action not in actions:
            actions.append(action)

    root = _cmd_root(lower)
    is_read_command = root in {"show", "display", "dis"}
    if is_read_command:
        if re.search(r"\b(current-configuration|running-config|startup-config|saved-configuration|configuration|current|cur|cu|run|running)\b", lower):
            add("network.read.config")
        else:
            add("network.read.status")
        return actions

    if re.search(r"\b(ping|traceroute|tracert|telnet)\b", lower):
        add("network.diagnostic")
    if re.search(r"\b(system-view|configure terminal|conf t)\b", lower):
        add("network.config.mode")
    if re.search(r"\b(interface|port link-type|switchport|shutdown|undo shutdown|vlan|port access|port trunk|description)\b", lower):
        add("network.interface.change")
    if re.search(r"\b(ip route-static|ip route|route add|route delete|static-route|ip prefix-list|route-policy)\b", lower):
        add("network.route.change")
    if re.search(r"\b(acl|access-list|security-policy|firewall|nat|policy-map|class-map|zone-pair|traffic-filter)\b", lower):
        add("network.acl_nat.change")
    if re.search(r"\b(save|write memory|copy running-config startup-config|copy run start)\b", lower):
        add("network.save_config")
    if re.search(r"\b(tftp|ftp|scp|sftp|copy tftp|copy ftp|copy scp|copy flash)\b", lower):
        add("network.file_transfer")
    if re.search(
        r"\b(reload|reboot|factory-reset|erase startup-config|write erase|reset saved-configuration|reset saved-config|delete /unreserved|format flash|format)\b",
        lower,
    ):
        add("network.reset")
    return actions
