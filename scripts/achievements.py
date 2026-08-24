#!/usr/bin/env python3
"""
achievements.py — Generate high-aesthetic developer achievement badges showcase SVG.

Usage:
    python scripts/achievements.py --out assets
"""

import argparse
import html
import os
import sys

ACHIEVEMENTS = [
    {
        "id": "antarix",
        "icon": "🪐",
        "title": "Deep Space Architect",
        "desc": "AntariX Earth–Mars Digital Twin & ML Comms",
        "tier": "DIAMOND",
        "tier_color": "#00f0ff",
    },
    {
        "id": "cancer",
        "icon": "🤖",
        "title": "Robotics Sim-to-Real",
        "desc": "12M+ RL Training Steps in MuJoCo & Three.js",
        "tier": "MASTER",
        "tier_color": "#a855f7",
    },
    {
        "id": "edtech",
        "icon": "🎓",
        "title": "EdTech Innovator",
        "desc": "NormEdu SaaS & sutraverse2.0 Biometric ERP",
        "tier": "GOLD",
        "tier_color": "#eab308",
    },
    {
        "id": "polyglot",
        "icon": "⚡",
        "title": "Full-Stack Polyglot",
        "desc": "36+ Repos (TS, JS, Python, React, Next.js)",
        "tier": "ELITE",
        "tier_color": "#39d353",
    },
    {
        "id": "cosmos",
        "icon": "🌌",
        "title": "Celestial Architect",
        "desc": "Constellation & Mythological Systems",
        "tier": "RARE",
        "tier_color": "#38bdf8",
    },
    {
        "id": "nightowl",
        "icon": "🌙",
        "title": "Night Owl Builder",
        "desc": "Codes at night, debugs at dawn",
        "tier": "LEGENDARY",
        "tier_color": "#f97316",
    },
]


def draw_achievements_svg(theme="dark", accent="#39D353", width=680, height=220):
    """Render a compact, high-polish 3x2 achievement trophy showcase."""
    if theme == "dark":
        bg_card = "#0b0f14"
        card_stroke = "#21262d"
        tile_bg = "#111822"
        tile_stroke = "#1e293b"
        text_primary = "#f0f6fc"
        text_secondary = "#8b949e"
    else:
        bg_card = "#ffffff"
        card_stroke = "#d0d7de"
        tile_bg = "#f6f8fa"
        tile_stroke = "#d0d7de"
        text_primary = "#1f2328"
        text_secondary = "#57606a"

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">')
    lines.append(f'''<defs>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@500;700&amp;display=swap');
    .ach-title {{ font-family: "JetBrains Mono", monospace; font-size: 12.5px; font-weight: 700; fill: {text_primary}; }}
    .ach-header {{ font-family: "JetBrains Mono", monospace; font-size: 11px; font-weight: 700; fill: {text_primary}; }}
    .ach-desc {{ font-family: "Inter", sans-serif; font-size: 9px; fill: {text_secondary}; }}
    .ach-tier {{ font-family: "JetBrains Mono", monospace; font-size: 8px; font-weight: 700; }}
    
    @keyframes trophyGlow {{
      0%, 100% {{ opacity: 0.7; }}
      50% {{ opacity: 1; }}
    }}
    .trophy-badge {{ animation: trophyGlow 3s ease-in-out infinite; }}
  </style>
  <linearGradient id="achCardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="{bg_card}"/>
    <stop offset="100%" stop-color="{theme == 'dark' and '#0e141d' or '#f8fafc'}"/>
  </linearGradient>
</defs>''')

    # Card background
    lines.append(f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="8" fill="url(#achCardGrad)" stroke="{card_stroke}" stroke-width="1"/>')

    # Header
    lines.append(f'<text x="20" y="24" class="ach-title">~/ Developer Trophies &amp; Milestones</text>')
    lines.append(f'<rect x="{width-92}" y="12" width="76" height="18" rx="9" fill="{accent}18" stroke="{accent}" stroke-opacity="0.3" stroke-width="0.8"/>')
    lines.append(f'<text x="{width-54}" y="24" text-anchor="middle" font-family="JetBrains Mono" font-size="8.5px" font-weight="700" fill="{accent}">6 UNLOCKED</text>')

    # 3x2 Grid layout
    cols = 3
    tile_w = (width - 40 - (cols - 1) * 10) // cols
    tile_h = 70
    start_y = 44

    for i, item in enumerate(ACHIEVEMENTS):
        c = i % cols
        r = i // cols
        tx = 20 + c * (tile_w + 10)
        ty = start_y + r * (tile_h + 10)

        tier_col = item["tier_color"]
        safe_title = html.escape(item["title"])
        safe_desc = html.escape(item["desc"])

        lines.append(f'<g transform="translate({tx}, {ty})">')
        # Tile box
        lines.append(f'  <rect x="0" y="0" width="{tile_w}" height="{tile_h}" rx="6" fill="{tile_bg}" stroke="{tile_stroke}" stroke-width="0.8"/>')
        # Tier bar on left
        lines.append(f'  <rect x="0" y="6" width="3" height="{tile_h-12}" rx="1.5" fill="{tier_col}"/>')

        # Icon
        lines.append(f'  <text x="12" y="26" font-size="18">{item["icon"]}</text>')

        # Title & Tier badge
        lines.append(f'  <text x="36" y="22" class="ach-header">{safe_title}</text>')
        lines.append(f'  <rect x="{tile_w-56}" y="11" width="48" height="14" rx="7" fill="{tier_col}18" stroke="{tier_col}" stroke-width="0.6"/>')
        lines.append(f'  <text x="{tile_w-32}" y="21.5" text-anchor="middle" class="ach-tier" fill="{tier_col}">{item["tier"]}</text>')

        # Description
        lines.append(f'  <text x="12" y="46" class="ach-desc">{safe_desc}</text>')
        lines.append(f'</g>')

    lines.append('</svg>')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate achievement badges SVG")
    parser.add_argument("--out", default="assets", help="Output directory")
    parser.add_argument("--accent", default="#39D353", help="Accent color")

    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    print("Generating Developer Achievement Badges...")
    for theme in ["dark", "light"]:
        svg = draw_achievements_svg(theme=theme, accent=args.accent, width=680, height=210)
        path = os.path.join(args.out, f"achievements-{theme}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  Wrote {path}")

    print("Done generating achievements showcase!")


if __name__ == "__main__":
    main()
