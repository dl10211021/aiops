from core.llm_factory import get_client_for_model


async def execute_chat_stream(
    model_name: str, messages: list, thinking_mode: str = "off"
):
    client, config = get_client_for_model(model_name)
    protocol = config.get("protocol")
    actual_model_name = config.get("model", model_name)
    supports_thinking = config.get("supports_thinking", False)

    is_thinking_requested = thinking_mode in ["low", "medium", "high"]

    if protocol == "openai":
        kwargs = {
            "model": actual_model_name,
            "messages": messages,
            "stream": True,
        }

        # Add reasoning_effort for o1/o3-mini
        if is_thinking_requested and (
            "o1" in actual_model_name or "o3-mini" in actual_model_name
        ):
            kwargs["reasoning_effort"] = thinking_mode

        response = await client.chat.completions.create(**kwargs)

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            reasoning_content = getattr(delta, "reasoning_content", None)
            if reasoning_content:
                yield {"type": "thinking", "content": reasoning_content}

            content = getattr(delta, "content", None)
            if content:
                yield {"type": "content", "content": content}

    elif protocol == "anthropic":
        # Extract system prompt if present
        system_prompt = None
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content")
            else:
                anthropic_messages.append(msg)

        kwargs = {
            "model": actual_model_name,
            "messages": anthropic_messages,
            "max_tokens": 8192,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if supports_thinking and is_thinking_requested:
            budget_map = {"low": 1024, "medium": 4096, "high": 8000}
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget_map[thinking_mode],
            }
            kwargs["temperature"] = 1.0

        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    delta_type = event.delta.type
                    if delta_type == "text_delta":
                        yield {"type": "content", "content": event.delta.text}
                    elif delta_type == "thinking_delta":
                        yield {"type": "thinking", "content": event.delta.thinking}
