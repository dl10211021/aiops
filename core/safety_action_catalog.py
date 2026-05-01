"""Action policy catalog used by the safety policy decision engine."""

from __future__ import annotations

from typing import Any


DEFAULT_ACTION_RULES: dict[str, dict[str, str]] = {
    "linux": {
        "linux.read.resource": "allow",
        "linux.read.logs": "allow",
        "linux.read.service": "allow",
        "linux.read.cron": "allow",
        "linux.read.history": "allow",
        "linux.read.network": "allow",
        "linux.read.file": "allow",
        "linux.read.filesystem": "allow",
        "linux.sensitive.read": "approval",
        "linux.network.probe": "approval",
        "linux.service.change": "approval",
        "linux.file.write": "approval",
        "linux.file.delete": "approval",
        "linux.permission.change": "approval",
        "linux.package.change": "approval",
        "linux.user.change": "approval",
        "linux.disk.change": "approval",
        "linux.network.change": "approval",
        "linux.system.power": "approval",
    },
    "sql": {
        "sql.read": "allow",
        "sql.data_write": "approval",
        "sql.schema_change": "approval",
        "sql.instance_admin": "approval",
        "sql.privilege_change": "approval",
        "sql.transaction": "approval",
        "sql.dangerous_drop": "deny",
    },
    "windows": {
        "windows.read.info": "allow",
        "windows.read.service": "allow",
        "windows.read.eventlog": "allow",
        "windows.read.process": "allow",
        "windows.read.network": "allow",
        "windows.read.file": "allow",
        "windows.read.virtualization": "allow",
        "windows.sensitive.read": "approval",
        "windows.network.probe": "approval",
        "windows.service.change": "approval",
        "windows.process.stop": "approval",
        "windows.file.write": "approval",
        "windows.file.delete": "approval",
        "windows.permission.change": "approval",
        "windows.user.change": "approval",
        "windows.registry.change": "approval",
        "windows.firewall.change": "approval",
        "windows.package.change": "approval",
        "windows.system.power": "approval",
        "hyperv.vm.power": "approval",
        "hyperv.vm.change": "approval",
        "hyperv.vm.delete": "deny",
    },
    "redis": {
        "redis.read": "allow",
        "redis.key_write": "approval",
        "redis.key_delete": "approval",
        "redis.expire": "approval",
        "redis.counter_change": "approval",
        "redis.config_change": "approval",
        "redis.acl_change": "approval",
        "redis.persistence_change": "approval",
        "redis.replication_change": "approval",
        "redis.flush": "deny",
    },
    "memcached": {
        "memcached.read": "allow",
        "memcached.key_write": "approval",
        "memcached.key_delete": "approval",
        "memcached.counter_change": "approval",
        "memcached.flush": "deny",
    },
    "mongodb": {
        "mongodb.find": "allow",
        "mongodb.aggregate": "approval",
        "mongodb.write": "approval",
        "mongodb.index_change": "approval",
        "mongodb.admin": "approval",
        "mongodb.drop": "deny",
    },
    "network": {
        "network.read.status": "allow",
        "network.read.config": "approval",
        "network.diagnostic": "approval",
        "network.config.mode": "approval",
        "network.interface.change": "approval",
        "network.route.change": "approval",
        "network.acl_nat.change": "approval",
        "network.save_config": "approval",
        "network.file_transfer": "approval",
        "network.reset": "deny",
    },
    "http": {
        "k8s.delete_namespace": "deny",
        "k8s.scale_deployment": "approval",
        "k8s.delete_pod": "approval",
        "k8s.delete_secret": "deny",
        "k8s.modify_sensitive_resource": "approval",
        "virtualization.delete_vm": "deny",
        "virtualization.reboot_vm": "approval",
        "virtualization.migrate_vm": "approval",
        "virtualization.snapshot_or_rollback": "approval",
        "virtualization.rollback_snapshot": "approval",
        "middleware.reload_config": "approval",
        "nacos.publish_config": "approval",
        "kafka.delete_topic": "deny",
        "yarn.kill_application": "approval",
        "bigdata.delete_partition": "deny",
        "cicd.deploy_prod": "approval",
        "argocd.rollback": "approval",
        "artifact.delete_release": "deny",
        "ai.stop_training_job": "approval",
        "ai.release_gpu": "approval",
        "mlflow.delete_model_version": "deny",
        "s3.download_object": "approval",
        "s3.change_bucket_policy": "approval",
        "s3.public_bucket": "deny",
        "s3.delete_bucket": "deny",
        "s3.delete_object": "approval",
        "monitoring.create_silence": "approval",
        "alertmanager.create_silence": "approval",
        "monitoring.modify_rule": "approval",
        "monitoring.update_rule": "approval",
        "monitoring.delete_rule": "deny",
    },
}


