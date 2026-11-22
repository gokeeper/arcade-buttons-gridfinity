"""Preview actual CAD geometry with a depth-buffered render and a true section."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

import cadquery as cq
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "arcade-buttons-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

from button_bin import Parameters, button_envelope, foot


def rasterize(shape: cq.Shape, size: int = 900) -> np.ndarray:
    """Orthographic depth buffer avoids painter-sorting artifacts in CAD renders."""
    vertices, triangles = shape.tessellate(0.05, 0.12)
    xyz = np.array([v.toTuple() for v in vertices])
    az, el = np.radians([-55, 48])
    eye = np.array([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.sin(el)])
    right = np.array([-np.sin(az), np.cos(az), 0])
    up = np.cross(eye, right)
    xyz -= [0, 0, 24]
    view = xyz @ np.array([right, up, eye]).T
    scale = size / 72
    screen = np.column_stack((size / 2 + scale * view[:, 0],
                              size / 2 - scale * view[:, 1], view[:, 2]))
    rgb = np.full((size, size, 3), [244, 246, 248], dtype=np.uint8)
    depth = np.full((size, size), -np.inf)
    light = np.array([-0.3, -0.5, 0.81])
    light /= np.linalg.norm(light)
    base = np.array([69, 139, 163])
    for triangle in triangles:
        a, b, c = screen[list(triangle)]
        x0 = max(0, int(np.floor(min(a[0], b[0], c[0]))))
        x1 = min(size - 1, int(np.ceil(max(a[0], b[0], c[0]))))
        y0 = max(0, int(np.floor(min(a[1], b[1], c[1]))))
        y1 = min(size - 1, int(np.ceil(max(a[1], b[1], c[1]))))
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


def draw_section(ax, shape: cq.Shape, color: str) -> None:
    # YZ slice avoids the X-facing clip reliefs and exposes the flange support.
    slab = cq.Solid.makeBox(0.02, 60, 60, cq.Vector(-0.01, -30, 0))
    vertices, triangles = shape.intersect(slab).tessellate(0.04, 0.1)
    polygons = [[(vertices[i].y, vertices[i].z) for i in triangle] for triangle in triangles]
    ax.add_collection(PolyCollection(polygons, facecolors=color, edgecolors="none"))


def render_preview(model: cq.Shape, p: Parameters, path: Path) -> None:
    fig, (ax, section) = plt.subplots(1, 2, figsize=(14, 8), facecolor="#f4f6f8")
    ax.imshow(rasterize(model))
    ax.axis("off")
    ax.set_title(f"OBSF-30 · 1×1×{p.height_u}U\nActual CAD geometry", fontsize=13, pad=8)
    section.set_facecolor("#f4f6f8")
    draw_section(section, model, "#458ba3")
    draw_section(section, button_envelope(p), "#e9aa50")
    draw_section(section, foot().translate((0, 0, p.nominal_z)), "#828b96")
    section.axhline(p.nominal_z, color="#828b96", linestyle="--", linewidth=0.8)
    section.annotate(f"{p.top_clearance:g} mm top clearance",
                     xy=(0, p.top_z + p.top_clearance / 2),
                     xytext=(-26, p.top_z - 2), fontsize=10,
                     arrowprops={"arrowstyle": "->", "color": "#354456"})
    section.annotate(f"{p.tip_z - p.floor_z:.1f} mm beneath terminals",
                     xy=(0, (p.tip_z + p.floor_z) / 2), xytext=(-26, 2), fontsize=10,
                     arrowprops={"arrowstyle": "->", "color": "#354456"})
    section.annotate("Flange seat", xy=(16.3, p.seat_z), xytext=(18, p.seat_z - 8),
                     fontsize=10, arrowprops={"arrowstyle": "->", "color": "#354456"})
    section.set(xlim=(-28, 36), ylim=(-2, p.total_z + 7), xlabel="Y (mm)", ylabel="Z (mm)")
    section.set_aspect("equal")
    section.spines[["top", "right"]].set_visible(False)
    section.set_title("Centre section: bin, button envelope, upper foot\nClips omitted from envelope", fontsize=12)
    fig.text(0.5, 0.06,
             f"41.5 × 41.5 × {p.total_z:g} mm overall  |  "
             f"{p.nominal_z:g} mm stacking pitch  |  PETG · 0.4 mm nozzle · 0.2 mm layers",
             ha="center", fontsize=11, color="#354456")
    fig.text(0.5, 0.025, "Prototype: print fit coupons and confirm the flange datum before loaded stacking.",
             ha="center", fontsize=10, color="#59687a")
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.15, top=0.87, wspace=0.12)
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
