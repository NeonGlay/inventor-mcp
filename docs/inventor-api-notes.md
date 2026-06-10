# Inventor 2026 COM API — Field Notes

Empirically verified knowledge from driving Autodesk Inventor 2026 through `pywin32`
dynamic dispatch. Much of this contradicts the official documentation or is
documented nowhere. Every item here was discovered by hitting the error first.

## Enum values (Inventor 2026)

```python
# DocumentTypeEnum
kPartDocumentObject = 12290     # NOT 12289 as often quoted!

# PartFeatureExtentDirectionEnum
kPositiveExtentDirection  = 20993
kNegativeExtentDirection  = 20994
kSymmetricExtentDirection = 20995

# PartFeatureOperationEnum
kJoinOperation      = 20481
kCutOperation       = 20482
kIntersectOperation = 20483
kSurfaceOperation   = 20484
kNewBodyOperation   = 20485

# DimensionOrientationEnum — docs say 40706/40707/40708; reality:
kHorizontalDim = 19201
kVerticalDim   = 19202
kAlignedDim    = 19203

# SurfaceTypeEnum (Face.SurfaceType)
# 5890=Plane, 5891=Cylinder, 5892/5893=Cone, 5894=Sphere, 5895=Torus
```

## Internal units are CENTIMETERS

All COM API geometry is in cm. Divide millimeters by 10 everywhere.
Angles are radians in most (but not all) places — see Flange below.

## gencache breaks GetActiveObject

`win32com.client.gencache.EnsureDispatch("Inventor.Application")` generates a
`gen_py` typed cache. After that, plain `GetActiveObject` fails with
`KeyError: '_dispobj_'` **until you delete `%LOCALAPPDATA%\Temp\gen_py`**.

But gencache is invaluable for one-off API discovery — typed signatures show
arguments that dynamic dispatch can't tell you about. Workflow:
1. Run a probe script with `EnsureDispatch` + `CastTo` in a separate process
2. Record the signatures you need
3. Delete `gen_py`, verify `GetActiveObject` works again
4. Continue with dynamic dispatch

With typed bindings, sheet-metal collections require casts:
```python
smf  = CastTo(comp.Features, "SheetMetalFeatures")
smcd = CastTo(part_doc.ComponentDefinition, "SheetMetalComponentDefinition")
```
(Dynamic dispatch reaches `comp.Features.FlangeFeatures` directly — no cast.)

## Chamfer — API changed in 2026

`CreateChamferDefinition()` was **removed**. Use:
```python
ec = app.TransientObjects.CreateEdgeCollection()   # EdgeCollection, NOT ObjectCollection!
ec.Add(body.Edges.Item(i))
comp.Features.ChamferFeatures.AddUsingDistance(ec, dist_cm)
# also: AddUsingDistanceAndAngle, AddUsingTwoDistances
```
Put ALL edges in ONE call — edge indices renumber after each feature.

## Revolve

- Full 360°: `RevolveFeatures.AddFull(profile, axis_entity, operation)`
- Partial: `AddByAngle(profile, axis, angle_RAD, direction, operation)`
- Preferred axis: a WorkAxis (`comp.WorkAxes.Item(1/2/3)` = X/Y/Z) — no
  construction line needed in the sketch.
- Do NOT use `CreateRevolveDefinition` + `SetAngleExtent`.

## HoleFeature

`CreateSimpleHoleDef` doesn't exist in 2026. Patterns that work:

```python
# Sketch-point placement
col = app.TransientObjects.CreateObjectCollection()   # of SketchPoints
col.Add(sketch_point)
pl = hf.CreateSketchPlacementDefinition(col)
hf.AddDrilledByThroughAllExtent(pl, diameter_cm_or_TapInfo, direction)
hf.AddDrilledByDistanceExtent(pl, dia_or_tap, depth_cm, direction)

# Edge-referenced (parametric) placement — survives part resizing
pl = hf.CreateLinearPlacementDefinition(face, edge1, d1_cm, edge2, d2_cm,
                                        bias_point)   # Point3d — REQUIRED
# bias_point disambiguates among 4 possible positions; compute it by stepping
# from each reference edge toward the face centroid.

# Counterbore (e.g. M5 socket head cap screw seat: Ø5.5 hole, Ø10×5.5 seat)
hf.AddCBoreByDistanceExtent(pl, 0.55, depth_cm, direction, 1.0, 0.55)
```

Gotchas:
- The hole-placement sketch must contain ONLY `SketchPoints.Add()` — a single
  construction line in it makes `AddDrilledByThroughAllExtent` fail with E_FAIL.
- Drill direction (positive/negative) into material is not predictable from the
  face normal. Create the feature, check `MassProperties.Volume` dropped, flip
  direction and retry if it didn't.
