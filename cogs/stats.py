import discord
from discord.ext import commands
import asyncio
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked, contains_mention
from utils.api_client import get_api_client, fetch_player_head
from utils.error_logging import log_error_to_channel
from cards import (
    generate_lifestats_card,
    generate_duelstats_card,
    generate_skywarsstats_card,
)

logger = logging.getLogger('archie-bot')


class StatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        name="stat",
        description="Show player stats card for any gamemode",
        options=[
            discord.Option(
                str,
                "Select the gamemode",
                choices=["lifesteal", "duels", "skywars"],
                required=True,
                name="mode"
            ),
            discord.Option(
                str,
                "Minecraft username",
                required=True,
                name="username"
            ),
        ]
    )
    async def stat(self, ctx: discord.ApplicationContext, mode: str, username: str):
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
            if mode == "lifesteal":
                await self._lifesteal_card(ctx, safe_username)
            elif mode == "duels":
                await self._duels_card(ctx, safe_username)
            elif mode == "skywars":
                await self._skywars_card(ctx, safe_username)
        except Exception as e:
            logger.error(f"stat error ({mode}): {e}")
            await log_error_to_channel(self.bot, "stat", ctx.author, ctx.guild, e, {"mode": mode, "username": safe_username})
            await ctx.respond("Failed to fetch stats. Please try again later.")

    async def _lifesteal_card(self, ctx, username):
        client = get_api_client()
        stats, profile = await asyncio.gather(
            client.get(f"/v1/ugc/trojan/players/username/{username}/statistics"),
            client.get(f"/v1/ugc/trojan/players/username/{username}/profile"),
            return_exceptions=True
        )

        if isinstance(stats, Exception):
            stats = None
        if isinstance(profile, Exception):
            profile = None

        if not stats or not isinstance(stats, dict):
            await ctx.respond("No stats found for that player.")
            return

        username_disp = stats.get("username", username)
        uuid = stats.get("uuid", "")
        statistics = stats.get("statistics", {})

        head_data = await fetch_player_head(uuid)

        loop = asyncio.get_event_loop()
        card = await loop.run_in_executor(
            None,
            generate_lifestats_card,
            username_disp, uuid, statistics, profile or {}, head_data
        )
        file = discord.File(card, filename="lifestats.png")
        await ctx.respond(file=file)

    async def _duels_card(self, ctx, username):
        client = get_api_client()
        data = await client.get(f"/v1/players/username/{username}/statistics")

        if not data or not isinstance(data, dict):
            await ctx.respond("No duel stats found for that player.")
            return

        username_disp = data.get("username", username)
        uuid = data.get("uuid", "")
        statistics = data.get("statistics", {})

        head_data = await fetch_player_head(uuid) if uuid else None

        loop = asyncio.get_event_loop()
        card = await loop.run_in_executor(
            None,
            generate_duelstats_card,
            username_disp, uuid, statistics, head_data
        )
        file = discord.File(card, filename="duelstats.png")
        await ctx.respond(file=file)

    async def _skywars_card(self, ctx, username):
        client = get_api_client()
        data = await client.get(f"/v1/players/username/{username}/statistics")

        if not data or not isinstance(data, dict):
            await ctx.respond("No SkyWars stats found for that player.")
            return

        username_disp = data.get("username", username)
        uuid = data.get("uuid", "")
        statistics = data.get("statistics", {})

        head_data = await fetch_player_head(uuid) if uuid else None

        loop = asyncio.get_event_loop()
        card = await loop.run_in_executor(
            None,
            generate_skywarsstats_card,
            username_disp, uuid, statistics, head_data
        )
        file = discord.File(card, filename="skywarsstats.png")
        await ctx.respond(file=file)


def setup(bot):
    bot.add_cog(StatCog(bot))
