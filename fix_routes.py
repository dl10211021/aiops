import re

with open('api/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add back LLMConfigRequest
if 'class LLMConfigRequest' not in content:
    content = content.replace('class EmbeddingConfigRequest(BaseModel):', '''class LLMConfigRequest(BaseModel):
    base_url: str
    api_key: str

class EmbeddingConfigRequest(BaseModel):''')

# Add back update_llm_config route and get_llm_config route
if 'def update_llm_config' not in content:
    content = content.replace('class EmbeddingConfigRequest(BaseModel):', '''@router.get("/config/llm", response_model=ResponseModel)
async def get_llm_config():
    import os
    from core.memory import memory_db

    # Look up environment variables first
    base_url = os.getenv("OPENAI_BASE_URL", "")
    api_key = os.getenv("OPENAI_API_KEY", "")

    return ResponseModel(
        status="success", data={"base_url": base_url, "api_key": "********" if api_key else ""}
    )


@router.post("/config/llm", response_model=ResponseModel)
async def update_llm_config(req: LLMConfigRequest):
    """前端动态覆盖大模型底层的 Base_URL 和 Key (作为自定义 OpenAI 模型)"""
    import os
    
    try:
        # 将配置持久化到 .env 文件中
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        keys_to_filter = ["OPENAI_API_KEY=", "OPENAI_BASE_URL="]
        env_lines = [
            line
            for line in env_lines
            if not any(line.startswith(k) for k in keys_to_filter)
        ]

        env_lines.append(f"OPENAI_BASE_URL={req.base_url}\n")
        env_lines.append(f"OPENAI_API_KEY={req.api_key}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)
            
        # Update OS env right away
        os.environ["OPENAI_BASE_URL"] = req.base_url
        os.environ["OPENAI_API_KEY"] = req.api_key

        return ResponseModel(
            status="success", message="AI 大脑已重新连接，并已保存为默认配置"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EmbeddingConfigRequest(BaseModel):''')

with open('api/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
