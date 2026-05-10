"""Regenerate PWA mask icons from ``static/images/logos/atlas.svg``.

Requires (dev-only, not a runtime dependency of the Suite):

    pip install pymupdf pillow

Run from repo root::

    python scripts/build_pwa_icons.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "static" / "images" / "logos" / "atlas.svg"
OUT_DIR = ROOT / "static" / "icons"


def main() -> None:
    import fitz
    from PIL import Image, ImageOps

    svg = SVG.read_bytes()
    doc = fitz.open(stream=svg, filetype="svg")
    page = doc[0]
    mat = fitz.Matrix(4, 4)
    pix = page.get_pixmap(matrix=mat, alpha=True)
    img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
    doc.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bg = (3, 7, 17, 255)
    for size in (192, 512):
        thumb = ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), bg)
        ox = (size - thumb.width) // 2
        oy = (size - thumb.height) // 2
        canvas.paste(thumb, (ox, oy), thumb)
        out = OUT_DIR / f"icon-{size}.png"
        canvas.save(out, optimize=True)
        print("wrote", out.relative_to(ROOT), canvas.size)


if __name__ == "__main__":
    main()
