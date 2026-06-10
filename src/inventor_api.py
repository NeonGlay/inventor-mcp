"""Wrapper around Autodesk Inventor COM API."""

import os
import win32com.client
import pythoncom


# Inventor 2026 enum constants (from type library)
# PartFeatureExtentDirectionEnum
kPositiveExtentDirection = 20993
kNegativeExtentDirection = 20994
kSymmetricExtentDirection = 20995

# PartFeatureOperationEnum
kJoinOperation = 20481
kCutOperation = 20482
kIntersectOperation = 20483
kSurfaceOperation = 20484
kNewBodyOperation = 20485

# DocumentTypeEnum
kPartDocumentObject = 12290

# DimensionOrientationEnum (from Inventor 2026 type library — NOT 40706/40707/40708!)
kHorizontalDim = 19201
kVerticalDim   = 19202
kAlignedDim    = 19203


class InventorConnection:
    def __init__(self):
        self._app = None

    @property
    def app(self):
        if self._app is None:
            raise RuntimeError(
                "Not connected to Inventor. Call connect() first."
            )
        return self._app

    def connect(self, visible: bool = True) -> str:
        pythoncom.CoInitialize()
        try:
            self._app = win32com.client.GetActiveObject("Inventor.Application")
            return f"Connected to running Inventor {self._app.SoftwareVersion.DisplayVersion}"
        except Exception:
            pass
        try:
            self._app = win32com.client.Dispatch("Inventor.Application")
            self._app.Visible = visible
            return f"Started Inventor {self._app.SoftwareVersion.DisplayVersion}"
        except Exception as e:
            raise RuntimeError(f"Cannot connect to Inventor: {e}")

    def is_connected(self) -> bool:
        if self._app is None:
            return False
        try:
            _ = self._app.SoftwareVersion
            return True
        except Exception:
            self._app = None
            return False

    # ---------- Document management ----------

    def create_part(self, name: str | None = None, template: str = "metric") -> str:
        import glob

        templates_path = self.app.FileLocations.TemplatesPath

        if template.lower() in ("sheet_metal", "sheetmetal", "sm"):
            # Sheet Metal template (metric mm)
            candidates_patterns = [
                os.path.join(templates_path, "Metric", "Sheet Metal (mm).ipt"),
                os.path.join(templates_path, "**", "Sheet Metal (mm).ipt"),
                os.path.join(templates_path, "Sheet Metal.ipt"),
            ]
            template_file = None
            for pattern in candidates_patterns:
                if "*" in pattern:
                    found = glob.glob(pattern, recursive=True)
                    if found:
                        template_file = found[0]
                        break
                elif os.path.exists(pattern):
                    template_file = pattern
                    break
            if template_file is None:
                raise RuntimeError(f"Cannot find Sheet Metal template in {templates_path}")
        elif template.lower() == "metric":
            # Search for metric template (mm)
            candidates_patterns = [
                os.path.join(templates_path, "Metric", "Standard (mm).ipt"),
                os.path.join(templates_path, "Metric", "Standard.ipt"),
                os.path.join(templates_path, "**", "Standard (mm).ipt"),
            ]
            template_file = None
            for pattern in candidates_patterns:
                if "*" in pattern:
                    found = glob.glob(pattern, recursive=True)
                    if found:
                        template_file = found[0]
                        break
                elif os.path.exists(pattern):
                    template_file = pattern
                    break
            if template_file is None:
                # Fallback: any .ipt template
                fallback = glob.glob(os.path.join(templates_path, "**", "*.ipt"), recursive=True)
                if fallback:
                    template_file = fallback[0]
                else:
                    raise RuntimeError(f"Cannot find metric template in {templates_path}")
        elif template.lower() == "english":
            candidates_patterns = [
                os.path.join(templates_path, "en-US", "Standard.ipt"),
                os.path.join(templates_path, "Standard.ipt"),
                os.path.join(templates_path, "**", "Standard.ipt"),
            ]
            template_file = None
            for pattern in candidates_patterns:
                if "*" in pattern:
                    found = glob.glob(pattern, recursive=True)
                    if found:
                        template_file = found[0]
                        break
                elif os.path.exists(pattern):
                    template_file = pattern
                    break
            if template_file is None:
                raise RuntimeError(f"Cannot find English template in {templates_path}")
        else:
            # template is a direct file path
            template_file = template
            if not os.path.exists(template_file):
                raise RuntimeError(f"Template not found: {template_file}")

        doc = self.app.Documents.Add(12290, template_file, True)
        if name:
            try:
                doc.DisplayName = name
            except Exception:
                pass  # DisplayName may be read-only before first save
        return f"Part created: {doc.DisplayName}"

    def active_document(self):
        doc = self.app.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document open in Inventor.")
        return doc

    def active_part(self):
        doc = self.active_document()
        if doc.DocumentType != 12290:  # kPartDocumentObject
            raise RuntimeError(
                f"Active document is not a part (type={doc.DocumentType})."
            )
        return doc.ComponentDefinition

    def save_document(self, path: str | None = None) -> str:
        doc = self.active_document()
        if path:
            path = os.path.abspath(path)
            doc.SaveAs(path, False)
            return f"Saved as: {path}"
        doc.Save()
        return f"Saved: {doc.FullFileName}"

    def export_document(self, path: str, format: str = "STEP") -> str:
        doc = self.active_document()
        path = os.path.abspath(path)

        format_upper = format.upper()
        if format_upper == "STEP":
            translator = "Autodesk Inventor STEP Translator"
        elif format_upper == "STL":
            translator = "Autodesk Inventor STL Translator"
        elif format_upper == "SAT":
            translator = "Autodesk Inventor SAT Translator"
        elif format_upper == "IGES":
            translator = "Autodesk Inventor IGES Translator"
        else:
            raise ValueError(f"Unsupported format: {format}. Use STEP, STL, SAT, or IGES.")

        context = self.app.TransientObjects.CreateTranslationContext()
        context.Type = 13059  # kFileBrowseIOMechanism
        options = self.app.TransientObjects.CreateNameValueMap()
        data_medium = self.app.TransientObjects.CreateDataMedium()
        data_medium.FileName = path

        addins = self.app.ApplicationAddIns
        found = None
        for i in range(1, addins.Count + 1):
            addin = addins.Item(i)
            if hasattr(addin, "DisplayName") and translator.lower() in addin.DisplayName.lower():
                found = addin
                break

        if found is None:
            raise RuntimeError(f"Translator not found: {translator}")

        if hasattr(found, "SaveCopyAs"):
            found.SaveCopyAs(doc, context, options, data_medium)
        else:
            doc.SaveAs(path, False)

        return f"Exported to: {path} ({format_upper})"

    # ---------- Sketches ----------

    def create_sketch(
        self,
        plane: str = "XY",
        face_index: int | None = None,
        offset: float = 0,
    ) -> str:
        """Create a sketch on a work plane, a body face, or an OFFSET work plane.

        offset (mm): creates a hidden work plane parallel to 'plane' at this
        distance and sketches on it. Offset direction: positive = along the
        plane's normal (XY→+Z, XZ→+Y, YZ→+X). Essential for features that
        don't start at the origin planes (ribs, bosses at a height).
        """
        comp = self.active_part()

        if face_index is not None:
            # Create sketch on a body face
            body = comp.SurfaceBodies.Item(1)
            if face_index < 1 or face_index > body.Faces.Count:
                raise ValueError(
                    f"face_index={face_index} out of range. Body has {body.Faces.Count} faces."
                )
            face = body.Faces.Item(face_index)
            sketch = comp.Sketches.Add(face)
            return f"Sketch created on face {face_index} (Sketch{comp.Sketches.Count})"

        planes = {
            "XY": comp.WorkPlanes.Item(3),  # XY plane
            "XZ": comp.WorkPlanes.Item(2),  # XZ plane
            "YZ": comp.WorkPlanes.Item(1),  # YZ plane
        }
        wp = planes.get(plane.upper())
        if wp is None:
            raise ValueError(f"Unknown plane: {plane}. Use XY, XZ, or YZ.")

        if offset:
            wp = comp.WorkPlanes.AddByPlaneAndOffset(wp, offset / 10.0)
            wp.Visible = False
            sketch = comp.Sketches.Add(wp)
            return (f"Sketch created on {plane.upper()}{offset:+g}mm offset plane "
                    f"(Sketch{comp.Sketches.Count})")

        sketch = comp.Sketches.Add(wp)
        return f"Sketch created on {plane.upper()} plane (Sketch{comp.Sketches.Count})"

    def _get_sketch(self, sketch_index: int | None = None):
        comp = self.active_part()
        if sketch_index is not None:
            return comp.Sketches.Item(sketch_index)
        return comp.Sketches.Item(comp.Sketches.Count)

    def _tg(self):
        return self.app.TransientGeometry

    def draw_rectangle(
        self,
        x: float = 0, y: float = 0,
        width: float = 100, height: float = 50,
        sketch_index: int | None = None,
    ) -> str:
        sketch = self._get_sketch(sketch_index)
        tg = self._tg()
        # All dimensions in cm (Inventor internal units)
        w = width / 10.0
        h = height / 10.0
        cx = x / 10.0
        cy = y / 10.0
        sketch.SketchLines.AddAsTwoPointRectangle(
            tg.CreatePoint2d(cx - w / 2, cy - h / 2),
            tg.CreatePoint2d(cx + w / 2, cy + h / 2),
        )
        return f"Rectangle {width}x{height}mm at ({x},{y})"

    def draw_circle(
        self,
        x: float = 0, y: float = 0,
        diameter: float = 50,
        sketch_index: int | None = None,
        construction: bool = False,
    ) -> str:
        """Draw a circle with an automatic diameter dimension constraint.
        construction=True draws a reference (non-profile) circle, e.g. bolt PCD.
        """
        sketch = self._get_sketch(sketch_index)
        tg = self._tg()
        r = (diameter / 10.0) / 2.0
        cx = x / 10.0
        cy = y / 10.0
        circle = sketch.SketchCircles.AddByCenterRadius(
            tg.CreatePoint2d(cx, cy), r
        )
        if construction:
            circle.Construction = True

        # Add diameter dimension — text placed just outside the circle
        text_x = cx + r * 0.8
        text_y = cy + r * 0.6
        try:
            sketch.DimensionConstraints.AddDiameter(
                circle, tg.CreatePoint2d(text_x, text_y)
            )
        except Exception:
            pass  # dimension already exists or sketch is consumed

        suffix = " [construction]" if construction else ""
        return f"Circle D={diameter}mm at ({x},{y}){suffix}"

    def draw_line(
        self,
        x1: float = 0, y1: float = 0,
        x2: float = 100, y2: float = 0,
        sketch_index: int | None = None,
        construction: bool = False,
    ) -> str:
        sketch = self._get_sketch(sketch_index)
        tg = self._tg()
        line = sketch.SketchLines.AddByTwoPoints(
            tg.CreatePoint2d(x1 / 10.0, y1 / 10.0),
            tg.CreatePoint2d(x2 / 10.0, y2 / 10.0),
        )
        if construction:
            line.Construction = True
        suffix = " [construction]" if construction else ""
        return f"Line from ({x1},{y1}) to ({x2},{y2})mm{suffix}"

    def draw_polygon(
        self,
        x: float = 0, y: float = 0,
        radius: float = 25,
        sides: int = 6,
        sketch_index: int | None = None,
    ) -> str:
        import math
        sketch = self._get_sketch(sketch_index)
        tg = self._tg()
        r = radius / 10.0
        cx = x / 10.0
        cy = y / 10.0
        points = []
        for i in range(sides):
            angle = 2 * math.pi * i / sides - math.pi / 2
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            points.append(tg.CreatePoint2d(px, py))
        # Draw connected lines — share endpoints for proper profile
        first_line = sketch.SketchLines.AddByTwoPoints(points[0], points[1])
        prev_line = first_line
        for i in range(2, sides):
            prev_line = sketch.SketchLines.AddByTwoPoints(
                prev_line.EndSketchPoint, points[i]
            )
        # Close the polygon
        sketch.SketchLines.AddByTwoPoints(
            prev_line.EndSketchPoint, first_line.StartSketchPoint
        )
        return f"Polygon {sides} sides, R={radius}mm at ({x},{y})"

    def draw_closed_profile(
        self,
        points: list[list[float]],
        sketch_index: int | None = None,
    ) -> str:
        """Draw a closed profile from a list of [x,y] points (mm).
        Lines share endpoints for proper profile recognition by Inventor."""
        sketch = self._get_sketch(sketch_index)
        tg = self._tg()

        if len(points) < 3:
            raise ValueError("Need at least 3 points for a closed profile")

        # First line
        pt1 = tg.CreatePoint2d(points[0][0] / 10.0, points[0][1] / 10.0)
        pt2 = tg.CreatePoint2d(points[1][0] / 10.0, points[1][1] / 10.0)
        first_line = sketch.SketchLines.AddByTwoPoints(pt1, pt2)

        # Subsequent lines — connect to previous endpoint
        prev_line = first_line
        for i in range(2, len(points)):
            next_pt = tg.CreatePoint2d(points[i][0] / 10.0, points[i][1] / 10.0)
            prev_line = sketch.SketchLines.AddByTwoPoints(
                prev_line.EndSketchPoint, next_pt
            )

        # Close the loop — connect last endpoint to first startpoint
        sketch.SketchLines.AddByTwoPoints(
            prev_line.EndSketchPoint, first_line.StartSketchPoint
        )

        return f"Closed profile with {len(points)} points ({len(points)} lines)"

    # ---------- Features ----------

    def extrude(
        self,
        distance: float = 10,
        direction: str = "positive",
        operation: str = "join",
        sketch_index: int | None = None,
        profile_index: int = 1,
        extent_type: str = "distance",
    ) -> str:
        comp = self.active_part()
        sketch = self._get_sketch(sketch_index)
        profile = sketch.Profiles.AddForSolid()

        dir_map = {
            "positive": kPositiveExtentDirection,
            "negative": kNegativeExtentDirection,
            "symmetric": kSymmetricExtentDirection,
        }
        op_map = {
            "join": kJoinOperation,
            "cut": kCutOperation,
            "intersect": kIntersectOperation,
            "surface": kSurfaceOperation,
            "new": kNewBodyOperation,
        }

        direction_enum = dir_map.get(direction.lower(), kPositiveExtentDirection)
        operation_enum = op_map.get(operation.lower(), kJoinOperation)
        before = self._vol_state()

        if extent_type.lower() == "all":
            feature = comp.Features.ExtrudeFeatures.AddByThroughAllExtent(
                profile, direction_enum, operation_enum
            )
            return f"Extrude through-all {direction} ({operation}): {feature.Name}{self._fmt_delta(before)}"
        else:
            dist_cm = distance / 10.0
            feature = comp.Features.ExtrudeFeatures.AddByDistanceExtent(
                profile, dist_cm, direction_enum, operation_enum
            )
            return f"Extrude {distance}mm {direction} ({operation}): {feature.Name}{self._fmt_delta(before)}"

    def revolve(
        self,
        angle: float = 360,
        sketch_index: int | None = None,
        axis: str = "Y",
        operation: str = "join",
        axis_line_index: int | None = None,
    ) -> str:
        """Revolve a sketch profile around an axis.

        axis: "X" / "Y" / "Z"  — use a named WorkAxis (preferred, no construction line needed)
        axis_line_index: sketch line index (legacy); overrides axis when provided.
        """
        import math
        comp = self.active_part()
        sketch = self._get_sketch(sketch_index)
        profile = sketch.Profiles.AddForSolid()

        # Resolve axis entity: named WorkAxis (preferred) or sketch line (legacy)
        _work_axis_map = {"X": 1, "Y": 2, "Z": 3}
        if axis_line_index is not None:
            # Explicit keyword: legacy sketch-line mode
            axis_entity = sketch.SketchLines.Item(axis_line_index)
            axis_label = f"sketch line {axis_line_index}"
        elif isinstance(axis, str) and axis.upper() in _work_axis_map:
            # Named work axis — preferred, no construction line needed
            axis_entity = comp.WorkAxes.Item(_work_axis_map[axis.upper()])
            axis_label = f"{axis.upper()} work axis"
        elif isinstance(axis, int):
            # Backward compat: integer passed positionally from old server.py
            axis_entity = sketch.SketchLines.Item(axis)
            axis_label = f"sketch line {axis}"
        else:
            axis_entity = sketch.SketchLines.Item(1)
            axis_label = "sketch line 1"

        op_map = {
            "join": kJoinOperation,
            "cut": kCutOperation,
            "intersect": kIntersectOperation,
            "new": kNewBodyOperation,
        }
        operation_enum = op_map.get(operation.lower(), kJoinOperation)

        revolve_features = comp.Features.RevolveFeatures
        before = self._vol_state()

        if angle >= 360:
            revolve_features.AddFull(profile, axis_entity, operation_enum)
        else:
            angle_rad = math.radians(angle)
            revolve_features.AddByAngle(
                profile, axis_entity, angle_rad,
                kPositiveExtentDirection, operation_enum
            )

        return f"Revolve {angle}° around {axis_label} ({operation}){self._fmt_delta(before)}"

    def fillet(self, radius: float = 2, edge_indices: list[int] | None = None) -> str:
        comp = self.active_part()
        r_cm = radius / 10.0

        edges_collection = self.app.TransientObjects.CreateEdgeCollection()
        body = comp.SurfaceBodies.Item(1)

        if edge_indices:
            for idx in edge_indices:
                edges_collection.Add(body.Edges.Item(idx))
        else:
            edges_collection.Add(body.Edges.Item(1))

        before = self._vol_state()
        fillet_def = comp.Features.FilletFeatures.CreateFilletDefinition()
        fillet_def.AddConstantRadiusEdgeSet(edges_collection, r_cm)
        comp.Features.FilletFeatures.Add(fillet_def)
        return f"Fillet R={radius}mm on {edges_collection.Count} edge(s){self._fmt_delta(before)}"

    def chamfer(self, distance: float = 2, edge_indices: list[int] | None = None) -> str:
        """Add equal-distance chamfer to edges.
        Inventor 2026 API: ChamferFeatures.AddUsingDistance(EdgeCollection, dist_cm)
        NOT CreateChamferDefinition (removed in 2026).
        Requires EdgeCollection (not ObjectCollection).
        """
        comp = self.active_part()
        d_cm = distance / 10.0

        ec = self.app.TransientObjects.CreateEdgeCollection()
        body = comp.SurfaceBodies.Item(1)

        if edge_indices:
            for idx in edge_indices:
                ec.Add(body.Edges.Item(idx))
        else:
            ec.Add(body.Edges.Item(1))

        before = self._vol_state()
        comp.Features.ChamferFeatures.AddUsingDistance(ec, d_cm)
        return f"Chamfer {distance}mm on {ec.Count} edge(s){self._fmt_delta(before)}"

    # Standard ISO metric coarse thread pitches (mm)
    _METRIC_COARSE_PITCH = {
        1: 0.25, 1.2: 0.25, 1.4: 0.3, 1.6: 0.35, 2: 0.4, 2.5: 0.45,
        3: 0.5, 3.5: 0.6, 4: 0.7, 5: 0.8, 6: 1.0, 8: 1.25, 10: 1.5,
        12: 1.75, 14: 2.0, 16: 2.0, 18: 2.5, 20: 2.5, 22: 2.5, 24: 3.0,
        27: 3.0, 30: 3.5, 33: 3.5, 36: 4.0, 39: 4.0, 42: 4.5, 45: 4.5,
        48: 5.0, 52: 5.0, 56: 5.5, 60: 5.5, 64: 6.0,
    }

    def hole(
        self,
        x: float = 0, y: float = 0,
        diameter: float = 10,
        depth: float = 0,
        tapped: bool = False,
        pitch: float | None = None,
    ) -> str:
        """Create a proper Inventor HoleFeature using native HoleFeatures API.
        depth=0 means through-all (default).
        tapped=True creates a tapped (threaded) hole with ISO Metric profile.
        pitch: thread pitch in mm (auto-selected from standard coarse series if None).
        Uses CreateSketchPlacementDefinition(ObjectCollection_of_SketchPoints) API.
        """
        comp = self.active_part()
        tg = self._tg()
        hf = comp.Features.HoleFeatures
        before = self._vol_state()

        # Create sketch on XY work plane for hole center point
        wp = comp.WorkPlanes.Item(3)  # XY plane
        sketch = comp.Sketches.Add(wp)
        pt = sketch.SketchPoints.Add(tg.CreatePoint2d(x / 10.0, y / 10.0))

        # Create ObjectCollection with the SketchPoint (required by API)
        col = self.app.TransientObjects.CreateObjectCollection()
        col.Add(pt)

        # Create sketch-based placement definition
        placement = hf.CreateSketchPlacementDefinition(col)

        diameter_cm = diameter / 10.0

        # Build second argument: TapInfo for tapped holes, float diameter for drilled holes
        if tapped:
            # Determine pitch (standard coarse if not given)
            if pitch is None:
                dia_int = int(round(diameter))
                pitch = self._METRIC_COARSE_PITCH.get(dia_int)
                if pitch is None:
                    raise ValueError(
                        f"No standard coarse pitch for M{dia_int}. "
                        "Pass pitch= explicitly."
                    )
            # Format designation: "M16x2" (not "M16x2.0")
            dia_int = int(round(diameter))
            pitch_str = str(int(pitch)) if pitch == int(pitch) else str(pitch)
            designation = f"M{dia_int}x{pitch_str}"
            tap_info = hf.CreateTapInfo(
                True,                   # RightHanded
                "ISO Metric profile",   # ThreadType (exact string from thread.xlsx)
                designation,            # ThreadDesignation e.g. "M16x2"
                "6H",                   # Class (standard internal metric)
                True,                   # FullTapDepth
            )
            hole_arg = tap_info
            type_str = f"M{dia_int} tapped (pitch {pitch}mm, 6H)"
        else:
            hole_arg = diameter_cm
            type_str = f"drilled D={diameter}mm"

        if depth <= 0:
            feature = hf.AddDrilledByThroughAllExtent(
                placement, hole_arg, kNegativeExtentDirection
            )
            extent_str = "through-all"
        else:
            depth_cm = depth / 10.0
            feature = hf.AddDrilledByDistanceExtent(
                placement, hole_arg, depth_cm, kNegativeExtentDirection
            )
            extent_str = f"{depth}mm deep"

        # --- Add position dimensions in a separate sketch (after hole creation) ---
        # HoleFeature placement sketch must have ONLY SketchPoints — construction lines
        # cannot be in the same sketch. So we create a dedicated dimension sketch.
        self._add_hole_position_dims(comp, x, y)

        return f"Hole {type_str} {extent_str} at ({x},{y}): {feature.Name}{self._fmt_delta(before)}"

    def _add_hole_position_dims(self, comp, x: float, y: float) -> None:
        """Add a dimension sketch showing the hole center position from origin.
        Uses a separate sketch with construction line(s) to allow AddTwoPointDistance.
        Only adds dimensions if hole is not at origin.
        """
        tg = self._tg()
        x_cm = x / 10.0
        y_cm = y / 10.0

        if abs(x) < 0.01 and abs(y) < 0.01:
            return  # hole at origin — nothing to dimension

        wp = comp.WorkPlanes.Item(3)  # XY plane
        dim_sketch = comp.Sketches.Add(wp)
        dc = dim_sketch.DimensionConstraints

        if abs(y) < 0.01:
            # Hole on X axis — one horizontal construction line
            line = dim_sketch.SketchLines.AddByTwoPoints(
                tg.CreatePoint2d(0.0, 0.0),
                tg.CreatePoint2d(x_cm, 0.0)
            )
            line.Construction = True
            text_pt = tg.CreatePoint2d(x_cm / 2, -1.5)
            dc.AddTwoPointDistance(line.StartSketchPoint, line.EndSketchPoint,
                                   kHorizontalDim, text_pt)
        elif abs(x) < 0.01:
            # Hole on Y axis — one vertical construction line
            line = dim_sketch.SketchLines.AddByTwoPoints(
                tg.CreatePoint2d(0.0, 0.0),
                tg.CreatePoint2d(0.0, y_cm)
            )
            line.Construction = True
            text_pt = tg.CreatePoint2d(-1.5, y_cm / 2)
            dc.AddTwoPointDistance(line.StartSketchPoint, line.EndSketchPoint,
                                   kVerticalDim, text_pt)
        else:
            # Hole at (x, y) — two construction lines: H and V legs
            h_line = dim_sketch.SketchLines.AddByTwoPoints(
                tg.CreatePoint2d(0.0, 0.0),
                tg.CreatePoint2d(x_cm, 0.0)
            )
            h_line.Construction = True
            v_line = dim_sketch.SketchLines.AddByTwoPoints(
                tg.CreatePoint2d(x_cm, 0.0),
                tg.CreatePoint2d(x_cm, y_cm)
            )
            v_line.Construction = True
            # Horizontal dim (X distance from center)
            dc.AddTwoPointDistance(h_line.StartSketchPoint, h_line.EndSketchPoint,
                                   kHorizontalDim, tg.CreatePoint2d(x_cm / 2, -1.5))
            # Vertical dim (Y distance)
            dc.AddTwoPointDistance(v_line.StartSketchPoint, v_line.EndSketchPoint,
                                   kVerticalDim, tg.CreatePoint2d(x_cm + 1.5, y_cm / 2))

    # ---------- Diagnostics / token-saving helpers ----------

    def _vol_state(self):
        """(volume_mm3, faces, edges) of body 1, or None if no body."""
        try:
            comp = self.active_part()
            mp = comp.MassProperties
            body = comp.SurfaceBodies.Item(1)
            return (mp.Volume * 1000, body.Faces.Count, body.Edges.Count)
        except Exception:
            return None

    def _fmt_delta(self, before):
        """Compact ' | V 35271 (−7854) | F7 E16' suffix comparing to 'before' state."""
        after = self._vol_state()
        if not after:
            return ""
        if not before:
            # first feature — no 'before' body existed
            return f" | V {after[0]:.0f} mm³ | F{after[1]} E{after[2]}"
        dv = after[0] - before[0]
        return f" | V {after[0]:.0f} ({dv:+.0f} mm³) | F{after[1]} E{after[2]}"

    def inspect(self) -> dict:
        """Compact one-call snapshot of the active part."""
        doc = self.active_document()
        comp = doc.ComponentDefinition
        info: dict = {"document": doc.DisplayName}
        try:
            body = comp.SurfaceBodies.Item(1)
            rb = body.RangeBox
            mp = comp.MassProperties
            info["volume_mm3"] = round(mp.Volume * 1000)
            info["bbox_mm"] = {
                "x": [round(rb.MinPoint.X * 10, 2), round(rb.MaxPoint.X * 10, 2)],
                "y": [round(rb.MinPoint.Y * 10, 2), round(rb.MaxPoint.Y * 10, 2)],
                "z": [round(rb.MinPoint.Z * 10, 2), round(rb.MaxPoint.Z * 10, 2)],
            }
            info["faces"] = body.Faces.Count
            info["edges"] = body.Edges.Count
        except Exception:
            info["body"] = "none"
        feats = []
        for i in range(1, comp.Features.Count + 1):
            f = comp.Features.Item(i)
            nm = f.Name
            if getattr(f, "Suppressed", False):
                nm += " [suppressed]"
            feats.append(f"[{i}] {nm}")
        info["features"] = feats
        info["sketches"] = [comp.Sketches.Item(i).Name for i in range(1, comp.Sketches.Count + 1)]
        try:
            info["sheet_metal_thickness"] = str(comp.ActiveSheetMetalStyle.Thickness)
        except Exception:
            pass
        return info

    def list_edges(self, body_index: int = 1, min_length: float = 0, max_count: int = 60) -> str:
        """Compact edge table: '[i] L=200.0 mid=(0.0,-225.0,0.8)' one per line.
        min_length filters out tiny edges (mm)."""
        body = self.active_part().SurfaceBodies.Item(body_index)
        lines = []
        for i in range(1, body.Edges.Count + 1):
            try:
                e = body.Edges.Item(i)
                sv, ev = e.StartVertex.Point, e.StopVertex.Point
                L = ((ev.X - sv.X) ** 2 + (ev.Y - sv.Y) ** 2 + (ev.Z - sv.Z) ** 2) ** 0.5 * 10
                if L < min_length:
                    continue
                mx, my, mz = (sv.X + ev.X) / 2 * 10, (sv.Y + ev.Y) / 2 * 10, (sv.Z + ev.Z) / 2 * 10
                lines.append(f"[{i}] L={L:.1f} mid=({mx:.1f},{my:.1f},{mz:.1f})")
            except Exception:
                lines.append(f"[{i}] (closed curve)")
            if len(lines) >= max_count:
                lines.append(f"... truncated at {max_count}")
                break
        return "\n".join(lines) if lines else "(no edges match)"

    def list_faces(self, body_index: int = 1, min_area: float = 0, max_count: int = 60) -> str:
        """Compact face table: '[i] Plane A=90000 c=(0.0,225.0,12.5)' one per line.
        min_area in mm²."""
        type_names = {5890: "Plane", 5891: "Cyl", 5892: "Cone", 5893: "Cone",
                      5894: "Sphere", 5895: "Torus"}
        body = self.active_part().SurfaceBodies.Item(body_index)
        lines = []
        for i in range(1, body.Faces.Count + 1):
            try:
                f = body.Faces.Item(i)
                a = f.Evaluator.Area * 100
                if a < min_area:
                    continue
                xs, ys, zs = [], [], []
                for v in range(1, f.Vertices.Count + 1):
                    p = f.Vertices.Item(v).Point
                    xs.append(p.X * 10); ys.append(p.Y * 10); zs.append(p.Z * 10)
                t = type_names.get(f.SurfaceType, str(f.SurfaceType))
                if xs:
                    c = f"c=({sum(xs)/len(xs):.1f},{sum(ys)/len(ys):.1f},{sum(zs)/len(zs):.1f})"
                else:
                    c = "c=(closed)"
                lines.append(f"[{i}] {t} A={a:.0f} {c}")
            except Exception:
                lines.append(f"[{i}] ?")
            if len(lines) >= max_count:
                lines.append(f"... truncated at {max_count}")
                break
        return "\n".join(lines) if lines else "(no faces match)"

    # ---------- Transactions (rollback support) ----------

    def transaction(self, action: str = "begin", name: str = "MCP batch") -> str:
        """begin: start an undo-transaction wrapping subsequent operations.
        commit: finalize. abort: roll back EVERYTHING since begin (one undo unit)."""
        action = action.lower()
        if action == "begin":
            if getattr(self, "_txn", None) is not None:
                return "Transaction already open — commit or abort it first"
            self._txn = self.app.TransactionManager.StartTransaction(
                self.app.ActiveDocument, name)
            return f"Transaction '{name}' started"
        if action == "commit":
            if getattr(self, "_txn", None) is None:
                return "No open transaction"
            self._txn.End()
            self._txn = None
            return "Transaction committed"
        if action == "abort":
            if getattr(self, "_txn", None) is None:
                return "No open transaction"
            self._txn.Abort()
            self._txn = None
            return "Transaction aborted — all changes since 'begin' rolled back"
        return f"Unknown action '{action}'. Use begin / commit / abort."

    def _plane_face(self, axis: str, value: float, body_index: int = 1, tol: float = 0.1):
        """Largest planar face whose vertices ALL lie at <axis>==value (mm).
        Re-resolve after every feature — face objects/indices go stale."""
        body = self.active_part().SurfaceBodies.Item(body_index)
        best_f, best_a = None, 0
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if f.SurfaceType != 5890:  # plane
                continue
            ok = True
            for v in range(1, f.Vertices.Count + 1):
                p = f.Vertices.Item(v).Point
                c = {"x": p.X, "y": p.Y, "z": p.Z}[axis.lower()] * 10
                if abs(c - value) > tol:
                    ok = False
                    break
            if ok:
                a = f.Evaluator.Area
                if a > best_a:
                    best_a, best_f = a, f
        if best_f is None:
            raise ValueError(f"No planar face at {axis}={value}mm")
        return best_f

    def _face_edge(self, face, axis: str, value: float, tol: float = 0.1):
        """Edge of a face whose BOTH vertices lie at <axis>==value (mm)."""
        for i in range(1, face.Edges.Count + 1):
            e = face.Edges.Item(i)
            sv, ev = e.StartVertex.Point, e.StopVertex.Point
            cs = {"x": sv.X, "y": sv.Y, "z": sv.Z}[axis.lower()] * 10
            ce = {"x": ev.X, "y": ev.Y, "z": ev.Z}[axis.lower()] * 10
            if abs(cs - value) < tol and abs(ce - value) < tol:
                return e
        raise ValueError(f"No edge of face at {axis}={value}mm")

    def hole_linear(
        self,
        face_axis: str, face_value: float,
        ref1_axis: str, ref1_value: float, dist1: float,
        ref2_axis: str, ref2_value: float, dist2: float,
        diameter: float = 5.5,
        depth: float = 0,
        tapped: bool = False,
        pitch: float | None = None,
        cbore_diameter: float = 0,
        cbore_depth: float = 0,
    ) -> str:
        """Hole placed parametrically from two face edges (Linear placement).

        The hole stays attached to the edges — change the part length and the
        hole keeps its 8mm-from-edge distance. This is the preferred way to
        place fastener holes (vs sketch-point placement with absolute coords).

        face_axis/face_value: the planar face to drill into, e.g. ("z", 25) = top.
        ref1/ref2: two edges OF THAT FACE by their constant coordinate,
                   e.g. ("x", -34.5, 8) = 8mm from the left edge.
        depth: 0 = through-all, otherwise mm.
        tapped: ISO metric thread (uses standard coarse pitch unless pitch given).
        cbore_diameter/cbore_depth: >0 adds a counterbore (e.g. 10 and 5.5 for
                   an M5 ISO 4762 socket head cap screw seat).

        Direction is resolved automatically: try positive, check that material
        was actually removed (volume), flip to negative if not.
        """
        comp = self.active_part()
        tg = self._tg()
        hf = comp.Features.HoleFeatures
        doc = self.active_document()

        # Build the hole argument (diameter or TapInfo)
        if tapped:
            if pitch is None:
                dia_int = int(round(diameter))
                pitch = self._METRIC_COARSE_PITCH.get(dia_int)
                if pitch is None:
                    raise ValueError(f"No standard coarse pitch for M{dia_int}")
            dia_int = int(round(diameter))
            pitch_str = str(int(pitch)) if pitch == int(pitch) else str(pitch)
            hole_arg = hf.CreateTapInfo(
                True, "ISO Metric profile", f"M{dia_int}x{pitch_str}", "6H", True)
            type_str = f"M{dia_int} tapped"
        else:
            hole_arg = diameter / 10.0
            type_str = f"D={diameter}mm"

        v0 = comp.MassProperties.Volume * 1000

        for direction in (kPositiveExtentDirection, kNegativeExtentDirection):
            # Re-resolve topology fresh each attempt
            face = self._plane_face(face_axis, face_value)
            e1 = self._face_edge(face, ref1_axis, ref1_value)
            e2 = self._face_edge(face, ref2_axis, ref2_value)

            # BiasPoint: 3D point near the intended hole location. Compute by
            # stepping from each reference edge toward the face centroid.
            xs, ys, zs = [], [], []
            for v in range(1, face.Vertices.Count + 1):
                p = face.Vertices.Item(v).Point
                xs.append(p.X * 10); ys.append(p.Y * 10); zs.append(p.Z * 10)
            centroid = {"x": sum(xs)/len(xs), "y": sum(ys)/len(ys), "z": sum(zs)/len(zs)}
            coords = dict(centroid)
            coords[face_axis.lower()] = face_value
            sgn1 = 1 if centroid[ref1_axis.lower()] >= ref1_value else -1
            coords[ref1_axis.lower()] = ref1_value + sgn1 * dist1
            sgn2 = 1 if centroid[ref2_axis.lower()] >= ref2_value else -1
            coords[ref2_axis.lower()] = ref2_value + sgn2 * dist2
            bias = tg.CreatePoint(coords["x"] / 10, coords["y"] / 10, coords["z"] / 10)

            placement = hf.CreateLinearPlacementDefinition(
                face, e1, dist1 / 10.0, e2, dist2 / 10.0, bias)

            if cbore_diameter > 0:
                d_cm = depth / 10.0 if depth > 0 else 10.0  # cbore needs finite depth
                feature = hf.AddCBoreByDistanceExtent(
                    placement, hole_arg, d_cm, direction,
                    cbore_diameter / 10.0, cbore_depth / 10.0)
                extent_str = f"{depth}mm deep, cbore Ø{cbore_diameter}x{cbore_depth}"
            elif depth > 0:
                feature = hf.AddDrilledByDistanceExtent(
                    placement, hole_arg, depth / 10.0, direction)
                extent_str = f"{depth}mm deep"
            else:
                feature = hf.AddDrilledByThroughAllExtent(
                    placement, hole_arg, direction)
                extent_str = "through-all"

            doc.Update()
            v1 = comp.MassProperties.Volume * 1000
            if v1 < v0 - 1:  # material removed — direction correct
                return (f"Hole {type_str} {extent_str} on {face_axis}={face_value} "
                        f"({dist1}mm from {ref1_axis}={ref1_value}, "
                        f"{dist2}mm from {ref2_axis}={ref2_value}): {feature.Name}"
                        f" | V {v1:.0f} ({v1-v0:+.0f} mm³)")
            feature.Delete()
            doc.Update()

        raise RuntimeError("Hole removed no material in either direction — check placement")

    def circular_pattern(
        self,
        feature_index: int,
        count: int = 8,
        angle: float = 360,
        axis: str = "Z",
    ) -> str:
        """Create a circular pattern of a feature around a work axis.
        Distributes 'count' instances evenly within 'angle' degrees.
        """
        import math
        comp = self.active_part()
        cpf = comp.Features.CircularPatternFeatures

        # Get the feature to pattern
        feature = comp.Features.Item(feature_index)

        feat_col = self.app.TransientObjects.CreateObjectCollection()
        feat_col.Add(feature)

        # Work axis selection (X=1, Y=2, Z=3)
        axis_map = {"X": 1, "Y": 2, "Z": 3}
        axis_index = axis_map.get(axis.upper(), 3)
        axis_obj = comp.WorkAxes.Item(axis_index)

        angle_rad = math.radians(angle)

        pattern = cpf.Add(
            feat_col,    # ParentFeatures — ObjectCollection
            axis_obj,    # AxisEntity — WorkAxis
            True,        # NaturalAxisDirection
            count,       # Count
            angle_rad,   # Angle (radians, total span)
            True,        # FitWithinAngle — distribute evenly within angle
            47363,       # ComputeType = kOptimizedCompute (default)
        )

        return (
            f"Circular pattern: {count}x '{feature.Name}' "
            f"around {axis.upper()}-axis, {angle} deg: {pattern.Name}"
        )

    # ---------- Parameters ----------

    def get_parameters(self) -> list[dict]:
        doc = self.active_document()
        params = doc.ComponentDefinition.Parameters
        result = []
        for i in range(1, params.Count + 1):
            p = params.Item(i)
            try:
                result.append({
                    "name": p.Name,
                    "value": p.Value,
                    "expression": p.Expression,
                    "unit": p.Units if hasattr(p, "Units") else "",
                })
            except Exception:
                pass
        return result

    def set_parameter(self, name: str, expression: str) -> str:
        doc = self.active_document()
        params = doc.ComponentDefinition.Parameters
        for i in range(1, params.Count + 1):
            p = params.Item(i)
            if p.Name.lower() == name.lower():
                p.Expression = expression
                doc.Update()
                return f"Parameter '{name}' set to '{expression}' (value={p.Value})"
        raise ValueError(f"Parameter '{name}' not found.")

    def add_parameter(self, name: str, expression: str, units: str = "mm") -> str:
        doc = self.active_document()
        params = doc.ComponentDefinition.Parameters.UserParameters
        params.AddByExpression(name, expression, units)
        doc.Update()
        return f"User parameter '{name}' = '{expression}' ({units}) added"

    # ---------- Query ----------

    def get_document_info(self) -> dict:
        doc = self.active_document()
        comp = doc.ComponentDefinition
        info = {
            "name": doc.DisplayName,
            "full_path": doc.FullFileName,
            "type": str(doc.DocumentType),
            "sketches_count": comp.Sketches.Count,
            "features_count": comp.Features.Count if hasattr(comp.Features, "Count") else 0,
            "bodies_count": comp.SurfaceBodies.Count,
        }
        if comp.SurfaceBodies.Count > 0:
            body = comp.SurfaceBodies.Item(1)
            info["edges_count"] = body.Edges.Count
            info["faces_count"] = body.Faces.Count
        return info

    def list_features(self) -> list[dict]:
        comp = self.active_part()
        result = []
        for i in range(1, comp.Features.Count + 1):
            f = comp.Features.Item(i)
            result.append({
                "index": i,
                "name": f.Name,
                "type": str(f.Type),
                "suppressed": f.Suppressed if hasattr(f, "Suppressed") else False,
            })
        return result

    def delete_feature(self, indices: list[int]) -> str:
        """Delete features by index. Always deletes in reverse order to avoid index shifting."""
        comp = self.active_part()
        total = comp.Features.Count
        for idx in sorted(indices, reverse=True):
            if idx < 1 or idx > total:
                raise ValueError(f"Feature index {idx} out of range (1–{total})")
            name = comp.Features.Item(idx).Name
            comp.Features.Item(idx).Delete()
            total -= 1
        deleted = sorted(indices)
        return f"Deleted {len(indices)} feature(s): indices {deleted}"

    def suppress_feature(self, indices: list[int], suppressed: bool = True) -> str:
        """Suppress or unsuppress features by index."""
        comp = self.active_part()
        names = []
        for idx in indices:
            f = comp.Features.Item(idx)
            f.Suppressed = suppressed
            names.append(f.Name)
        state = "Suppressed" if suppressed else "Unsuppressed"
        return f"{state}: {', '.join(names)}"

    # ---------- Sheet Metal Features ----------

    def set_sheet_metal_thickness(self, thickness_mm: float) -> str:
        """Set the thickness of the active sheet metal style. Inventor 2026.
        Uses local decimal (comma) — required by Inventor for European locales.
        """
        comp = self.active_part()
        style = comp.ActiveSheetMetalStyle
        # Try comma decimal first (European), fall back to dot
        try:
            style.Thickness = f"{thickness_mm:.3f}".replace(".", ",") + " mm"
        except Exception:
            style.Thickness = f"{thickness_mm:.3f} mm"
        return f"Sheet metal thickness set to {thickness_mm}mm (style: {style.Name})"

    def sheet_metal_face(self, sketch_index: int | None = None) -> str:
        """Create a base sheet-metal Face from a closed sketch profile.
        Equivalent of the 'Face' command in Inventor Sheet Metal UI.
        Uses the active sheet metal style's thickness automatically.
        """
        comp = self.active_part()
        sketch = self._get_sketch(sketch_index)
        profile = sketch.Profiles.AddForSolid()
        ff = comp.Features.FaceFeatures
        before = self._vol_state()
        fdef = ff.CreateFaceFeatureDefinition(profile)
        feat = ff.Add(fdef)
        return f"Sheet metal face: {feat.Name}{self._fmt_delta(before)}"

    def flange(
        self,
        edge_indices: list[int],
        distance: float = 25,
        angle: float = 90,
        body_index: int = 1,
    ) -> str:
        """Add a Sheet Metal Flange to one or more edges. Inventor 2026.

        distance: flange height in mm (default 25mm = Inventor's own default)
        angle: bend angle in degrees, default 90° (perpendicular)
        edge_indices: 1-based indices into the body's Edges collection

        IMPORTANT (Inventor 2026 sheet metal quirk):
          - CreateFlangeDefinition(Edges, AngleRad, Distance) ignores the Distance arg.
          - The resulting flange always defaults to height 25mm regardless of what you pass.
          - We work around by editing the resulting feature's parameter:
              feat.Definition.HeightExtent.Distance.Expression = "<distance> mm"
          - The Distance is a Parameter (d15-ish name) — changing its Expression
            re-evaluates the feature correctly.
          - Angle must be in RADIANS (Inventor multiplies by 180/π for display).
            Passing 90 → 5156°. Always convert via math.radians().

        Measurement default = "From Outer Intersection" (HeightDatumType=75521).
        With this datum the Distance value EQUALS the visible perpendicular height
        of the flange — material thickness is NOT subtracted. So distance=450 gives
        a body that reaches Z=450 (when the flange goes upward from a Z=0 dno).
        """
        import math
        comp = self.active_part()
        body = comp.SurfaceBodies.Item(body_index)
        ec = self.app.TransientObjects.CreateEdgeCollection()
        for idx in edge_indices:
            ec.Add(body.Edges.Item(idx))

        flf = comp.Features.FlangeFeatures
        angle_rad = math.radians(angle)
        before = self._vol_state()
        # Distance arg is ignored by Inventor — we set it explicitly after Add
        fdef = flf.CreateFlangeDefinition(ec, angle_rad, 2.5)
        feat = flf.Add(fdef)
        # Set actual distance via the Parameter
        feat.Definition.HeightExtent.Distance.Expression = f"{distance} mm"
        # Update so subsequent feature/edge operations see correct geometry
        self.active_document().Update()
        return f"Flange {distance}mm @ {angle}° on {ec.Count} edge(s): {feat.Name}{self._fmt_delta(before)}"

    def sheet_metal_cut(
        self,
        sketch_index: int | None = None,
        cut_across_bends: bool = False,
    ) -> str:
        """Cut through the sheet using a sketch profile. Sheet Metal Cut.
        Default: cut perpendicular to the face (through thickness).
        cut_across_bends: if True, cut wraps around bends (unfolds first).
        """
        comp = self.active_part()
        sketch = self._get_sketch(sketch_index)
        profile = sketch.Profiles.AddForSolid()

        cf = comp.Features.CutFeatures
        before = self._vol_state()
        cdef = cf.CreateCutDefinition(profile)
        # Default extent = through thickness (kThroughAllExtent style)
        feat = cf.Add(cdef)
        return f"Sheet metal cut: {feat.Name}{self._fmt_delta(before)}"

    def find_edge(
        self,
        body_index: int = 1,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
        tolerance: float = 0.1,
    ) -> int:
        """Locate a body edge by its midpoint coordinates (mm). Returns 1-based index.
        Pass any subset of x/y/z — None values are not constrained.
        Useful for finding the edge to flange (no need to print all 20 edges).
        """
        comp = self.active_part()
        body = comp.SurfaceBodies.Item(body_index)
        for i in range(1, body.Edges.Count + 1):
            e = body.Edges.Item(i)
            sv, ev = e.StartVertex.Point, e.StopVertex.Point
            mx = (sv.X + ev.X) / 2 * 10
            my = (sv.Y + ev.Y) / 2 * 10
            mz = (sv.Z + ev.Z) / 2 * 10
            if x is not None and abs(mx - x) > tolerance: continue
            if y is not None and abs(my - y) > tolerance: continue
            if z is not None and abs(mz - z) > tolerance: continue
            return i
        criteria = ", ".join(
            f"{k}={v}" for k, v in [("x", x), ("y", y), ("z", z)] if v is not None
        )
        raise ValueError(f"No edge found matching midpoint ({criteria}) tol={tolerance}mm")

    def find_face(
        self,
        body_index: int = 1,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
        min_area: float = 100,
        surface_type: int = 5890,
        tolerance: float = 0.5,
    ) -> int:
        """Locate a body face by its centroid coordinates (mm). Returns 1-based index.

        Useful for: finding a panel face to sketch on for sheet metal Cut.
        Centroid is computed as the average of the face's vertices.

        surface_type: 5890=Plane (default), 5891=Cylinder, 5892=Cone, 5893=Sphere, 5894=Torus
        min_area: filter out small auxiliary faces (mm²)
        tolerance: how close the centroid must be (mm)
        """
        comp = self.active_part()
        body = comp.SurfaceBodies.Item(body_index)
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if surface_type is not None and f.SurfaceType != surface_type: continue
            try:
                xs, ys, zs = [], [], []
                for vi in range(1, f.Vertices.Count + 1):
                    v = f.Vertices.Item(vi)
                    xs.append(v.Point.X * 10)
                    ys.append(v.Point.Y * 10)
                    zs.append(v.Point.Z * 10)
                if not xs: continue
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                cz = sum(zs) / len(zs)
                area_mm2 = f.Evaluator.Area * 100
                if area_mm2 < min_area: continue
                if x is not None and abs(cx - x) > tolerance: continue
                if y is not None and abs(cy - y) > tolerance: continue
                if z is not None and abs(cz - z) > tolerance: continue
                return i
            except Exception:
                continue
        criteria = ", ".join(
            f"{k}={v}" for k, v in [("x", x), ("y", y), ("z", z)] if v is not None
        )
        raise ValueError(f"No face matching centroid ({criteria}) area≥{min_area} tol={tolerance}mm")
