"""Generate the 8U and 9U sideways JLF-TP-8YT bins and the 9U shaft-bay lid."""

import argparse
from math import hypot
from pathlib import Path

import cadquery as cq

from arcade_bin import (
    BUTTON_RIM_Z, FLOOR_Z, FOOTPRINT, LOCATOR_CLEARANCE, LOCATOR_DEPTH,
    WALL_THICKNESS, make_3x3_blank,
)
from balltop_bin import BALL_DIAMETER
from button_bin import Parameters, cylinder, export_pair, rounded_prism
from button_lid import (
    FLUSH_LID_THICKNESS, PLATE_THICKNESS as SNAP_PANEL_THICKNESS, RIM_STOP_CORNER_RADIUS,
    RIM_STOP_HEIGHT, SNAP_BUTTONS, cut_snap_openings,
)
from validate_models import validate_export


PLATE_LENGTH = 95.0  # Along X, transverse to the horizontal shaft.
PLATE_WIDTH = 54.0   # Vertical when seated.
PLATE_THICKNESS = 1.6
PLATE_Y = -17.5
PLATE_FRONT_Y = PLATE_Y + PLATE_THICKNESS / 2
HANDLE_REACH = 70.0  # From the front of the plate to the end of the LB-35.
BARE_SHAFT_REACH = HANDLE_REACH - BALL_DIAMETER / 2  # Modeled to the ball center.
SHAFT_DIAMETER = 11.0
WASHER_DIAMETER = 46.0
WASHER_THICKNESS = 2.0

PLATE_LIFT = 7.0  # Height above the floor from the printed fit test.
PLATE_SEAT_Z = FLOOR_Z + PLATE_LIFT
SHAFT_Z = PLATE_SEAT_Z + PLATE_WIDTH / 2

BODY_LENGTH = 81.0  # Across the plate, including the two body mounting ears.
BODY_DEPTH = 37.0   # Behind the plate.
BODY_BELOW_SHAFT = PLATE_WIDTH / 2 + 6.0  # Allow 6 mm past the plate for the PCB and restrictor.

SLOT_LENGTH = 96.4
SLOT_DEPTH = 1.9  # 0.3 mm total play around the nominal 1.6 mm plate.
GUIDE_INNER_X = 42.0
GUIDE_DEPTH = 12.0
GUIDE_FRONT_Y = PLATE_Y + GUIDE_DEPTH / 2
LEAD_IN = 1.2

RIM_Z = {8: BUTTON_RIM_Z + 7, 9: BUTTON_RIM_Z + 14}
LID_BASE_Z = RIM_Z[9] - LOCATOR_DEPTH
LID_FACE_Z = RIM_Z[9] + RIM_STOP_HEIGHT
BUTTON_POSITIONS = (("obsf30", -37, 20), ("obsf30", 37, 20))
CENTER_EDGE_Y = -7.5
FINGER_X = 22.0
FINGER_RADIUS = 10.5


def centered_box(width: float, depth: float, bottom: float, top: float,
                 x: float = 0, y: float = 0) -> cq.Solid:
    return cq.Solid.makeBox(width, depth, top - bottom,
                            cq.Vector(x - width / 2, y - depth / 2, bottom))


def add_plate_guides(base: cq.Shape, *, outer_x: float, floor_z: float,
                     seat_z: float, top_z: float, slot_depth: float = SLOT_DEPTH) -> cq.Shape:
    """Join both guides to the floor and cut their common slot and tapered entry."""
    guide_width = outer_x - GUIDE_INNER_X
    guide_center = (outer_x + GUIDE_INNER_X) / 2
    guides = [centered_box(guide_width, GUIDE_DEPTH, floor_z - 0.5, top_z,
                           x=sign * guide_center, y=PLATE_Y) for sign in (-1, 1)]
    slot = centered_box(SLOT_LENGTH, slot_depth, seat_z, top_z + 1, y=PLATE_Y)
    lead_in = cq.Solid.makeLoft([
        cq.Workplane("XY", origin=(0, PLATE_Y, z)).rect(
            SLOT_LENGTH + flare, slot_depth + flare
        ).val()
        for z, flare in ((top_z - LEAD_IN, 0), (top_z, 2 * LEAD_IN))
    ], ruled=True)
    return base.fuse(*guides).cut(slot.fuse(lead_in)).clean()


def make_bin(height_u: int = 9) -> cq.Shape:
    if height_u not in RIM_Z:
        raise ValueError("The JLF bin comes in 8U and 9U.")
    rim_z = RIM_Z[height_u]
    cavity = rounded_prism(FOOTPRINT - 2 * WALL_THICKNESS,
                           RIM_STOP_CORNER_RADIUS - WALL_THICKNESS,
                           FLOOR_Z, rim_z + 1)
    tray = make_3x3_blank(rim_z).cut(cavity)
    return add_plate_guides(tray, outer_x=FOOTPRINT / 2 - WALL_THICKNESS / 2,
                            floor_z=FLOOR_Z, seat_z=PLATE_SEAT_Z, top_z=rim_z)


