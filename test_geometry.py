"""Geometry regressions for custom fit settings and printability."""

from dataclasses import replace
import sys

import cadquery as cq
import numpy as np
import pytest

from button_bin import Parameters, button_envelope, button_reference, foot, make_bin
from button_lid import main as lid_main
from button_lid import LOCATOR_DEPTH, PLATE_THICKNESS, make_flush_snap_lid, make_lid


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


def test_exposed_flange_stops_at_rim_and_can_be_lifted():
    p = Parameters(height_u=6, exposed_flange=True)
    model = make_bin(p)
    reference = button_reference(p)
    assert model.BoundingBox().zmax == pytest.approx(p.seat_z, abs=0.001)
    assert p.top_z - model.BoundingBox().zmax == pytest.approx(6.5, abs=0.001)
    assert p.tip_z - p.floor_z == pytest.approx(3.5)
    assert model.intersect(reference.translate((0, 0, -0.2))).Volume() > 1e-6
    for lift in (0, 0.5, 1, 3, 7, 15, 25, 35):
        assert model.intersect(reference.translate((0, 0, lift))).Volume() < 1e-6


@pytest.mark.parametrize("opening", [30.6, 30.2])
def test_lid_sits_on_reference_rim_and_clears_button(opening, default_bin):
    p = Parameters()
    lid = make_lid(opening)
    seated = lid.translate((0, 0, p.total_z - LOCATOR_DEPTH))
    assert default_bin.intersect(seated).Volume() < 1e-6
    assert default_bin.intersect(seated.translate((0, 0, -0.2))).Volume() > 1e-6

    seat = LOCATOR_DEPTH + PLATE_THICKNESS
    reference = button_reference(p).translate((0, 0, seat - p.seat_z))
    for lift in (0, 1, 3, 7, 15, 25, 35):
        assert lid.intersect(reference.translate((0, 0, lift))).Volume() < 1e-6
    assert lid.intersect(reference.translate((0, 0, -0.2))).Volume() > 1e-6


def test_flush_snap_lid_has_single_bore_and_recess():
    lid = make_flush_snap_lid()
    assert lid.isValid() and len(lid.Solids()) == 1
    bounds = lid.BoundingBox()
    assert (bounds.xlen, bounds.ylen, bounds.zlen) == pytest.approx((37, 37, 3.2))
    for angle in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        for z, radius in ((0.79, 17.3), (0.81, 15.25), (3.19, 15.25)):
            direction = np.cos(angle), np.sin(angle)
            assert not lid.isInside(cq.Vector(*((radius - 0.02) * x for x in direction), z))
            assert lid.isInside(cq.Vector(*((radius + 0.02) * x for x in direction), z))
    # The diagonal finger holes from the slotted version are filled in.
    for sign in (-1, 1):
        assert lid.isInside(cq.Vector(sign * 13, sign * 13, 2))


@pytest.mark.parametrize("layout, button, rim_stop, width, length, xs, ys, opening, recess", [
    ("2x4", None, False, 79, 163, (-21, 21), (-63, -21, 21, 63), 30.5, 34.6),
    ("2x4", None, True, 83.5, 167.5, (-21, 21), (-63, -21, 21, 63), 30.5, 34.6),
    ("1x4", None, True, 41.5, 167.5, (0,), (-64, -32, 0, 32, 64), 24.3, 28.6),
    ("1x4", "obsf30", True, 41.5, 167.5, (0,), (-63, -21, 21, 63), 30.5, 34.6),
])
def test_multi_button_snap_lid_places_buttons_at_expected_centers(
    layout, button, rim_stop, width, length, xs, ys, opening, recess,
):
    lid = make_flush_snap_lid(layout, rim_stop=rim_stop, button=button)
    assert lid.isValid() and len(lid.Solids()) == 1
    bounds = lid.BoundingBox()
    assert (bounds.xlen, bounds.ylen, bounds.zlen) == pytest.approx((width, length, 3.2))

    centers = {(x, y) for x in xs for y in ys}
    for face, radius in ((max(lid.Faces(), key=lambda f: f.Center().z), opening / 2),
                         (min(lid.Faces(), key=lambda f: f.Center().z), recess / 2)):
        holes = [wire.Edges()[0] for wire in face.innerWires()]
        assert len(holes) == len(centers)
        assert {(round(edge.Center().x, 6), round(edge.Center().y, 6)) for edge in holes} == centers
        assert [edge.radius() for edge in holes] == pytest.approx([radius] * len(centers))
    if rim_stop:
        # The four midpoints span the rim above the locator, with a stop
        # shoulder 2 mm above the bottom of the lid.
        assert bounds.ymin == pytest.approx(-83.75)
        x_edge = width / 2 - 0.75
        for x, y in ((-x_edge, 0), (x_edge, 0), (0, bounds.ymin + 0.75),
                     (0, bounds.ymax - 0.75)):
            assert not lid.isInside(cq.Vector(x, y, 1.99))
            assert lid.isInside(cq.Vector(x, y, 2.01))


