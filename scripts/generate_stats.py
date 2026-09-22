#!/usr/bin/env python3
"""
Generate custom GitHub Stats and Top Languages SVGs using GitHub GraphQL API.
Captures both public and private repository activity (via restrictedContributionsCount).
"""

import os
import sys
import json
import urllib.request
import urllib.error

USER = os.environ.get("GITHUB_USER", "Howerchen666")
TOKEN = os.environ.get("STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    repositoriesContributedTo(first: 100, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
      totalCount
    }
    pullRequests(first: 1) {
      totalCount
    }
    issues(first: 1) {
      totalCount
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}
"""


def fetch_github_data(token, user):
    if not token:
        print("Warning: No STATS_TOKEN or GITHUB_TOKEN found. Using fallback data.")
        return None

    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "GitHub-Stats-Generator",
    }
    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": user}}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "errors" in data:
                print(f"GraphQL Errors: {data['errors']}")
                return None
            return data.get("data", {}).get("user")
    except Exception as e:
        print(f"Failed to fetch GraphQL data: {e}")
        return None


def calculate_rank(commits, prs, issues, stars):
    score = commits * 2 + prs * 3 + issues * 2 + stars * 4
    if score >= 500:
        return "S"
    elif score >= 250:
        return "A+"
    elif score >= 100:
        return "A"
    elif score >= 50:
        return "B+"
    elif score >= 25:
        return "B"
    return "C"


def render_stats_svg(user_data):
    if user_data:
        contrib = user_data.get("contributionsCollection", {})
        public_commits = contrib.get("totalCommitContributions", 0)
        private_commits = contrib.get("restrictedContributionsCount", 0) or 0
        total_commits = public_commits + private_commits

        prs = user_data.get("pullRequests", {}).get("totalCount", 0)
        issues = user_data.get("issues", {}).get("totalCount", 0)
        contrib_to = user_data.get("repositoriesContributedTo", {}).get("totalCount", 0)

        repos = user_data.get("repositories", {}).get("nodes", [])
        stars = sum(r.get("stargazerCount", 0) for r in repos)
    else:
        # Fallback values
        total_commits = 28
        prs = 4
        issues = 1
        stars = 1
        contrib_to = 4

    rank = calculate_rank(total_commits, prs, issues, stars)

    svg = f"""<svg width="450" height="195" viewBox="0 0 450 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img">
  <style>
    .title {{ font: 700 17px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #7AA2F7; }}
    .label {{ font: 600 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #A9B1D6; }}
    .val {{ font: 700 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #C0CAF5; }}
    .rank-text {{ font: 800 28px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #7AA2F7; text-anchor: middle; dominant-baseline: central; }}
    .ring-bg {{ stroke: #24283B; stroke-width: 6; fill: none; }}
    .ring-fg {{ stroke: #7AA2F7; stroke-width: 6; stroke-linecap: round; fill: none; transform-origin: 375px 95px; transform: rotate(-90deg); }}
  </style>

  <rect width="448" height="193" x="1" y="1" rx="8" fill="#0D1117" stroke="#30363D" stroke-width="1.5" />

  <text x="25" y="35" class="title">Haowen Chen's GitHub Stats</text>

  <!-- Metrics -->
  <g transform="translate(25, 60)">
    <text y="0" class="label">⭐ Total Stars Earned:</text>
    <text x="210" y="0" class="val">{stars}</text>

    <text y="25" class="label">📦 Total Commits (inc. private):</text>
    <text x="210" y="25" class="val">{total_commits}</text>

    <text y="50" class="label">🔀 Total PRs:</text>
    <text x="210" y="50" class="val">{prs}</text>

    <text y="75" class="label">🎯 Total Issues:</text>
    <text x="210" y="75" class="val">{issues}</text>

    <text y="100" class="label">🌍 Contributed to:</text>
    <text x="210" y="100" class="val">{contrib_to}</text>
  </g>

  <!-- Rank Circle -->
  <g>
    <circle cx="375" cy="100" r="35" class="ring-bg" />
    <circle cx="375" cy="100" r="35" class="ring-fg" stroke-dasharray="220" stroke-dashoffset="60" />
    <text x="375" y="100" class="rank-text">{rank}</text>
  </g>
</svg>"""
    return svg


def render_langs_svg(user_data):
    lang_sizes = {}
    lang_colors = {
        "Python": "#3572A5",
        "Java": "#B07219",
        "JavaScript": "#F1E05A",
        "TypeScript": "#3178C6",
        "C++": "#F34B7D",
        "C": "#555555",
        "Swift": "#F05138",
        "Shell": "#89E051",
        "HTML": "#E34C26",
        "CSS": "#563D7C",
    }

    if user_data:
        repos = user_data.get("repositories", {}).get("nodes", [])
        for repo in repos:
            edges = repo.get("languages", {}).get("edges", [])
            for edge in edges:
                name = edge["node"]["name"]
                size = edge["size"]
                color = edge["node"].get("color")
                if color:
                    lang_colors[name] = color
                lang_sizes[name] = lang_sizes.get(name, 0) + size

    if not lang_sizes:
        lang_sizes = {"Python": 50, "Java": 25, "JavaScript": 15, "Swift": 10}

    total_size = sum(lang_sizes.values()) or 1
    sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:5]

    # Progress bar segments
    bar_rects = []
    current_x = 25
    bar_width = 400

    for name, size in sorted_langs:
        pct = size / total_size
        seg_w = round(pct * bar_width, 1)
        color = lang_colors.get(name, "#7AA2F7")
        bar_rects.append(f'<rect x="{current_x}" y="55" width="{seg_w}" height="10" fill="{color}" />')
        current_x += seg_w

    # Legend items
    legend_items = []
    col_x = [25, 230]
    row_y = [95, 125, 155]

    for idx, (name, size) in enumerate(sorted_langs):
        pct = (size / total_size) * 100
        x = col_x[idx % 2]
        y = row_y[idx // 2]
        color = lang_colors.get(name, "#7AA2F7")
        legend_items.append(f"""
    <circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{color}" />
    <text x="{x + 18}" y="{y}" class="label">{name} <tspan class="val">({pct:.1f}%)</tspan></text>
        """)

    svg = f"""<svg width="450" height="195" viewBox="0 0 450 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img">
  <style>
    .title {{ font: 700 17px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #7AA2F7; }}
    .label {{ font: 600 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #A9B1D6; }}
    .val {{ font: 500 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #C0CAF5; }}
  </style>

  <rect width="448" height="193" x="1" y="1" rx="8" fill="#0D1117" stroke="#30363D" stroke-width="1.5" />

  <text x="25" y="35" class="title">Most Used Languages</text>

  <!-- Progress Bar -->
  <g clip-path="url(#bar-clip)">
    <clipPath id="bar-clip">
      <rect x="25" y="55" width="400" height="10" rx="5" />
    </clipPath>
    {"".join(bar_rects)}
  </g>

  <!-- Legend -->
  <g>
    {"".join(legend_items)}
  </g>
</svg>"""
    return svg


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    user_data = fetch_github_data(TOKEN, USER)

    stats_svg = render_stats_svg(user_data)
    langs_svg = render_langs_svg(user_data)

    stats_path = os.path.join(ASSETS_DIR, "stats.svg")
    langs_path = os.path.join(ASSETS_DIR, "top-langs.svg")

    with open(stats_path, "w", encoding="utf-8") as f:
        f.write(stats_svg)

    with open(langs_path, "w", encoding="utf-8") as f:
        f.write(langs_svg)

    print(f"Generated {stats_path} and {langs_path} successfully!")


if __name__ == "__main__":
    main()

