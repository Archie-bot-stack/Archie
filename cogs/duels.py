import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import logging

from utils.security import check_cooldown, sanitize_username, is_username_blocked
from utils.api_client import get_api_client, fetch_player_head
from utils.error_logging import log_error_to_channel
from cards import generate_duelstats_card

logger = logging.getLogger('archie-bot')


def build_duelstats_embed(data, username, mode_stats, mode_labels, mode_keys, page, page_size):
    modes_per_page = 4
    start = page * modes_per_page
    end = start + modes_per_page
    shown_modes = mode_keys[start:end]
    embed = discord.Embed(
        title=f"Archie — 🥊 Duel Stats for {data.get('username', username)}",
        color=discord.Color.purple(),
        description=f"Page {page+1} of {((len(mode_keys)-1)//modes_per_page)+1}"
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/icons/1454187186651009116/3e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e.png?size=128")
    for mode in shown_modes:
        emoji, label = mode_labels.get(mode, ("❓", mode.capitalize()))
        for context, v in mode_stats[mode]["ELO"]:
            value = v.get("value", 0) if isinstance(v, dict) and "value" in v else v
            context_str = f" ({context})" if context else ""
            stat_name = f"{emoji} {label} ELO{context_str}" if context_str else f"{emoji} {label} ELO"
            embed.add_field(name=stat_name, value=f"`{value}`", inline=True)
        for context, v in mode_stats[mode]["WINS"]:
            value = v.get("value", 0) if isinstance(v, dict) and "value" in v else v
            context_str = f" ({context})" if context else ""
            stat_name = f"{emoji} {label} Wins{context_str}" if context_str else f"{emoji} {label} Wins"
            embed.add_field(name=stat_name, value=f"`{value}`", inline=True)
        for stat_type in mode_stats[mode]:
            if stat_type in ("ELO", "WINS"): continue
            for context, v in mode_stats[mode][stat_type]:
                value = v.get("value", 0) if isinstance(v, dict) and "value" in v else v
                context_str = f" ({context})" if context else ""
                stat_name = f"{emoji} {label} {stat_type}{context_str}" if context_str else f"{emoji} {label} {stat_type}"
                embed.add_field(name=stat_name, value=f"`{value}`", inline=True)
    embed.set_footer(text="Archie • ArchMC Duels • Official API")
    return embed


class DuelStatsView(View):
    def __init__(self, data, username, mode_stats, mode_labels, mode_keys, page):
        super().__init__(timeout=60)
        self.data = data
        self.username = username
        self.mode_stats = mode_stats
        self.mode_labels = mode_labels
        self.mode_keys = mode_keys
        self.page = page
        self.modes_per_page = 4
        self.max_page = (len(mode_keys) - 1) // self.modes_per_page
        if self.page > 0:
            self.add_item(self.PrevButton(self))
        if self.page < self.max_page:
            self.add_item(self.NextButton(self))

    class PrevButton(Button):
        def __init__(self, parent):
            super().__init__(label="Prev", style=discord.ButtonStyle.primary)
            self.parent = parent
        async def callback(self, interaction: discord.Interaction):
            if self.parent.page > 0:
                self.parent.page -= 1
                embed = build_duelstats_embed(
                    self.parent.data, self.parent.username, self.parent.mode_stats, self.parent.mode_labels, self.parent.mode_keys, self.parent.page, self.parent.modes_per_page
                )
                new_view = DuelStatsView(self.parent.data, self.parent.username, self.parent.mode_stats, self.parent.mode_labels, self.parent.mode_keys, self.parent.page)
                await interaction.response.edit_message(embed=embed, view=new_view)

    class NextButton(Button):
        def __init__(self, parent):
            super().__init__(label="Next", style=discord.ButtonStyle.primary)
            self.parent = parent
        async def callback(self, interaction: discord.Interaction):
            if self.parent.page < self.parent.max_page:
                self.parent.page += 1
                embed = build_duelstats_embed(
                    self.parent.data, self.parent.username, self.parent.mode_stats, self.parent.mode_labels, self.parent.mode_keys, self.parent.page, self.parent.modes_per_page
                )
                new_view = DuelStatsView(self.parent.data, self.parent.username, self.parent.mode_stats, self.parent.mode_labels, self.parent.mode_keys, self.parent.page)
                await interaction.response.edit_message(embed=embed, view=new_view)


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

    @discord.slash_command(
        name="duelstats",
        description="Show all duel stats for a player",
        options=[
            discord.Option(
                str,
                "Minecraft username",
                required=True,
                name="username"
            )
        ]
    )
    async def duelstats(self, ctx: discord.ApplicationContext, username: str):
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
            data = await client.get(f"/v1/players/username/{safe_username}/statistics")
            if data and isinstance(data, dict):
                username_disp = data.get("username", safe_username)
                uuid = data.get("uuid", "")
                statistics = data.get("statistics", {})
                
                head_data = await fetch_player_head(uuid) if uuid else None
                
                try:
                    loop = asyncio.get_event_loop()
                    card = await loop.run_in_executor(
                        None,
                        generate_duelstats_card,
                        username_disp, uuid, statistics, head_data
                    )
                    file = discord.File(card, filename="duelstats.png")
                    await ctx.respond(file=file)
                except Exception as card_error:
                    logger.error(f"Failed to generate duel card: {card_error}")
                    embed = discord.Embed(
                        title=f"🥊 Duel Stats for {username_disp}",
                        color=discord.Color.blue()
                    )
                    for key in ["elo:nodebuff:ranked:lifetime", "elo:sumo:ranked:lifetime", "elo:bridges:ranked:lifetime"]:
                        stat = statistics.get(key, {})
                        val = stat.get("value", 0) if isinstance(stat, dict) else stat
                        embed.add_field(name=key.split(":")[1].title() + " ELO", value=f"`{val}`", inline=True)
                    embed.set_footer(text="ArchMC Duels • Official API")
                    await ctx.respond(embed=embed)
            else:
                await ctx.respond("No duel stats found for that player.")
        except Exception as e:
            logger.error(f"[duelstats] Exception for {safe_username}: {e}")
            await log_error_to_channel(self.bot, "duelstats", ctx.author, ctx.guild, e, {"username": safe_username})
            await ctx.respond("Failed to fetch duel stats. Please try again later.")


def setup(bot):
    bot.add_cog(DuelsCog(bot))
