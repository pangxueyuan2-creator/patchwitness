"""Small stdio MCP adapter for any newline-delimited JSON-RPC host."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

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
            except Exception as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"},
                }
            if response is not None:
                output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
                output_stream.flush()
        return 0

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = str(request.get("method", ""))
        request_id = request.get("id")
        if method.startswith("notifications/"):
            return None
        if method == "initialize":
            return self._result(
                request_id,
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "patchwitness", "version": "0.1.0"},
                },
            )
        if method == "tools/list":
            return self._result(request_id, {"tools": self._tools()})
        if method == "tools/call":
            params = dict(request.get("params", {}))
            name = str(params.get("name", ""))
            arguments = dict(params.get("arguments", {}))
            try:
                result = self._call(name, arguments)
                content = [{"type": "text", "text": json.dumps(result, sort_keys=True)}]
                return self._result(request_id, {"content": content, "isError": False})
            except Exception as exc:
                content = [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}]
                return self._result(request_id, {"content": content, "isError": True})
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }

    def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "patchwitness_capture":
            contract = self._safe_path(str(arguments.get("contract", ".patchwitness.toml")))
            pack = capture_evidence(
                self.root,
                load_contract(contract),
                base=str(arguments.get("base", "HEAD")),
                execute_checks=bool(arguments.get("execute_checks", False)),
            )
            return pack.to_dict()
        if name == "patchwitness_verify":
            evidence = self._safe_path(str(arguments["evidence"]))
            pack = verify_evidence(load_evidence(evidence))
            return {"status": pack.status.value, "payload_sha256": pack.payload_sha256}
        if name == "patchwitness_impact":
            base = resolve_revision(self.root, str(arguments.get("base", "HEAD")))
            changes = collect_changes(self.root, base)
            return analyze_impact(self.root, changes)
        raise ValueError(f"unknown tool: {name}")

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

