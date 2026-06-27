# SGO V1 → V2 Migration Guide

Source: https://sportsgameodds.com/docs/info/v1-to-v2

## Key Changes

- **Faster odds updates** — <50% delay of V1; tier-dependent
- **Faster API response times**
- **Combined /odds and /events** — Single `/v2/events` endpoint replaces both
- **Deeplinks added** — Per-bookmaker deeplinks for FD, DK, BetMGM (more coming)
- **Odds persist when unavailable** — `available` boolean field instead of disappearing
- **New player ID system** — `PLAYER_NAME_NUMBER_LEAGUE_ID` instead of `PLAYER_NAME_TEAM_LEAGUE_ID`

## URL Changes

```
V1: https://api.sportsgameodds.com/v1/...
V2: https://api.sportsgameodds.com/v2/...
```

Both `/v1/events` and `/v1/odds` → `/v2/events` (no `/v2/odds`)

## Breaking Field Changes (v1/events.odds → v2/events.odds)

| V1 Path | V2 Path |
|---------|---------|
| `Event.odds.<oddID>.odds` | `Event.odds.<oddID>.fairOdds` |
| `Event.odds.<oddID>.spread` | `Event.odds.<oddID>.fairSpread` |
| `Event.odds.<oddID>.overUnder` | `Event.odds.<oddID>.fairOverUnder` |
| `Event.odds.<oddID>.closeOdds` | `Event.odds.<oddID>.closeFairOdds` |
| `Event.odds.<oddID>.closeSpread` | `Event.odds.<oddID>.closeFairSpread` |
| `Event.odds.<oddID>.closeOverUnder` | `Event.odds.<oddID>.closeFairOverUnder` |
| `Event.odds.<oddID>.isFallbackOdds` | **REMOVED** |

## Breaking Status Field Changes

| V1 | V2 |
|----|----|
| `Event.status.hasMarketOdds` | `Event.status.oddsPresent` |
| `Event.status.hasAnyOdds` | `Event.status.oddsPresent` |
| `Event.status.anyOddsAvailable` | `Event.status.oddsAvailable` |
| `Event.status.marketOddsAvailable` | `Event.status.oddsAvailable` |
| `Event.status.nextUpdateAt` | **REMOVED** |

## Breaking Player Field Changes

| V1 | V2 |
|----|----|
| `Player.firstName` | `Player.names.firstName` |
| `Player.lastName` | `Player.names.lastName` |
| `Player.name` | `Player.names.display` |

## ByBookmaker: `available` field

Odds now include unavailable odds with an `available` boolean:
- `Event.odds.<oddID>.byBookmaker.<bookmakerID>.available`
- `Event.odds.<oddID>.byBookmaker.<bookmakerID>.altLines[i].available`

Filter `available == false` to only see live/open odds.

## New v2/events Parameters

| Parameter | Description |
|-----------|-------------|
| `type` | Filter: `match`, `prop`, `tournament` |
| `oddsPresent` | Only events with/without odds markets |
| `includeOpposingOdds` | Renamed from `includeOpposingOddIDs` (old still works) |
| `includeAltLines` | **Default OFF** — must pass `true` to get alt lines |
| `bookmakerID` | Filter by bookmaker(s) |
| `teamID` | Filter by team(s) |
| `playerID` | Filter by player(s) — new v2 playerID format |
| `live` | Live-only or non-live filtering |
| `started` | Started/unstarted filtering |
| `ended` | Ended/unended filtering |
| `cancelled` | Cancelled/non-cancelled filtering |
| `includeOpenCloseOdds` | Open/close odds in byBookmaker (default false) |

## Limit Changes

| Endpoint | V1 Default | V2 Default | V1 Max | V2 Max |
|----------|-----------|-----------|--------|--------|
| /events | 30 | 10 | 300 | 100 |
| /teams, /players | 30 | 50 | 300 | 250 |

## Player ID Migration

**V1 format:** `PLAYER_NAME_TEAM_ID_LEAGUE_ID`
**V2 format:** `PLAYER_NAME_NUMBER_LEAGUE_ID`

**V1→V2:** `GET /v2/players?alias=<v1_playerID>`
**V2→V1:** `GET /v2/players?playerID=<v2_playerID>` → check `aliases` array

## API Key: Can now be in query params

`?apiKey=YOUR_KEY` works alongside `X-Api-Key` header.
