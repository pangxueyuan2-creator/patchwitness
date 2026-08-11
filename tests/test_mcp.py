from pathlib import Path

from patchwitness.mcp import MCPServer


def test_mcp_initialize_and_tool_discovery(tmp_path: Path) -> None:
    server = MCPServer(tmp_path)
    initialized = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["name"] == "patchwitness"
    listed = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert listed is not None
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert names == {"patchwitness_capture", "patchwitness_verify", "patchwitness_impact"}


def test_mcp_rejects_path_escape(tmp_path: Path) -> None:
    server = MCPServer(tmp_path)
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "patchwitness_verify",
                "arguments": {"evidence": "../outside.json"},
            },
        }
    )
    assert response is not None
    assert response["result"]["isError"] is True
    assert "escapes" in response["result"]["content"][0]["text"]
