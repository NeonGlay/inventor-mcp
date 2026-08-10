---
name: inventor-din-parts
description: Build standard DIN/ISO mechanical parts (hex nuts, hex bolts, socket head and countersunk screws, washers, flanges) in Autodesk Inventor via the project's MCP server, using parametric templates. Use this skill whenever the user asks for a specific standard part by designation — "DIN 934 M16 nut", "DIN 933 M20×60 bolt", "DIN 912 M8×40", "socket head cap screw", "imbus/allen bolt", "DIN 7991 countersunk screw", "DIN 439 thin nut", "DIN 125 washer", "DIN 2573 DN150 flange", "M12 nut", "ISO 4032 nut", "ISO 4762", "stud M10×80", or Ukrainian equivalents like "гайка М16", "болт М20×60", "гвинт з внутрішнім шестигранником", "фланець DIN", "шайба М12". Also triggers on phrases that imply a standard part — "стандартний болт", "звичайна гайка з різьбою", "плоска шайба". This skill assumes the `inventor-modeling` skill provides the core API knowledge; consult that for general gotchas first.
---

# DIN/ISO Standard Mechanical Parts — Parametric Templates

## Prerequisite

Read `inventor-modeling` skill first if any uncertainty about Inventor MCP setup, units, the "positive extrude" rule, etc. This skill builds on those primitives.

## When to use this skill

User wants a **specific standard part** with a defined designation:
- DIN 934 / ISO 4032 hex nut
- DIN 933 / ISO 4017 hex bolt (full thread)
- DIN 931 / ISO 4014 hex bolt (partial thread)
- DIN 912 / ISO 4762 socket head cap screw (hex socket, "imbus")
- DIN 7991 / ISO 10642 countersunk socket screw (90° head)
- DIN 439 / ISO 4035 thin hex nut
- DIN 125 / ISO 7089 flat washer
- DIN 127 spring washer
- DIN 2573 / EN 1092 flange

If the user says just "make a part shaped like X", that's the `inventor-modeling` skill (not this one).

## Standard dimension tables

These are the authoritative dimensions. Always use them — don't ask the user "what's the height of M16 nut".

### DIN 934 — Hex Nut (ISO 4032)
| Thread | s (across flats) | m (height) | Coarse pitch |
|---|---|---|---|
| M5  | 8   | 4.0  | 0.8  |
| M6  | 10  | 5.0  | 1.0  |
| M8  | 13  | 6.5  | 1.25 |
| M10 | 16  | 8.0  | 1.5  |
| M12 | 18  | 10.0 | 1.75 |
| M14 | 21  | 11.0 | 2.0  |
| M16 | 24  | 13.0 | 2.0  |
| M18 | 27  | 15.0 | 2.5  |
| M20 | 30  | 16.0 | 2.5  |
| M22 | 32  | 18.0 | 2.5  |
| M24 | 36  | 19.0 | 3.0  |
| M27 | 41  | 22.0 | 3.0  |
| M30 | 46  | 24.0 | 3.5  |
| M36 | 55  | 29.0 | 4.0  |

Helper: `circumradius = s / √3`, `apothem = s / 2`.

### DIN 933 — Hex Bolt (fully threaded), DIN 931 (partially threaded)
| Thread | s (across flats, head) | k (head height) | Common lengths |
|---|---|---|---|
| M6  | 10 | 4.0  | 8…200 |
| M8  | 13 | 5.3  | 10…300 |
| M10 | 16 | 6.4  | 16…300 |
| M12 | 18 | 7.5  | 20…300 |
| M16 | 24 | 10.0 | 25…300 |
| M20 | 30 | 12.5 | 30…300 |
| M24 | 36 | 15.0 | 40…300 |
| M30 | 46 | 18.7 | 60…300 |

### DIN 912 — Socket Head Cap Screw (ISO 4762)
| Thread | dk (head Ø) | k (head height) | s (socket across flats) | Coarse pitch |
|---|---|---|---|---|
| M3  | 5.5  | 3.0  | 2.5 | 0.5  |
| M4  | 7.0  | 4.0  | 3.0 | 0.7  |
| M5  | 8.5  | 5.0  | 4.0 | 0.8  |
| M6  | 10.0 | 6.0  | 5.0 | 1.0  |
| M8  | 13.0 | 8.0  | 6.0 | 1.25 |
| M10 | 16.0 | 10.0 | 8.0 | 1.5  |
| M12 | 18.0 | 12.0 | 10.0| 1.75 |
| M16 | 24.0 | 16.0 | 14.0| 2.0  |
| M20 | 30.0 | 20.0 | 17.0| 2.5  |

