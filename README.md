# CheckUnit

A personal script that pulls one Yahoo fantasy hockey league's rosters
into a private Google Sheet once a day.

Built for a single 12-team league I play in. Not a product, not hosted,
not distributed — it runs on my own machine and writes to my own sheet.

## What it does

Three read-only Yahoo Fantasy Sports API calls per run:

- `users;use_login=1/games;game_keys=nhl/leagues` — find my league
- `league/{league_key}/teams` — the teams in it
- `team/{team_key}/roster;date=YYYY-MM-DD` — each team's roster

About 14 requests per day total. No free agent or full player pool queries.

## Output

Three tabs in a private Google Sheet: teams, rosters, players.
The rosters tab is the point — it shows which players are on which
fantasy team, so roster churn is visible over a season.

Fantasy data provided by Yahoo Fantasy.

## Setup

Requires a Yahoo developer app (Client ID and Secret) and a Google
service account key. Neither is included in this repo.
