# inventor-mcp

**MCP server for parametric 3D modeling in Autodesk Inventor — drive Inventor with Claude (or any MCP client) in natural language.**

Build real parametric parts — flanges, shafts, nuts, brackets, sheet-metal enclosures — by talking to an AI assistant. The server wraps Inventor's COM API with high-level, millimeter-based tools and ships with battle-tested knowledge of Inventor 2026 API quirks that aren't documented anywhere else.

```
You:    "Build a DIN 934 M16 hex nut with proper conical chamfers"
Claude: creates sketch → hexagon → extrude → tapped M16×2 hole →
        revolve-cut chamfers → done. Fully parametric, dimensioned sketches.
```

## Features

- **34 MCP tools**: sketching, extrude/revolve, native hole features (drilled / tapped / counterbore), fillets, chamfers, circular patterns, sheet metal (Face / Flange / Cut with Flat Pattern support), parameters
- **`execute_python` power tool** — run arbitrary Python against the live COM connection with a persistent namespace (escape hatch for anything not covered by dedicated tools)
- **Auto-reporting** — every feature operation returns a volume/topology delta (`Hole1 | V 23497 (-503 mm³) | F7 E14`), so the AI can self-verify each step
- **Transactions** — wrap multi-step builds, roll back everything with one call
- **Hot reload** — edit the API wrapper and reload without restarting the MCP client
- **Topology helpers** — find edges/faces by coordinates instead of guessing indices
- **Parametric discipline** — projected origin points, symmetry constraints, dimensioned sketches that survive parameter changes

## Requirements

- Windows with **Autodesk Inventor** (developed and tested on Inventor 2026; older versions may need enum adjustments — see [docs/inventor-api-notes.md](docs/inventor-api-notes.md))
- **Python 3.12+**
- `pip install "mcp[cli]" pywin32`

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/NeonGlay/inventor-mcp.git
   ```

2. Install dependencies:
   ```
   pip install "mcp[cli]" pywin32
   ```

3. Register the server with your MCP client. For Claude Code, add to `.mcp.json` in your project root (see `.mcp.json.example`):
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

4. Start Inventor, then ask your AI assistant to build something.

> **Do NOT use `win32com.client.gencache.EnsureDispatch`** in your own scripts against the same Python install — the generated `gen_py` cache breaks `GetActiveObject`. If it happens: delete `%LOCALAPPDATA%\Temp\gen_py`. See the API notes for the full story.

## Skills (optional, recommended)

The `skills/` directory contains two [Agent Skills](https://code.claude.com/docs/en/skills) that teach Claude the workflow and the Inventor 2026 API quirks:

- **inventor-modeling** — core patterns: units, sketch discipline, hole placement, sheet metal, diagnostic verification, common failure modes
- **inventor-din-parts** — parametric recipes for DIN/ISO standard parts (hex nuts DIN 934, bolts DIN 933, washers DIN 125, flanges DIN 2573) with dimension tables

Install by copying into your skills directory:
```
cp -r skills/inventor-modeling ~/.claude/skills/
cp -r skills/inventor-din-parts ~/.claude/skills/
```

## Why this exists

Inventor's COM API documentation is wrong or silent about many things in recent versions. This project encodes empirically verified knowledge:

- Correct Inventor 2026 enum values (`kPartDocumentObject = 12290`, dimension orientation `19201/19202/19203`, …)
- `ChamferFeatures.AddUsingDistance(EdgeCollection, d)` — the 2026 replacement for the removed `CreateChamferDefinition`
- Sheet-metal `FlangeDefinition`: the Distance argument is **silently ignored**; the real height is set via `feature.Definition.HeightExtent.Distance.Expression` (and the angle is in radians — pass `90` and you get 5156°)
- `CreateLinearPlacementDefinition` requires a `BiasPoint` argument that dynamic dispatch won't tell you about
- Edge indices renumber after every feature; fillets shift adjacent edges
- …and more in [docs/inventor-api-notes.md](docs/inventor-api-notes.md)

## Architecture

```
src/server.py        FastMCP server — tool definitions (stdio transport)
src/inventor_api.py  InventorConnection — COM wrapper, all geometry logic (mm units)
skills/              Agent Skills for Claude
docs/                Hard-won API knowledge
```

## Contributing

Contributions welcome! Especially valuable:
- Testing on Inventor 2024/2025 (enum values may differ — please report)
- Assembly (IAM) and drawing (IDW) support
- More DIN/ISO part recipes
- Bug reports with the exact COM error and Inventor version

## License

MIT — see [LICENSE](LICENSE).
