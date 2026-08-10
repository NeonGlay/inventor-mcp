"""Live smoke test against a real Inventor installation.

Exercises every geometry-creating code path once and reports PASS/FAIL per step,
so a new Inventor release can be qualified in a couple of minutes:

    python tests/smoke_test.py            # starts Inventor if not running
    python tests/smoke_test.py --keep     # leave the test documents open

Nothing is saved to disk; the scratch documents are closed without saving
unless --keep is given. Exit code is the number of failed steps.
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import inventor_api as api  # noqa: E402


class Runner:
    def __init__(self):
        self.passed = 0
        self.failed = []

    def step(self, label, fn):
        try:
            result = fn()
        except Exception as e:
            self.failed.append((label, f"{type(e).__name__}: {e}"))
            print(f"  FAIL  {label}\n        {type(e).__name__}: {e}")
            if os.environ.get("SMOKE_TRACE"):
                traceback.print_exc()
            return None
        self.passed += 1
        print(f"  ok    {label}" + (f"  -> {result}" if isinstance(result, str) else ""))
        return result


def check_enums(inv, run):
    """Verify the hard-coded enum constants against the live type library."""
    import pythoncom
    import winreg

    expected = {
        "DocumentTypeEnum": {"kPartDocumentObject": api.kPartDocumentObject},
        "DimensionOrientationEnum": {
            "kHorizontalDim": api.kHorizontalDim,
            "kVerticalDim": api.kVerticalDim,
            "kAlignedDim": api.kAlignedDim,
        },
        "PartFeatureOperationEnum": {
            "kJoinOperation": api.kJoinOperation,
            "kCutOperation": api.kCutOperation,
            "kIntersectOperation": api.kIntersectOperation,
            "kSurfaceOperation": api.kSurfaceOperation,
            "kNewBodyOperation": api.kNewBodyOperation,
        },
        "PartFeatureExtentDirectionEnum": {
            "kPositiveExtentDirection": api.kPositiveExtentDirection,
            "kNegativeExtentDirection": api.kNegativeExtentDirection,
            "kSymmetricExtentDirection": api.kSymmetricExtentDirection,
        },
    }

    # Locate the Inventor type library without touching win32com's gencache
    # (EnsureDispatch would write %TEMP%\gen_py and break GetActiveObject).
    tlb = None
    root = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "TypeLib")
    i = 0
    while tlb is None:
        try:
            guid = winreg.EnumKey(root, i)
        except OSError:
            break
        i += 1
        try:
            k = winreg.OpenKey(root, guid)
            ver = winreg.EnumKey(k, 0)
            name = winreg.QueryValue(winreg.OpenKey(k, ver), None)
        except OSError:
            continue
        if name and "Inventor Object Library" in name:
            major, _, minor = ver.partition(".")
            tlb = pythoncom.LoadRegTypeLib(guid, int(major, 16), int(minor or "0", 16), 0)

    if tlb is None:
        run.failed.append(("enums", "Inventor type library not found in registry"))
        print("  FAIL  enum verification: type library not found")
        return

    actual = {}
    for idx in range(tlb.GetTypeInfoCount()):
        if tlb.GetTypeInfoType(idx) != pythoncom.TKIND_ENUM:
            continue
        ename = tlb.GetDocumentation(idx)[0]
        if ename not in expected:
            continue
        ti = tlb.GetTypeInfo(idx)
        members = {}
        for v in range(ti.GetTypeAttr().cVars):
            vd = ti.GetVarDesc(v)
            members[ti.GetNames(vd[0])[0]] = vd[1]
        actual[ename] = members

    for ename, members in expected.items():
        for mname, mvalue in members.items():
            live = actual.get(ename, {}).get(mname)
            run.step(
                f"enum {ename}.{mname} == {mvalue}",
                lambda live=live, mvalue=mvalue, mname=mname: (
                    f"{mvalue}"
                    if live == mvalue
                    else _raise(f"type library says {mname} = {live}, code has {mvalue}")
                ),
            )


def _raise(msg):
    raise AssertionError(msg)


def part_tests(inv, run):
    run.step("create_part(metric)", lambda: inv.create_part("smoke_part"))
    run.step("create_sketch(XY)", lambda: inv.create_sketch("XY"))
    run.step("draw_rectangle", lambda: inv.draw_rectangle(0, 0, 80, 60))
    run.step("extrude 10mm", lambda: inv.extrude(10, "positive", "join"))
    run.step("hole drilled through", lambda: inv.hole(25, 15, diameter=8))
    run.step("hole tapped M10", lambda: inv.hole(-25, 15, diameter=10, tapped=True))
    run.step("fillet r3", lambda: inv.fillet(3, None))
    run.step("list_edges", lambda: inv.list_edges()[:120])
    run.step("list_faces", lambda: inv.list_faces()[:120])
    run.step("find_face(top z=10)", lambda: inv.find_face(z=10))
    run.step("inspect", lambda: str(inv.inspect())[:120])
    run.step("list_features", lambda: str(inv.list_features())[:120])
    run.step("get_parameters", lambda: f"{len(inv.get_parameters())} parameters")
    run.step("add_parameter", lambda: inv.add_parameter("smoke_len", "42 mm"))
    run.step("set_parameter", lambda: inv.set_parameter("smoke_len", "43 mm"))
    run.step("transaction begin", lambda: inv.transaction("begin", "smoke"))
    run.step("transaction abort", lambda: inv.transaction("abort"))

    # chamfer + circular pattern on a fresh, simpler body
    run.step("create_part(metric) #2", lambda: inv.create_part("smoke_part2"))
    run.step("create_sketch(XY) #2", lambda: inv.create_sketch("XY"))
    run.step("draw_circle D40", lambda: inv.draw_circle(0, 0, 40))
    run.step("extrude 20mm", lambda: inv.extrude(20, "positive", "join"))
    run.step("chamfer 2mm", lambda: inv.chamfer(2, None))

    run.step("create_part(metric) #2b", lambda: inv.create_part("smoke_pattern"))
    run.step("create_sketch(XY) #2b", lambda: inv.create_sketch("XY"))
    run.step("draw_polygon hex", lambda: inv.draw_polygon(0, 0, 30, 6))
    run.step("extrude 12mm", lambda: inv.extrude(12, "positive", "join"))
    run.step("hole for pattern", lambda: inv.hole(10, 0, diameter=4))
    run.step("circular_pattern x6", lambda: inv.circular_pattern(2, 6, 360))
    run.step("suppress feature", lambda: inv.suppress_feature([3], True))
    run.step("unsuppress feature", lambda: inv.suppress_feature([3], False))
    run.step("delete feature", lambda: inv.delete_feature([3]))

    run.step("create_part(metric) #3", lambda: inv.create_part("smoke_revolve"))
    run.step("create_sketch(XY) #3", lambda: inv.create_sketch("XY"))
    run.step("draw_rectangle offset", lambda: inv.draw_rectangle(30, 10, 20, 20))
    run.step("revolve 360 about Y", lambda: inv.revolve(360, None, "Y", "join"))


def sheet_metal_tests(inv, run):
    run.step("create_part(sheet_metal)", lambda: inv.create_part("smoke_sm", "sheet_metal"))
    run.step("set_sheet_metal_thickness", lambda: inv.set_sheet_metal_thickness(2))
    run.step("create_sketch(XY) sm", lambda: inv.create_sketch("XY"))
    run.step("draw_rectangle sm", lambda: inv.draw_rectangle(0, 0, 100, 60))
    run.step("sheet_metal_face", lambda: inv.sheet_metal_face())
    idx = run.step("find_edge(x=50,y=0,z=0)", lambda: inv.find_edge(x=50, y=0, z=0))
    if isinstance(idx, int):
        run.step("flange 20mm", lambda: inv.flange([idx], 20, 90))
        run.step("create_sketch on top face", lambda: inv.create_sketch(face_index=inv.find_face(z=2)))
        run.step("draw_circle for cut", lambda: inv.draw_circle(0, 0, 20))
        run.step("sheet_metal_cut", lambda: inv.sheet_metal_cut())
    else:
        run.failed.append(("flange", "no edge found to flange"))
        print("  FAIL  flange: find_edge returned no usable index")


def main():
    keep = "--keep" in sys.argv
    inv = api.InventorConnection()
    run = Runner()

    print("Inventor MCP smoke test")
    print("-" * 60)
    try:
        print(" ", inv.connect())
    except Exception as e:
        print(f"Cannot connect to Inventor: {e}")
        return 1
    print("  version:", inv.app.SoftwareVersion.DisplayVersion)
    print()

    print("Enum constants vs. live type library:")
    check_enums(inv, run)
    print("\nPart modeling:")
    part_tests(inv, run)
    print("\nSheet metal:")
    sheet_metal_tests(inv, run)

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
