"""Fit regressions for the sideways JLF and the guide-supported lid."""

import pytest

from arcade_bin import FLOOR_Z
from joystick_bin import (
    LID_BASE_Z, check_fit, check_lid_fit, joystick_gauges, make_bin, make_lid,
)


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
