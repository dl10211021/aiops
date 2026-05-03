from __future__ import annotations

import json
import re
from typing import Any


def classify_platform_actions(tool_call_name: str, args: dict[str, Any]) -> list[str]:
    method = str(args.get("method") or "GET").upper()
    path = str(args.get("path") or "").lower()
    body_text = json.dumps(args.get("body") or {}, ensure_ascii=False).lower()
    actions: list[str] = []

    if tool_call_name == "k8s_api_request":
        if method == "DELETE" and re.search(r"/namespaces/[^/]+/?$", path):
            actions.append("k8s.delete_namespace")
        if method in {"PATCH", "PUT", "POST"} and "deployments" in path and ("scale" in path or "replicas" in body_text):
            actions.append("k8s.scale_deployment")
        if method == "DELETE" and "/pods/" in path:
            actions.append("k8s.delete_pod")
        if method == "DELETE" and "/secrets/" in path:
            actions.append("k8s.delete_secret")
        if method in {"PATCH", "PUT", "POST"} and ("secrets" in path or "rbac" in path):
            actions.append("k8s.modify_sensitive_resource")

    if tool_call_name == "virtualization_api_request":
        if method == "DELETE" and any(token in path for token in ("vm", "server", "instance")):
            actions.append("virtualization.delete_vm")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("reboot", "restart", "reset")):
            actions.append("virtualization.reboot_vm")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("migrate", "relocate")):
            actions.append("virtualization.migrate_vm")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("snapshot", "rollback", "revert")):
            actions.append("virtualization.snapshot_or_rollback")
            actions.append("virtualization.rollback_snapshot")

    if tool_call_name == "middleware_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"reload_config", "restart_service"} or any(token in path for token in ("reload", "restart")):
            actions.append("middleware.reload_config")
        if operation in {"publish_config", "update_config"} or (
            "nacos" in path and method in {"POST", "PUT", "PATCH"} and "config" in path
        ):
            actions.append("nacos.publish_config")
        if operation in {"delete_topic", "remove_topic"} or (method == "DELETE" and "topic" in path):
            actions.append("kafka.delete_topic")

    if tool_call_name == "bigdata_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"kill_application", "cancel_job", "stop_job"} or any(
            token in path for token in ("kill", "cancel", "stop")
        ):
            actions.append("yarn.kill_application")
        if operation in {"drop_partition", "delete_partition"} or (method == "DELETE" and "partition" in path):
            actions.append("bigdata.delete_partition")

    if tool_call_name == "cicd_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"deploy_prod", "release_prod"} or (
            "prod" in path and any(token in path for token in ("deploy", "release", "build"))
        ):
            actions.append("cicd.deploy_prod")
        if operation in {"rollback", "app_rollback"} or "rollback" in path:
            actions.append("argocd.rollback")
        if operation in {"delete_artifact", "delete_release"} or (
            method == "DELETE" and any(token in path for token in ("artifact", "repository", "release"))
        ):
            actions.append("artifact.delete_release")

    if tool_call_name == "ai_platform_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"stop_training_job", "kill_job"} or any(token in path for token in ("stop", "kill", "cancel")):
            actions.append("ai.stop_training_job")
        if operation in {"release_gpu", "free_gpu"} or ("gpu" in path and method in {"POST", "PUT", "PATCH", "DELETE"}):
            actions.append("ai.release_gpu")
        if operation in {"delete_model_version", "delete_model"} or (
            method == "DELETE" and any(token in path for token in ("model", "version"))
        ):
            actions.append("mlflow.delete_model_version")

    if tool_call_name == "storage_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"download_object", "get_object"}:
            actions.append("s3.download_object")
        if operation in {"delete_bucket", "remove_bucket"}:
            actions.append("s3.delete_bucket")
        if operation in {"delete_object", "remove_object"}:
            actions.append("s3.delete_object")
        if operation in {"put_bucket_policy", "put_bucket_acl", "put_public_access_block"}:
            actions.append("s3.change_bucket_policy")
            if "public" in operation or "public" in body_text:
                actions.append("s3.public_bucket")
        is_bucket_root = path.count("/") <= 1 and bool(path.strip("/"))
        object_path_parts = [part for part in path.split("?", 1)[0].split("/") if part]
        if method == "GET" and len(object_path_parts) >= 2 and "list-type" not in path:
            actions.append("s3.download_object")
        if method == "DELETE" and is_bucket_root:
            actions.append("s3.delete_bucket")
        if method == "DELETE" and not is_bucket_root:
            actions.append("s3.delete_object")
        if method in {"PUT", "PATCH", "POST"} and any(token in path for token in ("policy", "acl", "publicaccessblock")):
            actions.append("s3.change_bucket_policy")
            if "public" in body_text or "publicaccessblock" in path:
                actions.append("s3.public_bucket")

    if tool_call_name == "monitoring_api_query":
        if method == "POST" and "silence" in path:
            actions.append("monitoring.create_silence")
            actions.append("alertmanager.create_silence")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("ruler", "rules", "alert")):
            actions.append("monitoring.modify_rule")
            actions.append("monitoring.update_rule")
        if method == "DELETE" and any(token in path for token in ("ruler", "rules", "alert")):
            actions.append("monitoring.delete_rule")

    return actions
