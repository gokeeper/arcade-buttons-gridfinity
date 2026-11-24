"""Generate a 3×3 Gridfinity bin for a sideways Sanwa JLF-TP-8YT."""

import argparse
from pathlib import Path

import cadquery as cq

from arcade_bin import BUTTON_RIM_Z, FLOOR_Z, FOOTPRINT, WALL_THICKNESS, make_3x3_blank
from balltop_bin import BALL_DIAMETER
from button_bin import export_pair, rounded_prism
from button_lid import RIM_STOP_CORNER_RADIUS
from validate_models import validate_export


PLATE_LENGTH = 95.0  # Along X, transverse to the horizontal shaft.
PLATE_WIDTH = 54.0   # Vertical when seated.
PLATE_THICKNESS = 1.6
PLATE_Y = -17.5
HANDLE_REACH = 70.0  # From the front of the plate to the end of the LB-35.

# The drawing shows 75 mm across the body and 31 mm below the shaft with
# the connector up. Leave extra room for the PCB and restrictor tabs in the photo.
BODY_LENGTH = 81.0  # Across the plate, including the two body mounting ears.
BODY_DEPTH = 37.0   # Behind the plate.
BODY_BELOW_SHAFT = 40.0
BODY_FLOOR_CLEARANCE = 3.0
SHAFT_Z = FLOOR_Z + BODY_FLOOR_CLEARANCE + BODY_BELOW_SHAFT
PLATE_SEAT_Z = SHAFT_Z - PLATE_WIDTH / 2

SLOT_LENGTH = 96.4
SLOT_DEPTH = 2.3
GUIDE_INNER_X = 42.0
GUIDE_DEPTH = 12.0
GUIDE_TOP_Z = BUTTON_RIM_Z
LEAD_IN = 1.2


def centered_box(width: float, depth: float, bottom: float, top: float,
                 x: float = 0, y: float = 0) -> cq.Solid:
    return cq.Solid.makeBox(width, depth, top - bottom,
                            cq.Vector(x - width / 2, y - depth / 2, bottom))


def make_bin() -> cq.Shape:
    cavity = rounded_prism(FOOTPRINT - 2 * WALL_THICKNESS,
                           RIM_STOP_CORNER_RADIUS - WALL_THICKNESS,
                           FLOOR_Z, BUTTON_RIM_Z + 1)
    tray = make_3x3_blank().cut(cavity)

    # The guides join the floor and sidewalls, leaving the electronics bay open.
    guide_outer_x = FOOTPRINT / 2 - WALL_THICKNESS / 2
    guide_width = guide_outer_x - GUIDE_INNER_X
    guide_center = (guide_outer_x + GUIDE_INNER_X) / 2
    guides = [centered_box(guide_width, GUIDE_DEPTH, FLOOR_Z - 0.5, GUIDE_TOP_Z,
                           x=sign * guide_center, y=PLATE_Y) for sign in (-1, 1)]
    slot = centered_box(SLOT_LENGTH, SLOT_DEPTH, PLATE_SEAT_Z, GUIDE_TOP_Z + 1, y=PLATE_Y)
    lead_in = cq.Solid.makeLoft([
        cq.Workplane("XY", origin=(0, PLATE_Y, z)).rect(
            SLOT_LENGTH + flare, SLOT_DEPTH + flare
        ).val()
        for z, flare in ((GUIDE_TOP_Z - LEAD_IN, 0), (GUIDE_TOP_Z, 2 * LEAD_IN))
    ], ruled=True)
    return tray.fuse(*guides).cut(slot.fuse(lead_in)).clean()


def check_fit(bin_body: cq.Shape) -> None:
    """Check the plate seat and a straight vertical path for the assembly."""
    # Each clearance box extends upward from its seated position to check the
    # entire lift path in one intersection, including the play in the slots.
    play_x = SLOT_LENGTH - PLATE_LENGTH
    play_y = SLOT_DEPTH - PLATE_THICKNESS
    plate_back = PLATE_Y - PLATE_THICKNESS / 2
    plate_front = PLATE_Y + PLATE_THICKNESS / 2
    removal_top = BUTTON_RIM_Z + 1
    sweeps = {
        "mounting plate": centered_box(SLOT_LENGTH, SLOT_DEPTH, PLATE_SEAT_Z,
                                        removal_top, y=PLATE_Y),
        "switch body and connector": centered_box(
            BODY_LENGTH + play_x, BODY_DEPTH + play_y, SHAFT_Z - BODY_BELOW_SHAFT,
            removal_top, y=plate_back - BODY_DEPTH / 2,
        ),
        "shaft and LB-35": centered_box(
            BALL_DIAMETER + play_x, HANDLE_REACH + play_y, SHAFT_Z - BALL_DIAMETER / 2,
            removal_top, y=plate_front + HANDLE_REACH / 2,
        ),
    }
    for part, sweep in sweeps.items():
        if bin_body.intersect(sweep).Volume() > 1e-6:
            raise RuntimeError(f"The {part} catches in the bin.")

    # Both ends must bear on a shelf when the plate reaches its seated position.
    for side in (-1, 1):
        underside = centered_box(3, PLATE_THICKNESS, PLATE_SEAT_Z - 0.1, PLATE_SEAT_Z,
                                 x=side * (PLATE_LENGTH / 2 - 3), y=PLATE_Y)
        if bin_body.intersect(underside).Volume() < underside.Volume() - 1e-6:
            raise RuntimeError("A mounting plate seat is missing.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/bins"))
    args = parser.parse_args()

    bin_body = make_bin()
    check_fit(bin_body)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "jlf_tp_8yt_3x3_7u_bin"
    export_pair(bin_body, path)
    validate_export(bin_body, path)
    print(f"{path}: watertight STL, valid STEP solid, clear plate and body lift paths")


if __name__ == "__main__":
    main()
