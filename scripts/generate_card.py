"""
Gera um card SVG de estatísticas do GitHub para o README, com dados reais
buscados via API (REST + GraphQL). Pensado para rodar dentro do GitHub Actions,
usando o secret GH_TOKEN. Não depende de nenhum serviço externo (Vercel etc.),
então nunca fica fora do ar por culpa de terceiros.

Uso:
    GH_TOKEN=xxx GH_USERNAME=joao-torre python generate_card.py
Saída:
    generated/card.svg
"""

import os
import sys
import datetime
import requests

USERNAME = os.environ.get("GH_USERNAME", "joao-torre")
TOKEN = os.environ["GH_TOKEN"]
HEADERS = {"Authorization": f"bearer {TOKEN}"}

GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"


def gql(query: str, variables: dict) -> dict:
    resp = requests.post(
        GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_overview():
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes { stargazerCount primaryLanguage { name color } }
        }
        pullRequests(states: [MERGED, OPEN, CLOSED]) { totalCount }
        issues { totalCount }
        contributionsCollection {
          totalCommitContributions
          totalRepositoryContributions
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    data = gql(query, {"login": USERNAME})["user"]
    return data


def compute_streaks(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort()

    longest = current = 0
    today = datetime.date.today()
    running = 0
    for date_str, count in days:
        if count > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    # current streak: walk backwards from today
    by_date = {datetime.date.fromisoformat(d): c for d, c in days}
    cursor = today
    while by_date.get(cursor, 0) > 0:
        current += 1
        cursor -= datetime.timedelta(days=1)

    return current, longest


def top_languages(repo_nodes, limit=4):
    totals = {}
    for r in repo_nodes:
        lang = r.get("primaryLanguage")
        if not lang:
            continue
        totals[lang["name"]] = totals.get(lang["name"], {"count": 0, "color": lang["color"]})
        totals[lang["name"]]["count"] = totals.get(lang["name"], {"count": 0})["count"] + 1
    # fallback simple counting
    counts = {}
    colors = {}
    for r in repo_nodes:
        lang = r.get("primaryLanguage")
        if not lang:
            continue
        counts[lang["name"]] = counts.get(lang["name"], 0) + 1
        colors[lang["name"]] = lang["color"] or "#94A3B8"
    total = sum(counts.values()) or 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [(name, cnt / total * 100, colors[name]) for name, cnt in ranked]


def render_svg(stats: dict) -> str:
    langs = stats["languages"]
    while len(langs) < 4:
        langs.append(("—", 0, "#071A35"))

    # language bar segments
    x = 20
    bar_segments = ""
    for name, pct, color in langs:
        w = 270 * (pct / 100)
        bar_segments += f'<rect x="{x:.1f}" y="50" width="{w:.1f}" height="14" fill="{color}"/>'
        x += w

    legend_positions = [(26, 90), (26, 116), (160, 90), (160, 116)]
    legend = ""
    for (lx, ly), (name, pct, color) in zip(legend_positions, langs):
        legend += (
            f'<circle cx="{lx}" cy="{ly}" r="5" fill="{color}"/>'
            f'<text x="{lx+12}" y="{ly+4}" class="langName">{name}</text>'
            f'<text x="{lx+76}" y="{ly+4}" class="langPct">{pct:.0f}%</text>'
        )

    circumference = 389.5
    streak_ratio = min(stats["current_streak"] / 30, 1.0)  # cap visual fill at a 30-day streak
    dashoffset = circumference * (1 - streak_ratio)

    return f"""<svg width="720" height="460" viewBox="0 0 720 460" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#3B82F6"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      .title {{ font: 700 22px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #F8FAFC; }}
      .subtitle {{ font: 400 13px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #94A3B8; }}
      .label {{ font: 600 12px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #94A3B8; letter-spacing: .04em; text-transform: uppercase; }}
      .value {{ font: 700 30px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #F8FAFC; }}
      .streakNum {{ font: 700 34px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #3B82F6; }}
      .streakLbl {{ font: 600 12px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #94A3B8; }}
      .langName {{ font: 600 12px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #F8FAFC; }}
      .langPct {{ font: 400 11px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #94A3B8; }}
      .sectionHead {{ font: 700 13px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #3B82F6; letter-spacing: .06em; text-transform: uppercase; }}
    </style>
  </defs>

  <rect x="1" y="1" width="718" height="458" rx="18" fill="url(#bg)" stroke="#071A35" stroke-width="1.5"/>
  <rect x="1" y="1" width="718" height="458" rx="18" fill="none" stroke="url(#accent)" stroke-width="1" opacity="0.35"/>

  <text x="32" y="46" class="title">{stats['name']}</text>
  <text x="32" y="66" class="subtitle">{stats['subtitle']}</text>
  <line x1="32" y1="82" x2="688" y2="82" stroke="#071A35" stroke-width="1"/>

  <g>
    <rect x="32" y="102" width="200" height="92" rx="12" fill="#071A35" stroke="#071A35"/>
    <rect x="248" y="102" width="200" height="92" rx="12" fill="#071A35" stroke="#071A35"/>
    <rect x="464" y="102" width="224" height="92" rx="12" fill="#071A35" stroke="#071A35"/>

    <text x="52" y="132" class="label">Repositórios</text>
    <text x="52" y="168" class="value">{stats['repos']}</text>

    <text x="268" y="132" class="label">Commits (ano)</text>
    <text x="268" y="168" class="value">{stats['commits_year']}</text>

    <text x="484" y="132" class="label">Stars</text>
    <text x="484" y="168" class="value">{stats['stars']}</text>
  </g>

  <g transform="translate(32,214)">
    <rect x="0" y="0" width="330" height="220" rx="14" fill="#071A35" stroke="#071A35"/>
    <text x="20" y="30" class="sectionHead">Streak de contribuições</text>
    <g transform="translate(90,60)">
      <circle cx="75" cy="75" r="62" fill="none" stroke="#071A35" stroke-width="10"/>
      <circle cx="75" cy="75" r="62" fill="none" stroke="url(#accent)" stroke-width="10"
              stroke-linecap="round" stroke-dasharray="{circumference}" stroke-dashoffset="{dashoffset:.1f}"
              transform="rotate(-90 75 75)" filter="url(#glow)"/>
      <text x="75" y="70" text-anchor="middle" class="streakNum">{stats['current_streak']}</text>
      <text x="75" y="92" text-anchor="middle" class="streakLbl">dias seguidos</text>
    </g>
    <text x="20" y="200" class="langPct">Maior streak: {stats['longest_streak']} dias · desde {stats['member_since']}</text>
  </g>

  <g transform="translate(378,214)">
    <rect x="0" y="0" width="310" height="220" rx="14" fill="#071A35" stroke="#071A35"/>
    <text x="20" y="30" class="sectionHead">Linguagens mais usadas</text>
    <rect x="20" y="50" width="270" height="14" rx="7" fill="#071A35"/>
    {bar_segments}
    {legend}
    <text x="20" y="170" class="langPct">Atualizado automaticamente via GitHub Actions</text>
    <text x="20" y="190" class="langPct">{stats['username']} · gerado em {stats['generated_at']}</text>
  </g>

  <text x="688" y="446" text-anchor="end" class="langPct" opacity="0.6">github.com/{stats['username']}</text>
</svg>"""


def main():
    user = fetch_overview()
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    current, longest = compute_streaks(weeks)

    repos = user["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    langs = top_languages(repos)

    stats = {
        "name": "João Torre",
        "subtitle": "Analista de Planejamento de Cobrança · Ciência de Dados",
        "username": USERNAME,
        "repos": user["repositories"]["totalCount"],
        "commits_year": user["contributionsCollection"]["totalCommitContributions"],
        "stars": stars,
        "current_streak": current,
        "longest_streak": longest,
        "languages": langs,
        "member_since": "15 mar 2025",
        "generated_at": datetime.date.today().isoformat(),
    }

    svg = render_svg(stats)
    os.makedirs("generated", exist_ok=True)
    with open("generated/card.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Card gerado em generated/card.svg")


if __name__ == "__main__":
    main()
