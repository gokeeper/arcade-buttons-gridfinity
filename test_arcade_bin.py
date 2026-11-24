"""Geometry checks for the mixed bin and its matching lid."""

import cadquery as cq
import pytest

from arcade_bin import check_fit, make_bin, make_lid
from balltop_bin import seated_ball_center_z


@pytest.fixture(scope="module")
def bin_body():
    return make_bin()


@pytest.fixture(scope="module", params=[False, True], ids=["no-tab", "lift-tab"])
def lid(request):
    return make_lid(lift_tab=request.param)


def test_lid_bores_and_recesses_match_the_eight_cell_layout(lid):
    small = {(0, 42), (42, 42)}
    large = {(-42, 0), (0, 0), (42, 0), (-42, -42), (0, -42), (42, -42)}
    for face, small_diameter, large_diameter in (
        (max(lid.Faces(), key=lambda face: face.Center().z), 24.3, 30.5),
        (min(lid.Faces(), key=lambda face: face.Center().z), 28.6, 34.6),
    ):
        holes = [wire.Edges()[0] for wire in face.innerWires()]
        assert len(holes) == 8
        diameters = {(round(edge.Center().x), round(edge.Center().y)): 2 * edge.radius()
                     for edge in holes}
        assert diameters == pytest.approx({**dict.fromkeys(small, small_diameter),
                                           **dict.fromkeys(large, large_diameter)})
    recess_shoulders = [face for face in lid.Faces() if face.geomType() == "PLANE"
                        and face.Center().z == pytest.approx(0.8)]
    assert len(recess_shoulders) == 8
    assert lid.BoundingBox().zmax == pytest.approx(3.2)


def test_bin_has_nine_feet_and_plain_low_outer_walls(bin_body):
    bounds = bin_body.BoundingBox()
    assert (bounds.xlen, bounds.ylen, bounds.zmin, bounds.zmax) == pytest.approx(
        (125.5, 125.5, 0, 45.55), abs=1e-6
    )
    foot_pads = [face for face in bin_body.Faces() if face.BoundingBox().zmax < 1e-6]
    assert len(foot_pads) == 9
    assert {(round(face.Center().x), round(face.Center().y)) for face in foot_pads} == {
        (x, y) for x in (-42, 0, 42) for y in (-42, 0, 42)
    }
    for across in (27, 42, 57):
        for x, y in ((-62, across), (-across, 62)):
            assert bin_body.isInside(cq.Vector(x, y, 31.54))
            assert not bin_body.isInside(cq.Vector(x, y, 31.56))


def test_lid_seats_on_both_dividers_and_clears_the_loaded_bin(bin_body, lid):
    seated = lid.translate((0, 0, 43.55))
    for x, y in ((-21, 42), (-42, 21), (-21, 21)):
        assert bin_body.isInside(cq.Vector(x, y, 45.54))
        assert seated.isInside(cq.Vector(x, y, 45.56))
        assert not seated.isInside(cq.Vector(x, y, 45.54))
    assert check_fit(bin_body, seated) == pytest.approx({"obsf24": 7.55, "obsf30": 7.85})


def test_lift_tab_extends_only_the_two_button_rim_end():
    original = make_lid()
    tabbed = make_lid(lift_tab=True)
    assert original.BoundingBox().ymax == pytest.approx(62.75)
    assert original.cut(tabbed).Volume() < 1e-6
    bounds = tabbed.BoundingBox()
    assert (bounds.xmin, bounds.xmax, bounds.ymin, bounds.ymax) == pytest.approx(
        (-62.75, 62.75, -62.75, 70.75)
    )
    for x in (-21.5, 0, 42, 62):
        assert tabbed.isInside(cq.Vector(x, 66.75, 2.01))
        assert not tabbed.isInside(cq.Vector(x, 66.75, 1.99))
    assert not tabbed.isInside(cq.Vector(-42, 66.75, 2.6))


def test_nominal_ball_centers_on_the_rounded_seat(bin_body):
    x, y = -42, 42
    for offset, occupied in ((8.99, False), (9.01, True), (11.49, True), (11.51, False)):
        point = cq.Vector(x + offset, y, 9)
        assert bin_body.isInside(point) == occupied
    assert bin_body.isInside(cq.Vector(x + 10, y, 10.19))
    assert not bin_body.isInside(cq.Vector(x + 10, y, 10.21))
    assert sum(face.geomType() == "TORUS" for face in bin_body.Faces()) == 1

    radius = 17.5
    center = cq.Vector(x, y, seated_ball_center_z(7.2, radius))
    ball = cq.Solid.makeSphere(radius, center, angleDegrees1=-90, angleDegrees2=90)
    assert center.z + radius - 31.55 == pytest.approx(11, abs=0.1)
    assert bin_body.intersect(ball).Volume() < 1e-6
    assert bin_body.intersect(ball.translate((0, 0, -0.05))).Volume() > 1e-6
    for offset in ((0.25, 0, 0), (0, -0.25, 0)):
        assert bin_body.intersect(ball.translate(offset)).Volume() > 1e-6
