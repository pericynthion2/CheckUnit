#!/usr/bin/env python3
"""Pull Yahoo fantasy hockey rosters into a Google Sheet."""

import datetime as dt
import json
import pathlib

import gspread
import requests

HERE = pathlib.Path(__file__).parent
BASE = "https://fantasysports.yahooapis.com/fantasy/v2"
SHEET_NAME = "CheckUnit"      # <-- your sheet's exact name


# ---------------------------------------------------------------- auth

def access_token():
    """Trade the long-lived refresh token for a 1-hour access token."""
    secrets = json.loads((HERE / "yahoo_secrets.json").read_text())
    tok = json.loads((HERE / "yahoo_token.json").read_text())

    r = requests.post(
        "https://api.login.yahoo.com/oauth2/get_token",
        data={
            "client_id": secrets["client_id"],
            "client_secret": secrets["client_secret"],
            "redirect_uri": "https://localhost:8080",
            "refresh_token": tok["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    fresh = r.json()

    # Yahoo sometimes hands back a NEW refresh token. Save it or the next
    # run is locked out and you have to redo get_token.py.
    (HERE / "yahoo_token.json").write_text(json.dumps(fresh, indent=2))
    return fresh["access_token"]


def get(path, token):
    """One GET against the Yahoo Fantasy API."""
    r = requests.get(
        f"{BASE}/{path}?format=json",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["fantasy_content"]


# ------------------------------------------------- unpacking Yahoo's JSON

def numbered(d):
    """{"0": x, "1": y, "count": 2}  ->  [x, y]"""
    return [d[str(i)] for i in range(int(d.get("count", 0)))]


def flatten(chunks):
    """Yahoo's scattered list of small dicts  ->  one merged dict."""
    out = {}
    for c in chunks if isinstance(chunks, list) else [chunks]:
        if isinstance(c, dict):
            out.update(c)
        elif isinstance(c, list):
            out.update(flatten(c))
    return out


# ------------------------------------------------------------- the pulls

def first_league(token):
    fc = get("users;use_login=1/games;game_keys=nhl/leagues", token)
    blob = fc["users"]["0"]["user"][1]["games"]["0"]["game"][1]["leagues"]
    leagues = [flatten(x["league"]) for x in numbered(blob)]
    if not leagues:
        raise SystemExit("No NHL leagues found - is this season's league created yet?")
    return leagues[0]


def get_teams(league_key, token):
    fc = get(f"league/{league_key}/teams", token)
    rows = []
    for entry in numbered(fc["league"][1]["teams"]):
        t = flatten(entry["team"])
        managers = t.get("managers") or []
        manager = flatten(managers[0]["manager"]).get("nickname", "") if managers else ""
        rows.append({
            "team_key": t["team_key"],
            "team_name": t["name"],
            "manager": manager,
        })
    return rows


def get_roster(team_key, date, token):
    fc = get(f"team/{team_key}/roster;date={date}", token)
    rows = []
    for entry in numbered(fc["team"][1]["roster"]["0"]["players"]):
        p = entry["player"]
        info = flatten(p[0])                  # name, team, positions, status
        extra = flatten(p[1:])                # selected_position lives here
        slot = flatten(extra.get("selected_position", [])).get("position", "")
        rows.append({
            "player_id": info.get("player_id", ""),
            "player_name": info.get("name", {}).get("full", ""),
            "nhl_team": info.get("editorial_team_abbr", ""),
            "positions": info.get("display_position", ""),
            "status": info.get("status", ""),
            "slot": slot,
        })
    return rows


# ------------------------------------------------------------ the sheet

def write(sheet, tab, dicts):
    """Replace a tab's contents with these rows, header first."""
    if not dicts:
        return
    try:
        ws = sheet.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=tab, rows=1000, cols=20)

    header = list(dicts[0].keys())
    rows = [header] + [[str(d.get(k, "")) for k in header] for d in dicts]

    ws.clear()                                  # <-- for APPEND: delete this line
    ws.update(values=rows, range_name="A1")     #     and use ws.append_rows(rows[1:])


# -------------------------------------------------------------- run it

def main():
    today = dt.date.today().isoformat()
    token = access_token()

    league = first_league(token)
    print(f"League: {league['name']}  ({league['league_key']})")

    teams = get_teams(league["league_key"], token)
    print(f"{len(teams)} teams")

    roster_rows = []
    players = {}
    for t in teams:
        for p in get_roster(t["team_key"], today, token):
            roster_rows.append({
                "date_pulled": today,
                "team_key": t["team_key"],
                "team_name": t["team_name"],
                "player_id": p["player_id"],
                "player_name": p["player_name"],
                "slot": p["slot"],
            })
            players[p["player_id"]] = {
                "player_id": p["player_id"],
                "player_name": p["player_name"],
                "nhl_team": p["nhl_team"],
                "positions": p["positions"],
                "status": p["status"],
            }
        print(f"  {t['team_name']}")

    gc = gspread.service_account(filename=str(HERE / "google_key.json"))
    sheet = gc.open(SHEET_NAME)
    write(sheet, "teams", teams)
    write(sheet, "rosters", roster_rows)
    write(sheet, "players", list(players.values()))

    print(f"Done - {len(roster_rows)} roster rows, {len(players)} players.")


if __name__ == "__main__":
    main()