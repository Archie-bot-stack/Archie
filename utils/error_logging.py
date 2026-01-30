import discord
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger('archie-bot')

ERROR_LOG_CHANNEL_ID = 1454137711710703785

async def log_error_to_channel(bot, command: str, user, guild, error, extra=None):
    try:
        channel = bot.get_channel(ERROR_LOG_CHANNEL_ID)
        if not channel:
            channel = await bot.fetch_channel(ERROR_LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="⚠️ Command Error",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Command", value=f"`/{command}`", inline=True)
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Guild", value=f"{guild.name} ({guild.id})" if guild else "DM", inline=True)
            embed.add_field(name="Error", value=f"```{type(error).__name__}: {str(error)[:500]}```", inline=False)
            if extra:
                for k, v in extra.items():
                    embed.add_field(name=k, value=f"`{v}`", inline=True)
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to log error to channel: {e}")
