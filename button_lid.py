"""Generate OBSF-30 lids for Gridfinity bin rims."""

import argparse
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
SNAP_OPENING = 30.5
SNAP_RECESS_DIAMETER = 34.6
GRID_PITCH = 42.0
FLUSH_LAYOUTS = {"1x1": (1, 1), "2x4": (2, 4)}
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


def make_flush_snap_lid(layout: str = "1x1", *, rim_stop: bool = False) -> cq.Shape:
    """Build a snap-in lid with one bore per cell and an optional rim stop."""
    columns, rows = FLUSH_LAYOUTS[layout]
    width = FLUSH_LID_WIDTH + (columns - 1) * GRID_PITCH
    length = FLUSH_LID_WIDTH + (rows - 1) * GRID_PITCH
    locator_height = FLUSH_LID_THICKNESS - RIM_STOP_HEIGHT if rim_stop else FLUSH_LID_THICKNESS
    lid = (cq.Workplane("XY").rect(width, length).extrude(locator_height)
           .edges("|Z").fillet(FLUSH_LID_CORNER_RADIUS).val())
    if rim_stop:
        extra_width = LID_WIDTH - FLUSH_LID_WIDTH
        flange = (cq.Workplane("XY", origin=(0, 0, locator_height))
                  .rect(width + extra_width, length + extra_width).extrude(RIM_STOP_HEIGHT)
                  .edges("|Z").fillet(RIM_STOP_CORNER_RADIUS).val())
        lid = lid.fuse(flange)
    recess_depth = FLUSH_LID_THICKNESS - PLATE_THICKNESS
    cuts = []
    for column in range(columns):
        x = (column - (columns - 1) / 2) * GRID_PITCH
        for row in range(rows):
            y = (row - (rows - 1) / 2) * GRID_PITCH
            cuts.extend((
                cylinder(SNAP_OPENING, -1, FLUSH_LID_THICKNESS + 1, x, y),
                cylinder(SNAP_RECESS_DIAMETER, -1, recess_depth, x, y),
            ))
    return lid.cut(*cuts).clean()


def export_lid(lid: cq.Shape, path: Path, *, button_face_down: bool = False) -> None:
    if not lid.isValid() or len(lid.Solids()) != 1:
        raise RuntimeError("Expected one valid lid solid.")
    path.parent.mkdir(parents=True, exist_ok=True)
    stl_shape = None
    if button_face_down:
        # Starting on the recessed face leaves eight unsupported shoulders.
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
        "--flush-snap", nargs="?", const="1x1", choices=FLUSH_LAYOUTS,
        help="Export a 30.5 mm flush snap-in lid for MakerWorld 47599 (default: 1x1).",
    )
    snap_design.add_argument(
        "--rim-stop-snap", action="store_true",
        help="Export the 2x4 snap-in lid with a full rim stop for MakerWorld 47599.",
    )
    parser.add_argument("--opening", type=float, choices=(30.2, 30.6), action="append",
                        help="Body opening in mm. Omit to export both sizes.")
    parser.add_argument("--rim-profile", choices=RIM_PROFILES)
    parser.add_argument("--rim-opening", type=float)
    parser.add_argument("--lower-opening", type=float)
    parser.add_argument("--rim-corner-radius", type=float)
    parser.add_argument("--clearance", type=float,
                        help="Locator clearance per side in mm (default: 0.4).")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    if args.flush_snap or args.rim_stop_snap:
        if any(option is not None for option in (
            args.opening, args.rim_profile, args.rim_opening, args.lower_opening,
            args.rim_corner_radius, args.clearance,
        )):
            parser.error("Snap-in lids use fixed dimensions. Only --output can be combined with them.")
        layout = "2x4" if args.rim_stop_snap else args.flush_snap
        variant = "rim_stop" if args.rim_stop_snap else "flush"
        name = f"obsf30_{layout}_{variant}_snap_lid_30p5_mw47599"
        export_lid(make_flush_snap_lid(layout, rim_stop=args.rim_stop_snap), args.output / name,
                   button_face_down=layout == "2x4")
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
