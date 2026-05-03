import asyncio

from fastapi import APIRouter, HTTPException

from api.errors import raise_http_error
from api.response_mappers.config import (
    agent_runtime_config_response_kwargs,
    agent_runtime_config_saved_response_kwargs,
    embedding_config_saved_response_kwargs,
    llm_config_response_kwargs,
    models_response_kwargs,
    providers_response_kwargs,
    providers_saved_response_kwargs,
    safety_policy_response_kwargs,
    safety_policy_saved_response_kwargs,
    safety_policy_test_response_kwargs,
)
from api.schema_models.common import ResponseModel
from api.schema_models.config import (
    AgentRuntimeConfigRequest,
    EmbeddingConfigRequest,
    ProviderConfig,
    SafetyPolicyTestRequest,
    SafetyPolicyUpdateRequest,
)
from core.app_config_service import (
    AppConfigServiceError,
    build_llm_config_payload,
    get_agent_runtime_config_record,
    get_embedding_config_record,
    save_agent_runtime_config_record,
    save_embedding_config_record,
)
from core.model_catalog_service import fetch_model_catalog
from core.provider_config_service import (
    ProviderConfigServiceError,
    list_provider_config_records,
    save_provider_config_records,
)
from core.safety_policy_service import (
    SafetyPolicyServiceError,
    explain_safety_policy_test,
    get_safety_policy_record,
    save_safety_policy_record,
)


router = APIRouter()


@router.get("/models", response_model=ResponseModel)
async def get_models(provider_id: str | None = None, refresh: bool = False):
    models = await fetch_model_catalog(provider_id=provider_id, refresh=refresh)
    if models:
        return ResponseModel(**models_response_kwargs(models))
    raise HTTPException(status_code=502, detail="Cannot fetch models.")


@router.get("/config/llm", response_model=ResponseModel)
async def get_llm_config():
    """【新功能】获取当前大模型配置"""
    return ResponseModel(**llm_config_response_kwargs(build_llm_config_payload()))


@router.get("/config/agent-runtime", response_model=ResponseModel)
async def get_agent_runtime_config_endpoint():
    return ResponseModel(
        **agent_runtime_config_response_kwargs(get_agent_runtime_config_record())
    )


@router.post("/config/agent-runtime", response_model=ResponseModel)
async def update_agent_runtime_config_endpoint(req: AgentRuntimeConfigRequest):
    try:
        config = save_agent_runtime_config_record(req.chat_max_steps, req.headless_max_steps)
    except AppConfigServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**agent_runtime_config_saved_response_kwargs(config))


@router.get("/config/embedding")
async def get_embedding_config_endpoint():
    return {"status": "success", "data": get_embedding_config_record()}


@router.post("/config/embedding", response_model=ResponseModel)
async def update_embedding_config_endpoint(req: EmbeddingConfigRequest):
    try:
        save_embedding_config_record(req.model, req.dim)
        return ResponseModel(**embedding_config_saved_response_kwargs(req.model, req.dim))
    except AppConfigServiceError as exc:
        raise_http_error(exc)


@router.get("/config/providers", response_model=ResponseModel)
async def get_providers_endpoint():
    providers = await asyncio.to_thread(list_provider_config_records)
    return ResponseModel(**providers_response_kwargs(providers))


@router.post("/config/providers", response_model=ResponseModel)
async def update_providers_endpoint(req: list[ProviderConfig]):
    try:
        await asyncio.to_thread(save_provider_config_records, [p.model_dump() for p in req])
    except ProviderConfigServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**providers_saved_response_kwargs())


@router.get("/config/safety-policy", response_model=ResponseModel)
async def get_safety_policy_endpoint():
    return ResponseModel(**safety_policy_response_kwargs(get_safety_policy_record()))


@router.post("/config/safety-policy", response_model=ResponseModel)
async def update_safety_policy_endpoint(req: SafetyPolicyUpdateRequest):
    try:
        policy = save_safety_policy_record(req.policy)
    except SafetyPolicyServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**safety_policy_saved_response_kwargs(policy))


@router.post("/config/safety-policy/test", response_model=ResponseModel)
async def test_safety_policy_endpoint(req: SafetyPolicyTestRequest):
    result = explain_safety_policy_test(req)
    return ResponseModel(**safety_policy_test_response_kwargs(result))
