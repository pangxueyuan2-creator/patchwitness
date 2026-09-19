"""Wire decoding must reject ambiguous input before MCP tool dispatch."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

import patchwitness.mcp as mcp
from patchwitness.mcp import MCPServer

LIST_REQUEST = '{"jsonrpc":"2.0","id":"next","method":"tools/list"}\n'
CALL_PREFIX = ('{"jsonrpc":"2.0","id":1,"method":"tools/call",'
               '"params":{"name":"patchwitness_capture","arguments":')


def responses(server: MCPServer, wire: str | bytes) -> list[dict[str, Any]]:
    output = io.StringIO()
    source = io.BytesIO(wire) if isinstance(wire, bytes) else io.StringIO(wire)
    assert server.serve(source, output) == 0
    return [json.loads(line) for line in output.getvalue().splitlines()]


@pytest.mark.parametrize("payload", [
    CALL_PREFIX + '{"execute_checks":false,"execute_checks":true}}}',
    CALL_PREFIX + '{"execute_checks":true,"execute_checks":false}}}',
    CALL_PREFIX + '{"execute_checks":true,"execute_\\u0063hecks":true}}}',
    CALL_PREFIX + '{"execute_checks":true,"extra":{"x":1,"x":2}}}}',
    '{"jsonrpc":"2.0","id":1,"id":2,"method":"tools/list"}',
    '{"jsonrpc":"2.0","id":1,"method":"tools/list","method":"initialize"}',
    '{"jsonrpc":"2.0","id":1,"method":"tools/call",'
    '"params":{"name":"patchwitness_verify","name":"patchwitness_capture"}}',
])
def test_duplicate_keys_rejected_before_dispatch_and_next_request_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: str,
) -> None:
    server = MCPServer(tmp_path)
    dispatch = Mock(return_value={})
    monkeypatch.setattr(server, "_call", dispatch)
    result = responses(server, payload + "\n" + LIST_REQUEST)
    assert result[0]["error"] == {"code": -32700, "message": "parse error"}
    assert result[0]["id"] is None
    assert result[1]["id"] == "next" and "tools" in result[1]["result"]
    dispatch.assert_not_called()


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e10000", "-1e10000"])
def test_nonfinite_numbers_in_ignored_fields_are_not_valid_json_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, number: str,
) -> None:
    server = MCPServer(tmp_path)
    dispatch = Mock(return_value={})
    monkeypatch.setattr(server, "_call", dispatch)
    wire = CALL_PREFIX + '{"execute_checks":true,"extra":[' + number + ']}}}\n'
    result = responses(server, wire + LIST_REQUEST)
    assert result[0]["error"]["code"] == -32700
    assert result[1]["id"] == "next"
    dispatch.assert_not_called()


@pytest.mark.parametrize("number", ["0.5", "-0.25", "1e20"])
def test_finite_json_numbers_in_extensions_remain_supported(tmp_path: Path, number: str) -> None:
    wire = LIST_REQUEST.rstrip().removesuffix("}") + ',"extra":' + number + '}\n'
    assert "result" in responses(MCPServer(tmp_path), wire)[0]


@pytest.mark.parametrize("bad", [
    b'{"jsonrpc":"2.0","id":"bad\xff","method":"tools/list"}\n',
    b'\xef\xbb\xbf{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n',
])
def test_bytes_require_strict_utf8_json_and_preserve_following_frame(
    tmp_path: Path, bad: bytes,
) -> None:
    result = responses(MCPServer(tmp_path), bad + LIST_REQUEST.encode())
    assert result[0]["error"]["code"] == -32700
    assert result[1]["id"] == "next"


def test_utf16_is_not_silently_autodetected(tmp_path: Path) -> None:
    request = LIST_REQUEST.rstrip().encode("utf-16")
    result = responses(MCPServer(tmp_path), request)
    assert result[0]["error"]["code"] == -32700


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("character", ["x", "测"])
def test_line_budget_is_utf8_bytes_not_characters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, binary: bool, character: str,
) -> None:
    # Includes the delimiter. A small budget keeps boundary fixtures easy to inspect.
    limit = 256
    monkeypatch.setattr(mcp, "MAX_MCP_MESSAGE_BYTES", limit, raising=False)
    template = '{"jsonrpc":"2.0","id":1,"method":"tools/list","padding":"%s"}\n'
    space = limit - len((template % "").encode())
    padding = character * (space // len(character.encode()))
    padding += "x" * (space - len(padding.encode()))
    at_limit = template % padding
    assert len(at_limit.encode()) == limit
    over_limit = template % (padding + "x")
    wire = at_limit + over_limit + LIST_REQUEST
    result = responses(MCPServer(tmp_path), wire.encode() if binary else wire)
    assert "result" in result[0]
    assert result[1]["error"]["code"] == -32600 and result[1]["id"] is None
    assert result[2]["id"] == "next" and len(result) == 3


@pytest.mark.parametrize("binary", [False, True])
def test_overflow_is_drained_once_not_reinterpreted_as_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, binary: bool,
) -> None:
    monkeypatch.setattr(mcp, "MAX_MCP_MESSAGE_BYTES", 128, raising=False)
    # A valid-looking suffix of an oversized physical line must not be dispatched.
    wire = "x" * (128 * 2000) + LIST_REQUEST + LIST_REQUEST
    result = responses(MCPServer(tmp_path), wire.encode() if binary else wire)
    assert len(result) == 2
    assert result[0]["error"]["code"] == -32600
    assert result[1]["id"] == "next"


def test_text_stream_reads_are_bounded_even_when_draining(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mcp, "MAX_MCP_MESSAGE_BYTES", 128, raising=False)

    class GuardedStream(io.StringIO):
        def __iter__(self) -> Any:
            raise AssertionError("iteration performs an unbounded line read")

        def readline(self, size: int | None = -1) -> str:
            assert size is not None and 0 < size <= 64 * 1024
            return super().readline(size)

    output = io.StringIO()
    stream = GuardedStream("x" * 200000 + "\n" + LIST_REQUEST)
    assert MCPServer(tmp_path).serve(stream, output) == 0
    result = [json.loads(line) for line in output.getvalue().splitlines()]
    assert len(result) == 2 and result[1]["id"] == "next"


@pytest.mark.parametrize("bad", ["[" * 10000 + "0" + "]" * 10000, "9" * 10000],
                         ids=["deep-nesting", "large-integer"])
def test_parser_resource_errors_are_contained_parse_errors(tmp_path: Path, bad: str) -> None:
    result = responses(MCPServer(tmp_path), bad + "\n" + LIST_REQUEST)
    assert result[0]["error"]["code"] == -32700
    assert result[1]["id"] == "next"


@pytest.mark.parametrize("suffix", ["\n", "\r\n", ""])
def test_normal_blank_lines_unicode_and_eof_without_delimiter(tmp_path: Path, suffix: str) -> None:
    request = {"jsonrpc": "2.0", "id": "测试🧪", "method": "tools/list"}
    wire = "\n  \r\n" + json.dumps(request, ensure_ascii=False) + suffix
    result = responses(MCPServer(tmp_path), wire.encode("utf-8"))
    assert len(result) == 1 and result[0]["id"] == request["id"]


def test_duplicate_wire_flag_never_runs_real_check_but_valid_opt_in_does(tmp_path: Path) -> None:
    for args in [("init", "-q"), ("config", "user.email", "test@example.invalid"),
                 ("config", "user.name", "Test"), ("commit", "--allow-empty", "-qm", "base")]:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    (tmp_path / "check.py").write_text(
        "from pathlib import Path\nPath('check-ran').write_text('yes')\n", encoding="utf-8",
    )
    command = f'"{sys.executable}" check.py'
    (tmp_path / ".patchwitness.toml").write_text(
        "version = 1\n[policy]\nrequire_tests = false\n[[checks]]\n"
        f"id = 'marker'\ncommand = '{command}'\n", encoding="utf-8",
    )
    server = MCPServer(tmp_path)
    malformed = CALL_PREFIX + '{"execute_checks":false,"execute_checks":true}}}\n'
    result = responses(server, malformed)
    assert not (tmp_path / "check-ran").exists()
    assert result[0]["error"]["code"] == -32700
    valid = CALL_PREFIX + '{"execute_checks":true}}}\n'
    accepted = responses(server, valid)
    assert accepted[0]["result"]["isError"] is False
    assert (tmp_path / "check-ran").read_text() == "yes"


def test_default_stdio_uses_raw_bytes_not_the_locale_decoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = json.dumps(
        {"jsonrpc": "2.0", "id": "测试", "method": "tools/list"}, ensure_ascii=False,
    ).encode("utf-8") + b"\n"
    invalid = b'{"jsonrpc":"2.0","id":"bad\xff","method":"tools/list"}\n'
    text_input = io.TextIOWrapper(io.BytesIO(invalid + valid), encoding="ascii", errors="strict")
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", text_input)
    monkeypatch.setattr(sys, "stdout", output)
    assert MCPServer(tmp_path).serve() == 0
    result = [json.loads(line) for line in output.getvalue().splitlines()]
    assert result[0]["error"]["code"] == -32700
    assert result[1]["id"] == "测试" and "result" in result[1]


def test_default_stdio_supports_explicitly_decoded_text_hosts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(LIST_REQUEST))
    monkeypatch.setattr(sys, "stdout", output)
    assert MCPServer(tmp_path).serve() == 0
    assert json.loads(output.getvalue())["id"] == "next"


def test_binary_overflow_reads_are_bounded_and_eof_does_not_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mcp, "MAX_MCP_MESSAGE_BYTES", 128, raising=False)

    class GuardedBytes(io.BytesIO):
        def readline(self, size: int | None = -1) -> bytes:
            assert size is not None and 0 < size <= 64 * 1024
            return super().readline(size)

    output = io.StringIO()
    assert MCPServer(tmp_path).serve(GuardedBytes(b"x" * 200000), output) == 0
    result = [json.loads(line) for line in output.getvalue().splitlines()]
    assert len(result) == 1 and result[0]["error"]["code"] == -32600


def test_surrogate_in_decoded_text_is_not_valid_utf8(tmp_path: Path) -> None:
    bad = '{"jsonrpc":"2.0","id":"bad\ud800","method":"tools/list"}\n'
    result = responses(MCPServer(tmp_path), bad + LIST_REQUEST)
    assert result[0]["error"]["code"] == -32700
    assert result[1]["id"] == "next"


@pytest.mark.parametrize("error", [ValueError("closed stream"), OSError("read failed")])
def test_broken_stream_is_not_retried_as_a_json_parse_error(
    tmp_path: Path, error: Exception,
) -> None:
    class BrokenStream(io.StringIO):
        reads = 0

        def readline(self, size: int | None = -1) -> str:
            self.reads += 1
            if self.reads > 1:
                raise RuntimeError("unexpected retry of a broken stream")
            raise error

    output = io.StringIO()
    stream = BrokenStream()
    with pytest.raises(type(error), match=str(error)):
        MCPServer(tmp_path).serve(stream, output)
    assert stream.reads == 1 and not output.getvalue()
