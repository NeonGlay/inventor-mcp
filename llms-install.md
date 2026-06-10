# Installation guide for AI agents

Step-by-step setup of the inventor-mcp server. Follow in order.

## Prerequisites check

1. **Windows only** — this server drives Autodesk Inventor through COM; it cannot work on macOS/Linux.
2. **Autodesk Inventor** must be installed (2026 recommended; 2024/2025 may work with enum differences). Verify:
   ```powershell
   Test-Path "C:\Program Files\Autodesk"
   ```
3. **Python 3.12+** on PATH:
   ```powershell
   python --version
   ```

## Setup steps

1. Clone the repository to a stable location (avoid paths that may be deleted):
   ```powershell
   git clone https://github.com/NeonGlay/inventor-mcp.git
   cd inventor-mcp
   ```

2. Install Python dependencies:
   ```powershell
   pip install "mcp[cli]" pywin32
   ```

3. Register the MCP server in the client's MCP configuration. The server uses
   **stdio** transport. Configuration (adjust `cwd` to the actual clone path):
   ```json
   {
     "mcpServers": {
       "inventor": {
         "command": "python",
         "args": ["-m", "src.server"],
         "cwd": "C:/path/to/inventor-mcp"
       }
     }
   }
   ```
   - Claude Code: add to `.mcp.json` in the project root
   - Cline: add to `cline_mcp_settings.json`
   - Claude Desktop: add to `claude_desktop_config.json`

4. Verify: restart the MCP client, then start Autodesk Inventor (the server
   connects to a **running** Inventor instance). Call the `connect` tool —
   expected response: `Connected to running Inventor 2026`.

## Smoke test

Ask the agent to run:
1. `connect` → should report the Inventor version
2. `create_part` with `template="metric"` → creates an empty part
3. `create_sketch` with `plane="XY"` → `draw_circle` (diameter=50) → `extrude` (distance=10)
4. `inspect` → should show one extrusion, volume ≈ 19 635 mm³

## Common issues

- **`Cannot connect to Inventor`** — Inventor isn't running. Start it first (the
  server attaches to the active instance; it can also launch one, but attaching
  is more reliable).
- **`KeyError: '_dispobj_'`** — a stale `gen_py` COM cache. Fix:
  ```powershell
  Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Temp\gen_py"
  ```
- **Unicode errors in console scripts** — run Python with `-X utf8` on Windows.
- All tool dimensions are **millimeters**; Inventor internally uses centimeters —
  the server converts automatically.
