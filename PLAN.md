# Sanwa OBSF-30 Gridfinity storage bin

## Summary

Start with a **1×1×7U standalone bin**, holding one disconnected OBSF-30 upright and allowing loaded bins to stack. Use PETG with a 0.4 mm nozzle. Deliver editable **CadQuery source, STEP, and printable STL files**.

Correction after inspecting the [exact drawing](https://m.media-amazon.com/images/I/51oVK7HhGFL.jpg): **31.7 mm runs from the flange underside to the terminal tips**. Add 6.5 mm above the flange for a **38.2 mm overall height**. The earlier 6U design is superseded; its terminal tips would collide with the floor by 5 mm at the intended top elevation.

## Geometry and fit

Gridfinity uses a 42 mm pitch; the actual 1×1 bin exterior is **41.5 × 41.5 mm**. [Gridfinity reference](https://github.com/gridfinity-unofficial/specification)

| Feature | Initial design |
|---|---:|
| Nominal bin height / stacking pitch | 49 mm / 7U |
| Overall height with trimmed stacking lip | Approximately 52.8 mm |
| Interior floor elevation | 6.8 mm |
| Flange underside / seat elevation | 40.5 mm |
| Button top elevation | 47 mm |
| Terminal-tip elevation | 8.8 mm |
| Clearance beneath terminals | 2 mm |
| Clearance above button to nominal stacking plane | 2 mm |

Sanwa's drawing lists a **33.2 mm flange**, **29.5 mm body**, and **30 mm panel mounting hole**. These describe different features; the storage opening must also accommodate the retention clips. [Sanwa catalog](https://rs2006.co.jp/e/sanwaseimitsu/Sanwa2019.pdf)

- Support the **fixed flange underside**, with the switch and terminals hanging freely.
- Start with a **31 mm body opening**, chamfered entry, and two opposed clip-relief channels extending to a 34 mm envelope. Keep those channels continuous beneath the cradle so the clips cannot latch under it.
- Provide a **34.2 mm flange recess** and two opposite diagonal finger wells, initially 10 mm wide and reaching 4.5 mm below the flange seat.
- Set flange-seat height using the drawing's 6.5 mm top-to-flange-underside offset, giving a seat elevation of 40.5 mm. Derive overall button height by adding the 31.7 mm below-flange dimension.
- Use 1.6 mm walls and sloped supports beneath the cradle for support-free printing. Preserve the stacking rim around the full perimeter.
- Omit magnet and screw pockets for the first prototype.

## Implementation and deliverables

- Build a parameterized CadQuery model separating the Gridfinity shell from the button cradle. Expose body clearance, clip relief, flange dimensions, seat height, finger access, and bin height.
- Export a small fit-coupon set with **30.6, 31.0, and 31.4 mm openings**, each including the flange seat and clip relief.
- Export the full 7U prototype, STEP solid, STL, a shaped button reference, and dimensioned illustrations showing the source geometry and stacking clearance. Retain the conservative envelope for collision checks; mark undimensioned visual details as approximate.
- Include the exact source drawing in the README and remove the obsolete 6U exports.
- Document PETG starting settings: 0.2 mm layers, four perimeters, and upright printing without supports.
- Keep the cradle reusable for a later bin insert. Exact compatibility with the linked MakerWorld bin requires its interior geometry; that model could not be inspected.
- Adapt to OBSF-24 after validating the 30 mm prototype, using its own dimensions rather than scaling the entire model.

## Validation and acceptance

- Check exported solids are valid and STL meshes are watertight.
- Check button, terminals, finger wells, and an upper bin's mating foot for interference; maintain at least 1 mm clearance to the stacked bin.
- Print the coupons first. Select the smallest opening that allows insertion and removal without squeezing or catching the clips.
- Print one full bin and confirm easy finger removal, suspended terminals, baseplate fit, and loaded stacking without pressing the button.
- Treat physical fit as unverified until those print checks pass; adjust exposed clearance parameters before producing multiples.
