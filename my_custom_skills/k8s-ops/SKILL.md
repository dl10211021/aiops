---
name: k8s-ops
description: Kubernetes 运维与故障排查专家技能，提供 Pod 诊断、资源管理与集群监控的标准操作指南。
---

# Kubernetes Operations Skill

当用户要求进行 Kubernetes 集群相关的操作、排障或巡检时，请遵循以下指令。

## 核心工作流 (Troubleshooting Workflow)
在进行 K8s 故障排查时，请按以下标准化步骤进行操作：
1. **确认上下文**：在执行命令前，主动确认所在的 Namespace（如未指明，默认添加 `-n <namespace>` 或 `--all-namespaces` 进行探查）。
2. **检查状态与事件**：
   - 优先使用 `kubectl get pods -n <namespace> -o wide` 查看全局状态。
   - 使用 `kubectl get events -n <namespace> --sort-by='.metadata.creationTimestamp'` 查看近期异常事件。
3. **深入分析**：
   - 使用 `kubectl describe pod <pod-name> -n <namespace>` 查看 Pod 调度状态和报错信息。
   - 使用 `kubectl logs <pod-name> -n <namespace> --tail=200` (如果包含多个 container，请指定 `-c <container-name>`) 获取报错日志。
4. **资源与网络检查**：
   - 检查节点资源耗尽情况：`kubectl top nodes` / `kubectl top pods`。
   - 检查网络连通性：`kubectl get svc,ep -n <namespace>`。

## 安全与规范指南 (Guidelines)
- **只读优先**：默认情况下只进行 `get`, `describe`, `logs`, `top` 等只读探查操作。
- **高危操作确认**：在执行 `kubectl delete`, `kubectl scale`, `kubectl apply`, `kubectl edit` 前，必须先输出预检结果，并向用户明确声明风险，要求用户确认。
- **YAML 优先**：如果需要创建或修改资源，优先生成标准 YAML 内容并向用户展示，不要直接使用不可追溯的 imperative 命令（如 `kubectl run` 或 `kubectl expose`）。
- **精准输出**：过滤掉冗长的无用输出。结合 `grep` 或 JSONPath (如 `-o jsonpath="..."`) 精确获取需要的信息。

## 常用进阶诊断命令参考
- 查找 CrashLoopBackOff 的前序日志：`kubectl logs <pod-name> -n <ns> --previous`
- 检查证书过期情况：`kubeadm certs check-expiration` (需 Master 节点权限)
- 快速查看节点状态异常：`kubectl get nodes | grep -v Ready`
