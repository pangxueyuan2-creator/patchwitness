# MCP integration

Start the server with a fixed repository root:

```bash
patchwitness mcp --root /absolute/path/to/repository
```

The transport is newline-delimited stdio JSON-RPC. Supported methods include MCP `initialize`,
`tools/list`, and `tools/call`.

## Tools

- `patchwitness_capture`: capture evidence. `execute_checks` defaults to `false` so an agent cannot
  trigger repository commands merely by asking for inspection.
- `patchwitness_verify`: verify an evidence file beneath the configured root.
- `patchwitness_impact`: compute the current change blast radius.

All file arguments are resolved and confined to the configured root. The MCP surface does not accept
arbitrary shell commands.

## Example configuration

```json
{
  "mcpServers": {
    "patchwitness": {
      "command": "patchwitness",
      "args": ["mcp", "--root", "/workspace/project"]
    }
  }
}
```

The core CLI remains the recommended enforcement surface. MCP is intended for inspection and agent
handoff, not as the only CI trust boundary.

