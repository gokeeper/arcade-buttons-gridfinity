# Arcade Buttons × Gridfinity

Drop-in rim-stop lids for storing Sanwa OBSF-24 and OBSF-30 arcade buttons
in existing Gridfinity bins.

![Rim-stop lids for five OBSF-24 buttons on a 1×4 bin, four OBSF-30 buttons on a 1×4 bin, and eight OBSF-30 buttons on a 2×4 bin](https://raw.githubusercontent.com/gokeeper/arcade-buttons-gridfinity/master/output/preview.png?v=rim-stop-lids)

## Drop-in lids for existing bins

| Bin footprint | Buttons | Center spacing | Files |
|---|---|---:|---|
| 1×4 | 5 × OBSF-24 | 32 mm | [STL](output/obsf24_1x4_rim_stop_snap_lid_24p3_mw47599.stl) · [STEP](output/obsf24_1x4_rim_stop_snap_lid_24p3_mw47599.step) |
| 1×4 | 4 × OBSF-30 | 42 mm | [STL](output/obsf30_1x4_rim_stop_snap_lid_30p5_mw47599.stl) · [STEP](output/obsf30_1x4_rim_stop_snap_lid_30p5_mw47599.step) |
| 2×4 | 8 × OBSF-30 | 42 mm | [STL](output/obsf30_2x4_rim_stop_snap_lid_30p5_mw47599.stl) · [STEP](output/obsf30_2x4_rim_stop_snap_lid_30p5_mw47599.step) |

### Bin and button fit

The lids were sized for the rounded rims on `1x4x7u.stl` and `2x4x7u.stl`
from ABDELat's Ultimate Gridfinity Bins collection. The full lip rests on
all four sides of the rim, raising the button mounting face by 1.2 mm.
A 2 mm locator centers the lid inside the opening.
[Bin collection](https://makerworld.com/en/models/47599-ultimate-gridfinity-bins-collection-parametric)

| Bin footprint | Lid footprint | Rounded locator footprint |
|---|---:|---:|
| 1×4 | 41.5 × 167.5 mm | 37 × 163 mm |
| 2×4 | 83.5 × 167.5 mm | 79 × 163 mm |

| Fit dimension | OBSF-24 | OBSF-30 |
|---|---:|---:|
| Snap-in opening | 24.3 mm | 30.5 mm |
| Underside clip recess diameter | 28.6 mm | 34.6 mm |
| Button flange diameter | 27.2 mm | 33.2 mm |
| Flange underside to bare terminal tips | 32.0 mm | 31.7 mm |
| Bare terminal reach below the bin rim | 30.8 mm | 30.5 mm |

The lid leaves 2.4 mm of material at each opening for the clips to engage.
The five-button layout leaves 4.8 mm between flanges, and the OBSF-30 layouts
leave 8.8 mm. [OBSF-24 drawing](https://m.media-amazon.com/images/I/51gVxMsMtcL.jpg) ·
[OBSF-30 drawing](docs/obsf30-dimensions.jpg)

Checks against the 1×4 reference mesh found about 0.35 mm of locator
clearance per side and at least 7.5 mm below the bare terminals for the
OBSF-24 lid or 7.7 mm for the OBSF-30 lid. Check terminal clearance in
your bin before seating the loaded lid.

## Print and use

1. Print in PETG. The STLs are already oriented with the flat button-facing
   side on the bed and the clip recesses facing up.
2. Press the buttons into the lid and check that each flange seats flat
   and both clips engage. Check that the loaded lid rests on the bin rim.
3. To remove a button, lift the whole lid, squeeze the clips from underneath,
   and push the button out.

The geometry was verified digitally. Printed rim fit and clip engagement
still need a physical check.

## Regenerate

From the repository root, use the existing Python environment with
[CadQuery and Matplotlib](requirements.txt).

```bash
/home/gkp/codes/.headless/bin/pip install -r requirements.txt
```

```bash
# 1×4 lid for five OBSF-24 buttons
/home/gkp/codes/.headless/bin/python button_lid.py --rim-stop-snap 1x4

# 1×4 lid for four OBSF-30 buttons
/home/gkp/codes/.headless/bin/python button_lid.py --rim-stop-snap 1x4 --button obsf30

# 2×4 lid for eight OBSF-30 buttons
/home/gkp/codes/.headless/bin/python button_lid.py --rim-stop-snap 2x4

# README preview
/home/gkp/codes/.headless/bin/python preview.py
```

The lid generator checks that each lid is a single valid solid and that
its STL is watertight with consistent winding. Geometry tests cover the
openings, recesses, rim stops, and STL print orientation.

```bash
/home/gkp/codes/.headless/bin/pip install pytest
/home/gkp/codes/.headless/bin/python -m pytest -q
```
