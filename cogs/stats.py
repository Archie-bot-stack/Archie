import discord
from discord.ext import commands, tasks
import aiohttp
import logging
import io
import os
from datetime import datetime, timedelta
from collections import deque

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from utils.security import check_cooldown
from utils.error_logging import log_error_to_channel
from utils.json_ops import safe_json_load, safe_json_save

logger = logging.getLogger('archie-bot')

ARCHMC_IP = "arch.mc"
STATS_FILE = "server_stats.json"
ARCHMC_LOGO = "https://www.arch.mc/data/assets/logo/2L-bg.png"
ARCHMC_BANNER = "https://store.arch.mc/img/banner.png"


def load_stats_data():
    default = {
        "peak_alltime": 0,
        "peak_24h": 0,
        "peak_24h_timestamp": None,
        "hourly_history": [],
        "daily_history": []
    }
    data = safe_json_load(STATS_FILE, default)
    return data


def save_stats_data(data):
    safe_json_save(STATS_FILE, data)


def generate_player_graph(daily_history: list, hourly_history: list = None) -> io.BytesIO:
    # Use hourly data if not enough daily data yet
    if len(daily_history) < 2 and hourly_history and len(hourly_history) >= 2:
        dates = [datetime.fromisoformat(entry["timestamp"]).strftime('%H:%M') for entry in hourly_history]
        players = [entry["players"] for entry in hourly_history]
    elif len(daily_history) >= 2:
        dates = [datetime.fromisoformat(entry["date"]).strftime('%d/%m') for entry in daily_history]
        players = [entry["players"] for entry in daily_history]
    else:
        return None

    fig, ax = plt.subplots(figsize=(10, 3))
    fig.patch.set_facecolor('#2b2d31')
    ax.set_facecolor('#2b2d31')

    ax.plot(dates, players, color='#ED4245', linewidth=2.5, marker='o', markersize=5)
    ax.fill_between(dates, players, alpha=0.2, color='#ED4245')

    ax.set_ylabel('Players', color='white', fontsize=11)
    ax.tick_params(colors='white', labelsize=9)
    ax.spines['bottom'].set_color('#4a4a4a')
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_color('#4a4a4a')
    ax.spines['right'].set_visible(False)

    ax.grid(True, alpha=0.15, color='white', axis='y')

    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, facecolor='#2b2d31')
    buf.seek(0)
    plt.close(fig)
    return buf


class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats_data = load_stats_data()
        self.track_players.start()
        self.daily_snapshot.start()

    def cog_unload(self):
        self.track_players.cancel()
        self.daily_snapshot.cancel()

    async def fetch_server_data(self):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"https://api.mcsrvstat.us/3/{ARCHMC_IP}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        motd_lines = data.get("motd", {}).get("clean", [])
                        data["_motd"] = motd_lines[1] if len(motd_lines) > 1 else (motd_lines[0] if motd_lines else "")
                        return data
        except Exception as e:
            logger.error(f"Failed to fetch server data: {e}")
        return None

    @tasks.loop(minutes=5)
    async def track_players(self):
        data = await self.fetch_server_data()
        if not data or not data.get("online"):
            return

        current = data.get("players", {}).get("online", 0)
        now = datetime.utcnow()

        if current > self.stats_data["peak_alltime"]:
            self.stats_data["peak_alltime"] = current

        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        self.stats_data["hourly_history"] = [
            entry for entry in self.stats_data["hourly_history"]
            if entry["timestamp"] > cutoff_24h
        ]
        self.stats_data["hourly_history"].append({
            "timestamp": now.isoformat(),
            "players": current
        })

        if self.stats_data["hourly_history"]:
            self.stats_data["peak_24h"] = max(e["players"] for e in self.stats_data["hourly_history"])

        save_stats_data(self.stats_data)

    @track_players.before_loop
    async def before_track(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=datetime.strptime("00:00", "%H:%M").time())
    async def daily_snapshot(self):
        data = await self.fetch_server_data()
        if not data:
            return

        current = data.get("players", {}).get("online", 0) if data.get("online") else 0
        today = datetime.utcnow().date().isoformat()

        self.stats_data["daily_history"] = [
            entry for entry in self.stats_data["daily_history"]
            if entry["date"] != today
        ]
        self.stats_data["daily_history"].append({
            "date": today,
            "players": current
        })

        self.stats_data["daily_history"] = self.stats_data["daily_history"][-30:]

        save_stats_data(self.stats_data)

    @daily_snapshot.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    @discord.slash_command(
        name="stats",
        description="Show ArchMC server stats with player graph"
    )
    async def stats(self, ctx: discord.ApplicationContext):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return

        await ctx.defer()

        try:
            data = await self.fetch_server_data()

            if data and data.get("online"):
                current = data.get("players", {}).get("online", 0)
                max_players = data.get("players", {}).get("max", 0)
                version = data.get("version", "Unknown")
                is_online = True

                if current > self.stats_data["peak_alltime"]:
                    self.stats_data["peak_alltime"] = current
                    save_stats_data(self.stats_data)
            else:
                current = 0
                max_players = 0
                version = "Unknown"
                is_online = False

            peak_24h = self.stats_data.get("peak_24h", 0)
            peak_alltime = self.stats_data.get("peak_alltime", 0)

            embed = discord.Embed(color=0xED4245)
            embed.set_author(name="ArchMC Server Stats", icon_url=ARCHMC_LOGO)

            embed.add_field(name="Status", value="🟢 Online" if is_online else "🔴 Offline", inline=True)
            embed.add_field(name="Players", value=f"**{current:,}** / {max_players:,}", inline=True)
            embed.add_field(name="Version", value=version, inline=True)
            embed.add_field(name="24h Peak", value=f"**{peak_24h:,}**" if peak_24h else "**--**", inline=True)
            embed.add_field(name="All-Time Peak", value=f"**{peak_alltime:,}**" if peak_alltime else "**--**", inline=True)
            embed.add_field(name="IP", value="`play.arch.mc`", inline=True)

            embed.set_footer(text="ArchMC", icon_url=ARCHMC_LOGO)

            files = []
            daily = self.stats_data.get("daily_history", [])
            hourly = self.stats_data.get("hourly_history", [])
            graph = generate_player_graph(daily, hourly)
            if graph:
                file = discord.File(graph, filename="player_history.png")
                embed.set_image(url="attachment://player_history.png")
                files.append(file)
            else:
                embed.set_image(url=ARCHMC_BANNER)

            if files:
                await ctx.respond(embed=embed, files=files)
            else:
                await ctx.respond(embed=embed)

        except Exception as e:
            logger.error(f"stats error: {e}")
            await log_error_to_channel(self.bot, "stats", ctx.author, ctx.guild, e)
            await ctx.respond("Failed to fetch server stats. Please try again later.")


def setup(bot):
    bot.add_cog(StatsCog(bot))
