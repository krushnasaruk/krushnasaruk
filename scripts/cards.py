#!/usr/bin/env python3
"""
cards.py — Generate high-aesthetic stat cards and project cards as SVGs with animations.

Usage:
    python scripts/cards.py --user krushnasaruk --out assets --projects assets/projects.json
"""

import argparse
import html
import json
import math
import os
import sys
import urllib.request
import urllib.error

# GitHub language colors
LANG_COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "C#": "#178600",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "Lua": "#000080",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Jupyter Notebook": "#DA5B0B",
}

DEFAULT_FALLBACK_STATS = {
    "total_repos": 36,
    "total_stars": 5,
    "total_forks": 0,
    "top_language": "JavaScript",
    "contributions": 140,
    "streak": 12,
}

FALLBACK_PROJECT_METRICS = {
    "AntariX": {"stars": 2, "forks": 0, "language": "JavaScript"},
    "Cancer": {"stars": 1, "forks": 0, "language": "Python"},
    "sutraverse2.0": {"stars": 0, "forks": 0, "language": "JavaScript"},
    "NormEdu": {"stars": 0, "forks": 0, "language": "TypeScript"},
}


def fetch_user_stats(username):
    """Fetch user stats from GitHub API with graceful fallback on rate limit."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "GitHub-Profile-Gen"}
    if token:
        headers["Authorization"] = f"token {token}"

    stats = dict(DEFAULT_FALLBACK_STATS)

    try:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            repos = json.loads(resp.read().decode())

        stats["total_repos"] = len(repos)
        stars = 0
        forks = 0
        lang_counts = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            stars += repo.get("stargazers_count", 0)
            forks += repo.get("forks_count", 0)
            lang = repo.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        stats["total_stars"] = stars
        stats["total_forks"] = forks
        if lang_counts:
            stats["top_language"] = max(lang_counts, key=lang_counts.get)

    except Exception as e:
        print(f"  Note: Using cached/fallback stats ({e})")

    # Fetch real live all-time contributions count from public contributions API
    try:
        c_url = f"https://github-contributions-api.jogruber.de/v4/{username}"
        c_req = urllib.request.Request(c_url, headers={"User-Agent": "GitHub-Profile-Gen"})
        with urllib.request.urlopen(c_req, timeout=8) as c_resp:
            c_data = json.loads(c_resp.read().decode())
            all_contribs = sum(d.get("count", 0) for d in c_data.get("contributions", []))
            if all_contribs > 0:
                stats["contributions"] = all_contribs
    except Exception:
        stats["contributions"] = 1859

    # Try GraphQL for contributions if token present
    if token:
        try:
            query = '''
            query($login: String!) {
              user(login: $login) {
                contributionsCollection {
                  contributionCalendar {
                    totalContributions
                  }
                }
              }
            }
            '''
            payload = json.dumps({"query": query, "variables": {"login": username}}).encode()
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=payload,
                headers={**headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            stats["contributions"] = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        except Exception:
            pass

    return stats


def fetch_repo_info(username, repo_name):
    """Fetch info for a specific repo with fallback."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "GitHub-Profile-Gen"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        url = f"https://api.github.com/repos/{username}/{repo_name}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        metrics = FALLBACK_PROJECT_METRICS.get(repo_name, {"stars": 0, "forks": 0, "language": "TypeScript"})
        return {
            "name": repo_name,
            "stargazers_count": metrics["stars"],
            "forks_count": metrics["forks"],
            "language": metrics["language"],
        }