def lid_section(inset: float, shoulder_y: float, bottom: float, top: float) -> cq.Shape:
    half = FOOTPRINT / 2 - inset
    center_half = GUIDE_INNER_X - 7
    # The two shoulders run forward from the guides into the wide center panel.
    outline = [
        (-half, half), (half, half), (half, shoulder_y), (GUIDE_INNER_X, shoulder_y),
        (center_half, CENTER_EDGE_Y), (-center_half, CENTER_EDGE_Y),
        (-GUIDE_INNER_X, shoulder_y), (-half, shoulder_y),
    ]
    return (cq.Workplane("XY", origin=(0, 0, bottom)).polyline(outline).close()
            .extrude(top - bottom).edges("|Z").fillet(RIM_STOP_CORNER_RADIUS - inset).val())


def make_lid() -> cq.Shape:
    """Return the 9U lid face up with the bottom of its locator at Z=0."""
    # End the shoulders just ahead of the flared plate slots. Only the thinner
    # rim stop crosses the guide tops. The locator stops at their front faces.
    shoulder_y = GUIDE_FRONT_Y - 3.35
    stop = lid_section(0, shoulder_y, LOCATOR_DEPTH, FLUSH_LID_THICKNESS)
    locator = lid_section(WALL_THICKNESS + LOCATOR_CLEARANCE, GUIDE_FRONT_Y + LOCATOR_CLEARANCE,
                          0, LOCATOR_DEPTH)
    finger = cylinder(2 * FINGER_RADIUS, -1, FLUSH_LID_THICKNESS + 1, FINGER_X, CENTER_EDGE_Y)
    return cut_snap_openings(stop.fuse(locator).cut(finger), BUTTON_POSITIONS)


def joystick_gauges(*, with_ball: bool = False) -> dict[str, cq.Shape]:
    """Seated bounding boxes including the full X and Y play of the mounting plate."""
    play_x = SLOT_LENGTH - PLATE_LENGTH
    play_y = SLOT_DEPTH - PLATE_THICKNESS

    def gauge(width, depth, y, low_z, high_z):
        return centered_box(width + play_x, depth + play_y, low_z, high_z, y=y)

    plate_back = PLATE_Y - PLATE_THICKNESS / 2
    gauges = {
        "plate": gauge(PLATE_LENGTH, PLATE_THICKNESS, PLATE_Y,
                       PLATE_SEAT_Z, PLATE_SEAT_Z + PLATE_WIDTH),
        "PCB, restrictor and connector": gauge(
            BODY_LENGTH, BODY_DEPTH, plate_back - BODY_DEPTH / 2,
            SHAFT_Z - BODY_BELOW_SHAFT, SHAFT_Z + 41,
        ),
        "dust washer": gauge(WASHER_DIAMETER, WASHER_THICKNESS, PLATE_FRONT_Y + WASHER_THICKNESS / 2,
                             SHAFT_Z - WASHER_DIAMETER / 2, SHAFT_Z + WASHER_DIAMETER / 2),
        "bare shaft": gauge(SHAFT_DIAMETER, BARE_SHAFT_REACH, PLATE_FRONT_Y + BARE_SHAFT_REACH / 2,
                            SHAFT_Z - SHAFT_DIAMETER / 2, SHAFT_Z + SHAFT_DIAMETER / 2),
    }
    if with_ball:
        gauges["LB-35"] = gauge(BALL_DIAMETER, BALL_DIAMETER,
                                PLATE_FRONT_Y + HANDLE_REACH - BALL_DIAMETER / 2,
                                SHAFT_Z - BALL_DIAMETER / 2, SHAFT_Z + BALL_DIAMETER / 2)
    return gauges


def check_fit(bin_body: cq.Shape) -> None:
    """Check both seats and sweep the joystick up through the open bin."""
    rim_z = bin_body.BoundingBox().zmax
    for part, gauge in joystick_gauges(with_ball=True).items():
        b = gauge.BoundingBox()
        sweep = centered_box(b.xlen, b.ylen, b.zmin, max(b.zmax, rim_z + 1), y=b.center.y)
        if bin_body.intersect(sweep).Volume() > 1e-6:
            raise RuntimeError(f"The {part} catches in the bin.")

    for side in (-1, 1):
        underside = centered_box(3, PLATE_THICKNESS, PLATE_SEAT_Z - 0.1, PLATE_SEAT_Z,
                                 x=side * (PLATE_LENGTH / 2 - 3), y=PLATE_Y)
        if bin_body.intersect(underside).Volume() < underside.Volume() - 1e-6:
            raise RuntimeError("A mounting plate seat is missing.")