- Bodies extruded in the "negative" direction can make through-all holes
  silently remove nothing. Extrude bodies positive.

### Tapped holes (TapInfo)

```python
tap = hf.CreateTapInfo(True, "ISO Metric profile", "M16x2", "6H", True)
```
- ThreadType must be the **exact** sheet name from
  `Design Data\XLS\en-US\thread.xlsx` (e.g. `"ISO Metric profile"`).
- Designation: integer pitches WITHOUT decimal — `"M16x2"`, not `"M16x2.0"`.
- TapInfo works with both through-all and distance extents.

## Sketch dimensions

- `DimensionConstraints.AddDiameter(circle, textPt)` — straightforward.
- `AddTwoPointDistance(p1, p2, orientation, textPt)` — the points must be
  **line endpoints or projected points**; standalone `SketchPoints.Add()` gives
  E_UNEXPECTED (0x8000FFFF).
- Project the origin into the sketch to dimension from it:
  `sketch.AddByProjectingEntity(comp.WorkPoints.Item(1))`.
- Project axes as construction lines for symmetry/coincident constraints:
  result is collection-like — take `.Item(1)`, set `.Construction = True`.
- Prefer `GeometricConstraints.AddCoincident(center, projected_axis)` over
  zero-value dimensions; `AddSymmetry(l1, l2, axis_line)` to center base sketches.

## Sheet Metal (2026)

```python
comp.ActiveSheetMetalStyle.Thickness = "0,8 mm"   # comma decimal on European locales
```

**Face** (base panel): `ff.Add(ff.CreateFaceFeatureDefinition(profile))`.

**Flange** — the big trap:
```python
fdef = flf.CreateFlangeDefinition(edge_collection, angle_RADIANS, distance)
feat = flf.Add(fdef)
feat.Definition.HeightExtent.Distance.Expression = "450 mm"   # ← the real height
doc.Update()
```
- The `distance` argument of `CreateFlangeDefinition` is **silently ignored** —
  the flange is always created ~25 mm tall. Set the real height afterwards via
  the `Distance` Parameter's `.Expression`.
- The angle is in **radians**. Pass `90` and Inventor stores 90·180/π ≈ 5157°.
- Default `HeightDatumType` 75521 = "From Outer Intersection": the Distance
  equals the visible outer height (material thickness not subtracted).

**Cut**: sketch ON the panel face (not a work plane) → `CreateCutDefinition(profile)`
→ `Add`. Depth then defaults to the Thickness parameter, so the cut stays
correct when thickness changes. One sketch with many closed loops = one Cut
with many holes. Avoid extrude-cuts for sheet metal — they hardcode the depth.

**Flat Pattern** is the acid test: if it unfolds, your geometry is real sheet
metal; extrude-built "walls" look identical but won't unfold.

## Sketch-plane axis mapping

| Plane | sketch X | sketch Y |
|---|---|---|
| XY (WorkPlanes.Item(3)) | world +X | world +Y |
| XZ (Item 2) | **world −X (mirrored!)** | world +Z |
| YZ (Item 1) | world +Y | world +Z |

Offset planes: `comp.WorkPlanes.AddByPlaneAndOffset(base_wp, offset_cm)`;
offset is along the plane normal (XY→+Z, XZ→+Y, YZ→+X). Offset-from-XY planes
map directly (x→X, y→Y). Set `wp.Visible = False`.

**Sketch on a face**: the origin is at a face corner, not the center, and axes
can flip. Always verify with
`sketch.SketchToModelSpace(tg.CreatePoint2d(x_cm, y_cm))` → world Point3d.

## Topology pitfalls

- **Edge/face indices renumber after every feature.** Re-find by midpoint /
  centroid coordinates, never cache indices across features.
- **Fillets shift adjacent edges** — a fillet extends/shortens its neighbours,
  moving their midpoints. Re-scan topology after every fillet.
- **Feature order vs cuts**: material added after a cut fills the cut where
  they overlap. Adding a rib under an already-bored hub? Stop it below the
  bore's bottom, or reorder the feature tree.

## Misc

- `doc.SaveAs(path)` fails with E_INVALIDARG if the file is already open under
  that name — use `doc.Save()` for re-saves.
- Inventor numbers sketches/features globally and never reuses deleted numbers.
  Rename features (`feat.Name = "Bore20"`) for reliable references.
- Console scripts printing Unicode (Ø, ×, Cyrillic) need `python -X utf8` on
  Windows (cp1251/cp1252 consoles).
- `app.TransactionManager.StartTransaction(doc, "name")` → `.End()` / `.Abort()`
  wraps multi-feature operations into one undo unit with reliable rollback.
