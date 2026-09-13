#!/usr/bin/env python3
"""
Novix Sports API Scraper
Fetches football matches + stream sources from streamed.su
Runs via GitHub Actions every 10 minutes → outputs to api/
"""

import cloudscraper
import json
import os
import sys
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://streamed.su"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "api")

MAJOR_LEAGUES = [
    "premier league", "english premier league", "epl",
    "champions league", "uefa champions", "ucl",
    "la liga", "laliga", "primera division", "primera división",
    "serie a", "italian serie a",
    "bundesliga", "german bundesliga",
    "europa league", "uefa europa", "uel",
    "ligue 1",
    "world cup", "nations league",
    "fa cup", "carabao", "copa del rey", "dfb pokal", "coppa italia",
]

EXCLUDE_KEYWORDS = [
    "ukraine", "russian", "russia", "saudi", "chinese", "indian",
    "thai", "myanmar", "polish", "czech", "greek", "turkish",
    "belgian", "dutch", "women", "nữ", "femení", "championship nữ",
    "austria bundesliga", "swiss bundesliga",
]

STREAM_SOURCES = ["alpha", "daddy", "blue", "raw"]


def create_scraper():
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
        delay=3,
    )


def is_major_league(league_name: str) -> bool:
    lower = league_name.lower()
    # Must match a major league keyword
    if not any(kw in lower for kw in MAJOR_LEAGUES):
        return False
    # Must NOT match any exclude keyword
    if any(kw in lower for kw in EXCLUDE_KEYWORDS):
        return False
    return True


def categorize(league_name: str) -> str:
    lower = league_name.lower()
    if any(k in lower for k in ["premier league", "epl", "english premier", "fa cup", "carabao"]):
        if not any(x in lower for x in ["ukraine", "russian", "russia", "saudi"]):
            return "Premier League"
    if "champions league" in lower or "uefa champions" in lower:
        return "Champions League"
    if any(k in lower for k in ["la liga", "laliga", "primera divis", "copa del rey"]):
        return "La Liga"
    if "serie a" in lower or "coppa italia" in lower:
        return "Serie A"
    if "bundesliga" in lower and "austria" not in lower and "swiss" not in lower:
        return "Bundesliga"
    if "dfb pokal" in lower:
        return "Bundesliga"
    if "europa league" in lower or "uefa europa" in lower:
        return "Europa League"
    if "ligue 1" in lower:
        return "Ligue 1"
    if "world cup" in lower or "nations league" in lower:
        return "International"
    return "Major"


