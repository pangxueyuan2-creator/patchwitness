"""Small stdio MCP adapter for any newline-delimited JSON-RPC host."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, BinaryIO, TextIO

from patchwitness._version import __version__
from patchwitness.config import load_contract
from patchwitness.evidence import capture_evidence, load_evidence, verify_evidence
from patchwitness.git import collect_changes, resolve_revision
from patchwitness.impact import analyze_impact

# Includes the wire line delimiter. This is an adapter budget, not an MCP limit.
MAX_MCP_MESSAGE_BYTES = 1024 * 1024


class _MessageTooLarge(ValueError):
    """One physical input line exceeded the adapter's byte budget."""


class _MessageParseError(ValueError):
    """A consumed input frame cannot be decoded as strict JSON."""


def _line_ended(line: str | bytes) -> bool:
    return line.endswith(b"\n") if isinstance(line, bytes) else line.endswith("\n")


def _read_message_line(stream: TextIO | BinaryIO) -> str | None:
    """Read one bounded line; discard an oversized line without retaining its tail."""
    raw = stream.readline(MAX_MCP_MESSAGE_BYTES + 1)
    if not raw:
        return None
    oversized = len(raw) > MAX_MCP_MESSAGE_BYTES
    if not oversized and isinstance(raw, str):
        try:
            oversized = len(raw.encode("utf-8")) > MAX_MCP_MESSAGE_BYTES
        except UnicodeError as exc:
            raise _MessageParseError from exc
    if oversized:
        while raw and not _line_ended(raw):
            raw = stream.readline(64 * 1024)
        raise _MessageTooLarge
    # Decode bytes explicitly: json.loads(bytes) also accepts UTF-16/32 and BOMs.
    try:
        return raw.decode("utf-8") if isinstance(raw, bytes) else raw
    except UnicodeError as exc:
        raise _MessageParseError from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            # Never echo rejected keys or values from client input.
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite JSON number")
    return number


def _decode_message(line: str) -> object:
    try:
        request: object = json.loads(
            line, object_pairs_hook=_unique_object,
            parse_constant=_reject_constant, parse_float=_finite_float,
        )
        return request
    except (ValueError, RecursionError) as exc:
        raise _MessageParseError from exc


class MCPServer:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def serve(
        self,
        input_stream: TextIO | BinaryIO | None = None,
        output_stream: TextIO | None = None,
    ) -> int:
        # Raw stdin preserves frame boundaries even when a line is not UTF-8.
        source = (
            input_stream if input_stream is not None else getattr(sys.stdin, "buffer", sys.stdin)
        )
        sink = output_stream if output_stream is not None else sys.stdout
        while True:
            response: dict[str, Any] | None
            try:
                line = _read_message_line(source)
                if line is None:
                    return 0
                if not line.strip():
                    continue
                request = _decode_message(line)
            except _MessageTooLarge:
                response = self._error(None, -32600, "message exceeds the 1 MiB input limit")
            except _MessageParseError:
                response = self._error(None, -32700, "parse error")
            else:
                try:
                    response = self.handle(request)
                except Exception:
                    response = self._error(None, -32603, "internal server error")
            if response is not None:
                sink.write(json.dumps(response, separators=(",", ":")) + "\n")
                sink.flush()

    def handle(self, request: object) -> dict[str, Any] | None:
        if not isinstance(request, dict):
            return self._error(None, -32600, "request must be an object")
        request_id = request.get("id")
        valid_id = type(request_id) in (int, str)
        if (
            request.get("jsonrpc") != "2.0"
            or not isinstance(request.get("method"), str)
            or not request["method"]
            or ("id" in request and not valid_id)
        ):
            return self._error(request_id if valid_id else None, -32600, "invalid request")
        # Notifications have no response and must never dispatch a tool call.
        if "id" not in request:
            return None
        method = request["method"]
        params = request.get("params", {})
        if not isinstance(params, dict):
            return self._error(request_id, -32602, "params must be an object")
        if method == "initialize":
            return self._result(
                request_id,
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "patchwitness", "version": __version__},
                },
            )
        if method == "tools/list":
            return self._result(request_id, {"tools": self._tools()})
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str) or not name:
                return self._error(request_id, -32602, "tool name must be a nonempty string")
            if not isinstance(arguments, dict):
                return self._error(request_id, -32602, "arguments must be an object")
            try:
                result = self._call(name, arguments)
                content = [{"type": "text", "text": json.dumps(result, sort_keys=True)}]
                return self._result(request_id, {"content": content, "isError": False})
            except Exception as exc:
                content = [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}]
                return self._result(request_id, {"content": content, "isError": True})
        return self._error(request_id, -32601, "method not found")

    def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._validate_arguments(name, arguments)
        if name == "patchwitness_capture":
            contract = self._safe_path(arguments.get("contract", ".patchwitness.toml"))
            pack = capture_evidence(
                self.root,
                load_contract(contract),
                base=arguments.get("base", "HEAD"),
                execute_checks=arguments.get("execute_checks", False),
            )
            return pack.to_dict()
        if name == "patchwitness_verify":
            evidence = self._safe_path(arguments["evidence"])
            pack = verify_evidence(load_evidence(evidence))
            return {"status": pack.status.value, "payload_sha256": pack.payload_sha256}
        if name == "patchwitness_impact":
            base = resolve_revision(self.root, arguments.get("base", "HEAD"))
            changes = collect_changes(self.root, base)
            return analyze_impact(self.root, changes)
        raise ValueError(f"unknown tool: {name}")

    @classmethod
    def _validate_arguments(cls, name: str, arguments: dict[str, Any]) -> None:
        """Enforce advertised types before loading files, resolving refs or running checks."""
        tool = next((tool for tool in cls._tools() if tool["name"] == name), None)
        if tool is None:
            raise ValueError("unknown tool")
        schema = tool["inputSchema"]
        for field in schema.get("required", []):
            if field not in arguments:
                raise ValueError(f"missing required argument: {field}")
        for field, definition in schema["properties"].items():
            if field not in arguments:
                continue
            value = arguments[field]
            if definition["type"] == "boolean" and type(value) is not bool:
                raise ValueError(f"{field} must be a boolean")
            if definition["type"] == "string" and (
                not isinstance(value, str) or not value or "\0" in value
            ):
                raise ValueError(f"{field} must be a nonempty string without NUL characters")

    @staticmethod
    def _error(request_id: object, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def _safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("path escapes the configured repository root")
        return candidate

    @staticmethod
    def _result(request_id: object, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _tools() -> list[dict[str, Any]]:
        return [
            {
                "name": "patchwitness_capture",
                "description": "Capture deterministic change evidence; checks are opt-in.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base": {"type": "string", "default": "HEAD"},
                        "contract": {"type": "string", "default": ".patchwitness.toml"},
                        "execute_checks": {"type": "boolean", "default": False},
                    },
                },
            },
            {
                "name": "patchwitness_verify",
                "description": "Verify a Change Passport digest offline.",
                "inputSchema": {
                    "type": "object",
                    "required": ["evidence"],
                    "properties": {"evidence": {"type": "string"}},
                },
            },
            {
                "name": "patchwitness_impact",
                "description": "Compute the dependency blast radius of the current change.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"base": {"type": "string", "default": "HEAD"}},
                },
            },
        ]
