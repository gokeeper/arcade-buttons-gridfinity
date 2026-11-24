"""Generate arcade button lids for Gridfinity bin rims."""

import argparse
from collections.abc import Iterable
from pathlib import Path

import cadquery as cq

from button_bin import Parameters, cylinder, export_pair, rounded_prism, rounded_wire
from validate_models import mesh_report


LOCATOR_DEPTH = 1.2
PLATE_THICKNESS = 2.4
LID_WIDTH = 41.5
FLUSH_LID_WIDTH = 37.0
FLUSH_LID_THICKNESS = 3.2
FLUSH_LID_CORNER_RADIUS = 3.0
RIM_STOP_HEIGHT = 1.2
RIM_STOP_CORNER_RADIUS = 3.75
LIFT_TAB_EXTENSION = 8.0
GRID_PITCH = 42.0
SNAP_BUTTONS = {
    "obsf30": (30.5, 34.6),
    "obsf24": (24.3, 28.6),
}
SNAP_LAYOUTS = {
    "1x1": (1, 1, "obsf30"),
    "2x4": (2, 4, "obsf30"),
    "1x4": (1, 4, "obsf24"),
}
# Conservative straight taper fitted inside the rounded rim of the supplied
# ABDELat bin mesh. These are fit dimensions, not maximum rim measurements.
RIM_PROFILES = {
    "reference": (40.3, 37.9, 3.15),
    "makerworld-47599": (39.8, 37.4, 3.45),
}


def make_lid(
    opening: float,
    rim_opening: float = 40.3,
    lower_opening: float = 37.9,
    rim_corner_radius: float = 3.15,
    clearance: float = 0.4,
) -> cq.Shape:
    """Use the measured square opening widths at the rim and 1.2 mm below it.

    Clearance is per side. The defaults match the stacking bin in this repo.
    """
    p = Parameters()
    if not p.body_diameter < opening <= 31.4:
        raise ValueError("Body opening must be greater than 29.5 mm and at most 31.4 mm.")
    if not clearance > 0 or not lower_opening <= rim_opening < LID_WIDTH:
        raise ValueError("Use positive clearance and openings that widen toward the rim.")
    if lower_opening - 2 * clearance < p.clip_span + 2:
        raise ValueError("Measured opening is too narrow for the clip slots and locator walls.")
    bottom_radius = rim_corner_radius - (rim_opening - lower_opening) / 2
    if not clearance < bottom_radius <= rim_corner_radius < lower_opening / 2:
        raise ValueError("Corner radius must leave a rounded locator after clearance.")

    seat = LOCATOR_DEPTH + PLATE_THICKNESS
    locator = cq.Solid.makeLoft([
        rounded_wire(lower_opening - 2 * clearance, bottom_radius - clearance, 0),
        rounded_wire(rim_opening - 2 * clearance, rim_corner_radius - clearance,
                     LOCATOR_DEPTH),
    ], ruled=True)
    plate = rounded_prism(LID_WIDTH, 3.75, LOCATOR_DEPTH, seat)
    lid = plate.fuse(locator)
    # Keep the flange on top of the plate. The smaller finger holes preserve
    # more of the ring than the original coupon's two 10 mm holes.
    lid = lid.cut(
        cylinder(opening, -1, seat + 1),
        cq.Solid.makeBox(p.clip_span, p.clip_width, seat + 2,
                         cq.Vector(-p.clip_span / 2, -p.clip_width / 2, -1)),
        *[cylinder(8, -1, seat + 1, side * 13, side * 13) for side in (-1, 1)],
    )
    return lid.clean()


def make_rim_stop(width: float, length: float, bottom: float) -> cq.Shape:
    return (cq.Workplane("XY", origin=(0, 0, bottom)).rect(width, length)
            .extrude(RIM_STOP_HEIGHT).edges("|Z").fillet(RIM_STOP_CORNER_RADIUS).val())


def lift_tab_suffix(lift_tab: bool) -> str:
    return f"_lift_tab_{LIFT_TAB_EXTENSION:g}mm" if lift_tab else "_no_tab"


def make_flush_snap_lid(
    layout: str = "1x1", *, rim_stop: bool = False, button: str | None = None,
    lift_tab: bool = False,
) -> cq.Shape:
    """Build a snap-in lid for the selected bin footprint."""
    if lift_tab and (layout not in ("1x4", "2x4") or not rim_stop):
        raise ValueError("The lift tab requires a 1x4 or 2x4 rim-stop lid.")
    columns, rows, default_button = SNAP_LAYOUTS[layout]
    button = button or default_button
    width = FLUSH_LID_WIDTH + (columns - 1) * GRID_PITCH
    length = FLUSH_LID_WIDTH + (rows - 1) * GRID_PITCH
    locator_height = FLUSH_LID_THICKNESS - RIM_STOP_HEIGHT if rim_stop else FLUSH_LID_THICKNESS
    lid = (cq.Workplane("XY").rect(width, length).extrude(locator_height)
           .edges("|Z").fillet(FLUSH_LID_CORNER_RADIUS).val())
    if rim_stop:
        extra_width = LID_WIDTH - FLUSH_LID_WIDTH
        # Extend the flange at +Y while keeping the locator centered in the bin.
        tab = LIFT_TAB_EXTENSION if lift_tab else 0
        flange = make_rim_stop(width + extra_width, length + extra_width + tab,
                               locator_height).translate((0, tab / 2, 0))
        lid = lid.fuse(flange)
    y_centers = [(row - (rows - 1) / 2) * GRID_PITCH for row in range(rows)]
    if layout == "1x4" and button == "obsf24":
        # Fit five smaller buttons over four Gridfinity cells.
        y_centers = [-64, -32, 0, 32, 64]
    x_centers = [(column - (columns - 1) / 2) * GRID_PITCH for column in range(columns)]
    return cut_snap_openings(lid, ((button, x, y) for x in x_centers for y in y_centers))


