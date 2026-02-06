import discord
from discord.ext import commands
import asyncio
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked, contains_mention
from utils.api_client import get_api_client
from utils.error_logging import log_error_to_channel

logger = logging.getLogger('archie-bot')


def stat_to_embed(stat: dict, stat_name: str, username: str) -> discord.Embed:
    stat_emojis = {
        "kills": "⚔️",
        "deaths": "💀",
        "killstreak": "🔥",
        "killDeathRatio": "📊",
        "blocksMined": "⛏️",
        "blocksWalked": "🚶",
        "blocksPlaced": "🧱"
    }
    emoji = stat_emojis.get(stat_name, "📈")
    value = stat.get("value", stat.get("statValue", 0))
    position = stat.get("position")
    percentile = stat.get("percentile")
    total_players = stat.get("totalPlayers")
    embed = discord.Embed(
        title=f"{emoji} {stat_name.capitalize()} — {username}",
        description=f"**{value}**",
        color=discord.Color.red()
    )
    if position is not None:
        embed.add_field(name="Rank", value=f"`#{position:,}`", inline=True)
    if percentile is not None:
        embed.add_field(name="Percentile", value=f"Top {100 - float(percentile):.2f}%", inline=True)
    if total_players is not None:
        embed.add_field(name="Total Players", value=f"`{int(total_players):,}`", inline=True)
    embed.set_footer(text="ArchMC Lifesteal • Official API")
    return embed


class LifestealCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        name="lifetop",
        description="Show the top players for a selected Lifesteal stat",
        options=[
            discord.Option(
                str,
                "Select the statistic",
                choices=["kills", "deaths", "killstreak", "killDeathRatio", "blocksMined", "blocksWalked", "blocksPlaced"],
                required=True,
                name="stat"
            )
        ]
    )
    async def lifetop(self, ctx: discord.ApplicationContext, stat: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            leaderboard = await client.get_ugc_leaderboard("trojan", stat)
            if leaderboard and "entries" in leaderboard:
                leaderboard_lines = [
                    f"**#{entry.get('position', i+1)}** {entry.get('username', 'Unknown')} — `{entry.get('value', 0)}`"
                    for i, entry in enumerate(leaderboard["entries"])
                ]
                leaderboard_text = "\n".join(leaderboard_lines)
                embed = discord.Embed(
                    title=f"🏆 Lifesteal Top {stat.capitalize()}",
                    description=leaderboard_text,
                    color=discord.Color.red()
                )
                embed.set_footer(text="ArchMC Lifesteal • Official API")
                await ctx.respond(embed=embed)
            else:
                await ctx.respond("No leaderboard data found.")
        except Exception as e:
            logger.error(f"lifetop error: {e}")
            await log_error_to_channel(self.bot, "lifetop", ctx.author, ctx.guild, e, {"stat": stat})
            await ctx.respond("Failed to fetch leaderboard. Please try again later.")

    @discord.slash_command(
        name="lifestat",
        description="Show a specific Lifesteal stat for a player",
        options=[
            discord.Option(
                str,
                "Minecraft username",
                required=True,
                name="username"
            ),
            discord.Option(
                str,
                "Select the statistic",
                choices=["kills", "deaths", "killstreak", "killDeathRatio", "blocksMined", "blocksWalked", "blocksPlaced"],
                required=True,
                name="stat"
            )
        ]
    )
    async def lifestat(self, ctx: discord.ApplicationContext, username: str, stat: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        if contains_mention(username):
            await ctx.respond("Please enter a valid Minecraft username, not a Discord mention.", ephemeral=True)
            return
        
        safe_username = sanitize_username(username)
        if not safe_username:
            await ctx.respond("Invalid username. Minecraft usernames can only contain letters, numbers, and underscores (1-16 characters).", ephemeral=True)
            return
        if is_username_blocked(safe_username):
            await ctx.respond("That username cannot be looked up.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            stat_info = await client.get(f"/v1/ugc/trojan/players/username/{safe_username}/statistics/{stat}")
            if stat_info and isinstance(stat_info, dict) and "value" in stat_info:
                embed = stat_to_embed(stat_info, stat, safe_username)
                await ctx.respond(embed=embed)
            else:
                stats = await client.get_ugc_player_stats_by_username("trojan", safe_username)
                stat_val = stats["statistics"].get(stat) if stats and "statistics" in stats and stat in stats["statistics"] else None
                if stat_val is not None:
                    if not isinstance(stat_val, dict):
                        stat_val = {"value": stat_val}
                    embed = stat_to_embed(stat_val, stat, safe_username)
                    await ctx.respond(embed=embed)
                else:
                    await ctx.respond("No data found for that player/stat.")
        except Exception as e:
            logger.error(f"lifestat error: {e}")
            await log_error_to_channel(self.bot, "lifestat", ctx.author, ctx.guild, e, {"username": safe_username, "stat": stat})
            await ctx.respond("Failed to fetch stat. Please try again later.")

    @discord.slash_command(name="clantop", description="Show the top clans from ArchMC")
    async def clantop(self, ctx: discord.ApplicationContext):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            data = await client.get("/v1/ugc/trojan/clans?page=0&size=10")
            if data and isinstance(data, dict):
                clans = data.get("clans") or data.get("entries") or data.get("leaderboard") or []
                if isinstance(clans, list) and clans:
                    leaderboard_lines = []
                    for i, clan in enumerate(clans):
                        name = clan.get("displayName") or clan.get("name") or clan.get("clanName") or "Unknown"
                        level = clan.get("level", 0)
                        if isinstance(level, float):
                            level = int(level)
                        leader = clan.get("leaderUsername", "Unknown")
                        members = clan.get("memberCount", 0)
                        leaderboard_lines.append(f"**#{i+1} {name}** — Level {level} | Leader: {leader} | Members: {members}")
                    leaderboard_text = "\n".join(leaderboard_lines)
                    embed = discord.Embed(
                        title="🏅 Top Clans",
                        description=leaderboard_text,
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text="ArchMC Clans • Official API")
                    await ctx.respond(embed=embed)
                else:
                    await ctx.respond("No clan leaderboard data found.")
            else:
                await ctx.respond("No clan leaderboard data found.")
        except Exception as e:
            logger.error(f"clantop error: {e}")
            await log_error_to_channel(self.bot, "clantop", ctx.author, ctx.guild, e)
            await ctx.respond("Failed to fetch clan leaderboard. Please try again later.")


def setup(bot):
    bot.add_cog(LifestealCog(bot))
