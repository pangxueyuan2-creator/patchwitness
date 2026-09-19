"""Small stdio MCP adapter for any newline-delimited JSON-RPC host."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from patchwitness._version import __version__
from patchwitness.config import load_contract
from patchwitness.evidence import capture_evidence, load_evidence, verify_evidence
from patchwitness.git import collect_changes, resolve_revision
from patchwitness.impact import analyze_impact


class MCPServer:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def serve(self, input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> int:
        for line in input_stream:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                response = self.handle(request)
            except json.JSONDecodeError:
                response = self._error(None, -32700, "parse error")
            except Exception:
                response = self._error(None, -32603, "internal server error")
            if response is not None:
                output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
                output_stream.flush()
        return 0

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
