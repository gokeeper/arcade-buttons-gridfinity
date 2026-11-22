# Sanwa OBSF-30 Gridfinity storage bin

## Summary

Start with a **1×1×6U standalone bin**, holding one disconnected OBSF-30 upright and allowing loaded bins to stack. Use PETG with a 0.4 mm nozzle. Deliver editable **CadQuery source, STEP, and printable STL files**.

The confirmed **31.7 mm overall button height includes the button top through the terminal tips**, making 6U a reasonable target. A conventional 5U bin leaves too little room after accounting for its base and protective clearances.

## Geometry and fit

Gridfinity uses a 42 mm pitch; the actual 1×1 bin exterior is **41.5 × 41.5 mm**. [Gridfinity reference](https://github.com/gridfinity-unofficial/specification)

| Feature | Initial design |
|---|---:|
| Nominal bin height / stacking pitch | 42 mm / 6U |
| Overall height with trimmed stacking lip | Approximately 45.8 mm |
| Interior floor elevation | 6.8 mm |
| Button top elevation | 40 mm |
| Terminal-tip elevation | 8.3 mm |
| Clearance beneath terminals | 1.5 mm |
| Clearance above button to nominal stacking plane | 2 mm |

Sanwa's drawing lists a **33.2 mm flange**, **29.5 mm body**, and **30 mm panel mounting hole**. These describe different features; the storage opening must also accommodate the retention clips. [Sanwa catalog](https://rs2006.co.jp/e/sanwaseimitsu/Sanwa2019.pdf)

- Support the **fixed flange underside**, with the switch and terminals hanging freely.
- Start with a **31 mm body opening**, chamfered entry, and two opposed clip-relief channels extending to a 34 mm envelope. Keep those channels continuous beneath the cradle so the clips cannot latch under it.
- Provide a **34.2 mm flange recess** and two opposite diagonal finger wells, initially 10 mm wide and reaching 4.5 mm below the flange seat.
- Set flange-seat height from its distance below the button top. Start with the drawing's apparent 6.5 mm offset, giving a seat elevation of 33.5 mm; verify this on the fit coupon.
- Use 1.6 mm walls and sloped supports beneath the cradle for support-free printing. Preserve the stacking rim around the full perimeter.
- Omit magnet and screw pockets for the first prototype.

## Implementation and deliverables

- Build a parameterized CadQuery model separating the Gridfinity shell from the button cradle. Expose body clearance, clip relief, flange dimensions, seat height, finger access, and bin height.
- Export a small fit-coupon set with **30.6, 31.0, and 31.4 mm openings**, each including the flange seat and clip relief.
- Export the full 6U prototype, STEP solid, STL, and a section-view preview showing the button envelope and stacking clearance.
- Document PETG starting settings: 0.2 mm layers, four perimeters, and upright printing without supports.
- Keep the cradle reusable for a later bin insert. Exact compatibility with the linked MakerWorld bin requires its interior geometry; that model could not be inspected.
- Adapt to OBSF-24 after validating the 30 mm prototype, using its own dimensions rather than scaling the entire model.

## Validation and acceptance

- Check exported solids are valid and STL meshes are watertight.
- Check button, terminals, finger wells, and an upper bin's mating foot for interference; maintain at least 1 mm clearance to the stacked bin.
- Print the coupons first. Select the smallest opening that allows insertion and removal without squeezing or catching the clips.
- Print one full bin and confirm easy finger removal, suspended terminals, baseplate fit, and loaded stacking without pressing the button.
- Treat physical fit as unverified until those print checks pass; adjust exposed clearance parameters before producing multiples.
