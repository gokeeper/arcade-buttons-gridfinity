"""Make a four-compartment 5U ball-top bin from the supplied 1x4x7u STL."""

from __future__ import annotations

import argparse
from math import isclose
from pathlib import Path

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape

from button_bin import export_pair
from validate_models import mesh_report


CELL_PITCH = 42.0
HEIGHT_REDUCTION = 14.0
LOWER_CUT_Z = 12.0
FLOOR_Z = 6.1
SEAT_Z = 7.202  # The source has a raised floor pad under each ball.
DIVIDER_THICKNESS = 1.8
DIVIDER_HEIGHT = 18.0  # Above the ball seat.
SCOOP_RADIUS = 9.0
SCOOP_START = 12.0  # Above the ball seat.
BALL_DIAMETER = 35.0
BALL_CLEARANCE = 1.0  # Diametral allowance used for the vertical removal check.


def load_source(path: Path) -> cq.Solid:
    """Sew the source STL facets into a solid for the CAD boolean operations."""
    mesh = TopoDS_Shape()
    if not path.is_file() or not StlAPI_Reader().Read(mesh, str(path)):
        raise ValueError(f"Could not read source STL at {path}")
    sewing = BRepBuilderAPI_Sewing(1e-5)
    sewing.Add(mesh)
    sewing.Perform()
    shells = cq.Shape.cast(sewing.SewedShape()).Shells()
    if len(shells) != 1 or sewing.NbFreeEdges():
        raise ValueError("The source STL must contain one closed shell.")
    solid = cq.Solid.makeSolid(shells[0]).clean()
    bounds = solid.BoundingBox()
    if not all(isclose(actual, expected, abs_tol=0.05) for actual, expected in zip(
        (bounds.xlen, bounds.ylen, bounds.zlen), (41.5, 167.5, 45.55),
    )):
        raise ValueError("Use the original 1x4x7u bin with its long side along Y.")
    return solid


def make_balltop_bin(source: cq.Shape) -> cq.Shape:
    bounds = source.BoundingBox()
    x_center = (bounds.xmin + bounds.xmax) / 2
    y_center = (bounds.ymin + bounds.ymax) / 2
    rim_z = bounds.zmax - HEIGHT_REDUCTION
    outside_x = bounds.xmin - 1
    cut_width = bounds.xlen + 2

    # Remove a strip from the straight walls and rejoin the original rim and base.
    lower, upper = (
        source.intersect(cq.Solid.makeBox(
            cut_width, bounds.ylen + 2, top - bottom,
            cq.Vector(outside_x, bounds.ymin - 1, bottom),
        ))
        for bottom, top in ((bounds.zmin - 1, LOWER_CUT_Z),
                            (LOWER_CUT_Z + HEIGHT_REDUCTION, bounds.zmax + 1))
    )
    body = lower.fuse(upper.translate((0, 0, -HEIGHT_REDUCTION))).clean()

    # Overlap the side walls and floor so all three dividers join the original shell.
    divider_base = FLOOR_Z - 0.3
    dividers = [
        cq.Solid.makeBox(
            bounds.xlen - 1.2, DIVIDER_THICKNESS, SEAT_Z + DIVIDER_HEIGHT - divider_base,
            cq.Vector(bounds.xmin + 0.6, y_center + cell * CELL_PITCH - DIVIDER_THICKNESS / 2,
                      divider_base),
        )
        for cell in (-1, 0, 1)
    ]
    body = body.fuse(*dividers).clean()

    # An open U-shaped scoop on each side exposes the ball below its equator.
    cell_centers = [y_center + cell * CELL_PITCH for cell in (-1.5, -0.5, 0.5, 1.5)]
    scoop_center_z = SEAT_Z + SCOOP_START + SCOOP_RADIUS
    scoops = []
    for y in cell_centers:
        scoops.extend((
            cq.Solid.makeCylinder(SCOOP_RADIUS, cut_width,
                                  cq.Vector(outside_x, y, scoop_center_z), cq.Vector(1, 0, 0)),
            cq.Solid.makeBox(cut_width, 2 * SCOOP_RADIUS, rim_z + 1 - scoop_center_z,
                             cq.Vector(outside_x, y - SCOOP_RADIUS, scoop_center_z)),
        ))
    body = body.cut(*scoops).clean()
    if not body.isValid() or len(body.Solids()) != 1:
        raise RuntimeError("Expected one valid, connected ball-top bin.")

    radius = (BALL_DIAMETER + BALL_CLEARANCE) / 2
    for position, y in enumerate(cell_centers, start=1):
        center = cq.Vector(x_center, y, SEAT_Z + radius)
        bottom = cq.Solid.makeSphere(radius, center, angleDegrees1=-90, angleDegrees2=0)
        top = cq.Solid.makeCylinder(radius, rim_z + 1 - center.z, center)
        sweep = bottom.fuse(top)
        if body.intersect(sweep).Volume() > 1e-6:
            raise RuntimeError(f"The ball removal path is blocked in cell {position}.")

    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("1x4x7u.stl"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()

    body = make_balltop_bin(load_source(args.source))
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "balltop_1x4_5u_35mm"
    export_pair(body, path)
    mesh_report(path.with_suffix(".stl"))
    print(f"{path.with_suffix('.stl')} (four 35 mm ball-top compartments)")


if __name__ == "__main__":
    main()
