import discord
from discord.ext import commands
import asyncio
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked, contains_mention
from utils.api_client import get_api_client

logger = logging.getLogger('archie-bot')


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        name="compare",
        description="Compare two players' stats side by side",
        options=[
            discord.Option(
                str,
                "First player username",
                required=True,
                name="player1"
            ),
            discord.Option(
                str,
                "Second player username",
                required=True,
                name="player2"
            ),
            discord.Option(
                str,
                "Game mode to compare",
                choices=["lifesteal", "duels"],
                required=True,
                name="mode"
            )
        ]
    )
    async def compare(self, ctx: discord.ApplicationContext, player1: str, player2: str, mode: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        if contains_mention(player1) or contains_mention(player2):
            await ctx.respond("Please enter valid Minecraft usernames, not Discord mentions.", ephemeral=True)
            return
        
        p1 = sanitize_username(player1)
        p2 = sanitize_username(player2)
        if not p1 or not p2:
            await ctx.respond("Invalid username(s). Minecraft usernames can only contain letters, numbers, and underscores (1-16 characters).", ephemeral=True)
            return
        if is_username_blocked(p1) or is_username_blocked(p2):
            await ctx.respond("One of those usernames cannot be looked up.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            
            if mode == "lifesteal":
                stats1, stats2 = await asyncio.gather(
                    client.get(f"/v1/ugc/trojan/players/username/{p1}/statistics"),
                    client.get(f"/v1/ugc/trojan/players/username/{p2}/statistics"),
                    return_exceptions=True
                )
                
                if isinstance(stats1, Exception) or not stats1:
                    await ctx.respond(f"Could not find stats for **{p1}**.")
                    return
                if isinstance(stats2, Exception) or not stats2:
                    await ctx.respond(f"Could not find stats for **{p2}**.")
                    return
                
                s1 = stats1.get("statistics", {})
                s2 = stats2.get("statistics", {})
                
                def get_val(s, key):
                    stat = s.get(key, {})
                    return stat.get("value", 0) if isinstance(stat, dict) else (stat or 0)
                
                embed = discord.Embed(
                    title=f"⚔️ Lifesteal Compare",
                    description=f"**{p1}** vs **{p2}**",
                    color=discord.Color.red()
                )
                
                stats_to_compare = [
                    ("Kills", "kills"),
                    ("Deaths", "deaths"),
                    ("K/D", "killDeathRatio"),
                    ("Best Streak", "killstreak"),
                ]
                
                for label, key in stats_to_compare:
                    v1 = get_val(s1, key)
                    v2 = get_val(s2, key)
                    if v1 > v2:
                        line = f"**{v1}** vs {v2}"
                    elif v2 > v1:
                        line = f"{v1} vs **{v2}**"
                    else:
                        line = f"{v1} vs {v2}"
                    embed.add_field(name=label, value=line, inline=True)
                
                embed.set_footer(text="ArchMC Lifesteal • Bold = higher")
                await ctx.respond(embed=embed)
            
            else:
                stats1, stats2 = await asyncio.gather(
                    client.get(f"/v1/players/username/{p1}/statistics"),
                    client.get(f"/v1/players/username/{p2}/statistics"),
                    return_exceptions=True
                )
                
                if isinstance(stats1, Exception) or not stats1:
                    await ctx.respond(f"Could not find stats for **{p1}**.")
                    return
                if isinstance(stats2, Exception) or not stats2:
                    await ctx.respond(f"Could not find stats for **{p2}**.")
                    return
                
                s1 = stats1.get("statistics", {})
                s2 = stats2.get("statistics", {})
                
                def get_val(s, key):
                    stat = s.get(key, {})
                    return stat.get("value", 0) if isinstance(stat, dict) else (stat or 0)
                
                embed = discord.Embed(
                    title=f"🥊 Duels Compare",
                    description=f"**{p1}** vs **{p2}**",
                    color=discord.Color.blue()
                )
                
                duel_stats = [
                    ("NoDebuff ELO", "elo:nodebuff:ranked:lifetime"),
                    ("Sumo ELO", "elo:sumo:ranked:lifetime"),
                    ("Bridge ELO", "elo:bridge:ranked:lifetime"),
                    ("NoDebuff Wins", "wins:nodebuff:ranked:lifetime"),
                ]
                
                for label, key in duel_stats:
                    v1 = get_val(s1, key)
                    v2 = get_val(s2, key)
                    if v1 > v2:
                        line = f"**{v1}** vs {v2}"
                    elif v2 > v1:
                        line = f"{v1} vs **{v2}**"
                    else:
                        line = f"{v1} vs {v2}"
                    embed.add_field(name=label, value=line, inline=True)
                
                embed.set_footer(text="ArchMC Duels • Bold = higher")
                await ctx.respond(embed=embed)
                
        except Exception as e:
            logger.error(f"compare error: {e}")
            await ctx.respond("Failed to compare players. Please try again later.")

    @discord.slash_command(name="invite", description="Get the invite link for Archie")
    async def invite(self, ctx: discord.ApplicationContext):
        invite_url = (
            "https://discord.com/oauth2/authorize"
            "?client_id=1454187186651009116"
            "&permissions=6144"
            "&scope=bot%20applications.commands"
        )
        support_url = "https://discord.gg/pzSYrhBCA5"
        embed = discord.Embed(
            title="Invite Archie to your server!",
            description=(
                f"➕ [Click here to invite Archie]({invite_url})\n"
                f"💬 [Join the support server]({support_url})\n\n"
                "Add Archie to your server and join our support community for help and updates."
            ),
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Thank you for supporting Archie!")
        await ctx.respond(embed=embed)

    @discord.slash_command(name="help", description="Show help for Archie commands")
    async def help(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="Archie Help",
            description="**Here are all available commands:**",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="/playtime",
            value="⏱️ Show the playtime leaderboard for Lifesteal or Survival.",
            inline=False
        )
        embed.add_field(
            name="/stats",
            value="Show stats of the server.",
            inline=False
        )
        embed.add_field(
            name="/lifetop",
            value="🏆 Show the top players for a selected Lifesteal stat.",
            inline=False
        )
        embed.add_field(
            name="/stat",
            value="🎴 Show a player stats card — Lifesteal, Duels, SkyWars, or a specific Duel Kit.",
            inline=False
        )
        embed.add_field(
            name="/lifestat",
            value="📈 Show a specific Lifesteal stat for a player, with value, rank, and percentile.",
            inline=False
        )
        embed.add_field(
            name="/dueltop",
            value="🥊 Show the top players for a selected Duel stat (ELO or Wins).",
            inline=False
        )
        embed.add_field(
            name="/balance",
            value="💰 Show a player's balance for a selected gamemode.",
            inline=False
        )
        embed.add_field(
            name="/baltop",
            value="🏦 Show the baltop leaderboard for a selected currency or experience type.",
            inline=False
        )
        embed.add_field(
            name="/clantop",
            value="🏅 Show the top clans from ArchMC.",
            inline=False
        )
        embed.add_field(
            name="/guild",
            value="🏰 Show what guild a player is in.",
            inline=False
        )
        embed.add_field(
            name="/guildsearch",
            value="🔍 Search for guilds by name.",
            inline=False
        )
        embed.add_field(
            name="/compare",
            value="⚔️ Compare two players' stats (Lifesteal or Duels).",
            inline=False
        )
        embed.add_field(
            name="/invite",
            value="➕ Get the invite link for Archie and the support server.",
            inline=False
        )
        embed.set_footer(text="More commands and features coming soon! | Archie by ArchMC")
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(UtilityCog(bot))