Socket depth `t`: the standard's minimum key engagement is roughly **0.5·k**; use
`t = k/2` unless the user gives a value. Say so rather than quoting a fake figure.

### DIN 7991 — Countersunk Socket Screw (ISO 10642), 90° head
| Thread | dk (head Ø) | k (head height) | s (socket across flats) |
|---|---|---|---|
| M3  | 6.72  | 1.86 | 2.0  |
| M4  | 8.96  | 2.48 | 2.5  |
| M5  | 11.20 | 3.10 | 3.0  |
| M6  | 13.44 | 3.72 | 4.0  |
| M8  | 17.92 | 4.96 | 5.0  |
| M10 | 22.40 | 6.20 | 6.0  |
| M12 | 26.88 | 7.44 | 8.0  |
| M16 | 33.60 | 8.80 | 10.0 |
| M20 | 40.32 | 10.16| 12.0 |

The head is a **90° cone**: it runs from `dk` at the top face down to the shank
diameter `d` over the height `k`. `k` in the table is the "head sits flush"
height — the length `L` of a DIN 7991 screw is measured **including** the head.

### DIN 439 — Thin Hex Nut (ISO 4035)
Across flats `s` is identical to DIN 934; only the height differs.

| Thread | s | m (height) | Coarse pitch |
|---|---|---|---|
| M6  | 10 | 3.0  | 1.0  |
| M8  | 13 | 4.0  | 1.25 |
| M10 | 16 | 5.0  | 1.5  |
| M12 | 18 | 6.0  | 1.75 |
| M16 | 24 | 8.0  | 2.0  |
| M20 | 30 | 10.0 | 2.5  |
| M24 | 36 | 12.0 | 3.0  |

### DIN 125 — Flat Washer, type A (ISO 7089)
| For thread | d1 (inner) | d2 (outer) | t (thickness) |
|---|---|---|---|
| M5  | 5.3  | 10  | 1.0 |
| M6  | 6.4  | 12  | 1.6 |
| M8  | 8.4  | 16  | 1.6 |
| M10 | 10.5 | 20  | 2.0 |
| M12 | 13.0 | 24  | 2.5 |
| M14 | 15.0 | 28  | 2.5 |
| M16 | 17.0 | 30  | 3.0 |
| M20 | 21.0 | 37  | 3.0 |
| M24 | 25.0 | 44  | 4.0 |
| M30 | 31.0 | 56  | 4.0 |

## Templates

### DIN 934 Hex Nut — with revolve-cut chamfers (NOT Chamfer feature)

```python
"""DIN 934 hex nut — parametric. Pass thread spec, get the part."""
import sys, os, math
sys.path.insert(0, r"C:\path	o\inventor-mcp")  # repo root
from src.inventor_api import InventorConnection

# === DIMENSIONS ===
thread = "M16"               # ← change this
s      = 24                  # across flats (look up from table)
m      = 13                  # height
pitch  = 2.0                 # coarse pitch
diameter = 16                # nominal thread diameter (number after M)

# === COMPUTED ===
R         = s / math.sqrt(3)         # circumradius
r_in      = s/2 - 1                  # chamfer inner radius (just inside apothem)
r_out     = s/2 + 2                  # chamfer outer (past corners)
drop      = (r_out - r_in) * math.tan(math.radians(30))   # 30° chamfer

# === BUILD ===
inv = InventorConnection()
inv.connect()
print(inv.create_part(template="metric", name=f"HexNut_{thread}_DIN934"))

# 1. Hex prism (positive extrude!)
inv.create_sketch("XY")
inv.draw_polygon(0, 0, radius=R, sides=6)
inv.extrude(m, "positive", "join")

# 2. Tapped through-hole
inv.hole(x=0, y=0, diameter=diameter, depth=0, tapped=True, pitch=pitch)

# 3. Top chamfer via revolve cut (XZ plane, axis=Z)
inv.create_sketch("XZ")
inv.draw_closed_profile([[r_in, m], [r_out, m], [r_out, m - drop]])
inv.revolve(axis="Z", operation="cut")

# 4. Bottom chamfer via revolve cut
inv.create_sketch("XZ")
inv.draw_closed_profile([[r_in, 0], [r_out, 0], [r_out, drop]])
inv.revolve(axis="Z", operation="cut")

print(inv.save_document(f"./HexNut_{thread}_DIN934.ipt"))
```

