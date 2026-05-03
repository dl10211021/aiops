from __future__ import annotations

from typing import Any


def protocol_verification_overview_response_kwargs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }


def asset_verification_matrix_response_kwargs(matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"matrix": matrix},
    }


def asset_verification_run_response_kwargs(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"run": run},
    }


def asset_verification_runs_response_kwargs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"runs": runs},
    }
