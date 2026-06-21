"""
Testes de integração: fluxo completo com mocks (sem LLM real, sem rede).
Execute com: pytest tests/test_integration.py -v
"""

import os
import sys
import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tools import AVAILABLE_TOOLS
from src.core.tool_validator import ToolValidator
from src.core.fallback_parser import FallbackParser
from src.core.logger import InteractionLogger
from src.core.context_summarizer import _rule_based_summary


# ── ToolValidator — novos campos ──────────────────────────────────────────────

def test_heuristic_extracts_url_from_message():
    v = ToolValidator()
    call = {"name": "fetch_url", "arguments": {}}
    msg = "acesse https://python.org e me diga o que tem lá"
    repaired = v._heuristic_repair(call, AVAILABLE_TOOLS, msg)
    assert repaired is not None
    assert repaired["arguments"]["url"] == "https://python.org"


def test_heuristic_extracts_command_from_message():
    v = ToolValidator()
    call = {"name": "run_shell", "arguments": {}}
    msg = "execute dir /b no terminal"
    repaired = v._heuristic_repair(call, AVAILABLE_TOOLS, msg)
    assert repaired is not None
    assert "dir" in repaired["arguments"]["command"]


def test_heuristic_uses_session_cwd():
    # read_file tem 'path' como required — sem mensagem do usuário, usa session_cwd
    v = ToolValidator(cwd="C:/default")
    call = {"name": "read_file", "arguments": {}}
    repaired = v._heuristic_repair(call, AVAILABLE_TOOLS, "", session_cwd="C:/projetos")
    assert repaired is not None
    assert repaired["arguments"]["path"] == "C:/projetos"


def test_repair_passes_session_cwd():
    v = ToolValidator()
    call = {"name": "read_file", "arguments": {}}
    repaired = v.repair(call, AVAILABLE_TOOLS, [], session_cwd="C:/meu_projeto")
    assert repaired is not None
    assert repaired["arguments"]["path"] == "C:/meu_projeto"


# ── FallbackParser — novos padrões ────────────────────────────────────────────

def test_fallback_parser_me_mostre():
    fp = FallbackParser()
    calls = fp.parse("me mostre o arquivo agent.py")
    assert calls and calls[0]["name"] == "read_file"
    assert "agent.py" in calls[0]["arguments"]["path"]


def test_fallback_parser_o_que_e():
    fp = FallbackParser()
    calls = fp.parse("o que é Python?")
    assert calls and calls[0]["name"] == "web_search_fetch"
    assert "python" in calls[0]["arguments"]["query"].lower()


def test_fallback_parser_what_is():
    fp = FallbackParser()
    calls = fp.parse("what is asyncio in Python")
    assert calls and calls[0]["name"] == "web_search_fetch"


def test_fallback_parser_listar():
    fp = FallbackParser(cwd=".")
    calls = fp.parse("listar arquivos do projeto")
    assert calls and calls[0]["name"] == "list_dir"


def test_fallback_parser_estrutura():
    fp = FallbackParser(cwd="/proj")
    calls = fp.parse("estrutura da pasta src")
    assert calls and calls[0]["name"] == "list_dir"


# ── InteractionLogger — rotação de logs ──────────────────────────────────────

def test_logger_rotation_triggered():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = InteractionLogger(log_dir=tmpdir, max_size_mb=0, keep_files=3)
        # Com max_size_mb=0, qualquer arquivo não-vazio dispara rotação
        logger.log_metric("test", 1)
        logger.log_metric("test", 2)

        files = os.listdir(tmpdir)
        # Deve ter criado stats.jsonl e pelo menos stats.1.jsonl
        assert "stats.jsonl" in files
        assert any(f.startswith("stats.") and f.endswith(".jsonl") for f in files)


def test_logger_keep_files_limit():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = InteractionLogger(log_dir=tmpdir, max_size_mb=0, keep_files=2)
        for i in range(5):
            logger.log_metric("m", i)

        rotated = [f for f in os.listdir(tmpdir) if "stats." in f and ".jsonl" in f and f != "stats.jsonl"]
        # Com keep_files=2 nunca deve ter mais de 2 arquivos rotacionados
        assert len(rotated) <= 2


# ── _rule_based_summary ───────────────────────────────────────────────────────

def test_rule_based_summary_extracts_tool_names():
    messages = [
        {"role": "user", "content": "leia o arquivo config.py"},
        {"role": "assistant", "content": None, "tool_calls": [
            {"function": {"name": "read_file"}, "id": "1"}
        ]},
        {"role": "tool", "content": "arquivo lido com sucesso"},
    ]
    summary = _rule_based_summary(messages)
    assert "read_file" in summary
    assert "Usuário" in summary


def test_rule_based_summary_captures_errors():
    messages = [
        {"role": "tool", "content": "Erro: arquivo não encontrado em /tmp/x.txt"},
    ]
    summary = _rule_based_summary(messages)
    assert "Erro" in summary


def test_rule_based_summary_empty():
    summary = _rule_based_summary([])
    assert summary == "Sem eventos registrados."


# ── WebSearchFetchTool — retry com mock ──────────────────────────────────────

def test_web_search_fetch_retries_on_429():
    tool = AVAILABLE_TOOLS.get("web_search_fetch")
    if tool is None:
        pytest.skip("web_search_fetch não disponível")

    import httpx

    call_count = 0

    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        if call_count < 3:
            resp.status_code = 429
        else:
            resp.status_code = 200
            resp.text = "<html><body>conteúdo da página</body></html>"
            resp.headers = {"content-type": "text/html"}
        return resp

    with patch("src.tools.web.httpx.get", side_effect=mock_get):
        result = tool._fetch_with_retry("https://example.com", max_retries=3)

    assert result is not None
    assert result.status_code == 200


def test_web_search_fetch_returns_none_after_max_retries():
    tool = AVAILABLE_TOOLS.get("web_search_fetch")
    if tool is None:
        pytest.skip("web_search_fetch não disponível")

    import httpx

    def always_429(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 429
        return resp

    with patch("src.tools.web.httpx.get", side_effect=always_429):
        result = tool._fetch_with_retry("https://example.com", max_retries=2)

    assert result is None


# ── Fluxo completo: FallbackParser → validate → execute ──────────────────────

def test_full_read_flow(monkeypatch, tmp_path):
    import src.tools.filesystem as _fs
    monkeypatch.setattr(_fs, "_ask", lambda *a, **kw: None)

    test_file = tmp_path / "hello.txt"
    test_file.write_text("conteúdo de teste", encoding="utf-8")

    fp = FallbackParser(cwd=str(tmp_path))
    v = ToolValidator(cwd=str(tmp_path))

    calls = fp.parse(f'leia o arquivo "{test_file}"')
    assert calls, "FallbackParser não reconheceu o comando"
    assert calls[0]["name"] == "read_file"

    validated = v.validate(calls[0], AVAILABLE_TOOLS)
    result = AVAILABLE_TOOLS["read_file"].execute(**validated["arguments"])
    assert result.success
    assert "conteúdo de teste" in result.output
