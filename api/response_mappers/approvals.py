from __future__ import annotations

from typing import Any


def user_interaction_submitted_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "交互输入已提交。",
    }


def approval_requests_response_kwargs(approvals: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"approvals": approvals},
    }


def approval_audit_summary_response_kwargs(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"summary": summary},
    }


def approval_request_response_kwargs(approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"approval": approval},
    }


def approval_decision_response_kwargs(approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "审批已处理",
        "data": {"approval": approval},
    }


def approval_execution_response_kwargs(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "message": result.message,
        "data": {
            "approval": result.approval,
            "result": result.result,
        },
    }


def tool_approval_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    response = {
        "status": "success",
        "message": result["message"],
    }
    if result["include_approval"]:
        response["data"] = {"approval": result["approval"]}
    return response
