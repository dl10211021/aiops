import json
from core.llm_factory import get_client_for_model


def _convert_openai_tools_to_anthropic(openai_tools):
    anthropic_tools = []
    for t in openai_tools:
        func = t.get("function", {})
        anthropic_tools.append(
            {
                "name": func.get("name"),
                "description": func.get("description", ""),
                "input_schema": func.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
        )
    return anthropic_tools


def _convert_openai_messages_to_anthropic(messages):
    anthropic_messages = []
    system_prompt = None

    for msg in messages:
        if msg.get("role") == "system":
            if not system_prompt:
                system_prompt = msg.get("content")
            else:
                system_prompt += "\n" + msg.get("content", "")
            continue

        role = msg.get("role")
        content = msg.get("content") or ""

        if role == "assistant":
            blocks = []
            if content:
                blocks.append({"type": "text", "text": content})

            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except Exception:
                    args = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id"),
                        "name": func.get("name"),
                        "input": args,
                    }
                )

            if not blocks:
                blocks.append({"type": "text", "text": ""})

            anthropic_messages.append({"role": "assistant", "content": blocks})

        elif role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": msg.get("tool_call_id"),
                "content": str(content),
            }
            if anthropic_messages and anthropic_messages[-1]["role"] == "user":
                prev_content = anthropic_messages[-1]["content"]
                if isinstance(prev_content, list):
                    prev_content.append(block)
                else:
                    anthropic_messages[-1]["content"] = [
                        {"type": "text", "text": prev_content},
                        block,
                    ]
            else:
                anthropic_messages.append({"role": "user", "content": [block]})

        elif role == "user":
            anthropic_messages.append({"role": "user", "content": content})

    return system_prompt, anthropic_messages


async def execute_chat_stream(
    model_name: str, messages: list, thinking_mode: str = "off", tools: list = None
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

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Add reasoning_effort for o1/o3-mini
        if is_thinking_requested and (
            "o1" in actual_model_name or "o3-mini" in actual_model_name
        ):
            kwargs["reasoning_effort"] = thinking_mode

        response = await client.chat.completions.create(**kwargs)
        tool_calls_dict = {}

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

            tool_calls = getattr(delta, "tool_calls", None)
            if tool_calls:
                for tc in tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        tool_calls_dict[idx] = {
                            "id": tc.id or "",
                            "function": {"name": "", "arguments": ""},
                        }
                    else:
                        if getattr(tc, "id", None):
                            tool_calls_dict[idx]["id"] = tc.id

                    if getattr(tc, "function", None):
                        if getattr(tc.function, "name", None):
                            tool_calls_dict[idx]["function"]["name"] += tc.function.name
                        if getattr(tc.function, "arguments", None):
                            tool_calls_dict[idx]["function"]["arguments"] += (
                                tc.function.arguments
                            )

        if tool_calls_dict:
            final_tcs = [
                {"id": v["id"], "type": "function", "function": v["function"]}
                for k, v in sorted(tool_calls_dict.items())
            ]
            yield {"type": "tool_calls", "tool_calls": final_tcs}

    elif protocol == "anthropic":
        system_prompt, anthropic_messages = _convert_openai_messages_to_anthropic(
            messages
        )

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

        if tools:
            kwargs["tools"] = _convert_openai_tools_to_anthropic(tools)

        tool_calls_dict = {}

        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    delta_type = event.delta.type
                    if delta_type == "text_delta":
                        yield {"type": "content", "content": event.delta.text}
                    elif delta_type == "thinking_delta":
                        yield {"type": "thinking", "content": event.delta.thinking}
                    elif delta_type == "input_json_delta":
                        idx = event.index
                        if idx in tool_calls_dict:
                            tool_calls_dict[idx]["function"]["arguments"] += (
                                event.delta.partial_json
                            )
                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        idx = event.index
                        tool_calls_dict[idx] = {
                            "id": event.content_block.id,
                            "function": {
                                "name": event.content_block.name,
                                "arguments": "",
                            },
                        }

        if tool_calls_dict:
            final_tcs = [
                {"id": v["id"], "type": "function", "function": v["function"]}
                for k, v in sorted(tool_calls_dict.items())
            ]
            yield {"type": "tool_calls", "tool_calls": final_tcs}