def cut_snap_openings(lid: cq.Shape, positions: Iterable[tuple[str, float, float]]) -> cq.Shape:
    """Cut each snap bore and its underside clip recess into a lid based at Z=0."""
    recess_depth = FLUSH_LID_THICKNESS - PLATE_THICKNESS
    cuts = []
    for button, x, y in positions:
        opening, recess_diameter = SNAP_BUTTONS[button]
        cuts.extend((
            cylinder(opening, -1, FLUSH_LID_THICKNESS + 1, x, y),
            cylinder(recess_diameter, -1, recess_depth, x, y),
        ))
    return lid.cut(*cuts).clean()


def export_lid(lid: cq.Shape, path: Path, *, button_face_down: bool = False) -> None:
    if not lid.isValid() or len(lid.Solids()) != 1:
        raise RuntimeError("Expected one valid lid solid.")
    path.parent.mkdir(parents=True, exist_ok=True)
    stl_shape = None
    if button_face_down:
        # Starting on the recessed face leaves unsupported shoulders.
        # Flip the solid so each hole widens as the print reaches its recess.
        stl_shape = lid.rotate((0, 0, 0), (1, 0, 0), 180).translate(
            (0, 0, FLUSH_LID_THICKNESS)
        )
    export_pair(lid, path, stl_shape=stl_shape)
    mesh_report(path.with_suffix(".stl"))
    print(f"{path.with_suffix('.stl')} ({lid.Volume():.0f} mm³ of CAD solid)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    snap_design = parser.add_mutually_exclusive_group()
    snap_design.add_argument(
        "--flush-snap", nargs="?", const="1x1", choices=("1x1", "2x4"),
        help="Export a 30.5 mm flush snap-in lid for MakerWorld 47599 (default: 1x1).",
    )
    snap_design.add_argument(
        "--rim-stop-snap", nargs="?", const="2x4", choices=("2x4", "1x4"),
        help="Export a rim-stop lid for MakerWorld 47599 (default: 2x4).",
    )
    parser.add_argument("--button", choices=SNAP_BUTTONS,
                        help="Button model for --rim-stop-snap 1x4 (default: obsf24).")
    parser.add_argument("--lift-tab", action="store_true",
                        help="Add an 8 mm end tab to a rim-stop lid.")
    parser.add_argument("--opening", type=float, choices=(30.2, 30.6), action="append",
                        help="Body opening in mm. Omit to export both sizes.")
    parser.add_argument("--rim-profile", choices=RIM_PROFILES)
    parser.add_argument("--rim-opening", type=float)
    parser.add_argument("--lower-opening", type=float)
    parser.add_argument("--rim-corner-radius", type=float)
    parser.add_argument("--clearance", type=float,
                        help="Locator clearance per side in mm (default: 0.4).")
    parser.add_argument("--output", type=Path, default=Path("output/lids"))
    args = parser.parse_args()
    if args.button is not None and args.rim_stop_snap != "1x4":
        parser.error("--button requires --rim-stop-snap 1x4.")
    if args.lift_tab and not args.rim_stop_snap:
        parser.error("--lift-tab requires --rim-stop-snap.")
    if args.flush_snap or args.rim_stop_snap:
        if any(option is not None for option in (
            args.opening, args.rim_profile, args.rim_opening, args.lower_opening,
            args.rim_corner_radius, args.clearance,
        )):
            parser.error("Snap-in lids use fixed bore and rim dimensions.")
        layout = args.rim_stop_snap or args.flush_snap
        _, _, default_button = SNAP_LAYOUTS[layout]
        button = args.button or default_button
        opening, _ = SNAP_BUTTONS[button]
        variant = "rim_stop" if args.rim_stop_snap else "flush"
        opening_label = f"{opening:.1f}".replace(".", "p")
        name = f"{button}_{layout}_{variant}_snap_lid_{opening_label}_mw47599"
        if args.rim_stop_snap:
            name += lift_tab_suffix(args.lift_tab)
        lid = make_flush_snap_lid(
            layout, rim_stop=bool(args.rim_stop_snap), button=button, lift_tab=args.lift_tab,
        )
        export_lid(lid, args.output / name, button_face_down=layout != "1x1")
        return

    profile = args.rim_profile or "reference"
    clearance = 0.4 if args.clearance is None else args.clearance
    rim, lower, radius = (
        default if override is None else override
        for default, override in zip(
            RIM_PROFILES[profile],
            (args.rim_opening, args.lower_opening, args.rim_corner_radius),
        )
    )
    for opening in args.opening or (30.6, 30.2):
        lid = make_lid(opening, rim, lower, radius, clearance)
        name = f"obsf30_1x1_lid_{opening:.1f}".replace(".", "p")
        if profile != "reference":
            name += "_mw47599"
        export_lid(lid, args.output / name)


if __name__ == "__main__":
    main()
