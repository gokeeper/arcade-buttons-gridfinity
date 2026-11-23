"""Render CAD previews and dimensioned sections for the README."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

import cadquery as cq
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "arcade-buttons-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.path import Path as PlotPath
import numpy as np

from button_bin import Parameters, button_reference, foot
from button_lid import make_flush_snap_lid


PREVIEW_BACKGROUND = "#f4f6f8"


def rasterize(
    shape: cq.Shape, size: int | tuple[int, int] = 900, *, azimuth: float = -55,
    color: tuple[int, int, int] = (69, 139, 163),
) -> np.ndarray:
    """Orthographic depth buffer avoids painter-sorting artifacts in CAD renders."""
    width, height = (size, size) if isinstance(size, int) else size
    vertices, triangles = shape.tessellate(0.05, 0.12)
    xyz = np.array([v.toTuple() for v in vertices])
    az, el = np.radians([azimuth, 48])
    eye = np.array([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.sin(el)])
    right = np.array([-np.sin(az), np.cos(az), 0])
    up = np.cross(eye, right)
    view = xyz @ np.array([right, up, eye]).T
    projected = view[:, :2]
    projected -= (projected.min(axis=0) + projected.max(axis=0)) / 2
    scale = min(width * 0.93 / np.ptp(projected[:, 0]),
                height * 0.90 / np.ptp(projected[:, 1]))
    screen = np.column_stack((width / 2 + scale * view[:, 0],
                              height / 2 - scale * view[:, 1], view[:, 2]))
    background = matplotlib.colors.to_rgb(PREVIEW_BACKGROUND)
    rgb = np.full((height, width, 3), np.rint(np.array(background) * 255), dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    light = np.array([-0.3, -0.5, 0.81])
    light /= np.linalg.norm(light)
    base = np.array(color)
    for triangle in triangles:
        a, b, c = screen[list(triangle)]
        x0 = max(0, int(np.floor(min(a[0], b[0], c[0]))))
        x1 = min(width - 1, int(np.ceil(max(a[0], b[0], c[0]))))
        y0 = max(0, int(np.floor(min(a[1], b[1], c[1]))))
        y1 = min(height - 1, int(np.ceil(max(a[1], b[1], c[1]))))
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-10 or x1 < x0 or y1 < y0:
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        xx, yy = xx + 0.5, yy + 0.5
        u = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / denominator
        v = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / denominator
        w = 1 - u - v
        z = u * a[2] + v * b[2] + w * c[2]
        target = depth[y0:y1 + 1, x0:x1 + 1]
        mask = (u >= -1e-8) & (v >= -1e-8) & (w >= -1e-8) & (z > target)
        va, vb, vc = xyz[list(triangle)]
        normal = np.cross(vb - va, vc - va)
        norm = np.linalg.norm(normal)
        if norm < 1e-10:
            continue
        normal /= norm
        if normal @ eye < 0:
            normal = -normal
        shade = 0.55 + 0.45 * max(0, normal @ light)
        rgb[y0:y1 + 1, x0:x1 + 1][mask] = np.clip(base * shade, 0, 255).astype(np.uint8)
        target[mask] = z[mask]
    return rgb


def render_overview(path: Path) -> None:
    lid_color = (81, 114, 165)
    models = (
        ("1×4 lid", "5 × OBSF-24  ·  32 mm pitch",
         make_flush_snap_lid("1x4", rim_stop=True), (190, 125, 63)),
        ("1×4 lid", "4 × OBSF-30  ·  42 mm pitch",
         make_flush_snap_lid("1x4", rim_stop=True, button="obsf30"), lid_color),
        ("2×4 lid", "8 × OBSF-30  ·  42 mm pitch",
         make_flush_snap_lid("2x4", rim_stop=True), lid_color),
    )
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 3.9), facecolor=PREVIEW_BACKGROUND)
    fig.text(0.05, 0.90, "Rim-stop lids",
             fontsize=25, fontweight="bold", color="#172c3d")
    for ax, (title, subtitle, shape, color) in zip(axes, models):
        ax.imshow(rasterize(shape, (560, 340), azimuth=-15, color=color))
        ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color="#172c3d")
        ax.text(0, -0.04, subtitle, transform=ax.transAxes, va="top",
                fontsize=13, color="#354456")
        ax.axis("off")
    fig.text(0.05, 0.08, "Orthographic CAD views, scaled individually.",
             fontsize=10, color="#354456")
    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.24, top=0.76, wspace=0.20)
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_section(ax, shape: cq.Shape, color: str) -> None:
    # XZ slice is aligned with the opposed clip reliefs and source side view.
    slab = cq.Solid.makeBox(60, 0.02, shape.BoundingBox().zmax + 1,
                            cq.Vector(-30, -0.01, 0))
    vertices, triangles = shape.intersect(slab).tessellate(0.04, 0.1)
    polygons = [[(vertices[i].x, vertices[i].z) for i in triangle] for triangle in triangles]
    ax.add_collection(PolyCollection(polygons, facecolors=color, edgecolors="none"))


def draw_source_side_view(ax, p: Parameters) -> None:
    """Plot original source pixels, clipped to the button outline, at true datums.

    This is a side-view projection overlay, not a manufactured 3D solid. Pixel
    anchors are taken from docs/obsf30-dimensions.jpg. Piecewise vertical mapping
    aligns all four dimensioned planes despite minor scan distortion.
    """
    drawing = Path(__file__).resolve().parent / "docs" / "obsf30-dimensions.jpg"
    original = plt.imread(drawing)
    # Generous outline follows the source ink while excluding dimension lines.
    outline = PlotPath([
        (133, 325), (133, 310), (146, 289), (174, 270), (202, 270),
        (202, 230), (216, 222), (285, 213), (414, 209), (545, 213),
        (610, 222), (628, 230), (628, 270), (656, 270), (679, 289),
        (696, 310), (696, 326), (649, 326), (649, 365), (670, 365),
        (670, 373), (681, 373), (681, 381), (691, 381), (701, 393),
        (649, 528), (649, 607), (665, 607), (665, 638), (655, 648),
        (502, 648), (502, 671), (483, 671), (483, 733), (462, 733),
        (462, 842), (451, 855), (417, 855), (411, 844), (411, 733),
        (379, 733), (379, 671), (328, 671), (328, 549), (307, 549),
        (307, 648), (175, 648), (163, 638), (163, 607), (182, 607),
        (182, 528), (129, 393), (138, 383), (146, 383), (146, 375),
        (155, 375), (155, 365), (182, 365), (182, 326), (133, 325),
    ], closed=True)
    x0, x1, y0, y1 = 127, 704, 209, 856
    yy, xx = np.mgrid[y0:y1, x0:x1]
    mask = outline.contains_points(np.column_stack((xx.ravel(), yy.ravel())))
    rgba = np.empty((y1 - y0, x1 - x0, 4), dtype=float)
    rgba[:, :, :3] = original[y0:y1, x0:x1, :3] / 255.0
    rgba[:, :, 3] = mask.reshape(yy.shape).astype(float)
    x_edges = (np.arange(x0, x1 + 1) - 0.5 - 414) * p.flange_diameter / (692 - 136)
    z_edges = np.interp(np.arange(y0, y1 + 1) - 0.5,
                        [213, 324, 645, 853],
                        [p.top_z, p.seat_z, p.switch_bottom_z, p.tip_z])
    ax.pcolormesh(x_edges, z_edges, rgba, shading="flat", rasterized=True, zorder=2)


def render_preview(model: cq.Shape, p: Parameters, path: Path) -> None:
    fig, ((ax, section), (side_view, contact)) = plt.subplots(
        2, 2, figsize=(13, 12), facecolor=PREVIEW_BACKGROUND
    )
    ax.imshow(rasterize(model))
    ax.axis("off")
    ax.set_title(f"OBSF-30 · 1×1×{p.height_u}U\nActual CAD geometry", fontsize=13, pad=8)
    section.set_facecolor(PREVIEW_BACKGROUND)
    draw_section(section, model, "#458ba3")
    draw_source_side_view(section, p)
    if p.exposed_flange:
        section.annotate(f"{p.top_above_flange:g} mm above the rim",
                         xy=(0, p.top_z), xytext=(-24, p.top_z + 6),
                         fontsize=10, arrowprops={"arrowstyle": "->"})
        section.annotate("Flange overhangs\nthe finger cutout",
                         xy=(p.flange_diameter / 2 - 0.5, p.seat_z - 0.3),
                         xytext=(22, p.seat_z + 3), fontsize=10,
                         arrowprops={"arrowstyle": "->"})
    else:
        draw_section(section, foot().translate((0, 0, p.nominal_z)), "#828b96")
        section.axhline(p.nominal_z, color="#828b96", linestyle="--", linewidth=0.8)
        section.annotate(f"{p.top_clearance:g} mm top clearance",
                         xy=(0, p.top_z + p.top_clearance / 2),
                         xytext=(-26, p.top_z - 2), fontsize=10,
                         arrowprops={"arrowstyle": "->", "color": "#354456"})
    section.annotate(f"{p.tip_z - p.floor_z:.1f} mm beneath terminals",
                     xy=(0, (p.tip_z + p.floor_z) / 2), xytext=(-26, 2), fontsize=10,
                     arrowprops={"arrowstyle": "->", "color": "#354456"})
    # Rotate both solids together to cut across the load-bearing ledge.
    for solid, color in [(model, "#458ba3"), (button_reference(p), "#edba73")]:
        draw_section(contact, solid.rotate((0, 0, 0), (0, 0, 1), -90), color)
    outer = p.flange_diameter / 2
    inner = p.body_opening / 2 + p.entry_chamfer
    contact.plot([inner, outer], [p.seat_z, p.seat_z], color="#88230d", lw=4,
                 solid_capstyle="butt")
    contact.annotate(f"{outer-inner:.2f} mm radial contact",
                     xy=((outer+inner)/2, p.seat_z), xytext=(outer-5, p.seat_z-2.5),
                     arrowprops={"arrowstyle": "->"}, fontsize=11)
    contact.set(xlim=(outer-5.5, outer+2.5), ylim=(p.seat_z-3.5, p.seat_z+2.5),
                xlabel="Y (mm)", ylabel="Z (mm)", aspect="equal",
                title="Flange resting on cradle · enlarged YZ section")
    contact.text(outer-4.7, p.seat_z+1.4, "Button flange")
    contact.text(outer+0.2, p.seat_z-1.2, "Bin")
    section.set(xlim=(-28, 39), ylim=(-2, max(p.total_z + 7, p.top_z + 10)),
                xlabel="X (mm)", ylabel="Z (mm)")
    section.set_aspect("equal")
    section.spines[["top", "right"]].set_visible(False)
    section_title = "Cut through finger openings" if p.exposed_flange else "Cut through clip slots"
    section.set_title(f"XZ bin section + original button side view\n{section_title}", fontsize=12)
    # Show the exact source alongside the section, including the real clip
    # silhouette and dimension lines that cannot be inferred from a YZ slice.
    drawing = Path(__file__).resolve().parent / "docs" / "obsf30-dimensions.jpg"
    side_view.imshow(plt.imread(drawing))
    side_view.axis("off")
    side_view.set_title("Actual button side view\nExact source dimension drawing", fontsize=13, pad=8)
    height_note = "Exposed flange" if p.exposed_flange else f"{p.nominal_z:g} mm stacking pitch"
    fig.text(0.5, 0.06,
             f"41.5 × 41.5 × {p.total_z:g} mm overall  |  "
             f"{height_note}  |  PETG · 0.4 mm nozzle · 0.2 mm layers",
             ha="center", fontsize=11, color="#354456")
    fig.text(0.5, 0.025, "The lower-right CAD section shows the ledges that support the button.",
             ha="center", fontsize=10, color="#59687a")
    fig.subplots_adjust(left=0.05, right=0.98, bottom=0.12, top=0.94, wspace=0.15, hspace=0.38)
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def render_dimension_drawing(p: Parameters, path: Path) -> None:
    """Front silhouette of the shaped reference, with drawing-derived dimensions."""
    fig, ax = plt.subplots(figsize=(10, 8), facecolor="white")
    vertices, triangles = button_reference(p).tessellate(0.03, 0.1)
    front = [[(vertices[i].x, vertices[i].z) for i in tri] for tri in triangles]
    ax.add_collection(PolyCollection(front, facecolors="#e7b96d", edgecolors="none"))
    ink = "#354456"

    def vertical(x, bottom, top, label, extension=16.6):
        ax.plot([extension, x + 1], [bottom, bottom], color=ink, linewidth=0.7)
        ax.plot([extension, x + 1], [top, top], color=ink, linewidth=0.7)
        ax.annotate("", (x, bottom), (x, top),
                    arrowprops={"arrowstyle": "<->", "color": ink, "lw": 1})
        ax.text(x + 1.1, (bottom + top) / 2, label, va="center", rotation=90,
                fontsize=11, color=ink, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})

    def horizontal(left, right, z, origin_z, label):
        ax.plot([left, left], [origin_z, z + 0.5], color=ink, linewidth=0.7)
        ax.plot([right, right], [origin_z, z + 0.5], color=ink, linewidth=0.7)
        ax.annotate("", (left, z), (right, z),
                    arrowprops={"arrowstyle": "<->", "color": ink, "lw": 1})
        ax.text((left + right) / 2, z + 0.6, label, ha="center", va="bottom", fontsize=11,
                color=ink, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})

    horizontal(-p.flange_diameter / 2, p.flange_diameter / 2, p.top_z + 8, p.seat_z,
               f"Ø{p.flange_diameter:g}")
    horizontal(-p.cap_diameter / 2, p.cap_diameter / 2, p.top_z + 4, p.top_z,
               f"Ø{p.cap_diameter:g}")
    horizontal(-p.body_diameter / 2, p.body_diameter / 2, p.switch_bottom_z - 2,
               p.switch_bottom_z, f"Ø{p.body_diameter:g} max body")
    vertical(23, p.seat_z, p.top_z, f"{p.top_above_flange:g}")
    vertical(-18, p.top_z - p.cap_height, p.top_z, f"{p.cap_height:g}",
             extension=-p.cap_diameter / 2)
    vertical(23, p.switch_bottom_z, p.seat_z, f"{p.flange_to_switch_bottom:g}")
    vertical(23, p.tip_z, p.switch_bottom_z, f"{p.terminal_projection:g}", extension=1.4)
    vertical(36, p.tip_z, p.top_z, f"{p.button_height:g} overall", extension=1.4)
    vertical(-23, p.tip_z, p.seat_z, f"{p.flange_to_terminal:g} below flange", extension=-16.6)
    ax.axhline(p.seat_z, color=ink, linestyle="--", linewidth=0.6, alpha=0.5)
    ax.text(-28, p.seat_z + 0.6, "Flange underside", color=ink, fontsize=9)
    ax.set(xlim=(-29, 43), ylim=(p.tip_z - 5, p.top_z + 12))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Sanwa OBSF-30 · reference profile and dimensions (mm)", fontsize=14, pad=15)
    fig.text(0.5, 0.055,
             f"{p.button_height:g} overall = {p.top_above_flange:g} above flange "
             f"+ {p.flange_to_terminal:g} below flange",
             ha="center", fontsize=12, color=ink)
    fig.text(0.5, 0.025, "Dimensions follow the source drawing; clip, housing and terminal details are illustrative.",
             ha="center", fontsize=9, color=ink)
    fig.subplots_adjust(bottom=0.11, top=0.9, left=0.03, right=0.97)
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render the README model overview.")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    render_overview(args.output / "preview.png")
