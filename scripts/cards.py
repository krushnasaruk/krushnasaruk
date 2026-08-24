#!/usr/bin/env python3
"""
cards.py — Generate stat cards and project cards as SVGs.

Usage:
    python cards.py --user krushnasaruk --out assets

Generates:
    assets/stats-dark.svg / stats-light.svg    — contribution stats
    assets/card-REPO-dark.svg / card-REPO-light.svg  — per-project cards
"""

import argparse
import json
import math
import os
import sys
import urllib.request
import urllib.error


# GitHub language colors (subset)
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
    "Zig": "#ec915c",
    "Haskell": "#5e5086",
    "Scala": "#c22d40",
    "R": "#198CE7",
    "Julia": "#a270ba",
    "Elixir": "#6e4a7e",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
}


def fetch_user_stats(username):
    """Fetch basic user stats from GitHub API."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    stats = {
        "total_repos": 0,
        "total_stars": 0,
        "total_forks": 0,
        "top_language": "Unknown",
        "contributions": None,
        "streak": None,
    }

    try:
        # Fetch repos
        url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            repos = json.loads(resp.read().decode())

        stats["total_repos"] = len(repos)

        lang_counts = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            stats["total_stars"] += repo.get("stargazers_count", 0)
            stats["total_forks"] += repo.get("forks_count", 0)
            lang = repo.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        if lang_counts:
            stats["top_language"] = max(lang_counts, key=lang_counts.get)

    except urllib.error.URLError as e:
        print(f"Warning: Could not fetch user data: {e}")

    # Try GraphQL for contributions (requires token)
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
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            contributions = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
            stats["contributions"] = contributions
        except Exception:
            pass

    return stats


def fetch_repo_info(username, repo_name):
    """Fetch info for a specific repo."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("METRICS_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        url = f"https://api.github.com/repos/{username}/{repo_name}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError:
        return None


