#!/usr/bin/env python3
"""
dotify.py — Turn a photo into a dot-matrix SVG portrait.

Usage:
    python dotify.py photo.png -o assets/portrait --cols 100 --equalize --detail 0.5 --color
    python dotify.py photo.png -o assets/portrait --cols 88 --equalize --detail 0.5 --animate
    python dotify.py photo.png -o assets/portrait --mode binary --cols 62 --equalize --detail 0.5

Outputs:
    --color  → single portrait.svg (works on both themes)
    default  → portrait-dark.svg + portrait-light.svg (green monochrome)
"""

import argparse
import math
import sys
import os

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    print("Error: Pillow is required. Install with: pip install pillow")
    sys.exit(1)


def equalize_image(img):
    """Histogram equalization to stretch tones and recover shadow detail."""
    if img.mode == "RGBA":
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        rgb = ImageOps.equalize(rgb)
        r2, g2, b2 = rgb.split()
        return Image.merge("RGBA", (r2, g2, b2, a))
    return ImageOps.equalize(img.convert("RGB"))


def add_detail(img, amount=0.5):
    """Sharpen local structure (cheekbones, nose bridge, jaw edge)."""
    detail = img.filter(ImageFilter.DETAIL)
    return Image.blend(img, detail, amount)


def crop_square(img, focus=(0.5, 0.5)):
    """Crop to 1:1 around a focus point."""
    w, h = img.size
    side = min(w, h)
    cx = int(w * focus[0])
    cy = int(h * focus[1])
    left = max(0, cx - side // 2)
    top = max(0, cy - side // 2)
    left = min(left, w - side)
    top = min(top, h - side)
    return img.crop((left, top, left + side, top + side))


def make_circle_mask(size):
    """Create a circular mask with feathered edge."""
    from PIL import ImageDraw
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    margin = int(size * 0.02)
    draw.ellipse([margin, margin, size - margin, size - margin], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=size * 0.015))
    return mask


def sample_grid(img, cols, circle=False):
    """Sample the image into a grid of cells with brightness and optional color."""
    w, h = img.size
    cell_w = w / cols
    cell_h = cell_w  # square cells
    rows = int(h / cell_h)

    has_alpha = img.mode == "RGBA"
    rgb_img = img.convert("RGB")

    if circle:
        cmask = make_circle_mask(max(cols, rows))
        cmask = cmask.resize((cols, rows), Image.LANCZOS)

    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            x1 = int(c * cell_w)
            y1 = int(r * cell_h)
            x2 = int(min((c + 1) * cell_w, w))
            y2 = int(min((r + 1) * cell_h, h))

            if x2 <= x1 or y2 <= y1:
                row.append(None)
                continue

            # Check alpha
            if has_alpha:
                region_a = img.crop((x1, y1, x2, y2)).split()[3]
                avg_alpha = sum(region_a.getdata()) / max(len(list(region_a.getdata())), 1)
                if avg_alpha < 30:
                    row.append(None)
                    continue

            # Check circle mask
            if circle:
                if c < cmask.size[0] and r < cmask.size[1]:
                    if cmask.getpixel((c, r)) < 30:
                        row.append(None)
                        continue

            region = rgb_img.crop((x1, y1, x2, y2))
            pixels = list(region.getdata())
            if not pixels:
                row.append(None)
                continue

            avg_r = sum(p[0] for p in pixels) // len(pixels)
            avg_g = sum(p[1] for p in pixels) // len(pixels)
            avg_b = sum(p[2] for p in pixels) // len(pixels)
            brightness = (avg_r * 299 + avg_g * 587 + avg_b * 114) / 1000 / 255

            row.append({
                "brightness": brightness,
                "color": f"rgb({avg_r},{avg_g},{avg_b})",
                "hex": f"#{avg_r:02x}{avg_g:02x}{avg_b:02x}",
                "r": r,
                "c": c,
            })
        grid.append(row)
    return grid, cols, rows


def rgb_to_hex(r, g, b):
    """Convert rgb to short hex."""
    return f"#{r:02x}{g:02x}{b:02x}"


def render_dots_svg(grid, cols, rows, color_mode=False, accent="#39D353",
                    theme="dark", animate=False, reveal=True,
                    reveal_time=1.8, reveal_fade=0.35, reveal_dir="down",
                    invert=False):
    """Render the grid as an ultra-optimized SVG with smooth CSS animations."""
    cell_size = 10
    svg_w = cols * cell_size
    svg_h = rows * cell_size

    default_fill = accent if not color_mode else None
    if theme == "light" and not color_mode:
        default_fill = "#1a1a2e"

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">')
    lines.append("<defs>")
    lines.append("<style>")
    lines.append("""
  @keyframes matrixReveal {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes avatarGlow {
    0%, 100% { filter: drop-shadow(0 0 1px rgba(57, 211, 83, 0.2)); }
    50% { filter: drop-shadow(0 0 6px rgba(57, 211, 83, 0.45)); }
  }
  .dot-grid { animation: avatarGlow 4s ease-in-out infinite; }
  .row { animation: matrixReveal 0.4s ease-out both; }
""")

    # Generate row animation delay classes in style tag
    if reveal:
        total_rows = rows
        for r in range(rows):
            delay = (r / total_rows) * reveal_time if reveal_dir == "down" else ((total_rows - r) / total_rows) * reveal_time
            lines.append(f"  .r{r} {{ animation-delay: {delay:.2f}s; }}")

    lines.append("</style>")
    lines.append("</defs>")

    lines.append('<g class="dot-grid">')

    for r, row in enumerate(grid):
        row_circles = []
        for cell in row:
            if cell is None:
                continue

            b = cell["brightness"]
            if invert:
                b = 1.0 - b

            if color_mode:
                radius = max(1.1, math.sqrt(b) * (cell_size * 0.45))
            elif theme == "dark":
                radius = max(0.5, b * (cell_size * 0.48))
            else:
                radius = max(0.5, (1.0 - b) * (cell_size * 0.48))

            if radius < 0.4:
                continue

            cx = cell["c"] * cell_size + cell_size / 2
            cy = cell["r"] * cell_size + cell_size / 2

            # Use hex color
            fill = cell.get("hex") or (cell["color"] if color_mode else default_fill)

            row_circles.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{radius:.1f}" fill="{fill}"/>')

        if row_circles:
            cls_attr = f' class="row r{r}"' if reveal else ""
            lines.append(f'<g{cls_attr}>' + "".join(row_circles) + '</g>')

    lines.append('</g>')
    lines.append("</svg>")
    return "\n".join(lines)


def render_binary_svg(grid, cols, rows, accent="#39D353", theme="dark", invert=False):
    """Render as 0s and 1s."""
    cell_size = 10
    svg_w = cols * cell_size
    svg_h = rows * cell_size
    font_size = cell_size * 0.8

    fill = accent if theme == "dark" else "#1a1a2e"

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">')
    lines.append(f'<style>text {{ font-family: "JetBrains Mono", "Fira Code", monospace; font-size: {font_size}px; }}</style>')

    for row in grid:
        for cell in row:
            if cell is None:
                continue
            b = cell["brightness"]
            if invert:
                b = 1.0 - b
            char = "1" if b < 0.5 else "0"
            opacity = max(0.15, 1.0 - b if theme == "dark" else b)
            x = cell["c"] * cell_size + cell_size * 0.2
            y = cell["r"] * cell_size + cell_size * 0.8
            lines.append(
                f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" opacity="{opacity:.2f}">{char}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


def render_ascii(grid, cols, rows, invert=False):
    """Render as ASCII text."""
    chars = " .:-=+*#%@"
    lines = []
    for row in grid:
        line = ""
        for cell in row:
            if cell is None:
                line += " "
                continue
            b = cell["brightness"]
            if invert:
                b = 1.0 - b
            idx = int(b * (len(chars) - 1))
            line += chars[idx]
        lines.append(line)
    return "\n".join(lines)


def render_braille(grid, cols, rows, invert=False):
    """Render as braille characters."""
    # Braille patterns (2x4 dot grid per character)
    lines_out = []
    for r in range(0, rows, 4):
        line = ""
        for c in range(0, cols, 2):
            val = 0x2800
            offsets = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04),
                       (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20),
                       (0, 3, 0x40), (1, 3, 0x80)]
            for dc, dr, bit in offsets:
                ri = r + dr
                ci = c + dc
                if ri < rows and ci < cols:
                    cell = grid[ri][ci] if ri < len(grid) and ci < len(grid[ri]) else None
                    if cell is not None:
                        b = cell["brightness"]
                        if invert:
                            b = 1.0 - b
                        if b < 0.5:
                            val |= bit
            line += chr(val)
        lines_out.append(line)
    return "\n".join(lines_out)


