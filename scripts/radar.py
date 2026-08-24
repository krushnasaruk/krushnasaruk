#!/usr/bin/env python3
"""
radar.py — Draw radar charts for GitHub profile READMEs with clean typography,
proper margins, and no overlapping labels.

Two modes:
  1. --data skills.json   → self-rated radar from a JSON file
  2. --github USERNAME    → language radar from real GitHub API data
"""

import argparse
import html
import json
import math
import os
import sys
import urllib.request
import urllib.error

DEFAULT_FALLBACK_LANGUAGES = [
    {"label": "JavaScript", "value": 90, "raw_bytes": 420000},
    {"label": "Python", "value": 85, "raw_bytes": 1050000},
    {"label": "TypeScript", "value": 75, "raw_bytes": 180000},
    {"label": "Dart", "value": 60, "raw_bytes": 208000},
    {"label": "Jupyter", "value": 45, "raw_bytes": 63000},
    {"label": "CMake", "value": 35, "raw_bytes": 20000},
    {"label": "C", "value": 30, "raw_bytes": 26000},
]


def fetch_github_languages(username, limit=7, exclude=None, curve=0.4):
    """Fetch language byte counts from GitHub API and return radar axes."""
    if exclude is None:
        exclude = {"html", "css", "shell"}
    else:
        exclude = {e.strip().lower() for e in exclude}

    exclude.update({"html", "css", "shell", "makefile", "dockerfile", "batchfile", "procfile"})

    url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner"
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "GitHub-Radar-Gen"}

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            repos = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Warning: Could not fetch repos directly ({e}). Using cached language data.")
        return DEFAULT_FALLBACK_LANGUAGES[:limit]

    lang_totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        lang_url = repo.get("languages_url")
        if not lang_url:
            continue
        try:
            req = urllib.request.Request(lang_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                langs = json.loads(resp.read().decode())
            for lang, bytes_count in langs.items():
                clean_lang = "Jupyter" if "jupyter" in lang.lower() else lang
                if clean_lang.lower() in exclude:
                    continue
                lang_totals[clean_lang] = lang_totals.get(clean_lang, 0) + bytes_count
        except Exception:
            continue

    if not lang_totals:
        return DEFAULT_FALLBACK_LANGUAGES[:limit]

    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    max_bytes = sorted_langs[0][1] if sorted_langs else 1
    axes = []
    for lang, bytes_count in sorted_langs:
        raw = bytes_count / max_bytes
        curved = raw ** curve if curve != 1.0 else raw
        value = max(20, round(curved * 100))
        axes.append({
            "label": lang,
            "value": value,
            "raw_bytes": bytes_count,
        })

    return axes


def draw_radar_svg(axes, title="", theme="dark", accent="#39D353",
                   show_values=False, width=440, height=360):
    """Generate a high-polish radar chart SVG with ample margins."""
    n = len(axes)
    if n < 3:
        return ""

    cx, cy = width / 2, height / 2 + 10
    radius = min(width, height) * 0.32
    label_radius = radius + 24

    if theme == "dark":
        grid_color = "#21262d"
        axis_stroke = "#30363d"
        text_color = "#f0f6fc"
        label_color = "#8b949e"
        fill_color = accent
        fill_opacity = "0.22"
        stroke_color = accent
    else:
        grid_color = "#e1e4e8"
        axis_stroke = "#d0d7de"
        text_color = "#1f2328"
        label_color = "#57606a"
        fill_color = accent
        fill_opacity = "0.18"
        stroke_color = accent

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">')
    lines.append('<defs>')
    lines.append(f'''<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&amp;display=swap');
  .r-title {{ font-family: "JetBrains Mono", monospace; font-size: 13px; font-weight: 700; fill: {text_color}; }}
  .r-label {{ font-family: "JetBrains Mono", monospace; font-size: 10px; font-weight: 500; fill: {label_color}; }}
  .r-val {{ font-family: "JetBrains Mono", monospace; font-size: 9px; font-weight: 700; fill: {accent}; }}
  
  @keyframes radarPulse {{
    0%, 100% {{ fill-opacity: {fill_opacity}; }}
    50% {{ fill-opacity: 0.35; }}
  }}
  .radar-poly {{ animation: radarPulse 3s ease-in-out infinite; }}
</style>''')
    lines.append('</defs>')

    # Title with dedicated clearance
    if title:
        safe_title = html.escape(title)
        lines.append(f'<text x="{cx}" y="24" text-anchor="middle" class="r-title">~/ {safe_title}</text>')

    # Concentric Grid rings (5 levels)
    for level in range(1, 6):
        r = radius * level / 5
        points = []
        for i in range(n):
            angle = (2 * math.pi * i / n) - math.pi / 2
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            points.append(f"{px:.1f},{py:.1f}")
        lines.append(f'<polygon points="{" ".join(points)}" fill="none" stroke="{grid_color}" stroke-width="1"/>')

    # Axis radiating lines
    for i in range(n):
        angle = (2 * math.pi * i / n) - math.pi / 2
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        lines.append(f'<line x1="{cx}" y1="{cy}" x2="{px:.1f}" y2="{py:.1f}" stroke="{axis_stroke}" stroke-width="1" stroke-dasharray="2 3"/>')

    # Data polygon
    data_points = []
    for i, axis in enumerate(axes):
        val_norm = max(15, min(100, axis["value"])) / 100
        angle = (2 * math.pi * i / n) - math.pi / 2
        px = cx + radius * val_norm * math.cos(angle)
        py = cy + radius * val_norm * math.sin(angle)
        data_points.append((px, py))

    poly_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in data_points)

    # Filled polygon with smooth stroke
    lines.append(f'<polygon points="{poly_str}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="2" class="radar-poly"/>')

    # Data point circles
    for px, py in data_points:
        lines.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{accent}" stroke="{theme == "dark" and "#0d1117" or "#ffffff"}" stroke-width="1.5"/>')

    # Smart label positioning
    for i, axis in enumerate(axes):
        angle = (2 * math.pi * i / n) - math.pi / 2
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        lx = cx + label_radius * cos_a
        ly = cy + label_radius * sin_a

        # Accurate text anchor & offset based on radial quadrant
        if cos_a > 0.25:
            anchor = "start"
            dx = 4
        elif cos_a < -0.25:
            anchor = "end"
            dx = -4
        else:
            anchor = "middle"
            dx = 0

        if sin_a > 0.35:
            dy = 12
        elif sin_a < -0.35:
            dy = -4
        else:
            dy = 3.5

        raw_label = axis["label"]
        label_text = html.escape(raw_label)
        val_sub = ""

        if show_values:
            raw_bytes = axis.get("raw_bytes")
            if raw_bytes is not None:
                if raw_bytes >= 1_000_000:
                    val_sub = f"{raw_bytes / 1_000_000:.1f}M"
                elif raw_bytes >= 1_000:
                    val_sub = f"{raw_bytes / 1_000:.0f}K"
                else:
                    val_sub = f"{raw_bytes}B"
            else:
                val_sub = f"{axis['value']}%"

        # Render label and value cleanly
        if val_sub:
            lines.append(f'<text x="{lx + dx:.1f}" y="{ly + dy:.1f}" text-anchor="{anchor}" class="r-label">{label_text} <tspan class="r-val">({val_sub})</tspan></text>')
        else:
            lines.append(f'<text x="{lx + dx:.1f}" y="{ly + dy:.1f}" text-anchor="{anchor}" class="r-label">{label_text}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate radar charts for GitHub profile")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--data", help="Path to skills JSON file")
    group.add_argument("--github", help="GitHub username for language radar")

    parser.add_argument("-o", "--output", default="radar", help="Output path prefix")
    parser.add_argument("--limit", type=int, default=7, help="Max axes for language radar")
    parser.add_argument("--values", action="store_true", help="Show values next to labels")
    parser.add_argument("--curve", type=float, default=0.4, help="Curve exponent for language radar")
    parser.add_argument("--exclude", default="", help="Comma-separated languages to exclude")
    parser.add_argument("--accent", default="#39D353", help="Accent color")

    args = parser.parse_args()

    if args.data:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
        axes = data.get("axes", [])
        title = "Skills Matrix"
    else:
        exclude_set = set()
        if args.exclude:
            exclude_set = {e.strip().lower() for e in args.exclude.split(",")}
        axes = fetch_github_languages(args.github, args.limit, exclude_set, args.curve)
        title = "Languages (Bytes)"

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    for theme in ["dark", "light"]:
        svg = draw_radar_svg(axes, title=title, theme=theme, accent=args.accent,
                             show_values=args.values, width=440, height=340)
        out_path = f"{args.output}-{theme}.svg"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  Wrote {out_path}")

    print("Done generating radar charts!")


if __name__ == "__main__":
    main()
