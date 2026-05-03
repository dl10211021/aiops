from __future__ import annotations

from typing import Any


def models_response_kwargs(models: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"models": models},
    }


def llm_config_response_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": config,
    }


def agent_runtime_config_response_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"config": config},
    }


def agent_runtime_config_saved_response_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"config": config},
        "message": "Agent 执行保护配置已保存",
    }


def embedding_config_saved_response_kwargs(model: str, dim: int) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"Embedding 配置已更新: model={model}, dim={dim}",
    }


def providers_response_kwargs(providers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"providers": providers},
    }


def providers_saved_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "供应商配置已保存",
    }


def safety_policy_response_kwargs(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"policy": policy},
    }


def safety_policy_saved_response_kwargs(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "安全策略已保存",
        "data": {"policy": policy},
    }


def safety_policy_test_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"result": result},
    }
