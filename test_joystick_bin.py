"""Fit regressions for the sideways JLF and the guide-supported lid."""

import pytest

from arcade_bin import FLOOR_Z
from joystick_bin import (
    LID_BASE_Z, PLATE_Y, centered_box, check_fit, check_lid_fit, joystick_gauges, make_bin, make_lid,
)
from joystick_plate_fixture import make_fixture


@pytest.fixture(scope="module", params=[8, 9])
def bin_and_height(request):
    return make_bin(request.param), request.param


def test_rim_seats_and_open_bin_removal(bin_and_height):
    body, height_u = bin_and_height
    rim = body.BoundingBox().zmax
    gauges = joystick_gauges()
    assert rim == pytest.approx({8: 52.55, 9: 59.55}[height_u])
    assert gauges["bare shaft"].BoundingBox().zmax - rim == pytest.approx(
        {8: 3.15, 9: -3.85}[height_u]
    )
    assert gauges["PCB, restrictor and connector"].BoundingBox().zmin - FLOOR_Z == pytest.approx(3)
    assert gauges["plate"].BoundingBox().zmin == pytest.approx(23.2)
    check_fit(body)


def test_9u_lid_seats_and_lifts_with_two_snap_buttons():
    lid = make_lid().translate((0, 0, LID_BASE_Z))
    body = make_bin(9)
    check_lid_fit(body, lid)
    for face, diameter in ((max(lid.Faces(), key=lambda f: f.Center().z), 30.5),
                           (min(lid.Faces(), key=lambda f: f.Center().z), 34.6)):
        holes = [wire.Edges()[0] for wire in face.innerWires()]
        assert len(holes) == 2
        assert sorted((round(edge.Center().x, 6), round(edge.Center().y, 6))
                      for edge in holes) == [(-37, 20), (37, 20)]
        assert [2 * edge.radius() for edge in holes] == pytest.approx([diameter, diameter])

    shoulders = [face for face in lid.Faces() if face.geomType() == "PLANE"
                 and face.Center().z == pytest.approx(60.75 - 2.4)]
    assert len(shoulders) == 2


def test_fixture_plate_seats_and_pcb_floor():
    fixture = make_fixture()
    bounds = fixture.BoundingBox()
    assert (bounds.xlen, bounds.ylen, bounds.zmin, bounds.zmax) == pytest.approx(
        (106.8, 45, 0, 22), abs=1e-6
    )
    # The 95 × 54 × 1.6 mm plate can descend at either extreme of its slot play.
    path = centered_box(96.4, 2.3, 10, 22 + 54, y=PLATE_Y)
    assert fixture.intersect(path).Volume() < 1e-6
    for x in (-45, 45):
        contact = centered_box(3, 1.6, 9.9, 10, x=x, y=PLATE_Y)
        assert contact.cut(fixture).Volume() < 1e-6

    pad = centered_box(83, 39, 1.9, 2, y=PLATE_Y - 19.5)
    assert pad.cut(fixture).Volume() < 1e-6
    # A flat gauge covers the electronics footprint at the 8 mm seat offset.
    above_pad = centered_box(83, 39, 2, 10, y=PLATE_Y - 19.5)
    assert fixture.intersect(above_pad).Volume() < 1e-6
