"""Generate mixed-button 3×3 Gridfinity bins and rim-stop lids."""

import argparse
from collections.abc import Iterator
from pathlib import Path

import cadquery as cq

from balltop_bin import (
    BALL_DIAMETER, ball_lift_envelope, make_ball_seat, seated_ball_center_z,
)
from button_bin import Parameters, cylinder, export_pair, foot, rounded_prism
from button_lid import (
    FLUSH_LID_THICKNESS, GRID_PITCH, LID_WIDTH, LIFT_TAB_EXTENSION, RIM_STOP_CORNER_RADIUS,
    RIM_STOP_HEIGHT, SNAP_BUTTONS, cut_snap_openings, lift_tab_suffix, make_rim_stop,
)
from validate_models import validate_export


LAYOUT = (
    (None, "obsf24", "obsf24"),
    ("obsf30", "obsf30", "obsf30"),
    ("obsf30", "obsf30", "obsf30"),
)
FOOTPRINT = LID_WIDTH + 2 * GRID_PITCH
FOOT_TOP_Z = 4.75
FLOOR_Z = 7.2
BUTTON_RIM_Z = 45.55  # 7U rim datum of the repo's reference bin.
BALL_RIM_Z = BUTTON_RIM_Z - 14  # 5U.
BUTTON_CAVITIES = {
    6: (BUTTON_RIM_Z - 7, FLOOR_Z - 1),
    7: (BUTTON_RIM_Z, FLOOR_Z),
}
WALL_THICKNESS = 1.9
DIVIDER_THICKNESS = 2.4
LOCATOR_CLEARANCE = 0.35  # Per side.
LOCATOR_DEPTH = FLUSH_LID_THICKNESS - RIM_STOP_HEIGHT
LOCATOR_BOTTOM_Z = BUTTON_RIM_Z - LOCATOR_DEPTH
DIVIDER_BALL_EDGE = (GRID_PITCH + DIVIDER_THICKNESS) / 2
DIVIDER_BUTTON_EDGE = (GRID_PITCH - DIVIDER_THICKNESS) / 2
FLANGE_TO_TERMINAL = {"obsf24": 32.0, "obsf30": Parameters().flange_to_terminal}


def cell_center(row: int, column: int) -> tuple[float, float]:
    """Use one-based cell indices, with row 1 toward +Y and column 1 toward −X."""
    return (column - 2) * GRID_PITCH, (2 - row) * GRID_PITCH


def button_positions() -> Iterator[tuple[str, float, float]]:
    for row, cells in enumerate(LAYOUT, start=1):
        for column, button in enumerate(cells, start=1):
            if button is not None:
                yield button, *cell_center(row, column)


def ball_corner(edge: float, bottom: float, top: float) -> cq.Solid:
    """Box that covers the top-left corner to the given divider face."""
    outside = FOOTPRINT / 2 + 1
    return cq.Solid.makeBox(outside - edge, outside - edge, top - bottom,
                            cq.Vector(-outside, edge, bottom))


def button_section(inset: float, corner_edge: float, bottom: float, top: float) -> cq.Shape:
    """Form an L with a shared button cavity across the eight cells."""
    outer = rounded_prism(FOOTPRINT - 2 * inset, RIM_STOP_CORNER_RADIUS - inset, bottom, top)
    return outer.cut(ball_corner(corner_edge, bottom - 1, top + 1))


def make_3x3_blank(rim_z: float = BUTTON_RIM_Z) -> cq.Shape:
    """Return a body up to the given rim with nine Gridfinity feet."""
    body = rounded_prism(FOOTPRINT, RIM_STOP_CORNER_RADIUS, FOOT_TOP_Z, rim_z)
    foot_profile = foot()
    feet = [foot_profile.translate((*cell_center(row, column), 0))
            for row in range(1, 4) for column in range(1, 4)]
    return body.fuse(*feet)


def make_bin(button_height_u: int = 7) -> cq.Shape:
    rim_z, button_floor_z = BUTTON_CAVITIES[button_height_u]
    body = make_3x3_blank(rim_z)
    # The gap between the two cavity footprints forms the continuous dividers.
    cutter_top = rim_z + 1
    shared_cavity = button_section(WALL_THICKNESS, DIVIDER_BUTTON_EDGE, button_floor_z, cutter_top)
    inner = rounded_prism(FOOTPRINT - 2 * WALL_THICKNESS,
                          RIM_STOP_CORNER_RADIUS - WALL_THICKNESS, FLOOR_Z, cutter_top)
    ball_cavity = inner.intersect(ball_corner(DIVIDER_BALL_EDGE, FLOOR_Z - 1, cutter_top + 1))
    low_wall_cut = ball_corner(DIVIDER_BALL_EDGE, BALL_RIM_Z, cutter_top)
    seat = make_ball_seat(*cell_center(1, 1), FLOOR_Z)
    return body.cut(shared_cavity, ball_cavity, low_wall_cut).fuse(seat).clean()


