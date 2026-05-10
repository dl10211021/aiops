# 新建资产弹窗资产类型逐项检查报告（2026-05-10）

## 检查口径

- 只检查“资产中心 -> 新建资产”弹窗中出现的资产类型，不统计已保存资产。
- 每个类型按后端 `/api/v1/assets/types` 目录与弹窗规则核对：是否出现在新建入口、默认端口、账号/密码字段、协议能力、目录声明工具和后端 tool_registry 是否一致。
- 本轮额外使用 Playwright 实测关键路径：Oracle、MySQL、NAS / SAN、Synology NAS、华三通用交换机、Kafka、Linux 进程。
- 真实数据口径：以运行中后端 `/api/v1/assets/types` 返回为准，不用前端静态兜底数据当结论。

## 汇总

- 后端资产类型：177 个
- 新建弹窗资产类型：177 个
- 弹窗缺失：0 个
- 弹窗多出：0 个
- 目录声明工具缺失：0 个
- 网络设备、存储节点、中间件 SSH 资产误暴露通用 Linux 工具：0 个
- 网络/存储/中间件分类快捷指令缺失：0 个
- 协议验证矩阵分类标签错配：0 个
- 运行中接口 `/api/v1/assets/types` 复测：177 个
- 新建弹窗目录来源标识：已显示 `后端真实目录 177 类`
- 快捷指令分类覆盖缺口：0 个
- 资产画像角色分类错配：0 个
- 画像互联采集策略缺口：0 个
- 旧画像协议兜底误分类读取纠偏缺口：0 个
- 前端快捷指令兜底逻辑：已与后端分类策略对齐
- 多协议资产选择：已支持同一资产类型下切换运维接入协议
- 防火墙双协议复测：默认 `ssh` 走 `network_cli_execute_command`，切换 `http_api` 走 `network_api_request`
- 逐项检查问题：0 个

## 本轮实测结论

- 新建资产弹窗打开时会请求运行中后端 `/api/v1/assets/types`，Playwright 在资产页点击“新建资产”抓到 2 次 200 响应，均为 177 条真实后端目录。
- 弹窗头部已显示目录来源；正常加载后为 `后端真实目录 177 类`，后端未返回目录时才会标识为离线兜底，避免把静态兜底误认为真实资产目录。
- Oracle：默认端口 1521，默认账号 system，Oracle Thick 模式默认勾选，显示 Oracle Instant Client 目录和驱动可用状态。
- MySQL：默认端口 3306，默认账号 root，原生工具为 `db_execute_query`，连接参数显示 `ssl_mode=preferred`、`charset=utf8mb4`、`connect_timeout=10`。
- NAS / SAN：按 SSH 存储节点 Shell 处理，默认端口 22，默认账号 root，显示密码框，不再走 SNMP 表单。
- Synology NAS：按 SSH 存储节点 Shell 处理，默认端口 22，默认账号 root。
- 华三通用交换机：按网络设备 CLI 处理，默认端口 22，默认账号 admin，显示 Enable 密码参数。
- 防火墙：保留 SSH CLI 作为默认运维入口，同时在新建资产中提供 HTTP/API 管理接口选项；切换后端口改为 443，工具链路从 `network_cli_execute_command` 切到 `network_api_request`，不会暴露通用 Linux 或通用 HTTP 工具。
- Kafka：按中间件主机 Shell 处理，主连接默认端口 22；Broker/Controller 端口作为扩展参数展示，不会覆盖 SSH 登录端口。
- Kafka Client/JVM：按中间件分类展示 `/middleware` 快捷指令，协议分别为 Kafka/JMX 探测，不走 Linux 主机快捷指令。
- Linux 进程：按中间件主机 Shell 处理，默认端口 22，默认账号 root。
- 在线会话 API 复测：H3C 会话只启用 `network_cli_execute_command`，Pinned 快捷指令为 `inspect/status/network-device-health`；Oracle/MySQL 会话只启用 `db_execute_query`，Pinned 快捷指令分别含 `oracle-health` / `mysql-health`。
- 协议验证矩阵复测：H3C 显示 `网络设备 SSH CLI`，NAS/Synology 显示 `存储设备 SSH CLI`，Kafka 主机显示 `中间件主机 SSH Shell`，不再混成普通 Linux 主机链路。
- 快捷指令整改：`/db-inspect` 按后端数据库目录覆盖 ClickHouse、DB2、Hive、IoTDB、Xugu、MongoDB Atlas、Redis Cluster、Doris/StarRocks 等数据服务；容器、大数据、服务探测、服务发现、安全平台也补了分类指令；错误协议仍被护栏拦截，例如 Oracle/http_api 不会出现 Oracle 或数据库巡检指令。
- 画像整改：资产画像角色现在按后端目录分类识别，H3C/Huawei 等网络设备、NAS/Synology 等存储设备、Kafka/process 等中间件 SSH 资产不会再被画像成 Linux 主机。
- 互联信息整改：画像互联采集策略按真实资产域生成，网络看 LLDP/ARP/MAC/路由，存储看共享/Bucket/复制，数据库看活跃会话和外部依赖，中间件看端口/队列/集群，容器和大数据按各自 API/作业/依赖补证据。
- 历史画像兼容：已保存的老画像如果曾因 SSH/WinRM/HTTP 协议被兜底成 Linux/Windows/API，读取时会按后端真实资产目录纠偏角色与互联采集策略；不会覆盖 Oracle EBS、H3C 交换机这类已有明确专业画像。
- 前端兜底兼容：会话页正常优先使用后端 `/session/{id}/commands`；若接口短暂失败，本地兜底也会按 `extra_args.category`、当前工具集和协议分类生成指令。H3C/Switch 不会回退成数据库或 Linux 指令，Oracle/MySQL/PostgreSQL 保留数据库专项，Prometheus/ManageEngine 保留监控告警指令，Kafka/process 保留中间件指令。

