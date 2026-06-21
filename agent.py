import os
import traceback
from dotenv import load_dotenv
from openai import OpenAI

from src.core.system_prompt import SYSTEM_PROMPT
from src.core.llm import stream_llm
from src.core.executor import execute_tool, expand_at_mentions
from src.commands.slash import handle_slash_command
from src.tools import AVAILABLE_TOOLS, get_tools_schema
from src.skills.manager import list_skills, print_skills_hint
from src.session.store import save_current_session, has_current_session
from src.core.session_manager import SessionManager
from src.core.filesystem_context import FileSystemContext
from src.core.tool_validator import ToolValidator
from src.core.fallback_parser import FallbackParser
from src.core.logger import InteractionLogger
from src.core.context_summarizer import generate_session_summary, summarize_with_llm

try:
    from input_queue import get_global_capture as _get_global_capture
except ImportError:
    _get_global_capture = None  # type: ignore

from ui import (
    console,
    print_header,
    print_user_message,
    get_user_input,
    print_session_stats,
    print_system_message,
    AgentStream,
    AgentMode,
    get_mode,
    prompt_plan_approval,
    GOLD, MUTED, DIMC,
)

load_dotenv(override=True)

LM_STUDIO_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
MODEL_NAME    = os.getenv("MODEL_NAME", "gemma-2b-it")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
    base_url=LM_STUDIO_URL,
)

session_manager = SessionManager()
fs_context      = FileSystemContext()
validator       = ToolValidator(cwd=os.getcwd())
fallback_parser = FallbackParser(cwd=os.getcwd())
logger          = InteractionLogger()

tools_schema = get_tools_schema()


