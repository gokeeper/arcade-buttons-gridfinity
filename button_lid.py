"""Generate a thin OBSF-30 holder that sits on a 1×1 bin rim."""

import argparse
from pathlib import Path

import cadquery as cq

from button_bin import Parameters, cylinder, export_pair, rounded_prism, rounded_wire
from validate_models import mesh_report


LOCATOR_DEPTH = 1.2
PLATE_THICKNESS = 2.4
LID_WIDTH = 41.5
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opening", type=float, choices=(30.2, 30.6), action="append",
                        help="Body opening in mm. Omit to export both sizes.")
    parser.add_argument("--rim-profile", choices=RIM_PROFILES, default="reference")
    parser.add_argument("--rim-opening", type=float)
    parser.add_argument("--lower-opening", type=float)
    parser.add_argument("--rim-corner-radius", type=float)
    parser.add_argument("--clearance", type=float, default=0.4,
                        help="Locator clearance per side in mm.")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    rim, lower, radius = (
        default if override is None else override
        for default, override in zip(
            RIM_PROFILES[args.rim_profile],
            (args.rim_opening, args.lower_opening, args.rim_corner_radius),
        )
    )
    for opening in args.opening or (30.6, 30.2):
        lid = make_lid(opening, rim, lower, radius, args.clearance)
        if not lid.isValid() or len(lid.Solids()) != 1:
            raise RuntimeError("Expected one valid lid solid.")
        args.output.mkdir(parents=True, exist_ok=True)
        name = f"obsf30_1x1_lid_{opening:.1f}".replace(".", "p")
        if args.rim_profile != "reference":
            name += "_mw47599"
        path = args.output / name
        export_pair(lid, path)
        mesh_report(path.with_suffix(".stl"))
        print(f"{path.with_suffix('.stl')} ({lid.Volume():.0f} mm³ of CAD solid)")


if __name__ == "__main__":
    main()