**Why revolve-cut chamfer instead of `Chamfer` feature?** The Inventor `Chamfer` knocks the same width off each of the 12 hex edges → 12 small flat facets. The real DIN 934 chamfer is a single **conical** surface that "eats" the corners more deeply than the flats. Verify with a Face Types check: a correctly-built DIN 934 nut shows `Cone: 2` faces.

### DIN 933 Hex Bolt (fully threaded)

```python
thread, s, k = "M16", 24, 10.0
diameter, pitch, length = 16, 2.0, 50    # M16x50

R = s / math.sqrt(3)

inv = InventorConnection(); inv.connect()
inv.create_part(template="metric", name=f"HexBolt_{thread}x{length}_DIN933")

# 1. Hex head
inv.create_sketch("XY")
inv.draw_polygon(0, 0, radius=R, sides=6)
inv.extrude(k, "positive", "join")

# 2. Threaded shaft — extrude from the top face of the head downward
#    (or upward, picking a direction that keeps things tidy)
inv.create_sketch("XY")
inv.draw_circle(0, 0, diameter)
inv.extrude(length, "negative", "join")   # negative = shaft sticks "down" from XY

# 3. Head chamfers (revolve-cut, same pattern as DIN 934)
r_in, r_out = s/2 - 1, s/2 + 2
drop = (r_out - r_in) * math.tan(math.radians(30))
inv.create_sketch("XZ")
inv.draw_closed_profile([[r_in, k], [r_out, k], [r_out, k - drop]])
inv.revolve(axis="Z", operation="cut")

# 4. Thread tip chamfer — small 45° on the bottom end of the shaft
#    (cosmetic, helps the bolt "enter" a hole in assembly)
inv.create_sketch("XZ")
inv.draw_closed_profile([[diameter/2 - 1, -length], [diameter/2, -length], [diameter/2, -length + 1]])
inv.revolve(axis="Z", operation="cut")
```

**Threads on bolts**: Inventor does not render visible helical threads on external surfaces by default — there is no built-in API method exposed via this MCP. The bolt above is a "blank stud" geometry. For documentation drawings, add a cosmetic thread annotation in the drawing view, not on the 3D part.

### DIN 912 Socket Head Cap Screw — hex socket by extrude-cut

```python
import math
d, dk, k, s_socket, pitch, L = 8, 13.0, 8.0, 6.0, 1.25, 40   # M8x40
t_socket = k / 2

inv = InventorConnection(); inv.connect()
inv.create_part(template="metric", name=f"SHCS_M{d}x{L}_DIN912")

# 1. Cylindrical head: z = 0 … k
inv.create_sketch("XY")
inv.draw_circle(0, 0, dk)
inv.extrude(k, "positive", "join")

# 2. Shank: z = 0 … −L (length is measured under the head on DIN 912)
inv.create_sketch("XY")
inv.draw_circle(0, 0, d)
inv.extrude(L, "negative", "join")

# 3. Hex socket — sketch on an OFFSET plane at the head top, cut downward
inv.create_sketch("XY", offset=k)
inv.draw_polygon(0, 0, radius=s_socket / math.sqrt(3), sides=6)   # radius = circumradius!
inv.extrude(t_socket, "negative", "cut")

# 4. Small chamfer on the head's top edge (revolve-cut, same trick as DIN 934)
inv.create_sketch("XZ")
inv.draw_closed_profile([[dk/2 - 0.4, k], [dk/2, k], [dk/2, k - 0.4]])
inv.revolve(axis="Z", operation="cut")
```

`draw_polygon` takes the **circumradius**, while the standard quotes the socket
across flats `s` — always convert with `s / √3`, exactly like the nut hexagon.
The socket must be cut from a sketch on an offset plane at `z = k`: sketching on
the head's top *face* works too, but the face index moves as soon as you add the
next feature.

Verified build, M8×40: V = 2945 mm³ (head 1062 + shank 2011 − socket 125 − chamfer 3).

### DIN 7991 Countersunk Socket Screw — conical head by revolve-join