def fetch_matches(scraper) -> list:
    print("[1] Fetching football matches from streamed.su...")
    headers = {
        "Referer": f"{BASE_URL}/",
        "Origin": BASE_URL,
        "Accept": "application/json, */*",
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = scraper.get(f"{BASE_URL}/api/matches/football", headers=headers, timeout=25)
    resp.raise_for_status()
    matches = resp.json()
    print(f"   Raw matches: {len(matches)}")
    return matches


def fetch_streams(scraper, match_id: str) -> list:
    """Fetch stream URLs from all sources for a given match."""
    headers = {"Referer": f"{BASE_URL}/", "Accept": "application/json, */*"}
    all_streams = []

    for source in STREAM_SOURCES:
        try:
            resp = scraper.get(
                f"{BASE_URL}/api/stream/{source}/{match_id}",
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Normalize: could be list or dict
                if isinstance(data, list):
                    for item in data:
                        url = item.get("url") or item.get("embedUrl") or item.get("src", "")
                        if url:
                            all_streams.append({
                                "name": f"{source.capitalize()} {item.get('streamNo', len(all_streams)+1)}",
                                "url": url,
                                "source": source,
                                "quality": item.get("quality", "HD"),
                                "headers": item.get("headers", {}),
                            })
                elif isinstance(data, dict):
                    url = data.get("url") or data.get("embedUrl", "")
                    if url:
                        all_streams.append({
                            "name": f"{source.capitalize()} 1",
                            "url": url,
                            "source": source,
                            "quality": data.get("quality", "HD"),
                            "headers": data.get("headers", {}),
                        })
        except Exception as e:
            print(f"   [{source}] stream fetch failed: {e}")

    return all_streams


def process_match(raw: dict, scraper, fetch_streams_now: bool = True) -> dict | None:
    """Process a raw match dict into our normalized format."""
    league = raw.get("category") or raw.get("league") or raw.get("competition") or ""
    title = raw.get("title") or raw.get("name") or ""
    match_id = str(raw.get("id") or raw.get("_id") or raw.get("matchId") or "")

    if not is_major_league(league):
        return None

    # Parse time
    match_time = raw.get("date") or raw.get("time") or raw.get("kickoff") or ""

    # Fetch streams
    streams = []
    if fetch_streams_now and match_id:
        streams = fetch_streams(scraper, match_id)

    return {
        "id": match_id,
        "title": title,
        "homeTeam": raw.get("teams", {}).get("home", {}).get("name", "") if isinstance(raw.get("teams"), dict) else "",
        "awayTeam": raw.get("teams", {}).get("away", {}).get("name", "") if isinstance(raw.get("teams"), dict) else "",
        "homeLogo": raw.get("teams", {}).get("home", {}).get("badge", "") if isinstance(raw.get("teams"), dict) else "",
        "awayLogo": raw.get("teams", {}).get("away", {}).get("badge", "") if isinstance(raw.get("teams"), dict) else "",
        "league": league,
        "leagueCategory": categorize(league),
        "leagueLogo": raw.get("leagueLogo") or raw.get("badge") or "",
        "matchTime": match_time,
        "status": raw.get("status") or ("live" if raw.get("live") else "upcoming"),
        "popular": raw.get("popular", False),
        "streams": streams,
        "streamCount": len(streams),
        "scrapedAt": datetime.now(timezone.utc).isoformat(),
    }


def main():
    scraper = create_scraper()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Step 1: Fetch all matches ──
    try:
        raw_matches = fetch_matches(scraper)
    except Exception as e:
        print(f"FATAL: Could not fetch matches: {e}")
        sys.exit(1)

    # ── Step 2: Filter major leagues only ──
    major_raw = [m for m in raw_matches if is_major_league(
        m.get("category") or m.get("league") or m.get("competition") or ""
    )]
    print(f"   Major league matches: {len(major_raw)}")

    # ── Step 3: Process matches + fetch streams ──
    processed = []
    for i, raw in enumerate(major_raw):
        title = raw.get("title") or raw.get("name") or "Unknown"
        print(f"   [{i+1}/{len(major_raw)}] Processing: {title}")
        result = process_match(raw, scraper, fetch_streams_now=True)
        if result:
            processed.append(result)

    # ── Step 4: Save output ──
    # Full matches with streams
    matches_path = os.path.join(OUTPUT_DIR, "matches.json")
    with open(matches_path, "w", encoding="utf-8") as f:
        json.dump({
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "totalMatches": len(processed),
            "matches": processed,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved {len(processed)} matches → {matches_path}")

    # Live-only subset
    live = [m for m in processed if m["status"] == "live"]
    live_path = os.path.join(OUTPUT_DIR, "live.json")
    with open(live_path, "w", encoding="utf-8") as f:
        json.dump({
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "totalMatches": len(live),
            "matches": live,
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(live)} live matches → {live_path}")

    # Index by league category
    by_league: dict[str, list] = {}
    for m in processed:
        cat = m["leagueCategory"]
        by_league.setdefault(cat, []).append(m)
    index_path = os.path.join(OUTPUT_DIR, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "categories": {cat: len(ms) for cat, ms in by_league.items()},
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved league index → {index_path}")

    print("\n=== Done ===")
    for m in processed[:3]:
        print(f"  {m['title']} | {m['league']} | streams: {m['streamCount']}")


if __name__ == "__main__":
    main()
