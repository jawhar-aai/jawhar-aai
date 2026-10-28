#!/usr/bin/env python3
"""Generate the contribution and streak cards from GitHub's public contribution calendar.

Usage:  GITHUB_TOKEN=... python3 scripts/activity.py --user <login> --out assets/generated

Only the per-day contribution counts GitHub exposes on the public profile are read.
Private contributions appear only as anonymised counts, and only if the account owner
enabled "Include private contributions on my profile". Nothing else is queried.

On any failure the script exits non-zero and leaves previously generated cards untouched.
"""
import argparse
import datetime as dt
import json
import os
import sys
import tempfile
import urllib.request
from xml.sax.saxutils import escape

API = "https://api.github.com/graphql"

BG = "#0D1117"
PANEL = "#161B22"
BORDER = "#30363D"
CYAN = "#22D3EE"
VIOLET = "#A78BFA"
TEXT = "#E6EDF3"
MUTED = "#9DA7B3"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


# --------------------------------------------------------------------------- data
def graphql(token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-activity"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


YEARS_Q = """query($login:String!){ user(login:$login){ createdAt contributionsCollection{ contributionYears } } }"""
CAL_Q = """query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){ contributionsCollection(from:$from,to:$to){
    contributionCalendar{ weeks{ contributionDays{ date contributionCount } } } } } }"""


def fetch_days(token, login, today):
    """Return {date: count} for every calendar day GitHub reports, account lifetime."""
    data = graphql(token, YEARS_Q, {"login": login})
    if not data.get("user"):
        raise RuntimeError(f"user {login!r} not found")
    years = sorted(data["user"]["contributionsCollection"]["contributionYears"])
    if not years:
        raise RuntimeError("no contribution years returned")
    created = dt.date.fromisoformat(data["user"]["createdAt"][:10])
    days = {}
    for year in years:
        start = dt.datetime(year, 1, 1)
        end = min(dt.datetime(year, 12, 31, 23, 59, 59), dt.datetime.combine(today, dt.time(23, 59, 59)))
        cal = graphql(token, CAL_Q, {"login": login, "from": start.isoformat() + "Z", "to": end.isoformat() + "Z"})
        weeks = cal["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for week in weeks:
            for d in week["contributionDays"]:
                day = dt.date.fromisoformat(d["date"])
                if created <= day <= today:
                    days[day] = d["contributionCount"]
    if not days:
        raise RuntimeError("calendar returned no days")
    return days


# --------------------------------------------------------------------------- stats
def compute(days, today):
    """Compute totals and streaks. `days` may have gaps; missing days count as zero.

    Current streak: consecutive days with contributions ending today, or ending
    yesterday when today has none yet (today is still in progress).
    Longest streak: longest run over the whole period; ties go to the most recent run.
    """
    first = min(days)
    span = (today - first).days + 1
    series = [(first + dt.timedelta(i), days.get(first + dt.timedelta(i), 0)) for i in range(span)]

    total = sum(c for _, c in series)
    year_ago = today - dt.timedelta(days=364)
    last_year = sum(c for d, c in series if d >= year_ago)
    first_contrib = next((d for d, c in series if c > 0), None)

    longest = (0, None, None)
    run_start, run_len = None, 0
    for d, c in series:
        if c > 0:
            if run_len == 0:
                run_start = d
            run_len += 1
            if run_len >= longest[0]:
                longest = (run_len, run_start, d)
        else:
            run_len = 0

    current = (0, None, None)
    counts = dict(series)
    end = today if counts.get(today, 0) > 0 else today - dt.timedelta(days=1)
    if counts.get(end, 0) > 0:
        start = end
        while counts.get(start - dt.timedelta(days=1), 0) > 0:
            start -= dt.timedelta(days=1)
        current = ((end - start).days + 1, start, end)

    weekly = []
    for i in range(52):
        wk_end = today - dt.timedelta(days=7 * (51 - i))
        weekly.append(sum(counts.get(wk_end - dt.timedelta(days=k), 0) for k in range(7)))

    return {
        "period_start": first,
        "period_end": today,
        "total": total,
        "last_year": last_year,
        "first_contribution": first_contrib,
        "current": current,
        "longest": longest,
        "weekly": weekly,
    }


# --------------------------------------------------------------------------- rendering
def fmt_date(d):
    return d.strftime("%b %-d, %Y") if d else ""


def fmt_range(start, end):
    if not start:
        return "no active streak"
    if start == end:
        return fmt_date(start)
    if start.year == end.year:
        return f"{start.strftime('%b %-d')} – {fmt_date(end)}"
    return f"{fmt_date(start)} – {fmt_date(end)}"


def frame(w, h, title, body, desc):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">
<title id="t">{escape(title)}</title>
<desc id="d">{escape(desc)}</desc>
<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="{CYAN}"/><stop offset="100%" stop-color="{VIOLET}"/></linearGradient>
<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath></defs>
<g clip-path="url(#clip)"><rect width="{w}" height="{h}" fill="{PANEL}"/><rect width="{w}" height="4" fill="url(#g)"/></g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{BORDER}"/>
{body}
</svg>
'''


def stats_card(s, login):
    w, h = 640, 200
    period = f"{fmt_date(s['period_start'])} – {fmt_date(s['period_end'])}"
    peak = max(s["weekly"]) or 1
    bars = []
    bx, bw, base, bh = 300, 6, 160, 90
    for i, v in enumerate(s["weekly"]):
        hh = max(2, round(v / peak * bh)) if v else 2
        color = "url(#g)" if v else BORDER
        bars.append(f'<rect x="{bx + i * 6.4:.1f}" y="{base - hh}" width="{bw - 1.6:.1f}" height="{hh}" rx="1.5" fill="{color}"/>')
    body = f'''<text x="32" y="44" font-family="{MONO}" font-size="13" fill="{VIOLET}">contributions · @{escape(login)}</text>
<text x="32" y="104" font-family="{SANS}" font-size="46" font-weight="700" fill="{TEXT}">{s["total"]:,}</text>
<text x="32" y="132" font-family="{SANS}" font-size="15" fill="{MUTED}">total contributions</text>
<text x="32" y="160" font-family="{SANS}" font-size="15" fill="{MUTED}"><tspan fill="{CYAN}" font-weight="600">{s["last_year"]:,}</tspan> in the last 12 months</text>
{"".join(bars)}
<text x="32" y="182" font-family="{MONO}" font-size="11" fill="{MUTED}">{escape(period)}</text>
<text x="608" y="182" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">weekly · last 52 weeks</text>'''
    desc = f"{s['total']} total contributions from {period}; {s['last_year']} in the last 12 months."
    return frame(w, h, "Contributions", body, desc)


def streak_card(s, login):
    w, h = 640, 200
    cur_n, cur_s, cur_e = s["current"]
    lon_n, lon_s, lon_e = s["longest"]
    period = f"{fmt_date(s['period_start'])} – {fmt_date(s['period_end'])}"

    def block(x, label, n, rng, color):
        unit = "day" if n == 1 else "days"
        return (
            f'<text x="{x}" y="78" font-family="{SANS}" font-size="15" fill="{MUTED}">{escape(label)}</text>'
            f'<text x="{x}" y="128" font-family="{SANS}" font-size="46" font-weight="700" fill="{color}">{n}'
            f'<tspan font-size="18" font-weight="400" fill="{MUTED}"> {unit}</tspan></text>'
            f'<text x="{x}" y="156" font-family="{SANS}" font-size="14" fill="{MUTED}">{escape(rng)}</text>'
        )

    body = f'''<text x="32" y="44" font-family="{MONO}" font-size="13" fill="{VIOLET}">streaks · @{escape(login)}</text>
{block(32, "Current streak", cur_n, fmt_range(cur_s, cur_e), CYAN)}
<line x1="320" y1="64" x2="320" y2="160" stroke="{BORDER}"/>
{block(352, "Longest streak", lon_n, fmt_range(lon_s, lon_e), VIOLET)}
<text x="608" y="182" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">lifetime · {escape(period)}</text>'''
    desc = (f"Current streak {cur_n} days ({fmt_range(cur_s, cur_e)}). "
            f"Longest streak {lon_n} days ({fmt_range(lon_s, lon_e)}), over {period}.")
    return frame(w, h, "Contribution streaks", body, desc)


def write_atomic(files, out_dir):
    """Write all files to temp paths first, then swap them in together."""
    os.makedirs(out_dir, exist_ok=True)
    staged = []
    try:
        for name, content in files.items():
            fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
            staged.append((tmp, os.path.join(out_dir, name)))
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
        for tmp, final in staged:
            os.replace(tmp, final)
    finally:
        for tmp, _ in staged:
            if os.path.exists(tmp):
                os.remove(tmp)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
    args = ap.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set", file=sys.stderr)
        return 2
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()
    days = fetch_days(token, args.user, today)
    stats = compute(days, today)
    write_atomic({"stats.svg": stats_card(stats, args.user), "streak.svg": streak_card(stats, args.user)}, args.out)
    summary = {k: str(v) if isinstance(v, (dt.date, tuple)) else v for k, v in stats.items() if k != "weekly"}
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
