import os
import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
BRENTFORD_ID = 402
PREMIER_LEAGUE_ID = 2021

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

API_BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY}


# --- API helpers ---

def get(endpoint):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", headers=HEADERS, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_standings():
    data = get(f"/competitions/{PREMIER_LEAGUE_ID}/standings")
    if not data:
        return None
    for table in data["standings"]:
        if table["type"] == "TOTAL":
            for row in table["table"]:
                if row["team"]["id"] == BRENTFORD_ID:
                    return row
    return None


def get_matches(status=None):
    endpoint = f"/teams/{BRENTFORD_ID}/matches"
    if status:
        endpoint += f"?status={status}&limit=5"
    data = get(endpoint)
    return data.get("matches") if data else None


def get_squad():
    data = get(f"/teams/{BRENTFORD_ID}")
    return data.get("squad") if data else None


def get_scorers():
    data = get(f"/competitions/{PREMIER_LEAGUE_ID}/scorers?season=2024")
    return data.get("scorers") if data else None


# --- Fallback data ---

FALLBACK_INFO = {
    "name": "Brentford FC",
    "founded": 1889,
    "stadium": "Gtech Community Stadium",
    "capacity": 17250,
    "manager": "Thomas Frank",
    "website": "https://www.brentfordfc.com",
}


# --- Commands ---

@bot.command()
async def table(ctx):
    row = get_standings()
    if not row:
        await ctx.send("Could not fetch standings right now.")
        return

    msg = (
        f"**Brentford in the Premier League**\n"
        f"Position: {row['position']}\n"
        f"Played: {row['playedGames']} | Points: {row['points']}\n"
        f"W {row['won']} / D {row['draw']} / L {row['lost']}\n"
        f"GD: {row['goalDifference']}"
    )
    await ctx.send(msg)


@bot.command()
async def nextmatch(ctx):
    matches = get_matches(status="SCHEDULED")
    if not matches:
        await ctx.send("No upcoming fixtures found.")
        return

    m = matches[0]
    date = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
    home = m["homeTeam"]["name"]
    away = m["awayTeam"]["name"]
    competition = m["competition"]["name"]

    msg = (
        f"**Next Match**\n"
        f"{home} vs {away}\n"
        f"{competition}\n"
        f"{date.strftime('%A %d %B %Y, %H:%M UTC')}"
    )
    await ctx.send(msg)


@bot.command()
async def results(ctx):
    matches = get_matches(status="FINISHED")
    if not matches:
        await ctx.send("Could not fetch results.")
        return

    last5 = matches[-5:]
    lines = ["**Last 5 Results**"]
    for m in reversed(last5):
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        score = m["score"]["fullTime"]
        lines.append(f"{home} {score['home']} - {score['away']} {away}")

    await ctx.send("\n".join(lines))


@bot.command()
async def squad(ctx):
    players = get_squad()
    if not players:
        await ctx.send("Could not fetch squad data.")
        return

    groups = {}
    for p in players:
        pos = p.get("position") or "Unknown"
        groups.setdefault(pos, []).append(p["name"])

    lines = ["**Brentford Squad**"]
    for pos, names in groups.items():
        lines.append(f"\n__{pos}__")
        lines.extend(f"- {n}" for n in names)

    await ctx.send("\n".join(lines))


@bot.command()
async def info(ctx):
    data = get(f"/teams/{BRENTFORD_ID}")
    if data:
        msg = (
            f"**{data['name']}**\n"
            f"Founded: {data.get('founded', 'N/A')}\n"
            f"Stadium: {data.get('venue', 'N/A')}\n"
            f"Website: {data.get('website', 'N/A')}"
        )
    else:
        d = FALLBACK_INFO
        msg = (
            f"**{d['name']}**\n"
            f"Founded: {d['founded']}\n"
            f"Stadium: {d['stadium']} (capacity {d['capacity']})\n"
            f"Manager: {d['manager']}\n"
            f"Website: {d['website']}"
        )
    await ctx.send(msg)


@bot.command()
async def player(ctx, *, name: str):
    players = get_squad()
    if not players:
        await ctx.send("Could not fetch squad.")
        return

    name_lower = name.lower()
    match = next((p for p in players if name_lower in p["name"].lower()), None)

    if not match:
        await ctx.send(f"No player found matching '{name}'.")
        return

    msg = (
        f"**{match['name']}**\n"
        f"Position: {match.get('position', 'N/A')}\n"
        f"Nationality: {match.get('nationality', 'N/A')}\n"
        f"DOB: {match.get('dateOfBirth', 'N/A')}"
    )
    await ctx.send(msg)


@bot.command()
async def topscorer(ctx):
    scorers = get_scorers()
    if not scorers:
        await ctx.send("Could not fetch top scorers.")
        return

    brentford_scorers = [
        s for s in scorers if s["team"]["id"] == BRENTFORD_ID
    ]

    if not brentford_scorers:
        top = scorers[0]
        msg = (
            f"No Brentford player in top scorers.\n"
            f"Overall leader: {top['player']['name']} ({top['team']['name']}) - {top['goals']} goals"
        )
    else:
        top = brentford_scorers[0]
        msg = (
            f"**Brentford Top Scorer**\n"
            f"{top['player']['name']} - {top['goals']} goals"
        )

    await ctx.send(msg)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


bot.run(TOKEN)