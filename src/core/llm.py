"""
LLM streaming logic: _split_think, stream_llm.
"""


def split_think(raw: str) -> "tuple[str, str]":
    """Split <think>…</think> reasoning from the visible answer."""
    if "<think>" not in raw:
        return "", raw
    before, after = raw.split("<think>", 1)
    if "</think>" in after:
        reasoning, tail = after.split("</think>", 1)
        return reasoning, (before + tail)
    return after, before


def stream_llm(client, model_name: str, messages: list, tools_schema: list, stream_obj) -> "tuple[str, dict, object]":
    """
    Stream one LLM turn.
    Returns (answer_text, tool_calls_by_index, usage).
    stream_obj must have: set_reasoning, set_answer, add_tool_pending, set_usage.
    """
    from src.ui.output import print_error

    api_messages = [{k: v for k, v in m.items() if k != "_skill"} for m in messages]

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=api_messages,
            tools=tools_schema,
            tool_choice="auto",
            stream=True,
            stream_options={"include_usage": True},
        )
    except Exception as e:
        print_error(f"Erro ao conectar: {e}")
        return "", {}, None

    raw_content   = ""
    reasoning_acc = ""
    answer        = ""
    tool_calls_acc: dict[int, dict] = {}
    usage = None

    try:
        for chunk in response:
            if not chunk.choices:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                continue

            delta = chunk.choices[0].delta

            rc = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if rc:
                reasoning_acc += rc

            if delta.content:
                raw_content += delta.content

            think_part, answer = split_think(raw_content)
            combined = reasoning_acc + think_part
            if combined:
                stream_obj.set_reasoning(combined)
            stream_obj.set_answer(answer)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_acc[idx]["name"] += tc.function.name
                            stream_obj.add_tool_pending(tc.function.name)
                        if tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

            if getattr(chunk, "usage", None):
                usage = chunk.usage

    except Exception as e:
        print_error(f"Erro no streaming: {e}")

    if usage:
        stream_obj.set_usage(usage.prompt_tokens, usage.completion_tokens)

    full_reasoning = reasoning_acc + (split_think(raw_content)[0] if "<think>" in raw_content else "")
    return answer, tool_calls_acc, usage, full_reasoning


__all__ = ["split_think", "stream_llm"]