def main():
    parser = argparse.ArgumentParser(description="Turn a photo into a dot-matrix SVG portrait")
    parser.add_argument("image", help="Path to the source image")
    parser.add_argument("-o", "--output", default="portrait", help="Output path prefix (without extension)")
    parser.add_argument("--cols", type=int, default=88, help="Number of dots across (default: 88)")
    parser.add_argument("--equalize", action="store_true", help="Histogram equalization for shadow detail")
    parser.add_argument("--detail", type=float, default=0.0, help="Detail enhancement amount (0-1, default: 0)")
    parser.add_argument("--color", action="store_true", help="Keep original colors (single SVG for both themes)")
    parser.add_argument("--circle", action="store_true", help="Mask to a circle with feathered edge")
    parser.add_argument("--square", action="store_true", help="Crop to 1:1 square")
    parser.add_argument("--focus", default="0.5,0.5", help="Focus point for square crop (x,y in 0-1)")
    parser.add_argument("--invert", action="store_true", help="Invert brightness (dark subject on light bg)")
    parser.add_argument("--animate", action="store_true", help="Add shimmer animation")
    parser.add_argument("--reveal", action="store_true", help="Add row-by-row reveal animation")
    parser.add_argument("--reveal-time", type=float, default=2.5, help="Total reveal sweep time (default: 2.5s)")
    parser.add_argument("--reveal-fade", type=float, default=0.45, help="Per-row fade duration (default: 0.45s)")
    parser.add_argument("--reveal-dir", choices=["down", "up"], default="down", help="Reveal direction")
    parser.add_argument("--mode", choices=["dots", "binary", "ascii", "braille"], default="dots", help="Render mode")
    parser.add_argument("--accent", default="#39D353", help="Accent color for monochrome mode")

    args = parser.parse_args()

    # Load image
    img = Image.open(args.image)
    print(f"Loaded {args.image} ({img.size[0]}x{img.size[1]}, {img.mode})")

    # Square crop
    if args.square:
        fx, fy = [float(x) for x in args.focus.split(",")]
        img = crop_square(img, (fx, fy))
        print(f"  Cropped to square: {img.size[0]}x{img.size[1]}")

    # Equalize
    if args.equalize:
        img = equalize_image(img)
        print("  Applied histogram equalization")

    # Detail
    if args.detail > 0:
        img_rgb = img.convert("RGB") if img.mode == "RGBA" else img
        img_rgb = add_detail(img_rgb, args.detail)
        if img.mode == "RGBA":
            r, g, b = img_rgb.split()
            img = Image.merge("RGBA", (r, g, b, img.split()[3]))
        else:
            img = img_rgb
        print(f"  Applied detail enhancement: {args.detail}")

    # Sample grid
    grid, cols, rows = sample_grid(img, args.cols, args.circle)
    print(f"  Grid: {cols}x{rows} cells")

    # Ensure output directory exists
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Render
    if args.mode == "ascii":
        text = render_ascii(grid, cols, rows, args.invert)
        out_path = args.output + ".txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  Wrote {out_path}")

    elif args.mode == "braille":
        text = render_braille(grid, cols, rows, args.invert)
        out_path = args.output + ".txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  Wrote {out_path}")

    elif args.mode == "binary":
        if args.color:
            svg = render_binary_svg(grid, cols, rows, args.accent, "dark", args.invert)
            out_path = args.output + ".svg"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(svg)
            print(f"  Wrote {out_path}")
        else:
            for theme in ["dark", "light"]:
                svg = render_binary_svg(grid, cols, rows, args.accent, theme, args.invert)
                out_path = f"{args.output}-{theme}.svg"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(svg)
                print(f"  Wrote {out_path}")

    else:  # dots
        if args.color:
            svg = render_dots_svg(grid, cols, rows, color_mode=True, accent=args.accent,
                                  animate=args.animate, reveal=args.reveal,
                                  reveal_time=args.reveal_time, reveal_fade=args.reveal_fade,
                                  reveal_dir=args.reveal_dir, invert=args.invert)
            out_path = args.output + ".svg"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(svg)
            print(f"  Wrote {out_path} (color, single file)")
        else:
            for theme in ["dark", "light"]:
                svg = render_dots_svg(grid, cols, rows, color_mode=False, accent=args.accent,
                                      theme=theme, animate=args.animate, reveal=args.reveal,
                                      reveal_time=args.reveal_time, reveal_fade=args.reveal_fade,
                                      reveal_dir=args.reveal_dir, invert=args.invert)
                out_path = f"{args.output}-{theme}.svg"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(svg)
                print(f"  Wrote {out_path}")

    print("Done!")


if __name__ == "__main__":
    main()