SQL_ACTION_DETAILS: dict[str, dict[str, str]] = {
    "sql.read": {
        "label": "数据库读取",
        "description": "查询、解释计划或查看元数据，不直接改变数据库状态。",
        "severity": "low",
    },
    "sql.data_write": {
        "label": "数据库数据写入",
        "description": "INSERT、UPDATE、DELETE、MERGE 或过程调用等会改变业务数据。",
        "severity": "high",
    },
    "sql.schema_change": {
        "label": "数据库结构变更",
        "description": "CREATE、ALTER、DROP、TRUNCATE 或 RENAME 会改变库表对象结构。",
        "severity": "high",
    },
    "sql.instance_admin": {
        "label": "数据库实例管理",
        "description": "ALTER SYSTEM、日志切换、实例启停或检查点会影响数据库运行状态。",
        "severity": "high",
    },
    "sql.privilege_change": {
        "label": "数据库账号权限",
        "description": "GRANT、REVOKE 或用户变更会改变访问边界。",
        "severity": "high",
    },
    "sql.transaction": {
        "label": "数据库事务控制",
        "description": "COMMIT 或 ROLLBACK 会影响当前事务上下文。",
        "severity": "medium",
    },
    "sql.dangerous_drop": {
        "label": "数据库高危删除",
        "description": "删库、删用户、删表空间或清表属于高危不可逆动作。",
        "severity": "critical",
    },
}


LINUX_ACTION_DETAILS: dict[str, dict[str, str]] = {
    "linux.read.resource": {
        "label": "读取资源状态",
        "description": "查看 CPU、内存、磁盘、负载、系统版本等基础状态。",
        "severity": "low",
    },
    "linux.read.logs": {
        "label": "读取系统日志",
        "description": "查看 journalctl、dmesg 或 /var/log 下的日志内容。",
        "severity": "low",
    },
    "linux.read.service": {
        "label": "查看服务状态",
        "description": "查看 systemd 服务状态、失败服务或服务配置，不改变服务运行状态。",
        "severity": "low",
    },
    "linux.read.cron": {
        "label": "查看计划任务",
        "description": "读取 crontab 或计划任务配置。",
        "severity": "low",
    },
    "linux.read.history": {
        "label": "查看历史记录",
        "description": "查看登录、重启等系统历史记录。",
        "severity": "low",
    },
    "linux.read.network": {
        "label": "查看网络状态",
        "description": "查看端口、路由、网卡、连接状态等本机网络信息。",
        "severity": "low",
    },
    "linux.read.file": {
        "label": "读取文件",
        "description": "读取普通配置或文本文件内容。",
        "severity": "low",
    },
    "linux.read.filesystem": {
        "label": "读取文件系统/挂载状态",
        "description": "查看 fstab、当前挂载表、块设备、IO 调度器或文件系统只读状态，不改变挂载或磁盘状态。",
        "severity": "low",
    },
    "linux.sensitive.read": {
        "label": "读取敏感文件",
        "description": "读取账号、密钥、影子口令或私钥等敏感路径。",
        "severity": "high",
    },
    "linux.network.probe": {
        "label": "主动网络访问",
        "description": "对其他地址发起 ping、curl、ssh、nc、nmap 等主动连接或探测。",
        "severity": "medium",
    },
    "linux.service.change": {
        "label": "变更服务状态",
        "description": "启动、停止、重启、启用或禁用系统服务。",
        "severity": "high",
    },
    "linux.file.write": {
        "label": "写入文件",
        "description": "创建、覆盖、追加、移动或复制文件。",
        "severity": "medium",
    },
    "linux.file.delete": {
        "label": "删除文件",
        "description": "删除文件或目录。",
        "severity": "high",
    },
    "linux.permission.change": {
        "label": "修改权限",
        "description": "修改文件属主、权限或访问控制。",
        "severity": "high",
    },
    "linux.package.change": {
        "label": "软件包变更",
        "description": "安装、删除或升级系统软件包。",
        "severity": "high",
    },
    "linux.user.change": {
        "label": "账号变更",
        "description": "新增、删除或修改系统用户和用户组。",
        "severity": "high",
    },
    "linux.disk.change": {
        "label": "磁盘/挂载变更",
        "description": "格式化、分区、挂载、卸载或修改磁盘状态。",
        "severity": "critical",
    },
    "linux.network.change": {
        "label": "网络配置变更",
        "description": "修改防火墙、路由、网卡或网络规则。",
        "severity": "high",
    },
    "linux.system.power": {
        "label": "系统电源操作",
        "description": "重启、关机或切换系统运行级别。",
        "severity": "critical",
    },
}