def make_lid(*, lift_tab: bool = False) -> cq.Shape:
    """Return the lid with its locator at Z=0 and its button face pointing up."""
    stop = button_section(0, DIVIDER_BALL_EDGE, LOCATOR_DEPTH, FLUSH_LID_THICKNESS)
    if lift_tab:
        # Overlap the narrow +Y end so the tab's rounded corners blend into the rim.
        half = FOOTPRINT / 2
        tab_width = half + DIVIDER_BALL_EDGE
        tab_length = LIFT_TAB_EXTENSION + 2 * RIM_STOP_CORNER_RADIUS
        tab = make_rim_stop(tab_width, tab_length, LOCATOR_DEPTH).translate(
            (half - tab_width / 2, half + LIFT_TAB_EXTENSION - tab_length / 2, 0)
        )
        stop = stop.fuse(tab)
    locator = button_section(WALL_THICKNESS + LOCATOR_CLEARANCE,
                             DIVIDER_BUTTON_EDGE - LOCATOR_CLEARANCE, 0, LOCATOR_DEPTH)
    return cut_snap_openings(stop.fuse(locator), button_positions())


def check_fit(bin_body: cq.Shape, seated_lid: cq.Shape, *,
              button_height_u: int = 7) -> dict[str, float]:
    """Check rim seating, lift paths and bare terminal clearance in CAD."""
    assert bin_body.intersect(seated_lid).Volume() < 1e-6, "Lid interferes with bin"
    assert bin_body.intersect(seated_lid.translate((0, 0, -0.1))).Volume() > 1e-6, (
        "Lid has no rim stop"
    )
    # The opening and locator are vertical, so the locator only withdraws as it lifts.
    for lift in (0.5, 1, LOCATOR_DEPTH):
        assert bin_body.intersect(seated_lid.translate((0, 0, lift))).Volume() < 1e-6, (
            f"Lid catches at {lift} mm lift"
        )

    rim_z, button_floor_z = BUTTON_CAVITIES[button_height_u]
    lid_face_z = rim_z + RIM_STOP_HEIGHT
    terminal_clearance = {}
    for button, x, y in button_positions():
        tip_z = lid_face_z - FLANGE_TO_TERMINAL[button]
        # Sweep the full clip envelope up past the rim for loaded lid removal.
        _, clip_diameter = SNAP_BUTTONS[button]
        gauge = cylinder(clip_diameter, tip_z - 1, rim_z + 1, x, y)
        assert bin_body.intersect(gauge).Volume() < 1e-6, f"Blocked terminals at {(x, y)}"
        terminal_clearance[button] = tip_z - button_floor_z

    radius = BALL_DIAMETER / 2
    center = cq.Vector(*cell_center(1, 1), seated_ball_center_z(FLOOR_Z, radius))
    sweep = ball_lift_envelope(center, radius, lid_face_z + 1)
    assert bin_body.intersect(sweep).Volume() < 1e-6, "Ball catches in the bin"
    assert seated_lid.intersect(sweep).Volume() < 1e-6, "Ball catches on the lid"
    return terminal_clearance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output"),
                        help="Root directory for the bins and lids export folders.")
    parser.add_argument("--button-height", type=int, choices=BUTTON_CAVITIES, default=7,
                        help="Button-side height in U. Both heights use the 7U lid exports.")
    args = parser.parse_args()

    bin_body = make_bin(args.button_height)
    bin_path = args.output / "bins" / f"arcade_3x3_5u_{args.button_height}u_bin"
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    export_pair(bin_body, bin_path)
    validate_export(bin_body, bin_path)
    print(f"{bin_path}: watertight STL and valid STEP solid")

    rim_z, _ = BUTTON_CAVITIES[args.button_height]
    for lift_tab in (False, True):
        lid = make_lid(lift_tab=lift_tab)
        seated_lid = lid.translate((0, 0, rim_z - LOCATOR_DEPTH))
        clearance = check_fit(bin_body, seated_lid, button_height_u=args.button_height)
        lid_name = f"arcade_3x3_rim_stop_snap_lid{lift_tab_suffix(lift_tab)}"
        if args.button_height == 7:
            lid_path = args.output / "lids" / lid_name
            lid_path.parent.mkdir(parents=True, exist_ok=True)
            lid_for_print = lid.rotate((0, 0, 0), (1, 0, 0), 180).translate(
                (0, 0, FLUSH_LID_THICKNESS)
            )
            export_pair(seated_lid, lid_path, stl_shape=lid_for_print)
            validate_export(seated_lid, lid_path)
            print(f"{lid_path}: watertight STL and valid STEP solid")
        print(f"{lid_name} on {args.button_height}U:")
        for button, gap in clearance.items():
            print(f"{button.upper()}: {gap:.2f} mm below the bare terminal tips")


if __name__ == "__main__":
    main()