def run_agent_loop():
    print_header(MODEL_NAME, LM_STUDIO_URL)

    if has_current_session():
        console.print(
            f"  [{GOLD}]◈[/{GOLD}]  [{MUTED}]Sessão anterior encontrada  ·  [/{MUTED}]"
            f"[{GOLD}]/resume[/{GOLD}] [{MUTED}]para continuar  ·  [/{MUTED}]"
            f"[{GOLD}]/resume lista[/{GOLD}] [{MUTED}]para ver todas[/{MUTED}]"
        )
        console.print()

    print_skills_hint(list_skills())

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    input_queue: list[str] = []

    while True:
        # ── Para a captura antes do prompt_toolkit assumir o teclado ────────
        if _get_global_capture:
            cap = _get_global_capture()
            if cap and cap._active:
                cap.stop()

        # ── Pull from queue first, else prompt user ──────────────────────────
        if input_queue:
            user_msg = input_queue.pop(0)
            remaining = len(input_queue)
            suffix = f" ({remaining} restante{'s' if remaining != 1 else ''} na fila)" if remaining else ""
            print_system_message(f"Processando mensagem da fila{suffix}...")
            print_user_message(user_msg)
        else:
            user_msg = get_user_input()

        if user_msg.strip().lower() in {"exit", "quit", "sair", "q"}:
            print_session_stats()
            break
        if not user_msg.strip():
            continue

        # ── Slash command detection ──────────────────────────────────────────
        stripped = user_msg.strip()
        if stripped.startswith("/"):
            parts = stripped.split(None, 1)
            cmd  = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            consumed, effective = handle_slash_command(cmd, rest, messages, MODEL_NAME, LM_STUDIO_URL)
            if consumed:
                continue
            user_msg = effective if effective else user_msg

        # ── @file mention expansion ──────────────────────────────────────────
        display_msg = user_msg
        if "@" in user_msg:
            user_msg = expand_at_mentions(user_msg)

        print_user_message(display_msg)
        messages.append({"role": "user", "content": user_msg})

        # ── Inicia a captura de teclas para toda a fase de processamento ────
        if _get_global_capture:
            cap = _get_global_capture()
            if cap and not cap._active:
                cap.start()

        _turn_user_msg = user_msg

        while True:  # tool-call loop
            try:
                with AgentStream() as stream:
                    text, tool_calls, usage, reasoning = stream_llm(
                        client, MODEL_NAME, messages, tools_schema, stream
                    )
                input_queue.extend(stream.get_queued_inputs())
            except KeyboardInterrupt:
                print_system_message("Streaming interrompido. Continue com uma nova mensagem.")
                save_current_session(messages, MODEL_NAME, LM_STUDIO_URL)
                break

            assistant_msg: dict = {"role": "assistant", "content": text or None}
            if reasoning:
                assistant_msg["reasoning"] = reasoning
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in tool_calls.values()
                ]
            messages.append(assistant_msg)

            if not tool_calls:
                # ── Auto-sumarização: comprime histórico se ficar muito grande ──
                total_chars = sum(len(str(m.get("content") or "")) for m in messages)
                if total_chars > 16_000 and len(messages) > 12:
                    old = messages[1:-6]
                    summary = summarize_with_llm(old, client, MODEL_NAME)
                    messages = messages[:1] + [
                        {"role": "system", "content": f"[Resumo da conversa anterior: {summary}]"}
                    ] + messages[-6:]
                    print_system_message("Contexto comprimido automaticamente para economizar tokens.")

                save_current_session(messages, MODEL_NAME, LM_STUDIO_URL)
                logger.log_turn({
                    "user_input": _turn_user_msg[:200],
                    "assistant_response": (text or "")[:500],
                    "reasoning": (reasoning or "")[:300],
                    "tool_calls": [],
                    "success": True,
                })
                break

            # ── Validar tool calls ───────────────────────────────────────────
            last_user_msg = next(
                (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
            )
            valid_tool_calls = {}
            for idx, tc in tool_calls.items():
                try:
                    validator.validate(tc, AVAILABLE_TOOLS)
                    valid_tool_calls[idx] = tc
                except ValueError as val_err:
                    console.print(f"  [yellow]⚠ Validação:[/yellow] {val_err}")
                    logger.log_metric("tool_validation_error", str(val_err), {"tool": tc.get("name")})
                    repaired = validator.repair(tc, AVAILABLE_TOOLS, messages, last_user_msg)
                    if repaired:
                        valid_tool_calls[idx] = repaired
                        logger.log_metric("tool_repaired", True, {"original": tc.get("name")})
                    else:
                        logger.log_metric("tool_repaired", False, {"original": tc.get("name")})

            # ── FallbackParser se não houver calls válidas ───────────────────
            if not valid_tool_calls:
                parsed = fallback_parser.parse(text or "")
                if parsed:
                    for i, tc in enumerate(parsed):
                        tc.setdefault("id", f"fallback_{i}")
                        valid_tool_calls[i] = tc
                    logger.log_metric("fallback_triggered", True, {"parsed": [t["name"] for t in parsed]})
                else:
                    logger.log_metric("fallback_triggered", False, {"text": (text or "")[:100]})
                    save_current_session(messages, MODEL_NAME, LM_STUDIO_URL)
                    break

            # ── Mode: PLAN — confirm before executing ───────────────────────
            if get_mode() == AgentMode.PLAN:
                if not prompt_plan_approval(valid_tool_calls):
                    messages.append({
                        "role": "user",
                        "content": "O usuário revisou o plano e decidiu não executar. Pergunte o que ele prefere fazer.",
                    })
                    break

            # ── Execute tool calls ───────────────────────────────────────────
            for tc in valid_tool_calls.values():
                try:
                    result = execute_tool(tc, AVAILABLE_TOOLS)
                    success = True
                except Exception as exc:
                    trace = traceback.format_exc()
                    result = f"Erro crítico: {exc}"
                    success = False
                    logger.log_metric("tool_crash", True, {"tool": tc.get("name"), "trace": trace[:500]})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
                logger.log_turn({
                    "user_input": _turn_user_msg[:200],
                    "assistant_response": (text or "")[:300],
                    "reasoning": (reasoning or "")[:200],
                    "tool_call": {"name": tc.get("name"), "arguments": tc.get("arguments", "")[:200]},
                    "tool_result": result[:300],
                    "success": success,
                })
