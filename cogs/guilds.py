import discord
from discord.ext import commands
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked
from utils.api_client import get_api_client

logger = logging.getLogger('archie-bot')


class GuildsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        name="guild",
        description="Show what guild a player is in",
        options=[
            discord.Option(
                str,
                "Minecraft username",
                required=True,
                name="username"
            )
        ]
    )
    async def guild(self, ctx: discord.ApplicationContext, username: str):
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
            client = get_api_client()
            data = await client.get(f"/v1/guilds/player/username/{safe_username}")
            if data and isinstance(data, dict):
                guild_name = data.get("displayName") or data.get("name") or "Unknown"
                level = data.get("level", 0)
                if isinstance(level, float):
                    level = int(level)
                leader = data.get("leaderUsername", "Unknown")
                members = data.get("memberCount", 0)
                description = data.get("description", "No description")
                
                embed = discord.Embed(
                    title=f"🏰 {guild_name}",
                    description=description[:200] if description else "No description",
                    color=discord.Color.purple()
                )
                embed.add_field(name="Level", value=f"`{level}`", inline=True)
                embed.add_field(name="Leader", value=f"`{leader}`", inline=True)
                embed.add_field(name="Members", value=f"`{members}`", inline=True)
                embed.set_footer(text=f"Guild of {safe_username} • ArchMC")
                await ctx.respond(embed=embed)
            else:
                await ctx.respond(f"**{safe_username}** is not in a guild.")
        except Exception as e:
            logger.error(f"guild error: {e}")
            await ctx.respond("Failed to fetch guild info. Please try again later.")

    @discord.slash_command(
        name="guildsearch",
        description="Search for guilds by name",
        options=[
            discord.Option(
                str,
                "Guild name to search",
                required=True,
                name="query"
            )
        ]
    )
    async def guildsearch(self, ctx: discord.ApplicationContext, query: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        safe_query = query.strip()[:50]
        if not safe_query or len(safe_query) < 2:
            await ctx.respond("Search query must be at least 2 characters.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            data = await client.get(f"/v1/guilds/search/name?q={safe_query}")
            if data and isinstance(data, dict):
                guilds = data.get("guilds") or data.get("results") or []
                if isinstance(guilds, list) and guilds:
                    lines = []
                    for i, g in enumerate(guilds[:10]):
                        name = g.get("displayName") or g.get("name") or "Unknown"
                        level = g.get("level", 0)
                        members = g.get("memberCount", 0)
                        lines.append(f"**{name}** — Level {int(level)} | {members} members")
                    
                    embed = discord.Embed(
                        title=f"🔍 Guild Search: {safe_query}",
                        description="\n".join(lines),
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text=f"Found {len(guilds)} guild(s) • ArchMC")
                    await ctx.respond(embed=embed)
                else:
                    await ctx.respond(f"No guilds found matching **{safe_query}**.")
            else:
                await ctx.respond(f"No guilds found matching **{safe_query}**.")
        except Exception as e:
            logger.error(f"guildsearch error: {e}")
            await ctx.respond("Failed to search guilds. Please try again later.")


def setup(bot):
    bot.add_cog(GuildsCog(bot))
