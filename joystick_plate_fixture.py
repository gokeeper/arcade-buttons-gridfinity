"""Generate the JLF plate-seat fixture for measuring clearance under the PCB."""

from pathlib import Path

import cadquery as cq

from button_bin import export_pair
from joystick_bin import (
    GUIDE_DEPTH, LEAD_IN, PLATE_Y, SLOT_LENGTH, add_plate_guides, centered_box,
)
from validate_models import validate_export


def make_fixture() -> cq.Shape:
    floor_z = 2.0
    seat_z = floor_z + 8.0
    outer_x = SLOT_LENGTH / 2 + LEAD_IN + 4.0
    crossbar = centered_box(2 * outer_x, GUIDE_DEPTH, 0, floor_z, y=PLATE_Y)
    pad_depth = 39.0
    pcb_pad = centered_box(83, pad_depth, 0, floor_z, y=PLATE_Y - pad_depth / 2)
    return add_plate_guides(crossbar.fuse(pcb_pad), outer_x=outer_x,
                            floor_z=floor_z, seat_z=seat_z, top_z=seat_z + 12)


if __name__ == "__main__":
    fixture = make_fixture()
    path = Path("output/test_fixtures/jlf_tp_8yt_plate_seat_8mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    export_pair(fixture, path)
    report = validate_export(fixture, path)
    print(f"{path}: {report['dimensions_mm']} mm, valid STEP solid and watertight STL")
