#!/usr/bin/env python3
"""
radar.py — Draw radar charts for GitHub profile READMEs.

Two modes:
  1. --data skills.json   → self-rated radar from a JSON file
  2. --github USERNAME    → language radar from real GitHub API data

Usage:
    python radar.py --data assets/skills.json -o assets/radar
    python radar.py --github krushnasaruk -o assets/radar-langs --limit 7 --values --curve 0.4
"""

import argparse
import json
import math
import os
import sys
import urllib.request
import urllib.error


def fetch_github_languages(username, limit=7, exclude=None, curve=1.0):
    """Fetch language byte counts from GitHub API and return radar axes."""
    if exclude is None:
        exclude = {"html", "css", "shell"}
    else:
        exclude = {e.strip().lower() for e in exclude}

    # Always exclude these by default
    exclude.update({"html", "css", "shell"})

    url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner"
    headers = {"Accept": "application/vnd.github.v3+json"}

    # Use token if available
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            repos = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"Warning: Could not fetch repos for {username}: {e}")
        return []

    # Gather language bytes from each repo
    lang_totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        lang_url = repo.get("languages_url")
        if not lang_url:
            continue
        try:
            req = urllib.request.Request(lang_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                langs = json.loads(resp.read().decode())
            for lang, bytes_count in langs.items():
                if lang.lower() in exclude:
                    continue
                lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count
        except urllib.error.URLError:
            continue

    if not lang_totals:
        print("Warning: No language data found.")
        return []

    # Sort by bytes descending, take top N
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:limit]

    # Normalize and apply curve
    max_bytes = sorted_langs[0][1] if sorted_langs else 1
    axes = []
    for lang, bytes_count in sorted_langs:
        raw = bytes_count / max_bytes
        curved = raw ** curve if curve != 1.0 else raw
        value = round(curved * 100)
        axes.append({
            "label": lang,
            "value": value,
            "raw_bytes": bytes_count,
        })

    return axes


def draw_radar_svg(axes, title="", theme="dark", accent="#39D353",
                   show_values=False, size=400):
    """Generate a radar chart SVG."""
    n = len(axes)
    if n < 3:
        print("Warning: Need at least 3 axes for a radar chart.")
        return ""

    cx, cy = size / 2, size / 2
    radius = size * 0.35
    label_radius = radius + 30

    # Theme colors
    if theme == "dark":
        bg = "none"
        grid_color = "#333333"
        text_color = "#e6e6e6"
        fill_color = accent
        fill_opacity = "0.25"
        stroke_color = accent
        label_color = "#cccccc"
    else:
        bg = "none"
        grid_color = "#d0d0d0"
        text_color = "#333333"
        fill_color = accent
        fill_opacity = "0.20"
        stroke_color = accent
        label_color = "#555555"

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">')
    lines.append('<defs>')
    lines.append(f'''<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&amp;display=swap');
  text {{ font-family: "JetBrains Mono", "Fira Code", monospace; }}
</style>''')
    lines.append('</defs>')

    # Title
    if title:
        lines.append(f'<text x="{cx}" y="22" text-anchor="middle" fill="{text_color}" font-size="13" font-weight="600">{title}</text>')

    # Grid rings (5 levels)
    for level in range(1, 6):
        r = radius * level / 5
        points = []
        for i in range(n):
            angle = (2 * math.pi * i / n) - math.pi / 2
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            points.append(f"{px:.1f},{py:.1f}")
        lines.append(f'<polygon points="{" ".join(points)}" fill="none" stroke="{grid_color}" stroke-width="0.5"/>')

    # Axis lines
    for i in range(n):
        angle = (2 * math.pi * i / n) - math.pi / 2
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        lines.append(f'<line x1="{cx}" y1="{cy}" x2="{px:.1f}" y2="{py:.1f}" stroke="{grid_color}" stroke-width="0.5"/>')

    # Data polygon
    data_points = []
    for i, axis in enumerate(axes):
        value = axis["value"] / 100
        angle = (2 * math.pi * i / n) - math.pi / 2
        px = cx + radius * value * math.cos(angle)
        py = cy + radius * value * math.sin(angle)
        data_points.append((px, py))

    poly_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in data_points)

    # Animated fill
    lines.append(f'<polygon points="{poly_str}" fill="{fill_color}" fill-opacity="{fill_opacity}" stroke="{stroke_color}" stroke-width="2">')
    lines.append('  <animate attributeName="fill-opacity" values="0;' + fill_opacity + '" dur="0.8s" fill="freeze"/>')
    lines.append('</polygon>')

    # Data points (dots)
    for i, (px, py) in enumerate(data_points):
        lines.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{accent}" opacity="0.9">')
        lines.append(f'  <animate attributeName="r" values="0;3.5" dur="0.5s" begin="{i * 0.05:.2f}s" fill="freeze"/>')
        lines.append('</circle>')

    # Labels
    for i, axis in enumerate(axes):
        angle = (2 * math.pi * i / n) - math.pi / 2
        lx = cx + label_radius * math.cos(angle)
        ly = cy + label_radius * math.sin(angle)

        # Anchor based on position
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"

        dy = 0
        if math.sin(angle) > 0.3:
            dy = 12
        elif math.sin(angle) < -0.3:
            dy = -5

        label_text = axis["label"]
        if show_values:
            raw_bytes = axis.get("raw_bytes")
            if raw_bytes is not None:
                if raw_bytes >= 1_000_000:
                    label_text += f" ({raw_bytes / 1_000_000:.1f}M)"
                elif raw_bytes >= 1_000:
                    label_text += f" ({raw_bytes / 1_000:.0f}K)"
                else:
                    label_text += f" ({raw_bytes})"
            else:
                label_text += f" ({axis['value']})"

        lines.append(f'<text x="{lx:.1f}" y="{ly + dy:.1f}" text-anchor="{anchor}" fill="{label_color}" font-size="10">{label_text}</text>')

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
    parser.add_argument("--curve", type=float, default=1.0, help="Curve exponent for language radar (0.3-1.0)")
    parser.add_argument("--exclude", default="", help="Comma-separated languages to exclude")
    parser.add_argument("--accent", default="#39D353", help="Accent color")
    parser.add_argument("--size", type=int, default=400, help="SVG size in pixels")

    args = parser.parse_args()

    # Get axes data
    if args.data:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
        axes = data.get("axes", [])
        title = data.get("title", "")
        print(f"Loaded {len(axes)} axes from {args.data}")
    else:
        exclude_set = set()
        if args.exclude:
            exclude_set = {e.strip().lower() for e in args.exclude.split(",")}
        print(f"Fetching language data for {args.github}...")
        axes = fetch_github_languages(args.github, args.limit, exclude_set, args.curve)
        title = "Language Radar"
        if not axes:
            print("No data found. Make sure the username is correct and has public repos.")
            sys.exit(1)
        print(f"Found {len(axes)} languages")

    if len(axes) < 3:
        print("Error: Need at least 3 axes for a radar chart.")
        sys.exit(1)

    # Ensure output directory
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Generate dark and light variants
    for theme in ["dark", "light"]:
        svg = draw_radar_svg(axes, title=title, theme=theme, accent=args.accent,
                             show_values=args.values, size=args.size)
        out_path = f"{args.output}-{theme}.svg"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  Wrote {out_path}")

    print("Done!")


if __name__ == "__main__":
    main()