WINDOWS_ACTION_DETAILS: dict[str, dict[str, str]] = {
    "windows.read.info": {
        "label": "读取 Windows 基础信息",
        "description": "查看系统版本、补丁、硬件、CIM/WMI 等基础状态。",
        "severity": "low",
    },
    "windows.read.service": {
        "label": "查看 Windows 服务",
        "description": "读取服务列表、状态或配置，不改变服务运行状态。",
        "severity": "low",
    },
    "windows.read.eventlog": {
        "label": "读取事件日志",
        "description": "查看 Windows 事件日志或系统日志。",
        "severity": "low",
    },
    "windows.read.process": {
        "label": "查看进程",
        "description": "查看进程、任务或资源占用情况。",
        "severity": "low",
    },
    "windows.read.network": {
        "label": "查看网络状态",
        "description": "查看网卡、连接、路由、防火墙规则等本机网络状态。",
        "severity": "low",
    },
    "windows.read.file": {
        "label": "读取文件",
        "description": "读取普通配置或文本文件内容。",
        "severity": "low",
    },
    "windows.read.virtualization": {
        "label": "读取 Hyper-V 状态",
        "description": "查看虚拟机、虚拟交换机、磁盘或复制状态，不改变虚拟化资源。",
        "severity": "low",
    },
    "windows.sensitive.read": {
        "label": "读取 Windows 敏感数据",
        "description": "读取 SAM、SYSTEM、SECURITY、NTDS 或私钥等敏感文件/注册表数据。",
        "severity": "high",
    },
    "windows.network.probe": {
        "label": "主动网络访问",
        "description": "通过 ping、Test-NetConnection、Invoke-WebRequest 等主动连接或探测其他地址。",
        "severity": "medium",
    },
    "windows.service.change": {
        "label": "变更 Windows 服务",
        "description": "启动、停止、重启、创建、删除或修改服务配置。",
        "severity": "high",
    },
    "windows.process.stop": {
        "label": "终止进程",
        "description": "停止 Windows 进程或任务。",
        "severity": "high",
    },
    "windows.file.write": {
        "label": "写入文件",
        "description": "创建、覆盖、追加、复制、移动或重命名文件。",
        "severity": "medium",
    },
    "windows.file.delete": {
        "label": "删除文件",
        "description": "删除文件或目录。",
        "severity": "high",
    },
    "windows.permission.change": {
        "label": "修改权限",
        "description": "修改 ACL、文件权限或访问控制。",
        "severity": "high",
    },
    "windows.user.change": {
        "label": "账号/组变更",
        "description": "新增、删除或修改本地用户、本地组或组成员。",
        "severity": "high",
    },
    "windows.registry.change": {
        "label": "注册表变更",
        "description": "新增、删除或修改注册表键值。",
        "severity": "high",
    },
    "windows.firewall.change": {
        "label": "防火墙变更",
        "description": "新增、删除或修改 Windows 防火墙规则。",
        "severity": "high",
    },
    "windows.package.change": {
        "label": "软件/角色变更",
        "description": "安装、卸载或修改 Windows 功能、模块或软件包。",
        "severity": "high",
    },
    "windows.system.power": {
        "label": "Windows 电源操作",
        "description": "重启、关机或关闭计算机。",
        "severity": "critical",
    },
    "hyperv.vm.power": {
        "label": "Hyper-V 虚拟机电源操作",
        "description": "启动、停止、重启、挂起或保存虚拟机。",
        "severity": "high",
    },
    "hyperv.vm.change": {
        "label": "Hyper-V 虚拟机变更",
        "description": "创建、修改、检查点、恢复或迁移虚拟机资源。",
        "severity": "high",
    },
    "hyperv.vm.delete": {
        "label": "删除 Hyper-V 虚拟机",
        "description": "删除虚拟机资源，通常不可逆。",
        "severity": "critical",
    },
}


