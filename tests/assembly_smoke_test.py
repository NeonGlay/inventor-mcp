"""Live smoke test for the assembly (IAM) tools.

Builds two scratch parts on disk, places them in a new assembly, constrains them
by origin geometry and by an Insert constraint, then reports PASS/FAIL per step.

    python tests/assembly_smoke_test.py
    python tests/assembly_smoke_test.py --keep    # leave the documents open

Scratch files go to %TEMP%\\inventor_mcp_smoke and are not cleaned up, because
an assembly keeps references to the parts it places.
"""
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from src import inventor_api as api  # noqa: E402
from smoke_test import Runner  # noqa: E402


def build_parts(inv, run, workdir):
    """A 40x40x10 plate with a Ø10 through hole, and a Ø10x30 pin."""
    plate = os.path.join(workdir, "smoke_plate.ipt")
    pin = os.path.join(workdir, "smoke_pin.ipt")

    run.step("part: plate", lambda: inv.create_part("smoke_plate"))
    run.step("plate sketch", lambda: inv.create_sketch("XY"))
    run.step("plate rectangle", lambda: inv.draw_rectangle(0, 0, 40, 40))
    run.step("plate extrude", lambda: inv.extrude(10))
    run.step("plate hole", lambda: inv.hole(0, 0, diameter=10))
    run.step("plate save", lambda: inv.save_document(plate))

    run.step("part: pin", lambda: inv.create_part("smoke_pin"))
    run.step("pin sketch", lambda: inv.create_sketch("XY"))
    run.step("pin circle", lambda: inv.draw_circle(0, 0, 10))
    run.step("pin extrude", lambda: inv.extrude(30))
    run.step("pin save", lambda: inv.save_document(pin))

    return plate, pin


def assembly_tests(inv, run, plate, pin):
    run.step("create_assembly", lambda: inv.create_assembly("smoke_asm"))
    run.step("place plate (grounded)",
             lambda: inv.place_component(plate, 0, 0, 0, grounded=True))
    run.step("place pin", lambda: inv.place_component(pin, 60, 0, 0))
    run.step("list_occurrences", lambda: inv.list_occurrences())
    run.step("assembly_info", lambda: str(inv.assembly_info())[:160])

    run.step("mate XY planes",
             lambda: inv.constrain(1, "XY", 2, "XY", "mate", offset=0))
    run.step("list_constraints", lambda: inv.list_constraints())
    run.step("delete_constraint", lambda: inv.delete_constraint(1))

    run.step("flush XZ planes",
             lambda: inv.constrain(1, "XZ", 2, "XZ", "flush", offset=5))
    run.step("angle Z axes",
             lambda: inv.constrain(1, "Z", 2, "Z", "angle", angle=0))
    run.step("delete both constraints",
             lambda: (inv.delete_constraint(2), inv.delete_constraint(1))[1])

    edges = run.step("list_component_edges(plate)",
                     lambda: inv.list_component_edges(1))
    pin_edges = run.step("list_component_edges(pin)",
                         lambda: inv.list_component_edges(2))
    e1 = _first(edges)
    e2 = _first(pin_edges)
    if e1 and e2:
        run.step("insert constraint (pin into hole)",
                 lambda: inv.constrain_insert(1, e1, 2, e2, offset=0))
        run.step("pin moved into place", lambda: _assert_mated(inv))
    else:
        run.failed.append(("insert", "no circular edges found"))
        print("  FAIL  insert: no circular edges found")

    run.step("ground pin", lambda: inv.ground_occurrence(2, True))
    run.step("unground pin", lambda: inv.ground_occurrence(2, False))
    run.step("delete_occurrence", lambda: inv.delete_occurrence(2))


def _first(text):
    """First index out of a '[i] circle ...' listing."""
    import re
    if not isinstance(text, str):
        return None
    m = re.search(r"^\[(\d+)\]", text, re.M)
    return int(m.group(1)) if m else None


def _assert_mated(inv):
    """The pin was placed 60mm off in X; the Insert constraint must pull it back."""
    info = inv.assembly_info()
    pin = info["components"][1]
    dx = abs(pin["position_mm"][0])
    if dx > 1.0:
        raise AssertionError(f"pin still {dx:.1f}mm off in X — constraint did not solve")
    return f"pin at x={pin['position_mm'][0]:.2f}mm"


def main():
    keep = "--keep" in sys.argv
    workdir = os.path.join(tempfile.gettempdir(), "inventor_mcp_smoke")
    os.makedirs(workdir, exist_ok=True)

    inv = api.InventorConnection()
    run = Runner()

    print("Inventor MCP assembly smoke test")
    print("-" * 60)
    try:
        print(" ", inv.connect())
    except Exception as e:
        print(f"Cannot connect to Inventor: {e}")
        return 1
    print("  version:", inv.app.SoftwareVersion.DisplayVersion)
    print("  workdir:", workdir)

    print("\nScratch parts:")
    plate, pin = build_parts(inv, run, workdir)
    print("\nAssembly:")
    assembly_tests(inv, run, plate, pin)

    if not keep:
        print("\nClosing scratch documents...")
        for doc in list(inv.app.Documents):
            try:
                doc.Close(True)  # SkipSave
            except Exception:
                pass

    print("\n" + "-" * 60)
    print(f"{run.passed} passed, {len(run.failed)} failed")
    for label, err in run.failed:
        print(f"  FAILED  {label}: {err}")
    return len(run.failed)


if __name__ == "__main__":
    sys.exit(main())