## 分类数量

- 操作系统与主机: 17
- 数据库与缓存: 39
- 容器与云原生: 6
- 中间件与消息: 21
- 存储与备份: 9
- 监控与告警: 12
- 虚拟化与私有云: 7
- 网络设备: 11
- 应用与网络服务: 20
- 硬件带外: 7
- 安全与身份: 3
- 大数据与分析: 13
- 服务发现: 6
- AI 与大模型: 5
- CI/CD 与发布: 1

## 逐项结果

| 序号 | 分类 | 类型ID | 名称 | 协议 | 默认端口 | 弹窗端口 | 认证 | 默认账号 | 密码框 | 目录工具 | 工具注册 |
|---:|---|---|---|---|---:|---:|---|---|---|---|---|
| 1 | 操作系统与主机 | `linux` | Linux / Unix | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 2 | 操作系统与主机 | `windows` | Windows Server | `winrm` | 5985 | 5985 | basic | Administrator | 有 | winrm_execute_command | OK |
| 3 | 操作系统与主机 | `aix` | IBM AIX | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 4 | 数据库与缓存 | `mysql` | MySQL | `mysql` | 3306 | 3306 | basic | root | 有 | db_execute_query | OK |
| 5 | 数据库与缓存 | `oracle` | Oracle | `oracle` | 1521 | 1521 | basic | system | 有 | db_execute_query | OK |
| 6 | 数据库与缓存 | `postgresql` | PostgreSQL | `postgresql` | 5432 | 5432 | basic | postgres | 有 | db_execute_query | OK |
| 7 | 数据库与缓存 | `mssql` | SQL Server | `mssql` | 1433 | 1433 | basic | sa | 有 | db_execute_query | OK |
| 8 | 数据库与缓存 | `redis` | Redis | `redis` | 6379 | 6379 | password_only | 空 | 有 | redis_execute_command | OK |
| 9 | 数据库与缓存 | `mongodb` | MongoDB | `mongodb` | 27017 | 27017 | basic | root | 有 | mongodb_find | OK |
| 10 | 数据库与缓存 | `clickhouse` | ClickHouse | `clickhouse` | 8123 | 8123 | basic | root | 有 | database_api_request | OK |
| 11 | 数据库与缓存 | `tidb` | TiDB | `mysql` | 4000 | 4000 | basic | root | 有 | db_execute_query | OK |
| 12 | 数据库与缓存 | `oceanbase` | OceanBase | `mysql` | 2881 | 2881 | basic | root | 有 | db_execute_query | OK |
| 13 | 数据库与缓存 | `dameng` | 达梦数据库 DM | `dameng` | 5236 | 5236 | basic | SYSDBA | 有 | db_execute_query | OK |
| 14 | 数据库与缓存 | `kingbase` | 人大金仓 Kingbase | `postgresql` | 54321 | 54321 | basic | root | 有 | db_execute_query | OK |
| 15 | 数据库与缓存 | `elasticsearch` | ElasticSearch | `elasticsearch` | 9200 | 9200 | basic | root | 有 | database_api_request | OK |
| 16 | 容器与云原生 | `docker` | Docker Host | `ssh` | 22 | 22 | basic | root | 有 | container_execute_command | OK |
| 17 | 容器与云原生 | `containerd` | containerd Host | `ssh` | 22 | 22 | basic | root | 有 | container_execute_command | OK |
| 18 | 容器与云原生 | `podman` | Podman Host | `ssh` | 22 | 22 | basic | root | 有 | container_execute_command | OK |
| 19 | 容器与云原生 | `harbor` | Harbor Registry | `http_api` | 443 | 443 | basic | 空 | 有 | container_api_request | OK |
| 20 | 容器与云原生 | `k8s` | Kubernetes | `k8s` | 6443 | 6443 | none | 空 | 无 | k8s_api_request | OK |
| 21 | 中间件与消息 | `nginx` | Nginx | `ssh` | 22 | 22 | basic | root | 有 | middleware_execute_command | OK |
| 22 | 中间件与消息 | `tomcat` | Tomcat | `ssh` | 22 | 22 | basic | root | 有 | middleware_execute_command | OK |
| 23 | 中间件与消息 | `kafka` | Kafka | `ssh` | 22 | 22 | basic | root | 有 | middleware_execute_command | OK |
| 24 | 中间件与消息 | `rabbitmq` | RabbitMQ | `http_api` | 15672 | 15672 | basic | 空 | 有 | middleware_api_request | OK |
| 25 | 中间件与消息 | `rocketmq` | RocketMQ | `ssh` | 22 | 22 | basic | root | 有 | middleware_execute_command | OK |
| 26 | 中间件与消息 | `zookeeper` | ZooKeeper | `ssh` | 22 | 22 | basic | root | 有 | middleware_execute_command | OK |
| 27 | 中间件与消息 | `nacos` | Nacos | `http_api` | 8848 | 8848 | basic | 空 | 有 | middleware_api_request | OK |
| 28 | 中间件与消息 | `consul` | Consul | `http_api` | 8500 | 8500 | basic | 空 | 有 | middleware_api_request | OK |
| 29 | 存储与备份 | `minio` | MinIO | `minio` | 9000 | 9000 | none | 空 | 无 | storage_api_request | OK |
| 30 | 监控与告警 | `prometheus` | Prometheus | `http_api` | 9090 | 9090 | basic | 空 | 有 | monitoring_api_query | OK |
| 31 | 监控与告警 | `alertmanager` | Alertmanager | `http_api` | 9093 | 9093 | basic | 空 | 有 | monitoring_api_query | OK |
| 32 | 监控与告警 | `grafana` | Grafana | `http_api` | 3000 | 3000 | basic | 空 | 有 | monitoring_api_query | OK |
| 33 | 监控与告警 | `loki` | Loki | `http_api` | 3100 | 3100 | basic | 空 | 有 | monitoring_api_query | OK |
| 34 | 监控与告警 | `victoriametrics` | VictoriaMetrics | `http_api` | 8428 | 8428 | basic | 空 | 有 | monitoring_api_query | OK |
| 35 | 监控与告警 | `zabbix` | Zabbix | `http_api` | 80 | 80 | basic | 空 | 有 | monitoring_api_query | OK |
| 36 | 监控与告警 | `manageengine` | ManageEngine / 卓豪监控 | `http_api` | 8443 | 8443 | basic | 空 | 有 | monitoring_api_query | OK |
| 37 | 虚拟化与私有云 | `vmware` | VMware vCenter (API) | `vmware` | 443 | 443 | basic | root | 有 | virtualization_api_request | OK |
| 38 | 虚拟化与私有云 | `esxi` | VMware ESXi 主机 (SSH) | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 39 | 虚拟化与私有云 | `kvm` | KVM / Libvirt Host | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 40 | 虚拟化与私有云 | `openstack` | OpenStack | `openstack` | 5000 | 5000 | basic | root | 有 | virtualization_api_request | OK |
| 41 | 虚拟化与私有云 | `proxmox` | Proxmox VE | `proxmox` | 8006 | 8006 | basic | root | 有 | virtualization_api_request | OK |
| 42 | 虚拟化与私有云 | `hyperv` | Microsoft Hyper-V | `winrm` | 5985 | 5985 | basic | Administrator | 有 | winrm_execute_command | OK |
| 43 | 虚拟化与私有云 | `zstack` | ZStack | `zstack` | 8080 | 8080 | basic | root | 有 | virtualization_api_request | OK |
| 44 | 网络设备 | `switch` | Switch / Router | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 45 | 网络设备 | `firewall` | Firewall | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 46 | 网络设备 | `f5` | F5 BIG-IP | `http_api` | 443 | 443 | basic | 空 | 有 | network_api_request | OK |
| 47 | 网络设备 | `a10` | A10 Load Balancer | `http_api` | 443 | 443 | basic | 空 | 有 | network_api_request | OK |
| 48 | 网络设备 | `waf` | WAF | `http_api` | 443 | 443 | basic | 空 | 有 | network_api_request | OK |
| 49 | 应用与网络服务 | `dns` | DNS Server | `dns` | 53 | 53 | none | 空 | 无 | service_probe_request | OK |
| 50 | 网络设备 | `vpn` | VPN Gateway | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 51 | 存储与备份 | `ceph` | Ceph Cluster | `ssh` | 22 | 22 | basic | root | 有 | storage_execute_command | OK |
| 52 | 存储与备份 | `nfs` | NFS Server | `ssh` | 22 | 22 | basic | root | 有 | storage_execute_command | OK |
| 53 | 存储与备份 | `nas` | NAS / SAN | `ssh` | 22 | 22 | basic | root | 有 | storage_execute_command | OK |
| 54 | 存储与备份 | `s3` | S3 / Object Storage | `s3` | 443 | 443 | none | 空 | 无 | storage_api_request | OK |
| 55 | 存储与备份 | `hdfs` | HDFS | `ssh` | 22 | 22 | basic | root | 有 | storage_execute_command | OK |
| 56 | 存储与备份 | `glusterfs` | GlusterFS | `ssh` | 22 | 22 | basic | root | 有 | storage_execute_command | OK |
| 57 | 存储与备份 | `backup` | Backup System | `backup` | 443 | 443 | none | 空 | 无 | storage_api_request | OK |
| 58 | 硬件带外 | `snmp` | SNMP Device | `snmp` | 161 | 161 | custom_snmp | 空 | 无 | snmp_get | OK |
| 59 | 硬件带外 | `redfish` | Redfish / iLO / iDRAC | `redfish` | 443 | 443 | basic | 空 | 有 | http_api_request | OK |
| 60 | 硬件带外 | `ipmi` | IPMI | `ipmi` | 623 | 623 | basic | admin | 有 | service_probe_request | OK |
| 61 | 安全与身份 | `bastion` | 堡垒机 / Bastion | `http_api` | 443 | 443 | basic | 空 | 有 | security_api_request | OK |
| 62 | 安全与身份 | `ldap` | LDAP / Active Directory | `ldap` | 389 | 389 | basic | 空 | 有 | service_probe_request | OK |
| 63 | 安全与身份 | `audit` | Audit Platform | `http_api` | 443 | 443 | basic | 空 | 有 | security_api_request | OK |
| 64 | 中间件与消息 | `activemq` | ActiveMQ消息系统 | `http_api` | 8161 | 8161 | basic | 空 | 有 | middleware_api_request | OK |
| 65 | 大数据与分析 | `airflow` | Apache Airflow | `http_api` | 8080 | 8080 | basic | 空 | 有 | bigdata_api_request | OK |
| 66 | 操作系统与主机 | `almalinux` | AlmaLinux | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 67 | 应用与网络服务 | `api` | HTTP API | `http` | 80 | 80 | none | 空 | 无 | service_probe_request | OK |
| 68 | 应用与网络服务 | `api_code` | API业务状态码 | `http` | 80 | 80 | none | 空 | 无 | service_probe_request | OK |
| 69 | 中间件与消息 | `apollo` | Apollo配置中心 | `http_api` | 8080 | 8080 | basic | 空 | 有 | middleware_api_request | OK |
| 70 | 操作系统与主机 | `centos` | Centos Linux | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 71 | 网络设备 | `cisco_switch` | 思科通用交换机 | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 72 | 服务发现 | `consul_sd` | Consul Service Discovery | `http_api` | 8500 | 8500 | basic | 空 | 有 | discovery_api_request | OK |
| 73 | 操作系统与主机 | `coreos` | Fedora CoreOS | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 74 | 硬件带外 | `dahua` | 大华 | `http_api` | 80 | 80 | basic | 空 | 有 | oob_api_request | OK |
| 75 | 操作系统与主机 | `darwin` | Darwin操作系统 | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 76 | 数据库与缓存 | `db2` | DB2数据库 | `db2` | 50000 | 50000 | basic | db2inst1 | 有 | db_execute_query | OK |
| 77 | 操作系统与主机 | `debian` | Debian操作系统 | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 78 | AI 与大模型 | `deepseek` | Deepseek | `http_api` | 443 | 443 | none | 空 | 无 | ai_platform_api_request | OK |
| 79 | 数据库与缓存 | `dm` | 达梦数据库 | `dameng` | 5236 | 5236 | basic | SYSDBA | 有 | db_execute_query | OK |
| 80 | 服务发现 | `dns_sd` | Dns Service Discovery | `dns` | 53 | 53 | none | 空 | 无 | service_probe_request | OK |
| 81 | 大数据与分析 | `dolphinscheduler` | Apache DolphinScheduler | `http_api` | 12345 | 12345 | basic | 空 | 有 | bigdata_api_request | OK |
| 82 | 数据库与缓存 | `doris_be` | Apache Doris BE | `http_api` | 8040 | 8040 | basic | 空 | 有 | database_api_request | OK |
| 83 | 数据库与缓存 | `doris_fe` | Apache Doris FE | `mysql` | 9030 | 9030 | basic | root | 有 | db_execute_query | OK |
| 84 | 中间件与消息 | `dynamic_tp` | DynamicTp 线程池 | `http_api` | 8080 | 8080 | basic | 空 | 有 | middleware_api_request | OK |
| 85 | 中间件与消息 | `emqx` | EMQX MQTT | `http_api` | 18083 | 18083 | basic | 空 | 有 | middleware_api_request | OK |
| 86 | 操作系统与主机 | `euleros` | EulerOS 操作系统 | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 87 | 服务发现 | `eureka_sd` | Eureka Service Discovery | `http_api` | 8761 | 8761 | basic | 空 | 有 | discovery_api_request | OK |
| 88 | 大数据与分析 | `flink` | Apache Flink | `http_api` | 8081 | 8081 | basic | 空 | 有 | bigdata_api_request | OK |
| 89 | 大数据与分析 | `flink_on_yarn` | Apache Flink On Yarn | `http_api` | 8088 | 8088 | basic | 空 | 有 | bigdata_api_request | OK |
| 90 | 操作系统与主机 | `freebsd` | FreeBSD操作系统 | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 91 | 应用与网络服务 | `ftp` | FTP服务器 | `ftp` | 21 | 21 | none | 空 | 无 | service_probe_request | OK |
| 92 | 应用与网络服务 | `fullsite` | SiteMap全站 | `http` | 80 | 80 | none | 空 | 无 | service_probe_request | OK |
| 93 | 数据库与缓存 | `greenplum` | GreenPlum 数据库 | `postgresql` | 5432 | 5432 | basic | root | 有 | db_execute_query | OK |
| 94 | 数据库与缓存 | `greptime` | GreptimeDB | `mysql` | 4002 | 4002 | basic | root | 有 | db_execute_query | OK |
| 95 | 网络设备 | `h3c_switch` | 华三通用交换机 | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 96 | 大数据与分析 | `hadoop` | Apache Hadoop | `http_api` | 9870 | 9870 | basic | 空 | 有 | bigdata_api_request | OK |
| 97 | 数据库与缓存 | `hbase_master` | Apache Hbase Master | `http_api` | 16010 | 16010 | basic | 空 | 有 | database_api_request | OK |
| 98 | 数据库与缓存 | `hbase_regionserver` | Apache Hbase RegionServer | `http_api` | 16030 | 16030 | basic | 空 | 有 | database_api_request | OK |
| 99 | 大数据与分析 | `hdfs_datanode` | Apache HDFS DataNode | `http_api` | 9864 | 9864 | basic | 空 | 有 | bigdata_api_request | OK |
| 100 | 大数据与分析 | `hdfs_namenode` | Apache HDFS NameNode | `http_api` | 9870 | 9870 | basic | 空 | 有 | bigdata_api_request | OK |
| 101 | 监控与告警 | `hertzbeat` | HertzBeat | `http_api` | 1157 | 1157 | basic | 空 | 有 | monitoring_api_query | OK |
| 102 | 监控与告警 | `hertzbeat_token` | HertzBeat(Token) | `http_api` | 1157 | 1157 | basic | 空 | 有 | monitoring_api_query | OK |
| 103 | 硬件带外 | `hikvision_isapi` | 海康威视 ISAPI | `http_api` | 80 | 80 | basic | 空 | 有 | oob_api_request | OK |
| 104 | 数据库与缓存 | `hive` | Apache Hive | `hive` | 10000 | 10000 | basic | root | 有 | db_execute_query | OK |
| 105 | 网络设备 | `hpe_switch` | HPE通用交换机 | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 106 | 服务发现 | `http_sd` | Http Service Discovery | `http_api` | 80 | 80 | basic | 空 | 有 | discovery_api_request | OK |
| 107 | 网络设备 | `huawei_switch` | 华为通用交换机 | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 108 | 数据库与缓存 | `hugegraph` | HugeGraph | `http_api` | 8080 | 8080 | basic | 空 | 有 | database_api_request | OK |
| 109 | 大数据与分析 | `iceberg` | Apache Iceberg | `http_api` | 8181 | 8181 | basic | 空 | 有 | bigdata_api_request | OK |
| 110 | 硬件带外 | `idrac` | Dell iDRAC | `redfish` | 443 | 443 | basic | 空 | 有 | http_api_request | OK |
| 111 | 数据库与缓存 | `influxdb` | InfluxDB | `http_api` | 8086 | 8086 | basic | 空 | 有 | database_api_request | OK |
| 112 | 监控与告警 | `influxdb_promql` | InfluxDB-PromQL | `http_api` | 9090 | 9090 | basic | 空 | 有 | monitoring_api_query | OK |
| 113 | 数据库与缓存 | `iotdb` | Apache IoTDB | `iotdb` | 6667 | 6667 | basic | root | 有 | db_execute_query | OK |
| 114 | CI/CD 与发布 | `jenkins` | Jenkins | `http_api` | 8080 | 8080 | basic | 空 | 有 | cicd_api_request | OK |
| 115 | 中间件与消息 | `jetty` | Jetty应用服务器 | `http_api` | 8080 | 8080 | basic | 空 | 有 | middleware_api_request | OK |
| 116 | 中间件与消息 | `jvm` | JVM虚拟机 | `jmx` | 9999 | 9999 | basic | root | 有 | service_probe_request | OK |
| 117 | 中间件与消息 | `kafka_client` | Kafka消息系统（客户端） | `kafka` | 9092 | 9092 | basic | root | 有 | service_probe_request | OK |
| 118 | 监控与告警 | `kafka_promql` | Kafka-PromQL | `http_api` | 9090 | 9090 | basic | 空 | 有 | monitoring_api_query | OK |
| 119 | 容器与云原生 | `kubernetes` | Kubernetes | `k8s` | 6443 | 6443 | none | 空 | 无 | k8s_api_request | OK |
| 120 | 数据库与缓存 | `kvrocks` | Kvrocks 数据库 | `redis` | 6666 | 6666 | password_only | 空 | 有 | redis_execute_command | OK |
| 121 | 操作系统与主机 | `linux_script` | Linux 命令 | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 122 | AI 与大模型 | `lmstudio` | LM Studio 监控 | `http_api` | 1234 | 1234 | none | 空 | 无 | ai_platform_api_request | OK |
| 123 | 操作系统与主机 | `macos` | macOS | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 124 | 数据库与缓存 | `mariadb` | MariaDB数据库 | `mysql` | 3306 | 3306 | basic | root | 有 | db_execute_query | OK |
| 125 | 数据库与缓存 | `memcached` | Memcached | `memcached` | 11211 | 11211 | none | 空 | 无 | memcached_execute_command | OK |
| 126 | 应用与网络服务 | `modbus` | ModBus服务器 | `modbus` | 502 | 502 | none | 空 | 无 | service_probe_request | OK |
| 127 | 数据库与缓存 | `mongodb_atlas` | MongoDB Atlas 数据库 | `mongodb` | 27017 | 27017 | basic | root | 有 | mongodb_find | OK |
| 128 | 应用与网络服务 | `mqtt` | MQTT 连接 | `mqtt` | 1883 | 1883 | none | 空 | 无 | service_probe_request | OK |
| 129 | 服务发现 | `nacos_sd` | Nacos 服务发现 | `http_api` | 8848 | 8848 | basic | 空 | 有 | discovery_api_request | OK |
| 130 | 数据库与缓存 | `nebula_graph` | NebulaGraph | `nebula_graph` | 9669 | 9669 | basic | root | 有 | database_api_request | OK |
| 131 | 数据库与缓存 | `nebula_graph_cluster` | NebulaGraph集群 | `nebula_graph` | 9669 | 9669 | basic | root | 有 | database_api_request | OK |
| 132 | 应用与网络服务 | `netease_mailbox` | 网易邮箱监控 | `imap` | 993 | 993 | none | 空 | 无 | service_probe_request | OK |
| 133 | 应用与网络服务 | `ntp` | NTP服务器 | `ntp` | 123 | 123 | none | 空 | 无 | service_probe_request | OK |
| 134 | AI 与大模型 | `nvidia` | NVIDIA | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 135 | AI 与大模型 | `ollama` | Ollama | `http_api` | 11434 | 11434 | none | 空 | 无 | ai_platform_api_request | OK |
| 136 | AI 与大模型 | `openai` | OpenAI 监控 | `http_api` | 443 | 443 | none | 空 | 无 | ai_platform_api_request | OK |
| 137 | 数据库与缓存 | `opengauss` | OpenGauss数据库 | `postgresql` | 5432 | 5432 | basic | root | 有 | db_execute_query | OK |
| 138 | 操作系统与主机 | `opensuse` | OpenSUSE | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 139 | 应用与网络服务 | `ping` | PING连通性 | `icmp` |  |  | none | 空 | 无 | service_probe_request | OK |
| 140 | 应用与网络服务 | `pop3` | POP3邮件服务器 | `pop3` | 110 | 110 | none | 空 | 无 | service_probe_request | OK |
| 141 | 应用与网络服务 | `port` | 端口可用性 | `tcp` | 80 | 80 | none | 空 | 无 | service_probe_request | OK |
| 142 | 大数据与分析 | `prestodb` | PrestoDB | `http_api` | 8080 | 8080 | basic | 空 | 有 | bigdata_api_request | OK |
| 143 | 中间件与消息 | `process` | Linux进程 | `ssh` | 22 | 22 | basic | root | 有 | middleware_execute_command | OK |
| 144 | 中间件与消息 | `pulsar` | Pulsar | `http_api` | 8080 | 8080 | basic | 空 | 有 | middleware_api_request | OK |
| 145 | 应用与网络服务 | `qq_mailbox` | QQ 邮箱监控 | `imap` | 993 | 993 | none | 空 | 无 | service_probe_request | OK |
| 146 | 操作系统与主机 | `redhat` | Red Hat | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 147 | 数据库与缓存 | `redis_cluster` | Redis Cluster | `redis` | 6379 | 6379 | password_only | 空 | 有 | redis_execute_command | OK |
| 148 | 数据库与缓存 | `redis_sentinel` | Redis Sentinel | `redis` | 26379 | 26379 | password_only | 空 | 有 | redis_execute_command | OK |
| 149 | 应用与网络服务 | `registry` | 注册中心监控 | `registry` | 80 | 80 | none | 空 | 无 | service_probe_request | OK |
| 150 | 操作系统与主机 | `rockylinux` | Rocky Linux | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 151 | 应用与网络服务 | `s7` | s7服务器 | `s7` | 102 | 102 | none | 空 | 无 | service_probe_request | OK |
| 152 | 大数据与分析 | `seatunnel` | Seatunnel | `http_api` | 5801 | 5801 | basic | 空 | 有 | bigdata_api_request | OK |
| 153 | 中间件与消息 | `shenyu` | Apache ShenYu网关 | `http_api` | 9095 | 9095 | basic | 空 | 有 | middleware_api_request | OK |
| 154 | 应用与网络服务 | `smtp` | SMTP邮件服务器 | `smtp` | 25 | 25 | none | 空 | 无 | service_probe_request | OK |
| 155 | 大数据与分析 | `spark` | Apache Spark | `http_api` | 8080 | 8080 | basic | 空 | 有 | bigdata_api_request | OK |
| 156 | 中间件与消息 | `spring_gateway` | Spring Cloud Gateway | `http_api` | 8080 | 8080 | basic | 空 | 有 | middleware_api_request | OK |
| 157 | 中间件与消息 | `springboot2` | SpringBoot2.0 | `http_api` | 8080 | 8080 | basic | 空 | 有 | middleware_api_request | OK |
| 158 | 中间件与消息 | `springboot3` | SpringBoot3.0 | `http_api` | 8080 | 8080 | basic | 空 | 有 | middleware_api_request | OK |
| 159 | 数据库与缓存 | `sqlserver` | SqlServer数据库 | `mssql` | 1433 | 1433 | basic | root | 有 | db_execute_query | OK |
| 160 | 应用与网络服务 | `ssl_cert` | SSL证书 | `tls` | 443 | 443 | none | 空 | 无 | service_probe_request | OK |
| 161 | 数据库与缓存 | `starrocks_be` | StarRocks BE | `http_api` | 8040 | 8040 | basic | 空 | 有 | database_api_request | OK |
| 162 | 数据库与缓存 | `starrocks_fe` | StarRocks FE | `mysql` | 9030 | 9030 | basic | root | 有 | db_execute_query | OK |
| 163 | 大数据与分析 | `storm` | Apache Storm | `http_api` | 8080 | 8080 | basic | 空 | 有 | bigdata_api_request | OK |
| 164 | 存储与备份 | `synology_nas` | Synology NAS | `ssh` | 22 | 22 | basic | root | 有 | storage_execute_command | OK |
| 165 | 监控与告警 | `tdengine_promql` | TDengine-PromQL | `http_api` | 9090 | 9090 | basic | 空 | 有 | monitoring_api_query | OK |
| 166 | 网络设备 | `tplink_switch` | TP-LINK通用交换机 | `ssh` | 22 | 22 | basic | admin | 有 | network_cli_execute_command | OK |
| 167 | 操作系统与主机 | `ubuntu` | Ubuntu Linux | `ssh` | 22 | 22 | basic | root | 有 | linux_execute_command | OK |
| 168 | 应用与网络服务 | `udp_port` | UDP端口可用性 | `udp` | 53 | 53 | none | 空 | 无 | service_probe_request | OK |
| 169 | 硬件带外 | `uniview` | 宇视 | `http_api` | 80 | 80 | basic | 空 | 有 | oob_api_request | OK |
| 170 | 数据库与缓存 | `valkey` | Valkey数据库 | `redis` | 6379 | 6379 | password_only | 空 | 有 | redis_execute_command | OK |
| 171 | 数据库与缓存 | `vastbase` | Vastbase数据库 | `postgresql` | 5432 | 5432 | basic | root | 有 | db_execute_query | OK |
| 172 | 应用与网络服务 | `website` | 网站监测 | `http` | 80 | 80 | none | 空 | 无 | service_probe_request | OK |
| 173 | 应用与网络服务 | `websocket` | WebSocket | `websocket` | 80 | 80 | none | 空 | 无 | service_probe_request | OK |
| 174 | 操作系统与主机 | `windows_script` | Windows 命令 | `winrm` | 5985 | 5985 | basic | Administrator | 有 | winrm_execute_command | OK |
| 175 | 数据库与缓存 | `xugu` | 虚谷数据库 | `xugu` | 5138 | 5138 | basic | SYSDBA | 有 | db_execute_query | OK |
| 176 | 大数据与分析 | `yarn` | Apache Yarn | `http_api` | 8088 | 8088 | basic | 空 | 有 | bigdata_api_request | OK |
| 177 | 服务发现 | `zookeeper_sd` | Zookeeper Service Discovery | `tcp` | 2181 | 2181 | none | 空 | 无 | service_probe_request | OK |