@pytest.mark.parametrize("layout, button, width", [
    ("1x4", "obsf24", 41.5),
    ("1x4", "obsf30", 41.5),
    ("2x4", "obsf30", 83.5),
])
def test_lift_tab_only_extends_one_rim_end(layout, button, width):
    original = make_flush_snap_lid(layout, rim_stop=True, button=button)
    lid = make_flush_snap_lid(layout, rim_stop=True, button=button, lift_tab=True)
    bounds = lid.BoundingBox()
    assert (bounds.xlen, bounds.ymin, bounds.ymax, bounds.zlen) == pytest.approx(
        (width, -83.75, 91.75, 3.2)
    )
    assert original.cut(lid).Volume() < 1e-6
    extension = lid.cut(original)
    assert extension.BoundingBox().zmin == pytest.approx(2.0)
    assert extension.Volume() == pytest.approx(width * 8 * 1.2)
    x_edge = width / 2 - 0.75
    assert lid.isInside(cq.Vector(x_edge, 87, 2.6))
    assert lid.isInside(cq.Vector(-x_edge, 87, 2.6))


@pytest.mark.parametrize("args, name, width, length, corner_radius, count, opening", [
    (
        ["--flush-snap", "2x4"],
        "obsf30_2x4_flush_snap_lid_30p5_mw47599", 79, 163, 3, 8, 30.5,
    ),
    (
        ["--rim-stop-snap"],
        "obsf30_2x4_rim_stop_snap_lid_30p5_mw47599_no_tab", 83.5, 167.5, 3.75, 8, 30.5,
    ),
    (
        ["--rim-stop-snap", "2x4", "--lift-tab"],
        "obsf30_2x4_rim_stop_snap_lid_30p5_mw47599_lift_tab_8mm", 83.5, 175.5, 3.75, 8, 30.5,
    ),
    (
        ["--rim-stop-snap", "1x4"],
        "obsf24_1x4_rim_stop_snap_lid_24p3_mw47599_no_tab", 41.5, 167.5, 3.75, 5, 24.3,
    ),
    (
        ["--rim-stop-snap", "1x4", "--button", "obsf30"],
        "obsf30_1x4_rim_stop_snap_lid_30p5_mw47599_no_tab", 41.5, 167.5, 3.75, 4, 30.5,
    ),
    (
        ["--rim-stop-snap", "1x4", "--lift-tab"],
        "obsf24_1x4_rim_stop_snap_lid_24p3_mw47599_lift_tab_8mm", 41.5, 175.5, 3.75, 5, 24.3,
    ),
    (
        ["--rim-stop-snap", "1x4", "--button", "obsf30", "--lift-tab"],
        "obsf30_1x4_rim_stop_snap_lid_30p5_mw47599_lift_tab_8mm", 41.5, 175.5, 3.75, 4, 30.5,
    ),
])
def test_multi_button_stl_exports_button_face_on_bed(
    monkeypatch, tmp_path, args, name, width, length, corner_radius, count, opening,
):
    monkeypatch.setattr(sys, "argv", [
        "button_lid.py", *args, "--output", str(tmp_path),
    ])
    lid_main()
    path = tmp_path / f"{name}.stl"
    facets = np.fromfile(path, offset=84, dtype=[
        ("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attributes", "<u2"),
    ])
    vertices = facets["vertices"].astype(float)
    normals = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    down = normals[:, 2] < -1e-6
    # Every downward face must touch the build plate. In the reversed export
    # the ring-shaped shoulders instead hang above it at Z = 0.8.
    assert down.any()
    assert vertices[:, :, 2].min() == pytest.approx(0, abs=1e-6)
    assert np.allclose(vertices[down, :, 2], 0, atol=1e-6)
    expected_bed_area = (
        width * length - (4 - np.pi) * corner_radius**2 - count * np.pi * (opening / 2)**2
    )
    assert -normals[down, 2].sum() / 2 == pytest.approx(expected_bed_area, abs=5)
