"""Geometry regressions for custom fit settings and printability."""

from dataclasses import replace

import cadquery as cq
import numpy as np
import pytest

from button_bin import Parameters, button_envelope, button_reference, foot, make_bin


@pytest.mark.parametrize("overrides", [
    {"height_u": 5},
    {"height_u": 6},
    {"height_u": 6.5},
    {"body_opening": 29.5},
    {"body_opening": 32.5},
    {"top_clearance": 1.0},
    {"clip_span": 40.0},
    {"finger_diameter": 16.0},
    {"top_above_flange": 24.0},
    {"wall": 4.0},
    {"flange_clearance": float("nan")},
])
def test_rejects_unsafe_parameter_sets(overrides):
    with pytest.raises(ValueError):
        replace(Parameters(), **overrides).validate()


@pytest.fixture(scope="module")
def default_bin():
    return make_bin()


def test_default_support_slope(default_bin):
    """Detect hidden horizontal ceilings or steep undercuts beneath the cradle."""
    p = Parameters()
    vertices, triangles = default_bin.tessellate(0.05, 0.1)
    coords = np.array([v.toTuple() for v in vertices])[np.array(triangles)]
    normals = np.cross(coords[:, 1] - coords[:, 0], coords[:, 2] - coords[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    centres = coords.mean(axis=1)
    underside = ((centres[:, 2] > p.floor_z + 0.5)
                 & (centres[:, 2] < p.seat_z - p.entry_chamfer - 0.1)
                 & (normals[:, 2] < -1e-6) & (lengths > 1e-7))
    angles = np.degrees(np.arcsin(np.clip(-normals[underside, 2] / lengths[underside], 0, 1)))
    # Angle from vertical; allow small curved-surface tessellation error at 45°.
    assert angles.size
    assert angles.max() <= 46.0


def test_seat_and_full_depth_clip_reliefs(default_bin):
    p = Parameters()
    assert default_bin.isInside(cq.Vector(0, 16.2, p.seat_z - 0.05))
    for z in (p.floor_z + 1, p.seat_z - 3, p.seat_z - 0.1):
        for sign in (-1, 1):
            assert not default_bin.isInside(cq.Vector(sign * 16.8, 0, z))


def test_custom_height_and_clearance_remain_stackable():
    p = replace(Parameters(), height_u=8, body_opening=31.4, clip_span=34.4)
    model = make_bin(p)
    assert model.isValid() and len(model.Solids()) == 1
    assert model.intersect(button_envelope(p)).Volume() < 1e-6
    assert model.intersect(foot().translate((0, 0, p.nominal_z))).Volume() < 1e-6
    assert p.tip_z - p.floor_z == pytest.approx(9.0)


def test_exact_drawing_vertical_datums():
    p = Parameters()
    assert p.button_height == pytest.approx(38.2)
    assert p.terminal_projection == pytest.approx(12.5)
    assert p.seat_z == pytest.approx(40.5)
    assert p.switch_bottom_z == pytest.approx(21.3)
    assert p.tip_z == pytest.approx(8.8)
    assert p.tip_z - p.floor_z == pytest.approx(2.0)
    # Regression: the old 31.7 mm overall assumption hid 5 mm of floor collision.
    too_short = replace(p, height_u=6)
    assert too_short.tip_z - too_short.floor_z == pytest.approx(-5.0)
    with pytest.raises(ValueError, match="terminal tips"):
        too_short.validate()


def test_shaped_reference_matches_dimensioned_extents():
    p = Parameters()
    shape = button_reference(p)
    assert shape.isValid() and len(shape.Solids()) == 1
    bounds = shape.BoundingBox()
    assert bounds.zmin == pytest.approx(p.tip_z, abs=0.001)
    assert bounds.zmax == pytest.approx(p.top_z, abs=0.001)
    assert bounds.zlen == pytest.approx(38.2, abs=0.001)
