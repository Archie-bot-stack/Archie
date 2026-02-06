import discord
from discord.ext import commands
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked, contains_mention
from utils.api_client import get_api_client
from utils.error_logging import log_error_to_channel

logger = logging.getLogger('archie-bot')


class DuelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        name="dueltop",
        description="Show the top players for a selected Duel stat",
        options=[
            discord.Option(
                str,
                "Select the duel stat",
                choices=[
                    "elo:nodebuff:ranked:lifetime",
                    "elo:sumo:ranked:lifetime",
                    "elo:bridge:ranked:lifetime",
                    "wins:nodebuff:ranked:lifetime",
                    "wins:sumo:ranked:lifetime",
                    "wins:bridge:ranked:lifetime"
                ],
                required=True,
                name="statid"
            )
        ]
    )
    async def dueltop(self, ctx: discord.ApplicationContext, statid: str):
        if check_cooldown(ctx.author.id):
            await ctx.respond("Please wait a few seconds before using commands again.", ephemeral=True)
            return
        
        await ctx.defer()
        try:
            client = get_api_client()
            data = await client.get(f"/v1/leaderboards/{statid}?page=0&size=10")
            if data and isinstance(data, dict):
                entries = data.get("entries") or data.get("leaderboard") or []
                if isinstance(entries, list) and entries:
                    leaderboard_lines = [
                        f"**#{entry.get('position', i+1)}** {entry.get('username', 'Unknown')} — `{entry.get('value', 0)}`"
                        for i, entry in enumerate(entries)
                    ]
                    leaderboard_text = "\n".join(leaderboard_lines)
                    embed = discord.Embed(
                        title=f"🥊 Duel Top: {statid}",
                        description=leaderboard_text,
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text="ArchMC Duels • Official API")
                    await ctx.respond(embed=embed)
                else:
                    await ctx.respond("No duel leaderboard data found.")
            else:
                await ctx.respond("No duel leaderboard data found.")
        except Exception as e:
            logger.error(f"dueltop error: {e}")
            await log_error_to_channel(self.bot, "dueltop", ctx.author, ctx.guild, e, {"statid": statid})
            await ctx.respond("Failed to fetch duel leaderboard. Please try again later.")



def setup(bot):
    bot.add_cog(DuelsCog(bot))
