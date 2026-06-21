"""
Testes básicos das tools do vision_cli.
Execute com: pytest tests/
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tools import AVAILABLE_TOOLS
from src.tools.base import ToolResult


# ── read_file / write_file ────────────────────────────────────────────────────

def test_write_and_read_file(monkeypatch):
    # Bypassa o prompt de aprovação para rodar em ambiente de teste
    import src.tools.filesystem as _fs
    monkeypatch.setattr(_fs, "_ask", lambda *a, **kw: None)  # None = aprovado

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as f:
        tmp_path = f.name

    try:
        write_tool = AVAILABLE_TOOLS["write_file"]
        res = write_tool.execute(path=tmp_path, content="Olá mundo")
        assert res.success, f"write falhou: {res.error}"

        read_tool = AVAILABLE_TOOLS["read_file"]
        res = read_tool.execute(path=tmp_path)
        assert res.success, f"read falhou: {res.error}"
        assert "Olá mundo" in res.output
    finally:
        os.unlink(tmp_path)


def test_read_nonexistent_file():
    read_tool = AVAILABLE_TOOLS["read_file"]
    res = read_tool.execute(path="/caminho/que/nao/existe.txt")
    assert not res.success or "não encontrado" in res.output.lower() or res.error


# ── list_dir ─────────────────────────────────────────────────────────────────

def test_list_dir_current():
    list_tool = AVAILABLE_TOOLS["list_dir"]
    res = list_tool.execute(path=".")
    assert res.success
    assert res.output.strip()


def test_list_dir_nonexistent():
    list_tool = AVAILABLE_TOOLS["list_dir"]
    res = list_tool.execute(path="/diretorio/que/nao/existe")
    assert not res.success or "não encontrado" in res.output.lower() or res.error


# ── search_code ───────────────────────────────────────────────────────────────

def test_search_code():
    search_tool = AVAILABLE_TOOLS["search_code"]
    res = search_tool.execute(pattern="class.*Tool", path="src/tools")
    assert res.success
    assert res.output.strip()


# ── tool_validator ────────────────────────────────────────────────────────────

def test_validator_valid_call():
    from src.core.tool_validator import ToolValidator
    v = ToolValidator()
    call = {"name": "read_file", "arguments": {"path": "test.txt"}}
    result = v.validate(call, AVAILABLE_TOOLS)
    assert result["name"] == "read_file"


def test_validator_fuzzy_match():
    from src.core.tool_validator import ToolValidator
    v = ToolValidator()
    with pytest.raises(ValueError, match="quis dizer"):
        v.validate({"name": "reed_file", "arguments": {}}, AVAILABLE_TOOLS)


def test_validator_missing_args():
    from src.core.tool_validator import ToolValidator
    v = ToolValidator()
    with pytest.raises(ValueError, match="obrigatórios"):
        v.validate({"name": "read_file", "arguments": {}}, AVAILABLE_TOOLS)


# ── fallback_parser ───────────────────────────────────────────────────────────

def test_fallback_parser_read():
    from src.core.fallback_parser import FallbackParser
    fp = FallbackParser()
    calls = fp.parse("leia o arquivo config.py")
    assert len(calls) == 1
    assert calls[0]["name"] == "read_file"
    assert "config.py" in calls[0]["arguments"]["path"]


def test_fallback_parser_list():
    from src.core.fallback_parser import FallbackParser
    fp = FallbackParser(cwd=".")
    calls = fp.parse("liste os arquivos")
    assert len(calls) == 1
    assert calls[0]["name"] == "list_dir"


def test_fallback_parser_no_match():
    from src.core.fallback_parser import FallbackParser
    fp = FallbackParser()
    calls = fp.parse("olá, tudo bem?")
    assert calls == []


# ── logger ────────────────────────────────────────────────────────────────────

def test_logger_creates_files():
    import tempfile
    from src.core.logger import InteractionLogger
    with tempfile.TemporaryDirectory() as tmpdir:
        log = InteractionLogger(log_dir=tmpdir)
        log.log_turn({"user_input": "teste", "success": True})
        log.log_metric("test_metric", 42)

        files = os.listdir(tmpdir)
        assert any(f.startswith("session_") for f in files)
        assert "stats.jsonl" in files