REDIS_ACTION_DETAILS: dict[str, dict[str, str]] = {
    "redis.read": {
        "label": "Redis 读取",
        "description": "GET、MGET、SCAN、INFO、DBSIZE、TTL 等读取或状态查询。",
        "severity": "low",
    },
    "redis.key_write": {
        "label": "Redis 写入 Key",
        "description": "SET、HSET、LPUSH、SADD、ZADD 等会写入或修改数据。",
        "severity": "medium",
    },
    "redis.key_delete": {
        "label": "Redis 删除 Key",
        "description": "DEL、UNLINK、RENAME 等会删除或移动数据。",
        "severity": "high",
    },
    "redis.expire": {
        "label": "Redis 修改过期时间",
        "description": "EXPIRE、PERSIST、PEXPIRE 等会改变 Key 生命周期。",
        "severity": "medium",
    },
    "redis.counter_change": {
        "label": "Redis 计数变更",
        "description": "INCR、DECR 等会修改计数值。",
        "severity": "medium",
    },
    "redis.config_change": {
        "label": "Redis 配置变更",
        "description": "CONFIG SET、MODULE、SCRIPT FLUSH 等会改变实例配置或执行环境。",
        "severity": "high",
    },
    "redis.acl_change": {
        "label": "Redis ACL 变更",
        "description": "ACL SETUSER、ACL DELUSER 等会改变 Redis 访问权限。",
        "severity": "high",
    },
    "redis.persistence_change": {
        "label": "Redis 持久化变更",
        "description": "SAVE、BGSAVE、BGREWRITEAOF 等会影响持久化和性能。",
        "severity": "medium",
    },
    "redis.replication_change": {
        "label": "Redis 主从/复制变更",
        "description": "REPLICAOF、SLAVEOF 等会改变复制拓扑。",
        "severity": "high",
    },
    "redis.flush": {
        "label": "Redis 清空数据",
        "description": "FLUSHALL 或 FLUSHDB 会清空库或实例数据。",
        "severity": "critical",
    },
}


MEMCACHED_ACTION_DETAILS: dict[str, dict[str, str]] = {
    "memcached.read": {
        "label": "Memcached 读取",
        "description": "version、stats、get、gets 等只读命令。",
        "severity": "low",
    },
    "memcached.key_write": {
        "label": "Memcached 写入 Key",
        "description": "set、add、replace、append、prepend、cas 等会写入或修改数据。",
        "severity": "medium",
    },
    "memcached.key_delete": {
        "label": "Memcached 删除 Key",
        "description": "delete 会删除缓存数据。",
        "severity": "high",
    },
    "memcached.counter_change": {
        "label": "Memcached 计数变更",
        "description": "incr、decr、touch、gat、gats 等会改变数据或过期时间。",
        "severity": "medium",
    },
    "memcached.flush": {
        "label": "Memcached 清空缓存",
        "description": "flush_all 会清空缓存数据。",
        "severity": "critical",
    },
}


MONGODB_ACTION_DETAILS: dict[str, dict[str, str]] = {
    "mongodb.find": {
        "label": "MongoDB 读取查询",
        "description": "find 查询集合数据或元数据，不改变数据库状态。",
        "severity": "low",
    },
    "mongodb.aggregate": {
        "label": "MongoDB 聚合查询",
        "description": "aggregate 聚合可能消耗较多资源，默认需要审批后执行。",
        "severity": "medium",
    },
    "mongodb.write": {
        "label": "MongoDB 数据写入",
        "description": "insert、update、replace、delete 等会改变集合数据。",
        "severity": "high",
    },
    "mongodb.index_change": {
        "label": "MongoDB 索引变更",
        "description": "createIndex、dropIndex 等会改变集合索引并影响性能。",
        "severity": "high",
    },
    "mongodb.admin": {
        "label": "MongoDB 管理操作",
        "description": "用户、角色、分片、副本集、参数等管理动作会改变实例状态。",
        "severity": "high",
    },
    "mongodb.drop": {
        "label": "MongoDB 高危删除",
        "description": "dropDatabase、dropCollection 或删除索引/集合属于高危不可逆动作。",
        "severity": "critical",
    },
}


