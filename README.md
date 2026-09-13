# Novix Sports API

Self-hosted, zero-cost sports streaming data API powered by GitHub Actions + GitHub Pages.

## API Endpoints

After setup, your API will be live at:

```
https://xioverlinn1559-byte.github.io/novix-sports-api/matches.json
https://xioverlinn1559-byte.github.io/novix-sports-api/live.json
https://xioverlinn1559-byte.github.io/novix-sports-api/index.json
```

### matches.json
All major league matches today (EPL, UCL, La Liga, Serie A, Bundesliga, Europa League, Ligue 1)

### live.json  
Only currently live matches with stream URLs

### index.json
Match count by league category

## How It Works

```
GitHub Actions (every 10 min)
  → Python scraper (cloudscraper)
  → streamed.su API
  → Filter major leagues
  → Save JSON to api/
  → Commit & push
  → GitHub Pages serves the JSON
```

## Setup

1. Fork or clone this repo
2. Go to **Settings → Pages → Source: Deploy from branch (main, /root)**
3. Go to **Actions → Enable workflows**
4. Trigger first run manually: **Actions → Novix Sports Scraper → Run workflow**

## Data Format

```json
{
  "updatedAt": "2026-09-13T15:00:00Z",
  "totalMatches": 12,
  "matches": [
    {
      "id": "arsenal-chelsea",
      "title": "Arsenal vs Chelsea",
      "homeTeam": "Arsenal",
      "awayTeam": "Chelsea",
      "homeLogo": "https://...",
      "awayLogo": "https://...",
      "league": "Premier League",
      "leagueCategory": "Premier League",
      "matchTime": "2026-09-13T15:00:00Z",
      "status": "live",
      "streams": [
        {
          "name": "Alpha 1",
          "url": "https://....m3u8",
          "source": "alpha",
          "quality": "HD"
        }
      ],
      "streamCount": 3
    }
  ]
}
```

## Zero Cost

- GitHub Actions: Free (2000 min/month)
- GitHub Pages: Free
- Data source: streamed.su public API
