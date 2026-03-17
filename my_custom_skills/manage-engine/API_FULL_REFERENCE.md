# ManageEngine Applications Manager REST API 完全文档

## 目录
1. [概述](#概述)
2. [认证方式](#认证方式)
3. [Add Monitor APIs](#add-monitor-apis)
4. [Downtime Scheduler APIs](#downtime-scheduler-apis)
5. [Monitor Group Operations APIs](#monitor-group-operations-apis)
6. [List Data APIs](#list-data-apis)
7. [User Management APIs](#user-management-apis)
8. [Perform Operation APIs](#perform-operation-apis)
9. [Admin Activities APIs](#admin-activities-apis)
10. [Processes and Services APIs](#processes-and-services-apis)
11. [Error Handling](#error-handling)

---

## 概述

ManageEngine Applications Manager 提供了一套完整的REST API，用于从Applications Manager获取数据。通过这些API，可以将Applications Manager的数据集成到任何内部门户或第三方系统管理软件中。数据也可以在单个仪表板中展示。

**重要提示：**
- 建议使用安全通道(HTTPS)模式与Applications Manager通信，以避免REST API调用过程中的安全问题
- Applications Manager的REST API限制为每分钟1000次调用

---

## 认证方式

### API Key认证

每个用户应该获得一个API密钥，这是一个长文本，是Applications Manager账户的唯一标识。API密钥必须在每次API请求中传递。

### 生成API Key

1. 点击**Settings**选项卡
2. 在**Integration with Portals**下，点击**REST API**
3. 将生成API密钥，例如：*7b5fde68148fa2419bc2f1a1ab87e757*

### 使用方法

**基本URL格式：**
```
https://[HOST]:[PORT]/AppManager/xml/[API_ENDPOINT]?apikey=[YOUR_API_KEY]
```

### 使用Curl命令

**POST请求：**
```bash
curl -d "[API_REQUEST_PARAMETERS]" [API_URL]
```

示例：
```bash
curl -d "apikey=7b5fde68148fa2419bc2f1a1ab87e757&type=server" https://apm-prod-server:8443/AppManager/xml/ListServer?
```

**GET请求：**
```bash
curl "[API_URL]?[API_REQUEST_PARAMETERS]"
```

示例：
```bash
curl "http://localhost:9090/AppManager/xml/ShowPolledData?apikey=34ddf955a14953bbf7740c9f38d6be5d&resourceid=10000231&attributeID=402&period=1"
```

### 使用Wget命令

```bash
wget [COMPLETE_RESTAPI_URL]
```

示例：
```bash
wget https://apm-prod-server:8443/AppManager/xml/ListServer?apikey=7b5fde68148fa2419bc2f1a1ab87e757&type=server
```

---

## Add Monitor APIs

### 通用请求参数

| 参数 | 描述 |
|------|------|
| apikey | 从Settings选项卡中的"Generate API Key"选项生成的密钥 |
| displayname | 监控器的显示名称 |
| host | 主机名 |
| port | 端口号 |
| username | 用户名 |
| password | 密码 |
| pollInterval | 轮询间隔（分钟） |

### 应用服务器监控器

#### Apache Geronimo
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=ApacheGeronimo&host=[HostName]&port=[JMX PORT]&UserName=[Username]&Password=[password]&displayname=[Display Name]&JNDIPath=[JNDIPATH]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/AddMonitor?apikey=aaaaaabbbbbbccccccddddddeeeeee&type=ApacheGeronimo&host=app-xp2&port=8989&username=admin&password=appman&displayname=Apache Geronimo Server&JNDIPath=/jmxrmi
```

#### GlassFish
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=glassfish&host=[HOST]&port=[PORT]&username=[USERNAME]&password=[PASSWORD]&displayname=[DISPLAYNAME]&JNDIPath=[JNDIPATH]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/AddMonitor?apikey=aaaaaabbbbbbccccccddddddeeeeee&type=glassfish&host=app-xp2&port=8686&username=admin&password=appman&displayname=glfish&JNDIPath=/jmxrmi
```

#### JBoss Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=JBoss server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&version=[VERSION]&authEnabled=[AUTHENABLED]&username=[USERNAME]&password=[PASSWORD]
```

**支持的版本：**
- 3.2.x, 4.x, 4.0.1, 4.0.2, 5.x, 6.x, 7.x, Wildfly_8.x

**示例：**
```
https://prod-server2:9090/AppManager/xml/AddMonitor?apikey=aaaaaabbbbbbccccccddddddeeeeee&type=JBoss server&displayname=AppmanagerJBoss4&host=app-xp2&port=8080&version=Wildfly_8.x&authEnabled=on&username=admin&password=appman
```

#### Jetty Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Jetty Server&host=[HostName]&port=[JMX PORT]&UserName=[Username]&Password=[password]&displayname=Jetty&JNDIPath=[JNDIPATH]
```

#### Microsoft .NET
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=.Net&displayname=[DISPLAYNAME]&host=[HOST]&username=[USERNAME]&password=[PASSWORD]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/AddMonitor?apikey=aaaaaabbbbbbccccccddddddeeeeee&type=.Net&displayname=AppmanagerDotNet&host=app-xp3&username=admin&password=appman
```

#### Oracle Application Server
**支持的版本：**
- 10.1.3

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=oracle application server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&version=[VERSION]
```

#### Resin Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Resin&host=[HostName]&port=[JMX PORT]&UserName=[Username]&Password=[password]&displayname=Resin&JNDIPath=[JNDIPATH]
```

#### SilverStream
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=SilverStream&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### TongWeb Server
**语法：**
```
http://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=TongWeb&displayname=[DISPLAYNAME]&host=[TARGET_HOST]&port=[TARGET_PORT]&jndiurl=[JNDI_URL]&sslenabled=[true/false]&username=[USERNAME]&password=[PASSWORD]
```

#### Tomcat Server
**支持的版本：**
- 5及以上版本

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=tomcat server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&username=[USERNAME]&password=[PASSWORD]&version=[VERSION]
```

#### VMware vFabric tc Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=VMware vFabric tc Server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&username=[USERNAME]&password=[PASSWORD]&JNDIPath=[JNDI Path]
```

#### WebLogic Server
**支持的版本：**
- 6.1, 7.0, 8.1, 9.x, 10.x, 12.x, 14.x

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=WEBLOGIC SERVER&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&username=[USERNAME]&password=[PASSWORD]&version=[VERSION]
```

#### WebSphere Server
**支持的版本：**
- 5.x, 6.x, 7.x, 8.x, 9.x

**部署模式：**
- BASE（基础部署）
- ND（网络部署）

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=websphere server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&version=[VERSION]&mode=[MODE]&soapport=[SOAPPORT]
```

---

### 云服务监控器

#### Amazon
**支持的服务：**
- EC2, RDS, S3, DynamoDB, Lambda, SNS, SQS
- ALB, NLB, EKS, ECS, Elastic Beanstalk
- 多种其他AWS服务

**语法（版本15180及以上）：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Amazon&accessKey=[ACCESSKEY]&SecretAccessKey=[SECRETACCESSKEY]&displayname=[DISPLAYNAME]&AccountType=[ACCOUNTTYPE]&AmazonServices=[SERVICES]
```

**支持的区域类型：**
- AwsGlobal
- AwsChina
- AwsGovCloud

#### Google Cloud Platform
**支持的服务：**
- ComputeEngine
- CloudStorage
- CloudFilestore
- KubernetesEngine

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=GoogleCloudPlatform&displayname=[DISPLAY_NAME]&GCPServices=[GCP_Services]&ProjectID=[Project_ID]&provider=[OAuth_Provider_Name]
```

#### Microsoft 365
**支持的版本：**
- 16300及以下
- 16310及以上

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Office365&displayname=[DISPLAYNAME]&Office365TenantName=[TENANTNAME]&Office365Services=[SERVICES]&TenantID=[TENANTID]&ClientID=[CLIENTID]&ClientSecret=[CLIENTSECRET]
```

**支持的Office 365服务：**
- ExchangeOnline
- SharepointOnline
- MicrosoftTeams

#### Microsoft Azure
**支持的三种认证模式：**
1. AD Application & Service Principal (Mode 1)
2. Azure Organizational Account (Mode 2)
3. OAuth Mode (Mode 3)

**支持的Azure服务：**
- VirtualMachines, StorageAccounts, SQLDatabases
- KubernetesServices, AzureAppService, AzureFunctions
- AzureCosmosDB, AzureRedisCache等

**语法（Mode 1）：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=MicrosoftAzure&displayname=[DISPLAYNAME]&SubscriptionID=[SUBSCRIPTIONID]&AzureServices=[SERVICES]&AzureAccountType=[AZUREACCOUNTTYPE]&DiscoveryMode=AzureSPApp&ClientID=[CLIENTID]&TenantID=[TENANTID]&AppKey=[APPKEY]
```

#### OpenStack
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=OpenStack&displayname=[DISPLAY_NAME]&baseAuthURL=[IDENTITY_URL]&tenantName=[PROJECT_NAME]&username=[USENAME]&password=[PASSWORD]
```

#### Oracle Cloud Infrastructure
**支持的Oracle云服务：**
- Compute, Database
- OracleCloudLoadBalancer, Storage

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=OracleCloud&displayname=[DISPLAY_NAME]&TenancyOCID=[Tenancy_OCID]&UserID=[User_OCID]&OracleServices=[Oracle_Services]&PEMFilePath=[PEM_File_Path]
```

---

### 数据库服务器监控器

#### IBM DB2
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=db2&displayname=[DISPLAYNAME]&username=[USERNAME]&host=[HOST]&password=[PASSWORD]&port=[PORT]&instance=[INSTANCE]
```

#### IBM DB2 for i
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=db2&displayname=[DISPLAYNAME]&username=[USERNAME]&HostName=[HOST]&password=[PASSWORD]
```

#### IBM Informix
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Informix&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&informixserver=[DATABASE SERVER NAME]&username=[USERNAME]&password=[PASSWORD]
```

#### Memcached
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Memcached&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### MS SQL
**支持的认证类型：**
- SQL, NTLM, Kerberos, NativeAuthentication

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=MS SQL&displayname=[DISPLAYNAME]&username=[USERNAME]&host=[HOST]&password=[PASSWORD]&port=[PORT]
```

#### MySQL
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=mysql&displayname=[DISPLAYNAME]&username=[USERNAME]&host=[HOST]&password=[PASSWORD]&port=[PORT]
```

#### Oracle
**支持的版本：**
- 支持所有Oracle版本

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=oracle&displayname=[DISPLAYNAME]&username=[USERNAME]&host=[HOST]&password=[PASSWORD]&port=[PORT]
```

#### Oracle RAC
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=oracleRAC&displayname=[DISPLAYNAME]&username=[USERNAME]&host=[HOST]&password=[PASSWORD]&port=[PORT]
```

#### PostgreSQL
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=PostgreSQL&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&username=[USERNAME]&password=[PASSWORD]
```

#### SAP HANA
**支持的部署类型：**
- OnPremise
- OnDemand

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=SapHana&displayname=[DISPLAYNAME]&host=[HOST]&isOndemand=false&port=[PORT]&dbUser=[DB_USERNAME]&dbPassword=[DB_PASSWORD]
```

#### 其他数据库
- **Cassandra**
- **MongoDB**
- **Redis**
- **Neo4j**
- **CouchBase**
- **HBase**
- **Oracle NoSQL**
- **SAP ASE Servers**
- **SAP Replication Servers**
- **SQL Anywhere**
- **Dameng DB**
- **Kingbase DB**

---

### ERP系统监控器

#### Oracle EBS
**支持的版本：**
- R11i, R12.0, R12.1.3, R12.2.0, R12.2.5及以上

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=OracleEBS&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]&SSL=[SSL]&Version=[version]
```

#### SAP Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=sap server&displayname=[DISPLAYNAME]&host=[HOST]&username=[USERNAME]&password=[PASSWORD]&systemnumber=[SYSTEMNUMBER]
```

#### SAP Java
**语法：**
```
http://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[API_KEY]&type=SAPASJava&displayname=SAPREST&host=[HOSTNAME]&port=[P4PORT]&username=[USERNAME]&password=[PASSWORD]
```

#### SAP CCMS
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=SAP CCMS&displayname=[DISPLAYNAME]&host=[HOST]
```

#### Siebel Enterprise Server
**支持的监控模式：**
- SSH
- WMI

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=SiebelEnterpriseServer&displayname=[DISPLAYNAME]&HostName=[HOSTNAME]&mode=[SSH/WMI]
```

#### Microsoft Dynamics CRM/365
**支持的版本：**
- 2011, 2013, 2016, Dynamics365

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Microsoft Dynamics CRM&displayname=[DISPLAYNAME]&host=[HOSTNAME]&Version=[VERSION]
```

#### Microsoft Dynamics AX
**支持的版本：**
- 2012, 2012R2, 2013R3

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=MSDynamicsAX&displayname=[DISPLAYNAME]&host=[HOST NAME]&Version=[VERSION]
```

#### SAP Business One
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=SAPBusinessOne&displayname=[DISPLAYNAME]&host=[HOST NAME]&port=[PORT]
```

---

### 邮件服务器监控器

#### Exchange Server
**支持的版本：**
- 2003, 2007, 2010, 2013, 2016, 2019

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Exchange Server&displayname=[DISPLAYNAME]&host=[HOST]&username=[USERNAME]&password=[PASSWORD]
```

#### Mail Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Mail Server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

---

### 服务器监控器

#### AIX
**支持的发现方式：**
- Telnet
- SSH

**语法（Telnet）：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=servers&displayname=[DISPLAYNAME]&host=[HOST]&os=AIX&username=[USERNAME]&mode=TELNET&snmptelnetport=23
```

#### Linux
**支持的发现方式：**
- Telnet
- SSH
- SNMP (V1/V2, V3)

**语法（SSH）：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=servers&displayname=[DISPLAYNAME]&host=[HOST]&os=Linux&mode=SSH&snmptelnetport=22
```

#### Windows
**支持的监控方式：**
- WMI
- SNMP

**语法（WMI）：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&displayname=[DISPLAYNAME]&host=[HOST]&os=Windows 2019&mode=WMI
```

**支持的Windows版本：**
- Windows 2000, 2003, 2008, 2012, 2016, 2019, 2022
- Windows 7, 8, 10, 11
- Windows XP, NT

#### Windows Clusters
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Windows Cluster&displayname=[DISPLAYNAME]&host=[HOST]
```

---

### 虚拟化监控器

#### VMware ESX/ESXi Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=VMware ESX/ESXi&displayname=[DISPLAYNAME]&host=[HOST]
```

#### vCenter
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=vCenter&displayname=[DISPLAYNAME]&host=[HOST]
```

#### Microsoft Hyper-V Server
**支持的版本：**
- 2008, 2012, 2016, 2019

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Hyper-V Server&displayname=[DISPLAYNAME]&host=[HOST]
```

#### Docker
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Docker&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### Kubernetes
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Kubernetes&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### 其他虚拟化平台
- **Citrix Hypervisor (XenServer)**
- **Citrix Virtual Apps and Desktops**
- **VMware Horizon View Connection Broker**
- **Red Hat Virtualization (RHV)**
- **Kernel-based Virtual Machine (KVM)**
- **OpenShift**
- **Oracle VM (OVM)**
- **Podman**
- **XenApp**

---

### Web服务器/服务监控器

#### Apache Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Apache Server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### Nginx Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Nginx&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### IIS Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=IIS-server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### URL Monitor
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=UrlMonitor&displayname=[DISPLAYNAME]&timeout=[TIMEOUT]&url=[httpurl]
```

**URL方法：**
- G (GET)
- P (POST)

#### SSL/TLS Certificate Monitor
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=SSLCertificateMonitor&displayname=[DISPLAYNAME]&domain=[DOMAIN]&port=[PORT]
```

#### Real Browser Monitor (RBM)
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=RBM&displayname=[DISPLAYNAME]&rbmagentID=[RBMAGENTID]
```

#### REST API Monitor
**支持的认证方式：**
- Basic authentication (nocm)
- Credential manager (cm)
- OAuth Token (oauth)
- Web Token (WEBTOKEN)

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=RESTAPIMonitor&displayname=[DISPLAYNAME]&API=[REST_API_URL]
```

#### 其他Web服务
- **Apache Solr**
- **Elasticsearch Monitor**
- **HAProxy Monitor**
- **IBM HTTP Server**
- **Oracle HTTP Server**
- **Web Services**
- **Webpage Analyzer**
- **WebSocket Monitor**
- **Nginx Plus**

---

### 自定义监控器

#### Windows Performance Counters
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Windows Performance Counters&displayname=[DISPLAYNAME]&host=[HOST]
```

#### Database Query Monitor
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=QueryMonitor&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### File/Directory Monitor
**支持的监控类型：**
- File Monitor
- Directory Monitor

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=File Monitor&displayname=[DISPLAYNAME]&filepath=[FILEPATH]&serversite=[LOCAL/REMOTE]
```

#### Script Monitor
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Script Monitor&displayname=[DISPLAYNAME]&serverpath=[SERVERPATH]
```

---

### EUM监控器

#### Ping Monitor (EUM)
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Ping Monitor&displayname=[DISPLAYNAME]&host=[HOST]&timeout=[TIMEOUT]
```

#### DNS Monitor
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=DNSMonitor&displayname=[DISPLAYNAME]&timeout=[TIMEOUT]
```

#### LDAP Server
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=LDAP Server&displayname=[DISPLAYNAME]&timeout=[TIMEOUT]
```

#### Mail Server (EUM)
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Mail Server&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

#### Telnet (EUM)
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitor?apikey=[APIKEY]&type=Telnet (EUM)&displayname=[DISPLAYNAME]&host=[HOST]&port=[PORT]
```

---

## Downtime Scheduler APIs

### CreateMaintenanceTask

**支持的停机类型：**
- Daily（每天）
- Weekly（每周）
- Monthly（每月）
- Once（一次性）

#### Daily停机计划
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/CreateMaintenanceTask?apikey=[APIKEY]&taskMethod=daily&taskStartTime=[STARTTIME]&taskEndTime=[ENDTIME]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/CreateMaintenanceTask?apikey=aaaaaabbbbbbccccccddddddeeeeee&taskMethod=daily&taskStartTime=20:00&taskEndTime=21:00&taskStatus=disable&taskEffectFrom=2010-05-24%2016:48&taskName=dr1&taskType=monitor&resourceid=10000055
```

#### Weekly停机计划
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/CreateMaintenanceTask?apikey=[APIKEY]&taskType=monitor&resourceid=[RESOURCEID]&totalNumber=[TOTALNUMBER]&taskMethod=weekly
```

#### Monthly停机计划
**支持的调度方式：**
- 按周调度（week）
- 按日期调度（date）

**语法（按周）：**
```
https://[HOST]:[PORT]/AppManager/xml/CreateMaintenanceTask?apikey=[APIKEY]&taskType=monitor&resourceid=[RESOURCEID]&totalNumber=[1-5]&taskMethod=monthly
```

#### Once停机计划
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/CreateMaintenanceTask?apikey=[APIKEY]&taskMethod=once&customTaskStartTime=[STARTTIME]&customTaskEndTime=[ENDTIME]
```

### DeleteMaintenanceTask
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/DeleteMaintenanceTask?apikey=[APIKEY]&taskid=[TASKID]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/DeleteMaintenanceTask?apikey=aaaaaabbbbbbccccccddddddeeeeee&taskid=10000001
```

### EditMaintenanceTask
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/EditMaintenanceTask?apikey=[APIKEY]&taskMethod=[TASKMETHOD]
```

### GetMaintenanceTaskDetails / ListMaintenanceTaskDetails
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListMaintenanceTaskDetails?apikey=[APIKEY]
```

**响应示例：**
```xml
<AppManager-response uri="/AppManager/xml/ListMaintenanceTaskDetails">
   <result>
       <response response-code="4000">
          <Schedules>
             <Schedule TASKNAME="Test_Weekly" TASKID="10000001" STATUS="RUNNING" OCCURENCE="Weekly">
                  <ScheduledTime STARTTIME="Monday 20:00" ENDTIME="Wednesday 20:00" />  
             </Schedule>
          </Schedules>
       </response>
   </result>
</AppManager-response>
```

---

## Monitor Group Operations APIs

### AddMonitorGroup
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/AddMonitorGroup?apikey=[apikey]&grouptype=[type]&name=[displayname]
```

**支持的组类型：**
- monitorgroup
- webappgroup

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/AddMonitorGroup?apikey=aaaaaabbbbbbccccccddddddeeeeee&grouptype=monitorgroup&name=Bob's+Blog
```

### DeleteMonitorGroup
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/group/delete?apikey=[apikey]&name=[groupname]
```

或使用resourceid：
```
https://[HOST]:[PORT]/AppManager/xml/group/delete?apikey=[apikey]&haid=[resourceid]
```

### 其他监控组操作
- **Add Sub-Group**: 添加子组
- **Associate Monitor to Monitor Group**: 将监控器关联到监控组
- **Delete Sub-Group**: 删除子组
- **Edit Monitor Group**: 编辑监控组
- **Get Group Availability**: 获取组可用性
- **Move Group**: 移动组
- **Disassociate Monitor from Monitor Group**: 从监控组取消关联监控器

---

## List Data APIs

### GetMonitorData
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/GetMonitorData?apikey=[APIKEY]&resourceid=[RESOURCEID]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/GetMonitorData?apikey=aaaaaabbbbbbccccccddddddeeeeee&resourceid=10000293
```

### ListAlarms
**支持的告警类型：**
- all（所有）
- critical（严重）
- warning（警告）
- clear（清除）

#### 列出所有最近告警
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListAlarms?apikey=[API_KEY]&type=all
```

#### 按严重性列出告警
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListAlarms?apikey=[API_KEY]&type=[critical/warning/clear]
```

#### 按时间过滤
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListAlarms?apikey=[API_KEY]&time=[Time]
```

#### 按监控器类型
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListAlarms?apikey=[API_KEY]&type=[Monitor_Type]
```

#### 按监控器资源ID
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListAlarms?apikey=[API_KEY]&resourceid=[resourceid]
```

**响应参数：**
| 参数 | 描述 |
|------|------|
| DISPLAYNAME | 监控器显示名称 |
| RESOURCEID | 监控器资源ID |
| HEALTHSEVERITY | 健康严重性（1-严重，4-警告，5-清除） |
| STATUS | 告警状态 |
| MESSAGE | 告警消息 |
| MODTIME | 告警生成时间 |
| TYPE | 监控器类型 |
| DetailsPageURL | 监控器详情页URL |

### ListMonitorGroups
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListMonitorGroups?apikey=[API_KEY]
```

**支持的参数：**
| 参数 | 描述 | 默认值 |
|------|------|-------|
| groupId | 监控组ID | - |
| groupName | 监控组名称 | - |
| outageReports | 是否包含故障报告 | true |
| severityDetails | 是否包含严重性详情 | true |
| treeview | 树形结构显示 | - |

### ListMonitor
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListMonitor?apikey=[API_KEY]&type=[TYPE]
```

#### 按监控器类型
```
https://[HOST]:[PORT]/AppManager/xml/ListMonitor?apikey=[API_KEY]&type=Windows
```

#### 按资源ID
```
https://[HOST]:[PORT]/AppManager/xml/ListMonitor?apikey=[API_KEY]&resourceid=[Resourceid]
```

#### 列出所有监控器
```
https://[HOST]:[PORT]/AppManager/xml/ListMonitor?apikey=[API_KEY]&type=all
```

### ListServer
**支持的查询方式：**
- 列出所有服务器详情
- 按特定服务器名称
- 按服务器IP地址

#### 列出所有服务器详情
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListServer?apikey=[API_KEY]&type=all
```

#### 按服务器名称
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListServer?apikey=[API_KEY]&type=[Server_ParentNode_Name]
```

#### 按IP地址
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ListServer?apikey=[API_KEY]&ipaddress=[IP_Address_of_server]
```

**响应参数：**
| 参数 | 描述 |
|------|------|
| Name | 服务器名称 |
| PARENTIP | 服务器父网络IP |
| RESOURCEID | 服务器资源ID |
| TYPE | 服务器类型 |
| DISPLAYNAME | 服务器显示名称 |
| IPADDRESS | IP地址 |

### ShowPolledData
**支持的周期：**
| 周期值 | 描述 |
|--------|------|
| 0 | 今天 |
| 3 | 昨天 |
| 6 | 本周 |
| -7 | 最近7天 |
| 12 | 上周 |
| 7 | 本月 |
| -30 | 最近30天 |
| 11 | 上月 |
| 9 | 本季度 |
| 8 | 本年 |
| 5 | 最近1年 |
| 20 | 所有轮询数据 |

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/ShowPolledData?apikey=[API_KEY]&resourceid=[RESOURCEID]&period=[PERIOD]
```

**自定义时间段：**
```
https://[HOST]:[PORT]/AppManager/xml/ShowPolledData?apikey=[API_KEY]&resourceid=[RESOURCEID]&period=4&startDate=[STARTDATE]&endDate=[ENDDATE]
```

---

## User Management APIs

### Create User
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/Users/create?apikey=[API_KEY]&userName=[USERNAME]&role=[ROLE]
```

**支持的用户角色：**
- OPERATOR
- MANAGER
- ADMIN
- USER
- DELEGATEDADMIN

**参数：**
| 参数 | 描述 | 是否必填 |
|------|------|---------|
| userName | 用户名 | 是 |
| role | 用户角色 | 是 |
| password | 密码 | 是 |
| email | 邮箱 | 是 |
| description | 描述 | 否 |
| groupId | 关联的监控组ID | 否 |
| groupName | 关联的监控组名称 | 否 |
| usergroupId | 关联的用户组ID | 否 |

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/Users/create?apikey=aaaaaabbbbbbccccccddddddeeeeee&userName=admin&role=MANAGER&password=appman&email=example@example.com
```

### Delete User
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/Users/delete?apikey=[API_KEY]&userId=[id]
```

或使用用户名：
```
https://[HOST]:[PORT]/AppManager/xml/Users/delete?apikey=[API_KEY]&userName=[name]
```

### 其他用户管理操作
- **Get All User Roles**: 获取所有用户角色
- **List User Details**: 列出用户详情
- **Update User**: 更新用户信息
- **Add UserGroup**: 添加用户组
- **Delete Usergroup**: 删除用户组
- **List Usergroups**: 列出用户组
- **Update Usergroups**: 更新用户组

---

## Perform Operation APIs

### DeleteMonitor
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/DeleteMonitor?apikey=[APIKEY]&resourceid=[RESOURCEID]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/DeleteMonitor?apikey=aaaaaabbbbbbccccccddddddeeeeee&resourceid=10000032
```

**删除多个监控器：**
```
https://apm-prod-server:8443/AppManager/xml/DeleteMonitor?apikey=aaaaaabbbbbbccccccddddddeeeeee&resourceid=10000032,10000033,10000034
```

### Ping
**支持的查询方式：**
- 按资源ID
- 按主机名

**语法（按资源ID）：**
```
https://[HOST]:[PORT]/AppManager/xml/Ping?apikey=[API_KEY]&resourceid=[RESOURCE_ID]
```

**语法（按主机名）：**
```
https://[HOST]:[PORT]/AppManager/json/Ping?apikey=[API_KEY]&host=[HOSTNAME]
```

**响应参数：**
| 参数 | 描述 |
|------|------|
| Output | Ping操作输出 |
| Host | 主机名 |
| IPAddress | IP地址 |

### PollNow
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/PollNow?apikey=[APIKEY]&resourceid=[RESOURCEID]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/PollNow?apikey=aaaaaabbbbbbccccccddddddeeeeee&resourceid=10000293
```

### 其他操作
- **Alarm Actions**: 告警动作
- **Apply License**: 应用许可证
- **Configure Mail Server**: 配置邮件服务器
- **Configure Proxy Server**: 配置代理服务器
- **Configure SMS Server**: 配置SMS服务器
- **Enable / Disable Actions**: 启用/禁用动作
- **Execute Action**: 执行动作
- **Manage**: 管理
- **UnManage**: 取消管理
- **UnManage and Reset Status**: 取消管理并重置状态
- **Delete Downtime**: 删除停机时间
- **Probe Server Down Email Alert**: 探针服务器停机邮件告警
- **Fetch Data**: 获取数据

---

## Admin Activities APIs

### Credential Manager APIs

#### 添加凭证

##### Telnet凭证
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=Telnet&credentialName=[NAME]&username=[USERNAME]&prompt=[PROMPT]&password=[PASSWORD]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/credential?apikey=aaaaaabbbbbbccccccddddddeeeeee&type=Telnet&credentialName=Telnet&username=admin&prompt=$&password=appman
```

##### SNMP v1/v2凭证
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=SNMP v1v2&credentialName=[NAME]&snmpCommunityString=[COMMUNITY_STRING]&timeout=[MINUTES]
```

##### SNMP v3凭证
**支持的认证协议：**
- MD5
- SHA

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=SNMP v3&credentialName=[NAME]&snmpAuthProtocol=[AUTH_PROTOCOL]
```

##### SSH凭证
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=SSH&credentialName=[NAME]&username=[USERNAME]&password=[PASSWORD]
```

##### WMI凭证
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=WMI&credentialName=[NAME]&username=[USERNAME]&password=[PASSWORD]
```

##### 数据库凭证

**DB2凭证：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=DB2&credentialName=[NAME]&username=[USERNAME]&password=[PASSWORD]&instance=[DB_NAME]
```

**MS SQL凭证：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=MS SQL&credentialName=[NAME]&username=[USERNAME]&authType=[SQL/Windows]
```

**MySQL凭证：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=MySQL&credentialName=[NAME]&username=[USERNAME]&password=[PASSWORD]
```

**Oracle凭证：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=Oracle&credentialName=[NAME]&username=[USERNAME]&password=[PASSWORD]
```

**PostgreSQL凭证：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=PostgreSQL&credentialName=[NAME]&UserName=[USERNAME]&Password=[PASSWORD]
```

##### Redis凭证
**支持的认证类型：**
- DefaultAuth
- ACLAuth

**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=Redis&credentialName=[NAME]&AuthenticationType=[AUTH_TYPE]
```

##### 其他凭证类型
- **MongoDB**
- **Cassandra**
- **Apache Server**
- **Tomcat Server**
- **WebLogic Server**
- **WebSphere Server**
- **GlassFish**
- **JBoss Server**
- **VMware ESX/ESXi**
- **RabbitMQ**
- **Microsoft MQ (MSMQ)**
- **LDAP**
- **Mail Server**
- **SAP Server**
- **SAP Business One**
- **RBM (Real Browser Monitoring)**

#### 编辑/更新凭证
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&credentialID=[CREDENTIAL_ID]
```

**示例：**
```
http://app-windows:59090/AppManager/xml/credential?apikey=aaaaaabbbbbbccccccddddddeeeeee&credentialID=10&password=newpassword
```

#### 删除凭证
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential?apikey=[APIKEY]&type=[TYPE]&credentialID=[CREDENTIAL_ID]&TO_DELETE=true
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/credential?apikey=aaaaaabbbbbbccccccddddddeeeeee&credentialID=10&TO_DELETE=true
```

#### 列出凭证
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/credential/list?apikey=[APIKEY]&type=[TYPE]
```

**示例：**
```
https://apm-prod-server:8443/AppManager/xml/credential/list?apikey=aaaaaabbbbbbccccccddddddeeeeee&type=all
```

### 其他管理活动
- **REST APIs for Enterprise Edition**: 企业版REST API
- **Business Hours**: 营业时间配置
- **Configure Alarms**: 配置告警
- **Domain Configuration**: 域配置
- **Email Action Configuration**: 邮件动作配置
- **Event Log Configuration**: 事件日志配置
- **Mail Server Configuration**: 邮件服务器配置
- **Threshold configuration**: 阈值配置
- **List and Map Dependencies**: 列出和映射依赖关系
- **Rest API for generating alarms**: 生成告警的REST API
- **SNMP Trap Listener**: SNMP陷阱监听器

---

## Processes and Services APIs

### Processes

#### Add Process
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/process/add?apikey=[API_Key]&resourceid=[Server_ResourceID]&name=[Process_Name]
```

**参数：**
| 参数 | 描述 |
|------|------|
| resourceid | 服务器资源ID |
| name | 要添加的进程名称 |
| command | 进程运行的命令路径 |
| displayname | 进程的显示名称 |
| matchcriteria | 匹配条件（默认：Contains） |

#### Delete Process
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/process/delete?apikey=[APIKey]&monitorid=[resid]&processid=[Processid]
```

#### Edit Process
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/process/edit?apikey=[APIKey]&type=0&processid=[Processid]&name=[pname]
```

### Services

#### Add Service
**语法：**
```
https://[HOST]:[PORT]/AppManager/xml/service/add?apikey=[API_Key]&resourceid=[Server_ResourceID]&name=[Service_Name]
```

**参数：**
| 参数 | 描述 |
|------|------|
| resourceid | 服务器资源ID |
| name | 要添加的服务名称 |
| displayname | 服务的显示名称 |
| matchcriteria | 匹配条件（默认：Contains） |

---

## Error Handling

### 常见错误代码

| 错误代码 | 描述 |
|---------|------|
| 4000 | 操作成功完成 |
| 4002 | 请求URI中的resourceid应为整数 |
| 4003 | 请求URI中的resourceid错误 |
| 4004 | 请求中的apikey无效 |
| 4005 | 请求URI中的类型错误 |
| 4006 | URL中的ResoureID错误或重复 |
| 4007 | 请求URI中的monitorname错误 |
| 4008 | 请求URI不正确 |
| 4016 | 请求URI中的方法不正确 |
| 4024 | URL中的taskid错误 |
| 4025 | URL中的taskname已存在或为空 |
| 4032 | 请求URI中的参数不正确 |
| 4033 | taskName不能为空 |
| 4034 | taskName已存在 |
| 4035 | taskStatus应为enable或disable |
| 4036 | taskType应为group或monitor |
| 4040 | DestinationAddress、DestinationPort、GlobalTrap对于v1陷阱是必需的 |
| 4105 | 调用REST API时发生未知问题 |
| 4128 | 处理请求时服务器错误 |
| 4201 | pollInterval应为有效的整数 |
| 4202 | 类型不能为空 |
| 4203 | groupID应为有效的整数 |
| 4204 | WSDLUrl不能为空 |
| 4205 | emailid字段不能为空 |
| 4206 | 请求URL中的用户名和密码不能为空 |

### 错误响应格式

```xml
<Apm-response uri="/AppManager/xml/AddMonitor">
   <result>
      <response response-code="4004">
         <message>The specified apikey in the request is invalid.</message>
      </response>      
   </result>
</Apm-response>
```

---

## 附录

### 通用参数说明

| 参数 | 描述 | 是否必填 |
|------|------|---------|
| apikey | API密钥 | 是 |
| host | 主机名/IP地址 | 根据API类型 |
| port | 端口号 | 根据API类型 |
| username | 用户名 | 根据API类型 |
| password | 密码 | 根据API类型 |
| type | 监控器类型 | 是 |
| displayname | 显示名称 | 是 |
| resourceid | 资源ID | 根据API类型 |
| pollInterval | 轮询间隔（分钟） | 否 |

### 监控器类型值

| 类别 | 类型值 |
|------|-------|
| 服务器 | servers |
| Windows | Windows 2000/2003/2008/2012/2016/2019 |
| Linux | Linux |
| Apache | Apache Server |
| Tomcat | tomcat server |
| WebLogic | WEBLOGIC SERVER |
| WebSphere | websphere server |
| JBoss | JBoss server |
| MS SQL | MS SQL |
| MySQL | mysql |
| Oracle | oracle |
| PostgreSQL | PostgreSQL |
| Exchange Server | Exchange Server |
| Mail Server | Mail Server |
| DNS Monitor | DNSMonitor |
| URL Monitor | UrlMonitor |
| Ping Monitor | Ping Monitor |
| SSL/TLS Certificate | SSLCertificateMonitor |
| vCenter | vCenter |
| VMware ESX/ESXi | VMware ESX/ESXi |
| Hyper-V | Hyper-V Server |
| Docker | Docker |
| Kubernetes | Kubernetes |
| Amazon | Amazon |
| Azure | MicrosoftAzure |
| Office365 | Office365 |
| GCP | GoogleCloudPlatform |
| Oracle Cloud | OracleCloud |

---

## 使用建议

1. **认证安全**：
   - 使用HTTPS而非HTTP
   - 定期轮换API密钥
   - 不要在代码中硬编码API密钥

2. **API调用限制**：
   - 遵守每分钟1000次调用的限制
   - 使用批量操作减少调用次数
   - 实现重试机制处理临时错误

3. **错误处理**：
   - 始终检查响应代码
   - 实现适当的重试逻辑
   - 记录错误日志以便排查问题

4. **性能考虑**：
   - 使用适当的轮询间隔
   - 批量获取数据而非单个查询
   - 缓存不频繁变化的数据

---

## 官方文档链接

- **官方文档**：https://www.manageengine.com/products/applications_manager/help/
- **REST API文档**：https://www.manageengine.com/products/applications_manager/help/rest-apis.html
- **V1 REST APIs**：https://www.manageengine.com/products/applications_manager/help/v1-rest-apis.html
- **添加监控器API**：https://www.manageengine.com/products/applications_manager/help/addmonitor-api.html

---

**文档版本**: 2026-02-11  
**最后更新**: 2026-02-11
