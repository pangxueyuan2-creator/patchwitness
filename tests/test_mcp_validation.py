"""MCP input validation must precede filesystem access or check execution."""

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from patchwitness.mcp import MCPServer


def call(name: str, arguments: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0", "id": "request-1", "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None, [], {}, [False]])
def test_capture_rejects_non_boolean_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: Any,
) -> None:
    load = Mock()
    capture = Mock()
    monkeypatch.setattr("patchwitness.mcp.load_contract", load)
    monkeypatch.setattr("patchwitness.mcp.capture_evidence", capture)
    response = MCPServer(tmp_path).handle(call("patchwitness_capture", {"execute_checks": value}))
    assert response is not None
    load.assert_not_called()
    capture.assert_not_called()
    assert response["id"] == "request-1"
    assert response["result"]["isError"] is True
    assert "execute_checks" in response["result"]["content"][0]["text"]


@pytest.mark.parametrize("arguments,expected", [({}, False), ({"execute_checks": False}, False),
                                               ({"execute_checks": True}, True)])
def test_explicit_boolean_and_default_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arguments: dict[str, Any], expected: bool,
) -> None:
    pack = Mock()
    pack.to_dict.return_value = {"status": "PASS"}
    capture = Mock(return_value=pack)
    monkeypatch.setattr("patchwitness.mcp.load_contract", Mock())
    monkeypatch.setattr("patchwitness.mcp.capture_evidence", capture)
    response = MCPServer(tmp_path).handle(call("patchwitness_capture", arguments))
    assert response is not None and response["result"]["isError"] is False
    assert capture.call_args.kwargs["execute_checks"] is expected


@pytest.mark.parametrize("name,field", [("patchwitness_capture", "base"),
                                       ("patchwitness_capture", "contract"),
                                       ("patchwitness_verify", "evidence"),
                                       ("patchwitness_impact", "base")])
@pytest.mark.parametrize("value", [None, 12, False, [], {}, "", "bad\0value"])
def test_string_arguments_are_not_coerced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, field: str, value: Any,
) -> None:
    operations = [Mock() for _ in range(3)]
    for attribute, operation in zip(
        ("load_contract", "load_evidence", "resolve_revision"), operations, strict=True,
    ):
        monkeypatch.setattr(f"patchwitness.mcp.{attribute}", operation)
    response = MCPServer(tmp_path).handle(call(name, {field: value}))
    assert response is not None
    for operation in operations:
        operation.assert_not_called()
    assert response["result"]["isError"] is True


@pytest.mark.parametrize("value", [None, [], [["execute_checks", True]], "invalid", 42])
@pytest.mark.parametrize("field", ["params", "arguments"])
def test_malformed_envelopes_return_invalid_params(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: Any,
) -> None:
    server = MCPServer(tmp_path)
    operation = Mock()
    monkeypatch.setattr(server, "_call", operation)
    request = call("patchwitness_capture", {})
    if field == "params":
        request[field] = value
    else:
        request["params"][field] = value
    response = server.handle(request)
    assert response is not None and response["error"]["code"] == -32602
    assert response["id"] == "request-1"
    operation.assert_not_called()


@pytest.mark.parametrize("payload", [[], None, 1, "request", {},
                                     {"jsonrpc": "1.0", "id": 1, "method": "tools/list"},
                                     {"jsonrpc": "2.0", "id": 1, "method": 12}])
def test_invalid_requests_do_not_crash(tmp_path: Path, payload: Any) -> None:
    response = MCPServer(tmp_path).handle(payload)
    assert response is not None and response["error"]["code"] == -32600


def test_notifications_cannot_invoke_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = MCPServer(tmp_path)
    operation = Mock()
    monkeypatch.setattr(server, "_call", operation)
    request = call("patchwitness_capture", {"execute_checks": True})
    del request["id"]
    assert server.handle(request) is None
    operation.assert_not_called()


def test_stdio_recovers_after_parse_and_envelope_errors(tmp_path: Path) -> None:
    lines = ["{", "[]", json.dumps(call("patchwitness_capture", None)),
             json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})]
    output = io.StringIO()
    assert MCPServer(tmp_path).serve(io.StringIO("\n".join(lines) + "\n"), output) == 0
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [response["error"]["code"] for response in responses[:3]] == [-32700, -32600, -32602]
    assert responses[3]["id"] == 4 and "tools" in responses[3]["result"]


def test_rejected_capture_never_runs_a_real_check(tmp_path: Path) -> None:
    for args in [("init", "-q"), ("config", "user.email", "test@example.invalid"),
                 ("config", "user.name", "Test"), ("commit", "--allow-empty", "-qm", "base")]:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    (tmp_path / "check.py").write_text(
        "from pathlib import Path\nPath('check-ran').write_text('yes')\n", encoding="utf-8",
    )
    # A quoted TOML literal keeps Windows backslashes unchanged.
    command = f'"{sys.executable}" check.py'
    (tmp_path / ".patchwitness.toml").write_text(
        "version = 1\n[policy]\nrequire_tests = false\n[[checks]]\n"
        f"id = 'marker'\ncommand = '{command}'\n", encoding="utf-8",
    )
    server = MCPServer(tmp_path)
    response = server.handle(call("patchwitness_capture", {"execute_checks": "false"}))
    assert response is not None and response["result"]["isError"] is True
    assert not (tmp_path / "check-ran").exists()
    accepted = server.handle(call("patchwitness_capture", {"execute_checks": True}))
    assert accepted is not None and accepted["result"]["isError"] is False
    assert (tmp_path / "check-ran").read_text() == "yes"