def check_lid_fit(bin_body: cq.Shape, seated: cq.Shape) -> None:
    """Verify 9U support, locator stops, snap mounts and loaded vertical removal."""
    rim_z = RIM_Z[9]
    if bin_body.intersect(seated).Volume() > 1e-6:
        raise RuntimeError("The lid interferes with the bin.")
    # Probe matching patches above and below the seating plane, away from slots.
    for x, y in ((-51, GUIDE_FRONT_Y - 1.5), (51, GUIDE_FRONT_Y - 1.5),
                 (0, FOOTPRINT / 2 - 0.95), (-FOOTPRINT / 2 + 0.95, 25),
                 (FOOTPRINT / 2 - 0.95, 25)):
        pad = centered_box(1, 1, rim_z - 0.1, rim_z, x, y)
        if (pad.cut(bin_body).Volume() > 1e-6
                or pad.translate((0, 0, 0.1)).cut(seated).Volume() > 1e-6):
            raise RuntimeError(f"Lid support missing at {(x, y)}.")

    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for travel in (LOCATOR_CLEARANCE - 0.01, LOCATOR_CLEARANCE + 0.01):
            shifted = seated.translate((dx * travel, dy * travel, 0))
            blocked = bin_body.intersect(shifted).Volume() > 1e-6
            if blocked != (travel > LOCATOR_CLEARANCE):
                raise RuntimeError(f"Unexpected locator travel toward {(dx, dy)}.")

    # The locator has a constant section up to the rim. Its overlap with
    # the cavity only shrinks as it lifts. Check both ends of its travel.
    if bin_body.intersect(seated.translate((0, 0, LOCATOR_DEPTH))).Volume() > 1e-6:
        raise RuntimeError("The lid catches on the rim.")

    p = Parameters()
    tip_z = LID_FACE_Z - p.flange_to_terminal
    load = [seated]
    max_button_shift = hypot(LOCATOR_CLEARANCE, LOCATOR_CLEARANCE)
    for button, x, y in BUTTON_POSITIONS:
        barrel = cylinder(p.body_diameter, tip_z, LID_FACE_Z, x, y)
        clips = cylinder(p.clip_span, tip_z, LID_FACE_Z - SNAP_PANEL_THICKNESS, x, y)
        flange = cylinder(p.flange_diameter, LID_FACE_Z, LID_FACE_Z + p.top_above_flange, x, y)
        if any(seated.intersect(part).Volume() > 1e-6 for part in (barrel, clips, flange)):
            raise RuntimeError(f"The button or its clips hit the lid at {(x, y)}.")
        load.extend((clips, barrel, flange))
        # Sweep the full recess diameter from the terminal tips past the rim,
        # allowing the locator to move into any corner of its clearance.
        sweep = cylinder(SNAP_BUTTONS[button][1] + 2 * max_button_shift,
                         tip_z, rim_z + 1, x, y)
        if bin_body.intersect(sweep).Volume() > 1e-6:
            raise RuntimeError(f"The button catches in the bin at {(x, y)}.")

    # Allow a 16 mm fingertip to reach 12 mm under the loaded lid at the scallop.
    finger = cylinder(16, LID_BASE_Z - 12, LID_FACE_Z + 25, FINGER_X, CENTER_EDGE_Y + 2)
    if any(finger.intersect(item).Volume() > 1e-6 for item in [bin_body, *load]):
        raise RuntimeError("The finger recess is obstructed.")
    load.append(finger)

    # In the rising lid's frame, every joystick part moves straight down.
    # Project each seated envelope to the floor to cover the entire stroke.
    for part, gauge in joystick_gauges().items():
        b = gauge.BoundingBox()
        sweep = centered_box(b.xlen + 2 * LOCATOR_CLEARANCE, b.ylen + 2 * LOCATOR_CLEARANCE,
                             FLOOR_Z, b.zmax, y=b.center.y)
        if any(item.intersect(sweep).Volume() > 1e-6 for item in load):
            raise RuntimeError(f"The loaded lid catches on the {part}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="Write all parts here (defaults to output/bins and output/lids).")
    args = parser.parse_args()
    bins = args.output or Path("output/bins")
    lids = args.output or Path("output/lids")
    bins.mkdir(parents=True, exist_ok=True)
    lids.mkdir(parents=True, exist_ok=True)
    for height_u in RIM_Z:
        body = make_bin(height_u)
        check_fit(body)
        path = bins / f"jlf_tp_8yt_3x3_{height_u}u_bin"
        export_pair(body, path)
        validate_export(body, path)
        print(f"{path}: verified plate seats, lift path, STL and STEP")
        if height_u == 9:
            lid = make_lid()
            seated = lid.translate((0, 0, LID_BASE_Z))
            check_lid_fit(body, seated)
            face_down = lid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, FLUSH_LID_THICKNESS))
            path = lids / "jlf_tp_8yt_3x3_9u_shaft_bay_lid"
            export_pair(seated, path, stl_shape=face_down)
            validate_export(seated, path)
            print(f"{path}: verified lid supports, locator, loaded lift path, STL and STEP")


if __name__ == "__main__":
    main()
