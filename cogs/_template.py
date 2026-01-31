"""
Template for creating new cogs/commands.

To add a new cog:
1. Copy this file and rename it (e.g., my_commands.py)
2. Rename the class (e.g., MyCog)
3. Add your commands
4. Add 'cogs.my_commands' to the cogs list in bot.py
"""

import discord
from discord.ext import commands
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked
from utils.api_client import get_api_client
from utils.error_logging import log_error_to_channel

logger = logging.getLogger('archie-bot')


class TemplateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === SIMPLE COMMAND (no options) ===
    @discord.slash_command(
        name="example",
        description="A simple example command"
    )
    async def example(self, ctx: discord.ApplicationContext):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds.", ephemeral=True)
            return
        
        await ctx.respond("Hello from example command!")

    # === COMMAND WITH REQUIRED OPTION ===
    @discord.slash_command(
        name="greet",
        description="Greet a player",
        options=[
            discord.Option(
                str,
                "Minecraft username",
                required=True,
                name="username"
            )
        ]
    )
    async def greet(self, ctx: discord.ApplicationContext, username: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds.", ephemeral=True)
            return
        
        safe_username = sanitize_username(username)
        if not safe_username:
            await ctx.respond("Invalid username.", ephemeral=True)
            return
        if is_username_blocked(safe_username):
            await ctx.respond("That username cannot be looked up.", ephemeral=True)
            return
        
        await ctx.respond(f"Hello, **{safe_username}**!")

    # === COMMAND WITH CHOICES ===
    @discord.slash_command(
        name="pick",
        description="Pick a gamemode",
        options=[
            discord.Option(
                str,
                "Select a gamemode",
                choices=["lifesteal", "duels", "bedwars", "skywars"],
                required=True,
                name="gamemode"
            )
        ]
    )
    async def pick(self, ctx: discord.ApplicationContext, gamemode: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds.", ephemeral=True)
            return
        
        await ctx.respond(f"You picked **{gamemode}**!")

    # === COMMAND WITH API CALL ===
    @discord.slash_command(
        name="apicall",
        description="Example API call",
        options=[
            discord.Option(
                str,
                "Minecraft username",
                required=True,
                name="username"
            )
        ]
    )
    async def apicall(self, ctx: discord.ApplicationContext, username: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds.", ephemeral=True)
            return
        
        safe_username = sanitize_username(username)
        if not safe_username:
            await ctx.respond("Invalid username.", ephemeral=True)
            return
        
        await ctx.defer()  # Use defer for API calls that take time
        
        try:
            client = get_api_client()
            data = await client.get(f"/v1/players/username/{safe_username}")
            
            if data:
                embed = discord.Embed(
                    title=f"Data for {safe_username}",
                    description=f"UUID: `{data.get('uuid', 'N/A')}`",
                    color=discord.Color.green()
                )
                await ctx.respond(embed=embed)
            else:
                await ctx.respond(f"No data found for **{safe_username}**.")
        except Exception as e:
            logger.error(f"apicall error: {e}")
            await log_error_to_channel(self.bot, "apicall", ctx.author, ctx.guild, e)
            await ctx.respond("Failed to fetch data. Please try again later.")

    # === COMMAND WITH OPTIONAL PARAMETER ===
    @discord.slash_command(
        name="info",
        description="Get info with optional detail level",
        options=[
            discord.Option(
                str,
                "Username",
                required=True,
                name="username"
            ),
            discord.Option(
                bool,
                "Show detailed info",
                required=False,
                default=False,
                name="detailed"
            )
        ]
    )
    async def info(self, ctx: discord.ApplicationContext, username: str, detailed: bool = False):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds.", ephemeral=True)
            return
        
        if detailed:
            await ctx.respond(f"Detailed info for **{username}**...")
        else:
            await ctx.respond(f"Basic info for **{username}**")


def setup(bot):
    bot.add_cog(TemplateCog(bot))
