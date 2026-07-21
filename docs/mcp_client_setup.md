# MCP Client Setup

This checkout includes local MCP client configuration for:

- Claude Code project scope: `.mcp.json`;
- VS Code workspace scope: `.vscode/mcp.json`.

Both entries point to:

```bash
/home/chakwong/research-assistant/scripts/ra-mcp-dev --root /home/chakwong/research-assistant
```

`scripts/ra-mcp-dev` sets `PYTHONPATH=src` automatically and starts the same
stdio MCP server as the installed `ra-mcp` entrypoint.

## Claude Code

From this repository:

```bash
claude mcp get research-assistant
```

If Claude Code asks whether to trust the project MCP server, approve it only for
this repository. The server is local stdio and uses the repository workspace as
its root.

In the current WSL environment, `claude mcp get research-assistant` and
`claude mcp list` may time out while performing their health check even when the
configured server command itself is valid. If that happens, verify the entrypoint
directly with `scripts/ra-mcp-dev --help`, restart Claude Code, and approve the
project server from the client UI.

## VS Code

Open this repository in VS Code. The workspace MCP config lives at:

```text
.vscode/mcp.json
```

Use the MCP/Copilot tools view to start or refresh the `research-assistant`
server if VS Code does not pick it up immediately.

The VS Code CLI is present as `code`; no separate command-line MCP health check
is exposed by this local `code --help` output.

## Safety Boundary

The MCP adapter remains local stdio. It is not a hosted service or HTTP server.

Default MCP tools are read-only. Grant-bound arXiv source intake is available
only with a matching local grant and plan hash. Live query discovery, PDF
download execution, review mutation, restore, delete, and destructive tools are
not exposed through MCP.

To check the local server entrypoint without starting a client:

```bash
scripts/ra-mcp-dev --help
scripts/ra-agent mcp-status
```

## References

- Claude Code MCP project-scope configuration:
  <https://code.claude.com/docs/en/mcp>
- VS Code MCP workspace configuration:
  <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration>