def draw_stat_card_svg(stats, username, theme="dark", accent="#39D353"):
    """Generate a stats card SVG."""
    w, h = 480, 180

    if theme == "dark":
        bg = "#0d1117"
        border = "#30363d"
        text_primary = "#e6edf3"
        text_secondary = "#8b949e"
    else:
        bg = "#ffffff"
        border = "#d0d7de"
        text_primary = "#1f2328"
        text_secondary = "#656d76"

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">')
    lines.append(f'''<defs>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&amp;display=swap');
    text {{ font-family: "Inter", -apple-system, sans-serif; }}
  </style>
</defs>''')

    # Card background
    lines.append(f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="6" fill="{bg}" stroke="{border}"/>')

    # Title
    lines.append(f'<text x="24" y="35" fill="{text_primary}" font-size="15" font-weight="600">{username}\'s GitHub Stats</text>')

    # Stat tiles
    tiles = [
        ("Repos", str(stats["total_repos"])),
        ("Stars", str(stats["total_stars"])),
        ("Forks", str(stats["total_forks"])),
    ]

    if stats.get("contributions") is not None:
        tiles.insert(0, ("Contributions", str(stats["contributions"])))

    if stats.get("streak") is not None:
        tiles.append(("Streak", f"{stats['streak']}d"))

    tiles.append(("Top Lang", stats["top_language"]))

    tile_y = 60
    cols = min(len(tiles), 3)
    tile_w = (w - 48 - (cols - 1) * 12) // cols

    for i, (label, value) in enumerate(tiles):
        col = i % cols
        row = i // cols
        tx = 24 + col * (tile_w + 12)
        ty = tile_y + row * 55

        # Tile background
        tile_bg = f"{accent}15" if theme == "dark" else f"{accent}10"
        lines.append(f'<rect x="{tx}" y="{ty}" width="{tile_w}" height="45" rx="4" fill="{tile_bg}" stroke="{accent}" stroke-width="0.5" stroke-opacity="0.3"/>')
        lines.append(f'<text x="{tx + tile_w//2}" y="{ty + 20}" text-anchor="middle" fill="{accent}" font-size="16" font-weight="600">{value}</text>')
        lines.append(f'<text x="{tx + tile_w//2}" y="{ty + 36}" text-anchor="middle" fill="{text_secondary}" font-size="10">{label}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def draw_project_card_svg(repo_data, description, theme="dark", accent="#39D353"):
    """Generate a project card SVG."""
    w, h = 420, 140

    if theme == "dark":
        bg = "#0d1117"
        border = "#30363d"
        text_primary = "#e6edf3"
        text_secondary = "#8b949e"
    else:
        bg = "#ffffff"
        border = "#d0d7de"
        text_primary = "#1f2328"
        text_secondary = "#656d76"

    name = repo_data.get("name", "project")
    stars = repo_data.get("stargazers_count", 0)
    forks = repo_data.get("forks_count", 0)
    language = repo_data.get("language", "")
    lang_color = LANG_COLORS.get(language, "#8b949e")

    # Use provided description or fall back to repo description
    desc = description or repo_data.get("description", "") or "No description"
    # Truncate long descriptions
    if len(desc) > 90:
        desc = desc[:87] + "..."

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">')
    lines.append(f'''<defs>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&amp;display=swap');
    text {{ font-family: "Inter", -apple-system, sans-serif; }}
  </style>
</defs>''')

    # Card background with accent border-left
    lines.append(f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="6" fill="{bg}" stroke="{border}"/>')
    lines.append(f'<rect x="0" y="8" width="3" height="{h-16}" rx="1.5" fill="{accent}"/>')

    # Repo icon (book)
    lines.append(f'<text x="20" y="34" fill="{text_secondary}" font-size="14">📁</text>')

    # Repo name
    lines.append(f'<text x="40" y="34" fill="{accent}" font-size="14" font-weight="600">{name}</text>')

    # Description (word-wrap into two lines)
    words = desc.split()
    line1 = ""
    line2 = ""
    for word in words:
        test = line1 + " " + word if line1 else word
        if len(test) <= 55:
            line1 = test
        else:
            if not line2:
                line2 = word
            elif len(line2 + " " + word) <= 55:
                line2 += " " + word
            else:
                line2 += "..."
                break

    lines.append(f'<text x="20" y="58" fill="{text_secondary}" font-size="11">{line1}</text>')
    if line2:
        lines.append(f'<text x="20" y="73" fill="{text_secondary}" font-size="11">{line2}</text>')

    # Bottom row: language, stars, forks
    by = h - 22

    x_cursor = 20
    if language:
        lines.append(f'<circle cx="{x_cursor + 5}" cy="{by}" r="5" fill="{lang_color}"/>')
        lines.append(f'<text x="{x_cursor + 15}" y="{by + 4}" fill="{text_secondary}" font-size="11">{language}</text>')
        x_cursor += 15 + len(language) * 6.5 + 16

    # Star icon
    lines.append(f'<text x="{x_cursor}" y="{by + 4}" fill="{text_secondary}" font-size="11">⭐ {stars}</text>')
    x_cursor += 40 + len(str(stars)) * 7

    # Fork icon
    lines.append(f'<text x="{x_cursor}" y="{by + 4}" fill="{text_secondary}" font-size="11">🍴 {forks}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def draw_placeholder_project_card(project, theme="dark", accent="#39D353"):
    """Draw a card without API data (for placeholder projects)."""
    repo_data = {
        "name": project.get("repo", "project"),
        "stargazers_count": 0,
        "forks_count": 0,
        "language": "",
        "description": project.get("description", ""),
    }
    return draw_project_card_svg(repo_data, project.get("description", ""), theme, accent)


def main():
    parser = argparse.ArgumentParser(description="Generate stat and project cards")
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--out", default="assets", help="Output directory")
    parser.add_argument("--accent", default="#39D353", help="Accent color")
    parser.add_argument("--projects", default=None, help="Path to projects.json")

    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # Fetch user stats
    print(f"Fetching stats for {args.user}...")
    stats = fetch_user_stats(args.user)
    print(f"  Repos: {stats['total_repos']}, Stars: {stats['total_stars']}, "
          f"Forks: {stats['total_forks']}, Top: {stats['top_language']}")

    # Generate stat cards
    for theme in ["dark", "light"]:
        svg = draw_stat_card_svg(stats, args.user, theme, args.accent)
        path = os.path.join(args.out, f"stats-{theme}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  Wrote {path}")

    # Load projects
    projects_path = args.projects
    if not projects_path:
        # Auto-detect
        for candidate in ["assets/projects.json", "../assets/projects.json", "projects.json"]:
            if os.path.exists(candidate):
                projects_path = candidate
                break

    if projects_path and os.path.exists(projects_path):
        with open(projects_path, "r", encoding="utf-8") as f:
            projects_data = json.load(f)

        projects = projects_data.get("projects", [])
        print(f"\nGenerating {len(projects)} project cards...")

        for project in projects:
            repo_name = project["repo"]
            description = project.get("description", "")

            # Try to fetch live data
            repo_info = fetch_repo_info(args.user, repo_name)

            for theme in ["dark", "light"]:
                if repo_info:
                    svg = draw_project_card_svg(repo_info, description, theme, args.accent)
                else:
                    svg = draw_placeholder_project_card(project, theme, args.accent)

                path = os.path.join(args.out, f"card-{repo_name}-{theme}.svg")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
                print(f"  Wrote {path}")
    else:
        print("\nNo projects.json found — skipping project cards.")

    print("\nDone!")


if __name__ == "__main__":
    main()
