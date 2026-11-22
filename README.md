# Arcade Buttons × Gridfinity

Parametric 3D-printable storage for arcade buttons, starting with
**one Sanwa OBSF-30 snap-in button in a 1×1×6U Gridfinity bin**.
The button drops into a flange cradle, with its switch and bare terminals
suspended above the floor. Opposed clip reliefs prevent intentional snap-in
retention; diagonal finger wells provide access beneath the fixed flange.

**Status: digitally validated prototype; physical fit has not been verified.**
Start with the [31.0 mm fit coupon](output/fit_coupon_31p0.stl) before printing
the full bin. OBSF-24 models and inserts for existing bins are planned.

![CAD preview and section](output/preview.png)

## Files

- [Saved design plan](PLAN.md)
- [Bin STL](output/obsf30_1x1_6u.stl) and [STEP](output/obsf30_1x1_6u.step)
- Fit-coupon STLs: [30.6 mm](output/fit_coupon_30p6.stl),
  [31.0 mm](output/fit_coupon_31p0.stl), [31.4 mm](output/fit_coupon_31p4.stl)
- [Inspection assembly](output/inspection_assembly.step): bin, conservative
  button envelope, and the foot of a bin stacked above it. **Do not print this assembly.**
- [Parameters used](output/parameters.json) and [validation results](output/validation.json)
- [Editable CadQuery source](button_bin.py)

## Fit and dimensions

| Feature | Millimetres |
|---|---:|
| Grid pitch | 42 × 42 |
| Exterior footprint | 41.5 × 41.5 |
| Nominal height / stacking pitch | 42 (6U) |
| Overall height, including trimmed lip | 45.8 |
| Body opening | 31.0 |
| Flange recess diameter | 34.2 |
| Clip relief | 34 along X × 8 along Y |
| Wall thickness | 1.6 |
| Floor elevation from underside of foot | 6.8 |
| Flange seat elevation | 33.5 |
| Button top elevation | 40.0 |
| Terminal tip elevation | 8.3 |
| Space under terminals / above button | 1.5 / 2.0 |

The design uses a **31.7 mm overall button height**, from top to terminal tip.
Flange OD 33.2 mm and body OD 29.5 mm come from the
[Sanwa catalog](https://rs2006.co.jp/e/sanwaseimitsu/Sanwa2019.pdf).
The **6.5 mm top-to-flange-underside distance is provisional**: confirm it on
your button before relying on the vertical clearances. If that distance changes,
adjust `top_above_flange`; this moves the seat while preserving the designed top
and terminal elevations for a correctly dimensioned button.

The relief dimensions are initial allowances, not measured dimensions of the
uncompressed clips. The button must be oriented with its two clips pointing
along the long direction of the relief opening (X). No clip compression should
be needed. Clear, silent, RG, screw-in, and other brands are not qualified by
this first model. OBSF-24 and inserts for existing bins are planned follow-ups.

The Gridfinity base follows the common 4.75 mm foot profile and a 41.5 mm body
on a 42 mm grid. The stacking socket uses a 4.4 mm theoretical profile trimmed
by 0.6 mm at the crown, giving a 3.8 mm printed lip. Profile dimensions are based
on the [community reference](https://github.com/gridfinity-unofficial/specification).
Physical compatibility with your particular baseplate and other bins still
needs checking.

## Print and fit sequence

1. Print the **31.0 mm fit coupon** flat with its engraved number facing up:
   PETG, 0.4 mm nozzle, 0.2 mm layers, four perimeters, no supports. Use your
   calibrated PETG temperatures and bed settings; leave XY scaling at 100%.
2. Hold the coupon above the table while inserting the button: terminals
   protrude through this short gauge. Align the clips with the opposed reliefs.
   Check that the fixed flange seats and lifts out freely without squeezing
   clips or prying. The engraved number is the body-opening diameter.
3. If the body opening binds, try 31.4 mm. If it feels unnecessarily loose,
   try 30.6 mm. If a clip catches, enlarge `clip_span` or `clip_width` rather
   than assuming a larger round hole will solve it.
4. Confirm the top-to-flange-underside distance. Update the parameters if
   necessary, and regenerate before printing the full bin.
5. Print the bin upright, foot on the bed: same PETG settings, four perimeters,
   about 15% infill, and no supports as the starting setup. Check the slicer's
   overhang preview and layer paths; the cradle underside is a 15 mm tall gradual
   loft, checked to stay within 46° from vertical on its tessellated underside.
6. Check baseplate fit, flange support, finger access, terminal clearance,
   and vertical removal. Stack an empty bin above the loaded bin and confirm
   it seats without touching or actuating the button.

The coupons test the local body/flange/clip fit. The full bin is required to
qualify reach, terminal protection, and stacking. This is a storage holder;
it is not designed for playing on the button or retaining it upside down.

## Regenerate

Use the existing Python environment at `/home/gkp/codes/.headless`.
CadQuery generates the solids and exports; Matplotlib generates the preview.
Install dependencies into that environment if needed:

```bash
/home/gkp/codes/.headless/bin/pip install -r requirements.txt
```

Run from the repository root:

```bash
/home/gkp/codes/.headless/bin/python button_bin.py
```

Override any field of `Parameters` with a JSON file, for example:

```json
{
  "body_opening": 31.4,
  "clip_span": 34.4
}
```

```bash
/home/gkp/codes/.headless/bin/python button_bin.py --config fit.json --output output-adjusted
```

Units are millimetres. Clearances named `flange_clearance` are **diametral**.
Regeneration writes four individual STEP/STL pairs, an inspection assembly,
a preview, parameters, and validation results. The three coupon diameters stay
30.6/31.0/31.4 mm; other coupon dimensions follow the selected parameters.

## Validation

Every generation checks connected valid solids, STEP round trips, exported STL edge
closure and winding, button-envelope removal, and stacking interference.
The button envelope deliberately overestimates the lower body but **omits clips**;
these checks cannot establish physical clip fit or compensate for printer error.

The geometry regression suite checks unsafe parameter combinations, cradle
overhangs, flange support, continuous clip reliefs, and a larger 7U variant.
The initial suite contains **13 passing tests**. To run it:

```bash
/home/gkp/codes/.headless/bin/pip install pytest
/home/gkp/codes/.headless/bin/python -m pytest -q
```

## Planned models

- Sanwa OBSF-24 with its own button dimensions.
- Removable inserts fitted to measured bin interiors, including the
  [Simple Gridfinity Box](https://makerworld.com/en/models/784676-simple-gridfinity-box-stackable-many-sizes).
- Larger layouts using the validated button cradle on the 42 mm grid.