def draw_stat_card_svg(stats, username, theme="dark", accent="#39D353"):
    """Generate a sleek, compact animated stats card SVG."""
    w, h = 480, 160

    if theme == "dark":
        bg_card = "#0b0f14"
        card_stroke = "#21262d"
        tile_bg = "#111822"
        tile_stroke = "#212d3b"
        text_primary = "#f0f6fc"
        text_secondary = "#8b949e"
        glow_color = accent
    else:
        bg_card = "#ffffff"
        card_stroke = "#d0d7de"
        tile_bg = "#f6f8fa"
        tile_stroke = "#d0d7de"
        text_primary = "#1f2328"
        text_secondary = "#57606a"
        glow_color = "#2da44e"

    safe_username = html.escape(username)
    safe_top_lang = html.escape(str(stats.get("top_language", "JS")))

    contrib_val = stats.get("contributions", 1859)
    contrib_str = f"{contrib_val:,}" if isinstance(contrib_val, int) else str(contrib_val)

    tiles = [
        ("Repositories", str(stats.get("total_repos", 36)), "📦"),
        ("Total Stars", str(stats.get("total_stars", 5)), "⭐"),
        ("Total Forks", str(stats.get("total_forks", 0)), "🍴"),
        ("Contributions", contrib_str, "🔥"),
        ("Current Streak", f"{stats.get('streak', 12)}d", "⚡"),
        ("Top Stack", safe_top_lang, "💻"),
    ]

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">')
    lines.append(f'''<defs>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@500;700&amp;display=swap');
    .title {{ font-family: "JetBrains Mono", monospace; font-size: 13px; font-weight: 700; fill: {text_primary}; }}
    .subtitle {{ font-family: "Inter", sans-serif; font-size: 10px; fill: {text_secondary}; }}
    .val {{ font-family: "JetBrains Mono", monospace; font-size: 15px; font-weight: 700; fill: {accent}; }}
    .lbl {{ font-family: "Inter", sans-serif; font-size: 9.5px; font-weight: 500; fill: {text_secondary}; }}
    .badge {{ font-family: "JetBrains Mono", monospace; font-size: 9px; font-weight: 600; fill: {accent}; }}
    
    @keyframes pulseDot {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}
    .pulse {{ animation: pulseDot 2s ease-in-out infinite; transform-origin: 20px 22px; }}
    
    @keyframes borderGlow {{
      0%, 100% {{ stroke-opacity: 0.4; }}
      50% {{ stroke-opacity: 0.9; }}
    }}
    .glow-border {{ animation: borderGlow 4s ease-in-out infinite; }}
  </style>
  <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="{bg_card}"/>
    <stop offset="100%" stop-color="{tile_bg}"/>
  </linearGradient>
  <linearGradient id="accentLine" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="{accent}" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="{accent}" stop-opacity="0.1"/>
  </linearGradient>
</defs>''')

    # Card background with subtle rounded border
    lines.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="url(#cardGrad)" stroke="{card_stroke}" stroke-width="1"/>')
    lines.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="none" stroke="{glow_color}" stroke-width="1.2" stroke-dasharray="8 380" class="glow-border"/>')

    # Accent top border indicator
    lines.append(f'<rect x="12" y="1" width="80" height="2" rx="1" fill="url(#accentLine)"/>')

    # Header section: Online Pulse + Title
    lines.append(f'<circle cx="20" cy="22" r="4" fill="{accent}" class="pulse"/>')
    lines.append(f'<text x="32" y="26" class="title">~/ {safe_username} <tspan font-weight="400" fill="{text_secondary}">stats</tspan></text>')
    lines.append(f'<rect x="{w-95}" y="12" width="82" height="20" rx="10" fill="{accent}18" stroke="{accent}" stroke-opacity="0.3" stroke-width="0.8"/>')
    lines.append(f'<text x="{w-54}" y="25.5" text-anchor="middle" class="badge">ACTIVE DEV</text>')

    # 3x2 Grid for compact layout
    cols = 3
    tile_w = (w - 32 - (cols - 1) * 8) // cols
    tile_h = 46
    start_y = 44

    for i, (label, val, icon) in enumerate(tiles):
        c = i % cols
        r = i // cols
        tx = 16 + c * (tile_w + 8)
        ty = start_y + r * (tile_h + 8)

        lines.append(f'<rect x="{tx}" y="{ty}" width="{tile_w}" height="{tile_h}" rx="6" fill="{tile_bg}" stroke="{tile_stroke}" stroke-width="0.8"/>')
        lines.append(f'<text x="{tx + 10}" y="{ty + 20}" font-size="11">{icon}</text>')
        lines.append(f'<text x="{tx + 26}" y="{ty + 20}" class="val">{val}</text>')
        lines.append(f'<text x="{tx + 10}" y="{ty + 36}" class="lbl">{label}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def draw_project_card_svg(repo_data, description, theme="dark", accent="#39D353"):
    """Generate a sleek, modern, animated project card SVG."""
    w, h = 420, 130

    if theme == "dark":
        bg_card = "#0c1017"
        card_stroke = "#212832"
        badge_bg = "#161e2a"
        text_primary = "#f0f6fc"
        text_secondary = "#8b949e"
        glow_color = accent
    else:
        bg_card = "#ffffff"
        card_stroke = "#d0d7de"
        badge_bg = "#f6f8fa"
        text_primary = "#1f2328"
        text_secondary = "#57606a"
        glow_color = "#2da44e"

    raw_name = repo_data.get("name", "project")
    name = html.escape(raw_name)
    stars = repo_data.get("stargazers_count", 0)
    forks = repo_data.get("forks_count", 0)
    language = repo_data.get("language") or "Code"
    lang_color = LANG_COLORS.get(language, "#39D353")
    safe_language = html.escape(language)

    raw_desc = description or repo_data.get("description", "") or "No description provided."
    if len(raw_desc) > 95:
        raw_desc = raw_desc[:92] + "..."

    # Word wrap into 2 lines
    words = raw_desc.split()
    line1_words = []
    line2_words = []
    curr_len = 0
    for word in words:
        if curr_len + len(word) + 1 <= 52 and not line2_words:
            line1_words.append(word)
            curr_len += len(word) + 1
        else:
            line2_words.append(word)

    line1 = html.escape(" ".join(line1_words))
    line2 = html.escape(" ".join(line2_words[:9]))
    if len(line2_words) > 9:
        line2 += "..."

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">')
    lines.append(f'''<defs>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@500;700&amp;display=swap');
    .proj-name {{ font-family: "JetBrains Mono", monospace; font-size: 13.5px; font-weight: 700; fill: {text_primary}; }}
    .proj-desc {{ font-family: "Inter", sans-serif; font-size: 10.5px; line-height: 1.4; fill: {text_secondary}; }}
    .meta-text {{ font-family: "Inter", sans-serif; font-size: 10px; font-weight: 500; fill: {text_secondary}; }}
    
    @keyframes barShine {{
      0% {{ transform: translateX(-100%); }}
      100% {{ transform: translateX(200%); }}
    }}
    .shine {{ animation: barShine 3.5s ease-in-out infinite; }}
  </style>
  <linearGradient id="pGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="{bg_card}"/>
    <stop offset="100%" stop-color="{badge_bg}"/>
  </linearGradient>
  <clipPath id="cardClip">
    <rect x="0" y="0" width="{w}" height="{h}" rx="8"/>
  </clipPath>
</defs>''')

    # Card background
    lines.append(f'<g clip-path="url(#cardClip)">')
    lines.append(f'  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" fill="url(#pGrad)" stroke="{card_stroke}" stroke-width="1"/>')
    # Left accent bar
    lines.append(f'  <rect x="0" y="0" width="3.5" height="{h}" fill="{accent}"/>')
    lines.append(f'</g>')

    # Top row: Folder icon + Repo name + Star count badge
    lines.append(f'<g transform="translate(18, 26)">')
    # Clean SVG folder icon
    lines.append(f'  <path d="M2 3.5A1.5 1.5 0 0 1 3.5 2h3.086a1.5 1.5 0 0 1 1.06.44l1.415 1.414A.5.5 0 0 0 9.414 4H14.5A1.5 1.5 0 0 1 16 5.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 2 12.5v-9z" fill="{accent}" opacity="0.9"/>')
    lines.append(f'  <text x="22" y="10" class="proj-name">{name}</text>')
    lines.append(f'</g>')

    # Top-right quick badge
    lines.append(f'<rect x="{w-78}" y="15" width="62" height="18" rx="9" fill="{badge_bg}" stroke="{card_stroke}" stroke-width="0.8"/>')
    lines.append(f'<text x="{w-47}" y="27" text-anchor="middle" font-family="JetBrains Mono" font-size="9px" font-weight="600" fill="{accent}">PROJECT</text>')

    # Description (2 clean lines)
    lines.append(f'<text x="18" y="58" class="proj-desc">{line1}</text>')
    if line2:
        lines.append(f'<text x="18" y="74" class="proj-desc">{line2}</text>')

    # Footer metadata pills (Language, Stars, Forks)
    by = h - 22
    lines.append(f'<g transform="translate(18, {by})">')
    # Language dot + name
    lines.append(f'  <circle cx="5" cy="0" r="4.5" fill="{lang_color}"/>')
    lines.append(f'  <text x="14" y="3.5" class="meta-text">{safe_language}</text>')

    # Offset for stars
    star_x = 22 + len(language) * 6.5 + 16
    lines.append(f'  <path d="M{star_x} -4.5 l1.2 2.6 2.8.4-2 2 .5 2.8-2.5-1.3-2.5 1.3.5-2.8-2-2 2.8-.4z" fill="#e3b341"/>')
    lines.append(f'  <text x="{star_x + 9}" y="3.5" class="meta-text">{stars}</text>')

    # Offset for forks
    fork_x = star_x + 36 + len(str(stars)) * 6.5
    lines.append(f'  <text x="{fork_x}" y="3.5" font-size="10">🍴</text>')
    lines.append(f'  <text x="{fork_x + 14}" y="3.5" class="meta-text">{forks}</text>')
    lines.append(f'</g>')

    lines.append('</svg>')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate stat and project cards")
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--out", default="assets", help="Output directory")
    parser.add_argument("--accent", default="#39D353", help="Accent color")
    parser.add_argument("--projects", default=None, help="Path to projects.json")

    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    print(f"Generating sleek stat cards for {args.user}...")
    stats = fetch_user_stats(args.user)
    print(f"  Repos: {stats['total_repos']}, Stars: {stats['total_stars']}, "
          f"Forks: {stats['total_forks']}, Top: {stats['top_language']}")

    for theme in ["dark", "light"]:
        svg = draw_stat_card_svg(stats, args.user, theme, args.accent)
        path = os.path.join(args.out, f"stats-{theme}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  Wrote {path}")

    projects_path = args.projects
    if not projects_path:
        for candidate in ["assets/projects.json", "../assets/projects.json", "projects.json"]:
            if os.path.exists(candidate):
                projects_path = candidate
                break

    if projects_path and os.path.exists(projects_path):
        with open(projects_path, "r", encoding="utf-8") as f:
            projects_data = json.load(f)

        projects = projects_data.get("projects", [])
        print(f"\nGenerating {len(projects)} featured project cards...")

        for project in projects:
            repo_name = project["repo"]
            description = project.get("description", "")
            repo_info = fetch_repo_info(args.user, repo_name)

            for theme in ["dark", "light"]:
                svg = draw_project_card_svg(repo_info, description, theme, args.accent)
                path = os.path.join(args.out, f"card-{repo_name}-{theme}.svg")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
                print(f"  Wrote {path}")
    else:
        print("\nNo projects.json found — skipping project cards.")

    print("\nDone generating cards!")


if __name__ == "__main__":
    main()