NETWORK_ACTION_DETAILS: dict[str, dict[str, str]] = {
    "network.read.status": {
        "label": "查看网络设备状态",
        "description": "show/display 接口、路由、邻居、版本、会话等运行状态，不改变设备配置。",
        "severity": "low",
    },
    "network.read.config": {
        "label": "读取设备配置",
        "description": "查看 running-config、current-configuration、startup-config 等配置内容，可能包含密钥或口令。",
        "severity": "medium",
    },
    "network.diagnostic": {
        "label": "网络诊断探测",
        "description": "从网络设备发起 ping、traceroute、telnet 等主动探测或连接。",
        "severity": "medium",
    },
    "network.config.mode": {
        "label": "进入配置模式",
        "description": "system-view、configure terminal 等进入可变更设备配置的模式。",
        "severity": "high",
    },
    "network.interface.change": {
        "label": "接口配置变更",
        "description": "进入接口配置、shutdown/undo shutdown、修改端口/VLAN/描述等接口状态或配置。",
        "severity": "high",
    },
    "network.route.change": {
        "label": "路由配置变更",
        "description": "新增、删除或修改静态路由、默认路由或路由策略。",
        "severity": "high",
    },
    "network.acl_nat.change": {
        "label": "ACL/NAT/安全策略变更",
        "description": "修改 ACL、访问控制、防火墙策略、NAT 或安全域规则。",
        "severity": "high",
    },
    "network.save_config": {
        "label": "保存设备配置",
        "description": "save、write memory、copy running-config startup-config 等会固化当前配置。",
        "severity": "high",
    },
    "network.file_transfer": {
        "label": "设备文件传输",
        "description": "通过 TFTP、FTP、SCP 或 copy 上传下载镜像、配置或文件。",
        "severity": "high",
    },
    "network.reset": {
        "label": "重启或清空设备配置",
        "description": "reload、reboot、reset saved-configuration、erase startup-config、format flash 等高危操作。",
        "severity": "critical",
    },
}


PLATFORM_ACTION_DETAILS: dict[str, tuple[str, str, str]] = {
    "k8s.delete_namespace": ("删除 Namespace", "会批量删除命名空间内业务资源。", "critical"),
    "k8s.scale_deployment": ("调整 Deployment 副本", "会改变业务容量和调度状态。", "medium"),
    "k8s.delete_pod": ("删除 Pod", "会终止正在运行的业务实例。", "high"),
    "k8s.delete_secret": ("删除 Secret", "会影响业务认证和访问凭据。", "critical"),
    "k8s.modify_sensitive_resource": ("修改敏感资源", "会改变 Secret、RBAC 等敏感配置。", "high"),
    "virtualization.delete_vm": ("删除虚拟机", "会删除虚拟机资源，通常不可逆。", "critical"),
    "virtualization.reboot_vm": ("重启虚拟机", "会影响虚拟机上业务可用性。", "high"),
    "virtualization.migrate_vm": ("迁移虚拟机", "会改变虚拟机运行位置和资源状态。", "medium"),
    "virtualization.snapshot_or_rollback": ("快照或回滚", "会创建或改变虚拟机快照状态。", "high"),
    "virtualization.rollback_snapshot": ("快照回滚", "会改变系统和数据状态。", "high"),
    "middleware.reload_config": ("重载配置", "会让中间件重新加载配置并可能影响入口流量。", "medium"),
    "nacos.publish_config": ("发布配置", "会影响依赖该配置的服务。", "high"),
    "kafka.delete_topic": ("删除消息 Topic", "可能造成消息数据丢失。", "critical"),
    "yarn.kill_application": ("停止大数据任务", "会中断数据处理链路。", "high"),
    "bigdata.delete_partition": ("删除数据分区", "会删除数据分区并可能造成数据不可恢复。", "critical"),
    "cicd.deploy_prod": ("生产发布", "会改变线上版本或生产流量。", "high"),
    "argocd.rollback": ("回滚部署", "会改变线上应用版本。", "high"),
    "artifact.delete_release": ("删除制品", "会影响回滚和审计追溯。", "critical"),
    "ai.stop_training_job": ("停止训练任务", "会中断训练或计算过程。", "medium"),
    "ai.release_gpu": ("释放 GPU", "可能影响正在运行的训练或推理任务。", "high"),
    "mlflow.delete_model_version": ("删除模型版本", "会影响推理服务和模型追溯。", "critical"),
    "s3.download_object": ("下载对象", "对象可能包含敏感数据。", "medium"),
    "s3.change_bucket_policy": ("修改 Bucket 策略", "会改变对象存储访问边界。", "high"),
    "s3.public_bucket": ("公开 Bucket", "会造成数据泄露风险。", "critical"),
    "s3.delete_bucket": ("删除 Bucket", "会删除对象存储命名空间。", "critical"),
    "s3.delete_object": ("删除对象", "会删除对象数据。", "high"),
    "monitoring.create_silence": ("创建告警静默", "可能掩盖真实故障。", "high"),
    "alertmanager.create_silence": ("创建告警静默", "可能掩盖真实故障。", "high"),
    "monitoring.modify_rule": ("修改监控规则", "会影响监控覆盖和告警质量。", "high"),
    "monitoring.update_rule": ("修改告警规则", "会影响监控覆盖和告警质量。", "high"),
    "monitoring.delete_rule": ("删除告警规则", "会造成监控缺口。", "critical"),
}