```python
import math
d, dk, k, s_socket, L = 8, 17.92, 4.96, 5.0, 40      # M8x40
t_socket = 4.4

inv = InventorConnection(); inv.connect()
inv.create_part(template="metric", name=f"CSK_M{d}x{L}_DIN7991")

# 1. Shank downward from the head's top face (z = 0 … −L, head included in L)
inv.create_sketch("XY")
inv.draw_circle(0, 0, d)
inv.extrude(L, "negative", "join")

# 2. 90° conical head — revolve a trapezoid that touches the axis
inv.create_sketch("XZ")
inv.draw_closed_profile([[0, 0], [dk/2, 0], [d/2, -k], [0, -k]])
inv.revolve(axis="Z", operation="join")

# 3. Hex socket from the flat top face
inv.create_sketch("XY")
inv.draw_polygon(0, 0, radius=s_socket / math.sqrt(3), sides=6)
inv.extrude(t_socket, "negative", "cut")
```

The head profile must include the two points **on the axis** (`x = 0`) —
a triangle that stops short of the axis revolves into a ring, not a cone, and
the screw ends up hollow. Check the volume delta of step 2: a solid head adds
material (+437 mm³ for M8), a ring adds noticeably less.

Verified build, M8×40: V = 2352 mm³, bbox Ø17.92 × 40.

### DIN 439 Thin Hex Nut

Same recipe as DIN 934 with the smaller height `m` from the table — including the
two revolve-cut conical chamfers. Reuse the nut template and change three numbers:

```python
thread, s, m, pitch, diameter = "M16", 24, 8.0, 2.0, 16   # DIN 439 M16
```

Verified build, M16: V = 2662 mm³, and `list_faces` shows `Cone: 2` — the same
acid test as DIN 934. If you see 12 small planar facets instead, the Chamfer
feature was used by mistake.

### DIN 125 Washer

```python
thread, d1, d2, t = "M16", 17.0, 30, 3.0

inv = InventorConnection(); inv.connect()
inv.create_part(template="metric", name=f"Washer_{thread}_DIN125")

# Outer ring
inv.create_sketch("XY")
inv.draw_circle(0, 0, d2)
inv.extrude(t, "positive", "join")

# Inner hole
inv.create_sketch("XY")
inv.draw_circle(0, 0, d1)
inv.extrude(extent_type="all", operation="cut")
```

(A washer doesn't need a `hole()` feature — simple circle + extrude cut is cleaner.)

### DIN 2573 / EN 1092 Welding Flange (PN6, DN150)

This is the "blind disc with bolt circle" pattern. For DN150 PN6:
- Outer Ø D = 285 mm, thickness ≈ 22 mm
- Bore Ø d = 168 mm
- Bolt PCD = 240 mm, 8× Ø18 bolt holes (M16)

```python
inv = InventorConnection(); inv.connect()
inv.create_part(template="metric", name="DIN2573_DN150_PN6")

# Disc
inv.create_sketch("XY")
inv.draw_circle(0, 0, 285)
inv.extrude(22, "positive", "join")

# Bore (with PCD as construction circle for documentation)
inv.create_sketch("XY")
inv.draw_circle(0, 0, 168)
inv.draw_circle(0, 0, 240, construction=True)   # bolt PCD ref
inv.extrude(extent_type="all", operation="cut")

# One M16 bolt hole at PCD, then circular pattern × 8
inv.hole(x=120, y=0, diameter=16, depth=0, tapped=False)
features = inv.list_features()
hole_idx = features[-1]["index"]
inv.circular_pattern(feature_index=hole_idx, count=8, angle=360, axis="Z")
```

## Strategy for unfamiliar standards

If the user asks for a standard not listed above (e.g., "DIN 580 eye bolt", "DIN 6912 low-head socket cap"):

1. Acknowledge: "У мене немає таблиці DIN 580 в шаблонах. Ось ключові розміри з пам'яті: [...]. Підтвердиш?"
2. Ask the user to confirm 2-3 critical dimensions (across flats / outer Ø / thread Ø / height).
3. Build using whichever feature pattern fits (extrude + hole + chamfer + revolve, etc.).
4. **Don't fabricate dimensions** — for safety-critical parts the user may rely on the model, so verified numbers matter.

## Execution conventions

- Default to **Python script** (`python -X utf8 my_part.py`), not raw MCP tool calls. Scripts are easier to iterate, more readable, and reload the latest `inventor_api.py` automatically (no MCP server restart needed). Save scripts under `the inventor-mcp project root\`.
- Use **unique filenames** for each variant (`HexNut_M16_DIN934.ipt`, `HexNut_M16_DIN934_v2.ipt`). Saving over an open file fails with `E_INVALIDARG`.
- After build, run a one-line verification: face count + volume + Z range. Catches "feature created but didn't cut" silently.
- Report concrete results (file name, volume, face count) so the user can verify at a glance.
