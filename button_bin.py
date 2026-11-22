"""Parametric, millimetre-based Sanwa OBSF-30 Gridfinity prototype.

Run with /home/gkp/codes/.headless/bin/python button_bin.py.
The button envelope is deliberately conservative and omits the snap clips;
physical coupons are required to qualify the clip reliefs.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

import cadquery as cq


@dataclass(frozen=True)
class Parameters:
    height_u: int = 6
    wall: float = 1.6
    floor_z: float = 6.8
    body_diameter: float = 29.5
    body_opening: float = 31.0
    flange_diameter: float = 33.2
    flange_clearance: float = 1.0  # Diametral, not radial.
    button_height: float = 31.7  # Confirmed by user: top to terminal tip.
    top_above_flange: float = 6.5  # Provisional; verify on the real button.
    top_clearance: float = 2.0
    clip_span: float = 34.0  # X extent of the through relief rectangle.
    clip_width: float = 8.0  # Y extent; orient the two clips along X.
    finger_diameter: float = 10.0
    finger_offset: float = 12.0  # Both X and Y; two diagonal wells.
    finger_depth: float = 4.5
    support_height: float = 15.0
    entry_chamfer: float = 0.3

    @property
    def nominal_z(self) -> float:
        return self.height_u * 7.0

    @property
    def total_z(self) -> float:
        return self.nominal_z + 3.8

    @property
    def top_z(self) -> float:
        return self.nominal_z - self.top_clearance

    @property
    def seat_z(self) -> float:
        return self.top_z - self.top_above_flange

    @property
    def tip_z(self) -> float:
        return self.top_z - self.button_height

    def validate(self) -> None:
        values = asdict(self)
        if any(not isinstance(v, (int, float)) or not (0 < v < 1000)
               for v in values.values()):
            raise ValueError("All parameters must be finite, positive millimetres or units.")
        if not isinstance(self.height_u, int):
            raise ValueError("height_u must be an integer.")
        if self.tip_z - self.floor_z < 1.0 - 1e-8:
            raise ValueError("Need at least 1 mm below the terminal tips; increase height_u.")
        if self.top_clearance < 2:
            raise ValueError("Need at least 2 mm above the button for this stacking socket.")
        if not 1.0 <= self.wall < 3.75:
            raise ValueError("Wall thickness must be at least 1 and less than 3.75 mm.")
        if self.body_opening <= self.body_diameter:
            raise ValueError("body_opening must clear the button body.")
        if self.flange_diameter - self.body_opening - 2 * self.entry_chamfer < 1.2:
            raise ValueError("Need at least 0.6 mm radial flange support after the entry chamfer.")
        if self.seat_z - self.support_height <= self.floor_z:
            raise ValueError("Cradle support must begin above the interior floor.")
        if self.support_height <= self.entry_chamfer:
            raise ValueError("Cradle support must be taller than the entry chamfer.")
        if not (self.entry_chamfer < self.finger_depth < self.support_height):
            raise ValueError("Finger depth must lie within the cradle support height.")
        inner_half = (41.5 - 2 * self.wall) / 2
        if self.finger_offset + self.finger_diameter / 2 >= inner_half:
            raise ValueError("Finger wells must remain inside the bin walls.")
        if self.flange_diameter + self.flange_clearance >= 36.3:
            raise ValueError("Flange recess must fit below the stacking socket.")
        if self.clip_span >= 41.5 - 2 * self.wall:
            raise ValueError("Clip relief must remain inside the walls.")


def rounded_wire(width: float, radius: float, z: float) -> cq.Wire:
    wire = cq.Workplane("XY", origin=(0, 0, z)).rect(width, width).val()
    return wire.fillet2D(radius, wire.Vertices())


def circle_wire(diameter: float, z: float) -> cq.Wire:
    return cq.Workplane("XY", origin=(0, 0, z)).circle(diameter / 2).val()


def rounded_prism(width: float, radius: float, bottom: float, top: float) -> cq.Solid:
    return cq.Solid.makeLoft([
        rounded_wire(width, radius, bottom), rounded_wire(width, radius, top)
    ], ruled=True)


def cylinder(diameter: float, bottom: float, top: float,
             x: float = 0, y: float = 0) -> cq.Solid:
    return cq.Solid.makeCylinder(diameter / 2, top - bottom, cq.Vector(x, y, bottom))


def foot() -> cq.Solid:
    """Common Gridfinity male profile, including its 4.75 mm foot height."""
    return cq.Solid.makeLoft([
        rounded_wire(35.6, 0.8, 0),
        rounded_wire(37.2, 1.6, 0.8),
        rounded_wire(37.2, 1.6, 2.6),
        rounded_wire(41.5, 3.75, 4.75),
    ], ruled=True)


def shell(p: Parameters) -> cq.Shape:
    """Shell before cutting the reusable button cradle opening."""
    return foot().fuse(rounded_prism(41.5, 3.75, 4.75, p.total_z)).clean()


def cradle_cutters(p: Parameters) -> list[cq.Shape]:
    """Open cavity and flange seat; reusable inside a future fitted insert."""
    inner_width = 41.5 - 2 * p.wall
    inner_radius = 3.75 - p.wall
    support_bottom = p.seat_z - p.support_height
    mouth_bottom = p.seat_z - p.entry_chamfer
    eps = 0.01
    return [
        rounded_prism(inner_width, inner_radius, p.floor_z, support_bottom),
        cq.Solid.makeLoft([
            rounded_wire(inner_width, inner_radius, support_bottom),
            circle_wire(p.body_opening, mouth_bottom),
        ], ruled=True),
        cq.Solid.makeCone(p.body_opening / 2,
                         p.body_opening / 2 + p.entry_chamfer,
                         p.entry_chamfer + eps,
                         cq.Vector(0, 0, mouth_bottom)),
        cylinder(p.flange_diameter + p.flange_clearance, p.seat_z, p.total_z + 1),
        cq.Solid.makeBox(p.clip_span, p.clip_width, p.total_z + 1 - p.floor_z,
                         cq.Vector(-p.clip_span / 2, -p.clip_width / 2, p.floor_z)),
        *[cylinder(p.finger_diameter, p.seat_z - p.finger_depth, p.total_z + 1,
                   sign * p.finger_offset, sign * p.finger_offset)
          for sign in (-1, 1)],
    ]


def make_bin(p: Parameters = Parameters()) -> cq.Shape:
    p.validate()
    model = shell(p)
    for cutter in cradle_cutters(p):
        model = model.cut(cutter)

    # Above the recessed button, reopen the cavity and retain a full stacking lip.
    w = 41.5 - 2 * p.wall
    r = 3.75 - p.wall
    socket = cq.Solid.makeLoft([
        rounded_wire(w, r, p.top_z + 0.5),
        rounded_wire(w, r, p.nominal_z - 1.0),
        rounded_wire(36.3, 1.15, p.nominal_z),
        rounded_wire(37.7, 1.85, p.nominal_z + 0.7),
        rounded_wire(37.7, 1.85, p.nominal_z + 2.5),
        rounded_wire(40.3, 3.15, p.total_z),
        rounded_wire(40.3, 3.15, p.total_z + 1.0),
    ], ruled=True)
    return model.cut(socket).clean()


def make_coupon(opening: float, p: Parameters = Parameters()) -> cq.Shape:
    """Short flange/clip fit gauge; not a terminal-protecting storage bin."""
    p = replace(p, body_opening=opening)
    p.validate()
    seat = 2.4
    top = 3.6
    model = rounded_prism(41.5, 3.75, 0, top)
    for cutter in [
        cylinder(opening, -1, top + 1),
        cq.Solid.makeCone(opening / 2, opening / 2 + p.entry_chamfer,
                         p.entry_chamfer + 0.01,
                         cq.Vector(0, 0, seat - p.entry_chamfer)),
        cylinder(p.flange_diameter + p.flange_clearance, seat, top + 1),
        cq.Solid.makeBox(p.clip_span, p.clip_width, top + 2,
                         cq.Vector(-p.clip_span / 2, -p.clip_width / 2, -1)),
        *[cylinder(p.finger_diameter, -1, top + 1,
                   sign * p.finger_offset, sign * p.finger_offset)
          for sign in (-1, 1)],
    ]:
        model = model.cut(cutter)
    tab = rounded_prism(22, 1.8, 0, seat)
    # Trim a rounded square to an attached, flat label tab.
    tab = tab.intersect(cq.Solid.makeBox(24, 9, 3, cq.Vector(-12, -4.5, 0)))
    model = model.fuse(tab.translate((0, 24, 0)))
    font_path = Path("/usr/share/fonts/liberation/LiberationSans-Regular.ttf")
    text = cq.Workplane("XY", origin=(0, 24, seat - 0.4)).text(
        f"{opening:.1f}", 4, 0.6, font="Liberation Sans",
        fontPath=str(font_path) if font_path.exists() else None, combine=False
    )
    for letter in text.vals():
        model = model.cut(letter)
    return model.clean()


def button_envelope(p: Parameters) -> cq.Shape:
    """Conservative cylinders, not a detailed or clip-inclusive button CAD model."""
    return cylinder(p.body_diameter, p.tip_z, p.seat_z).fuse(
        cylinder(p.flange_diameter, p.seat_z, p.top_z)
    ).clean()


def export_pair(shape: cq.Shape, path: Path) -> None:
    cq.exporters.export(shape, str(path.with_suffix(".step")))
    cq.exporters.export(shape, str(path.with_suffix(".stl")),
                        tolerance=0.025, angularTolerance=0.08)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--config", type=Path, help="JSON overrides for Parameters fields")
    args = parser.parse_args()
    overrides = json.loads(args.config.read_text()) if args.config else {}
    p = Parameters(**overrides)
    p.validate()
    args.output.mkdir(parents=True, exist_ok=True)
    model = make_bin(p)
    name = f"obsf30_1x1_{p.height_u}u"
    export_pair(model, args.output / name)
    shapes = {name: model}
    for opening in (30.6, 31.0, 31.4):
        coupon_name = f"fit_coupon_{opening:.1f}".replace(".", "p")
        coupon = make_coupon(opening, p)
        export_pair(coupon, args.output / coupon_name)
        shapes[coupon_name] = coupon

    assembly = cq.Assembly(name="inspection_only_do_not_print")
    assembly.add(model, name="bin", color=cq.Color(0.15, 0.5, 0.65))
    assembly.add(button_envelope(p), name="conservative_button_envelope",
                 color=cq.Color(0.95, 0.55, 0.15, 0.5))
    assembly.add(foot().translate((0, 0, p.nominal_z)), name="upper_bin_foot",
                 color=cq.Color(0.5, 0.5, 0.5, 0.5))
    assembly.export(str(args.output / "inspection_assembly.step"))
    (args.output / "parameters.json").write_text(json.dumps(asdict(p), indent=2) + "\n")

    from validate_models import validate_all
    report = validate_all(p, shapes, args.output)
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    from preview import render_preview
    render_preview(model, p, args.output / "preview.png")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