ACTION_PRIORITY: dict[str, int] = {
    "linux.system.power": 5,
    "linux.disk.change": 8,
    "windows.system.power": 9,
    "sql.dangerous_drop": 10,
    "hyperv.vm.delete": 12,
    "redis.flush": 13,
    "memcached.flush": 14,
    "mongodb.drop": 14,
    "network.reset": 15,
    "sql.instance_admin": 20,
    "linux.service.change": 25,
    "linux.network.change": 26,
    "linux.package.change": 27,
    "linux.user.change": 28,
    "linux.permission.change": 29,
    "linux.file.delete": 30,
    "windows.service.change": 31,
    "windows.firewall.change": 32,
    "windows.registry.change": 33,
    "windows.user.change": 34,
    "windows.file.delete": 35,
    "redis.key_delete": 35,
    "memcached.key_delete": 35,
    "windows.process.stop": 36,
    "hyperv.vm.power": 37,
    "hyperv.vm.change": 38,
    "sql.privilege_change": 30,
    "sql.schema_change": 40,
    "linux.file.write": 45,
    "windows.file.write": 46,
    "windows.package.change": 47,
    "windows.permission.change": 48,
    "redis.config_change": 49,
    "redis.acl_change": 50,
    "redis.replication_change": 51,
    "sql.data_write": 50,
    "redis.key_write": 52,
    "redis.counter_change": 53,
    "redis.expire": 54,
    "memcached.key_write": 55,
    "memcached.counter_change": 56,
    "mongodb.admin": 56,
    "mongodb.index_change": 57,
    "mongodb.write": 58,
    "sql.transaction": 60,
    "redis.persistence_change": 61,
    "mongodb.aggregate": 62,
    "network.config.mode": 62,
    "network.interface.change": 63,
    "network.route.change": 64,
    "network.acl_nat.change": 65,
    "linux.sensitive.read": 65,
    "windows.sensitive.read": 66,
    "network.save_config": 67,
    "network.file_transfer": 68,
    "linux.network.probe": 70,
    "windows.network.probe": 71,
    "network.diagnostic": 72,
    "sql.read": 90,
    "network.read.config": 90,
    "network.read.status": 90,
    "windows.read.info": 91,
    "windows.read.service": 92,
    "windows.read.eventlog": 93,
    "windows.read.process": 94,
    "windows.read.network": 95,
    "windows.read.file": 96,
    "windows.read.virtualization": 97,
    "redis.read": 98,
    "memcached.read": 99,
    "mongodb.find": 99,
}


def action_detail(action_id: str) -> dict[str, Any] | None:
    if action_id in SQL_ACTION_DETAILS:
        return dict(SQL_ACTION_DETAILS[action_id])
    if action_id in LINUX_ACTION_DETAILS:
        return dict(LINUX_ACTION_DETAILS[action_id])
    if action_id in WINDOWS_ACTION_DETAILS:
        return dict(WINDOWS_ACTION_DETAILS[action_id])
    if action_id in REDIS_ACTION_DETAILS:
        return dict(REDIS_ACTION_DETAILS[action_id])
    if action_id in MEMCACHED_ACTION_DETAILS:
        return dict(MEMCACHED_ACTION_DETAILS[action_id])
    if action_id in MONGODB_ACTION_DETAILS:
        return dict(MONGODB_ACTION_DETAILS[action_id])
    if action_id in NETWORK_ACTION_DETAILS:
        return dict(NETWORK_ACTION_DETAILS[action_id])
    platform_detail = PLATFORM_ACTION_DETAILS.get(action_id)
    if platform_detail:
        label, description, severity = platform_detail
        return {"label": label, "description": description, "severity": severity}
    return None
