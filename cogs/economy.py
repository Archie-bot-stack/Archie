import discord
from discord.ext import commands
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked
from utils.api_client import get_api_client
from utils.error_logging import log_error_to_channel

logger = logging.getLogger('archie-bot')


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        name="balance",
        description="Show a player's balance for a selected gamemode",
        options=[
            discord.Option(
                str,
                "Select the gamemode",
                choices=["lifesteal", "survival", "bedwars", "kitpvp", "skywars"],
                required=True,
                name="gamemode"
            ),
            discord.Option(
                str,
                "Minecraft username",
                required=True,
                name="username"
            )
        ]
    )
    async def balance(self, ctx: discord.ApplicationContext, gamemode: str, username: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        safe_username = sanitize_username(username)
        if not safe_username:
            await ctx.respond("Invalid username.", ephemeral=True)
            return
        if is_username_blocked(safe_username):
            await ctx.respond("That username cannot be looked up.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            type_map = {
                "lifesteal": "lifesteal-coins",
                "survival": "gems",
                "bedwars": "bedwars-coins",
                "kitpvp": "kitpvp-coins",
                "skywars": "skywars-coins"
            }
            bal_type = type_map.get(gamemode)
            if not bal_type:
                await ctx.respond("Invalid gamemode selected.")
                return
            
            client = get_api_client()
            data = await client.get(f"/v1/economy/player/username/{safe_username}")
            
            if data and isinstance(data, dict):
                balances = data.get("balances", {})
                if not balances:
                    await ctx.respond(f"No balance data found for {safe_username}.")
                    return
                if bal_type in balances:
                    bal = balances[bal_type]
                    embed = discord.Embed(
                        title=f"💰 {gamemode.capitalize()} Balance for {safe_username}",
                        description=f"**{bal:,}**",
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text=f"ArchMC {gamemode.capitalize()} • Official API")
                    await ctx.respond(embed=embed)
                else:
                    bal_lines = [f"**{k.replace('-', ' ').title()}**: `{v:,}`" for k, v in balances.items()]
                    embed = discord.Embed(
                        title=f"💰 All Balances for {safe_username}",
                        description="\n".join(bal_lines),
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text="ArchMC Economy • Official API")
                    await ctx.respond(embed=embed)
            else:
                await ctx.respond(f"No balance profile found for **{safe_username}**.")
        except Exception as e:
            logger.error(f"balance error: {e}")
            await log_error_to_channel(self.bot, "balance", ctx.author, ctx.guild, e, {"username": safe_username, "gamemode": gamemode})
            await ctx.respond("Failed to fetch balance. Please try again later.")

    @discord.slash_command(
        name="baltop",
        description="Show the baltop leaderboard for a selected type",
        options=[
            discord.Option(
                str,
                "Select the baltop type",
                choices=[
                    "lifesteal-coins",
                    "bedwars-coins",
                    "kitpvp-coins",
                    "gems",
                    "bedwars-experience",
                    "skywars-coins",
                    "skywars-experience"
                ],
                required=True,
                name="type"
            )
        ]
    )
    async def baltop(self, ctx: discord.ApplicationContext, type: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            data = await client.get(f"/v1/economy/baltop/{type}")
            if data and isinstance(data, dict):
                entries = data.get("entries") or []
                if isinstance(entries, list) and entries:
                    leaderboard_lines = [
                        f"**#{entry.get('position', i+1)}** {entry.get('username', 'Unknown')} — `{entry.get('balance', 0)}`"
                        for i, entry in enumerate(entries)
                    ]
                    leaderboard_text = "\n".join(leaderboard_lines)
                    embed = discord.Embed(
                        title=f"🏦 Baltop Leaderboard: {type.replace('-', ' ').title()}",
                        description=leaderboard_text,
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text="ArchMC Baltop • Official API")
                    await ctx.respond(embed=embed)
                else:
                    await ctx.respond("No baltop data found for that type.")
            else:
                await ctx.respond("No baltop data found for that type.")
        except Exception as e:
            logger.error(f"baltop error: {e}")
            await log_error_to_channel(self.bot, "baltop", ctx.author, ctx.guild, e, {"type": type})
            await ctx.respond("Failed to fetch baltop leaderboard. Please try again later.")

    @discord.slash_command(
        name="playtime",
        description="Show the playtime leaderboard for a selected mode",
        options=[
            discord.Option(
                str,
                "Select the server mode",
                choices=["lifesteal", "survival"],
                required=True,
                name="mode"
            )
        ]
    )
    async def playtime(self, ctx: discord.ApplicationContext, mode: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            gamemode = "trojan" if mode == "lifesteal" else "spartan"
            leaderboard = await client.get(f"/v1/ugc/{gamemode}/leaderboard/playtime?page=0&size=10")
            entries = leaderboard.get("entries") or leaderboard.get("players") or leaderboard.get("leaderboard") or []
            if isinstance(entries, list) and entries:
                leaderboard_lines = []
                for i, entry in enumerate(entries):
                    username = entry.get("username") or entry.get("name") or "Unknown"
                    playtime_ms = entry.get("playtimeSeconds") or 0
                    playtime_hours = int(playtime_ms // 1000 // 3600)
                    leaderboard_lines.append(f"**#{entry.get('position', i+1)}** {username} — `{playtime_hours} hours`")
                leaderboard_text = "\n".join(leaderboard_lines)
                color = discord.Color.red() if mode == "lifesteal" else discord.Color.green()
                embed = discord.Embed(
                    title=f"⏱️ {mode.capitalize()} Playtime Top",
                    description=leaderboard_text,
                    color=color
                )
                embed.set_footer(text=f"ArchMC {mode.capitalize()} • Official API")
                await ctx.respond(embed=embed)
            else:
                await ctx.respond("No leaderboard data found.")
        except Exception as e:
            logger.error(f"playtime error: {e}")
            await log_error_to_channel(self.bot, "playtime", ctx.author, ctx.guild, e, {"mode": mode})
            await ctx.respond("Failed to fetch playtime leaderboard. Please try again later.")


def setup(bot):
    bot.add_cog(EconomyCog(bot))
