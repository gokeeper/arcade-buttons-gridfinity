"""Checks actual CAD solids, exported meshes, and loaded stacking clearance."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import struct

import cadquery as cq
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box

from button_bin import Parameters, button_envelope, foot


def mesh_report(path: Path) -> dict:
    """Read the binary STL itself; merge shared vertices at 1 micrometre."""
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + 50 * count:
        raise AssertionError(f"Unexpected binary STL size: {path}")
    edges: Counter = Counter()
    directed: Counter = Counter()
    vertices = set()
    volume = 0.0
    degenerate = 0
    for offset in range(84, len(data), 50):
        coords = struct.unpack_from("<12fH", data, offset)[3:12]
        triangle = [tuple(round(v, 6) for v in coords[i:i + 3]) for i in (0, 3, 6)]
        a, b, c = triangle
        if len(set(triangle)) != 3:
            degenerate += 1
        vertices.update(triangle)
        for start, end in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((start, end)))] += 1
            directed[(start, end)] += 1
        volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6
    bad_edges = sum(n != 2 for n in edges.values())
    inconsistent = sum(directed[(a, b)] != directed[(b, a)] for a, b in edges)
    assert not bad_edges, f"{path}: {bad_edges} non-manifold/boundary edges"
    assert not inconsistent, f"{path}: {inconsistent} inconsistently oriented edges"
    assert not degenerate, f"{path}: degenerate triangles"
    assert volume > 0, f"{path}: nonpositive signed volume"
    return {"triangles": count, "vertices": len(vertices), "watertight": True,
            "consistent_winding": True, "volume_mm3": round(volume, 3)}


def validate_all(p: Parameters, shapes: dict[str, cq.Shape], output: Path) -> dict:
    results = {}
    for name, shape in shapes.items():
        assert shape.isValid(), f"Invalid CAD: {name}"
        assert len(shape.Solids()) == 1, f"Expected one connected solid: {name}"
        mesh = mesh_report(output / f"{name}.stl")
        # Confirm STEP export can be read as the same valid solid.
        imported = cq.importers.importStep(str(output / f"{name}.step")).val()
        assert imported.isValid() and len(imported.Solids()) == 1
        assert abs(imported.Volume() - shape.Volume()) < 0.01
        assert abs(mesh["volume_mm3"] - shape.Volume()) / shape.Volume() < 0.005
        # Ignore tessellation deflection when measuring the CAD boundary.
        bounds = Bnd_Box()
        BRepBndLib.AddOptimal_s(shape.wrapped, bounds, False, False)
        x0, y0, z0, x1, y1, z1 = bounds.Get()
        results[name] = {"valid_single_solid": True, "step_roundtrip": True,
                         "dimensions_mm": [round(x1 - x0, 3),
                                           round(y1 - y0, 3),
                                           round(z1 - z0, 3)],
                         "cad_volume_mm3": round(shape.Volume(), 3), **mesh}
    model = next(iter(shapes.values()))
    envelope = button_envelope(p)
    upper_foot = foot().translate((0, 0, p.nominal_z))
    assert model.intersect(envelope).Volume() < 1e-6, "Button envelope hits bin"
    assert model.intersect(upper_foot).Volume() < 1e-6, "Stacking foot hits bin"
    assert envelope.intersect(upper_foot).Volume() < 1e-6, "Upper foot presses button"
    # Test the removal path, not just the seated position.
    for lift in (0.5, 1.0, 3.0, 7.0, 15.0, 25.0, 35.0):
        assert model.intersect(envelope.translate((0, 0, lift))).Volume() < 1e-6, (
            f"Button envelope catches during removal at {lift} mm"
        )
    for sign in (-1, 1):
        assert not model.isInside(cq.Vector(sign * 16.5, 0, p.seat_z - 0.5)), (
            "Clip relief is blocked"
        )
        assert not model.isInside(cq.Vector(sign * 15, sign * 15, p.seat_z - 2)), (
            "Finger recess is blocked"
        )
    assert model.isInside(cq.Vector(0, 16.2, p.seat_z - 0.05)), "Missing flange seat"
    assert model.isInside(cq.Vector(0, 0, p.floor_z - 0.1)), "Missing protective floor"
    results["clearance"] = {
        "terminal_to_floor_mm": round(p.tip_z - p.floor_z, 3),
        "button_to_upper_foot_mm": round(p.top_clearance, 3),
        "button_bin_interference_mm3": 0,
        "stacking_interference_mm3": 0,
        "button_removal_path_clear": True,
        "clips_require_physical_fit_test": True,
        "flange_height_requires_physical_confirmation": True,
    }
    return results
