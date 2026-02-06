import logging
import discord
import os
import asyncio
import io
import zoneinfo
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from utils.json_ops import safe_json_load, safe_json_save
from cards.resources import load_all as load_card_resources

# === Logging setup ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('archie-bot')
load_dotenv()

# === Channel IDs ===
GUILD_JOIN_CHANNEL = int(os.getenv("GUILD_JOIN_CHANNEL", 0))
GUILD_LEAVE_CHANNEL = int(os.getenv("GUILD_LEAVE_CHANNEL", 0))
BOT_ERRORS_CHANNEL = 1454137711710703785
STATS_CHANNEL = 1465102978644971858
BOT_STATUS_CHANNEL = 1454137711140147332
YEARLY_STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yearly_stats.json")

# === Bot instance ===
bot = discord.Bot(
    allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False)
)

# === Daily stats tracking ===
daily_stats = {
    "commands": defaultdict(int),
    "guilds": set(),
    "guild_usage": defaultdict(int),
    "guild_names": {},
    "start_time": datetime.now()
}

def reset_daily_stats():
    daily_stats["commands"] = defaultdict(int)
    daily_stats["guilds"] = set()
    daily_stats["guild_usage"] = defaultdict(int)
    daily_stats["guild_names"] = {}
    daily_stats["start_time"] = datetime.now()

# === Yearly stats persistence ===
def load_yearly_stats():
    default = {
        "year": datetime.now().year,
        "commands": defaultdict(int),
        "total_commands": 0,
        "guild_usage": defaultdict(int),
        "guild_names": {},
    }
    data = safe_json_load(YEARLY_STATS_FILE, {})
    if data:
        return {
            "year": data.get("year", datetime.now().year),
            "commands": defaultdict(int, data.get("commands", {})),
            "total_commands": data.get("total_commands", 0),
            "guild_usage": defaultdict(int, data.get("guild_usage", {})),
            "guild_names": data.get("guild_names", {}),
        }
    return default

def save_yearly_stats():
    data = {
        "year": yearly_stats["year"],
        "commands": dict(yearly_stats["commands"]),
        "total_commands": yearly_stats["total_commands"],
        "guild_usage": dict(yearly_stats["guild_usage"]),
        "guild_names": yearly_stats["guild_names"],
    }
    safe_json_save(YEARLY_STATS_FILE, data)

def reset_yearly_stats():
    yearly_stats["year"] = datetime.now().year
    yearly_stats["commands"] = defaultdict(int)
    yearly_stats["total_commands"] = 0
    yearly_stats["guild_usage"] = defaultdict(int)
    yearly_stats["guild_names"] = {}
    save_yearly_stats()

yearly_stats = load_yearly_stats()

# === Stats chart generation ===
def generate_stats_chart():
    commands = dict(daily_stats["commands"])
    if not commands:
        return None
    
    sorted_cmds = sorted(commands.items(), key=lambda x: x[1], reverse=True)
    names = [cmd for cmd, _ in sorted_cmds]
    counts = [count for _, count in sorted_cmds]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(names, counts, color='#5865F2')
    ax.set_xlabel('Usage Count')
    ax.set_title(f'Daily Command Usage - {daily_stats["start_time"].strftime("%Y-%m-%d")}')
    ax.invert_yaxis()
    
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                str(count), va='center', fontsize=10)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    return buf

async def send_daily_recap():
    channel = bot.get_channel(STATS_CHANNEL)
    if not channel:
        return
    
    total_commands = sum(daily_stats["commands"].values())
    unique_guilds = len(daily_stats["guilds"])
    
    embed = discord.Embed(
        title="📈 Daily Stats Recap",
        description=f"Stats for **{daily_stats['start_time'].strftime('%Y-%m-%d')}**",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Total Commands", value=f"`{total_commands}`", inline=True)
    embed.add_field(name="Active Servers", value=f"`{unique_guilds}`", inline=True)
    
    if daily_stats["commands"]:
        top_cmds = sorted(daily_stats["commands"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_text = "\n".join([f"`/{cmd}` — {count}" for cmd, count in top_cmds])
        embed.add_field(name="Top Commands", value=top_text, inline=False)
    
    if daily_stats["guild_usage"]:
        top_guilds = sorted(daily_stats["guild_usage"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_guilds_text = "\n".join([
            f"**{daily_stats['guild_names'].get(gid, 'Unknown')}** — {count} commands"
            for gid, count in top_guilds
        ])
        embed.add_field(name="Top Servers", value=top_guilds_text, inline=False)
    
    embed.set_footer(text="Archie Daily Stats • Updates every 5 min")
    
    chart = generate_stats_chart()
    if chart:
        file = discord.File(chart, filename="daily_stats.png")
        embed.set_image(url="attachment://daily_stats.png")
        await channel.send(embed=embed, file=file)
    else:
        await channel.send(embed=embed)

def generate_yearly_wrapped_chart():
    commands = dict(yearly_stats["commands"])
    if not commands:
        return None
    
    sorted_cmds = sorted(commands.items(), key=lambda x: x[1], reverse=True)[:10]
    names = [cmd for cmd, _ in sorted_cmds]
    counts = [count for _, count in sorted_cmds]
    
    fig, ax = plt.subplots(figsize=(12, 8))
    colors = plt.cm.viridis([i/len(names) for i in range(len(names))])
    bars = ax.barh(names, counts, color=colors)
    ax.set_xlabel('Usage Count', fontsize=14)
    ax.set_title(f'🎉 Archie Wrapped {yearly_stats["year"]} 🎉', fontsize=20, fontweight='bold')
    ax.invert_yaxis()
    
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + max(counts)*0.01, bar.get_y() + bar.get_height()/2, 
                f'{count:,}', va='center', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

async def send_yearly_wrapped():
    channel = bot.get_channel(STATS_CHANNEL)
    if not channel:
        return
    
    year = yearly_stats["year"]
    total_commands = yearly_stats["total_commands"]
    total_servers = len(yearly_stats["guild_usage"])
    
    embed = discord.Embed(
        title=f"🎉 Archie Wrapped {year} 🎉",
        description="Here's your year in review!",
        color=discord.Color.gold()
    )
    embed.add_field(name="📊 Total Commands", value=f"`{total_commands:,}`", inline=True)
    embed.add_field(name="🌐 Servers Reached", value=f"`{total_servers}`", inline=True)
    
    if yearly_stats["commands"]:
        top_cmds = sorted(yearly_stats["commands"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_text = "\n".join([f"**{i+1}.** `/{cmd}` — {count:,} uses" for i, (cmd, count) in enumerate(top_cmds)])
        embed.add_field(name="🏆 Top Commands", value=top_text, inline=False)
    
    if yearly_stats["guild_usage"]:
        top_guilds = sorted(yearly_stats["guild_usage"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_guilds_text = "\n".join([
            f"**{i+1}.** {yearly_stats['guild_names'].get(str(gid), 'Unknown')} — {count:,} commands"
            for i, (gid, count) in enumerate(top_guilds)
        ])
        embed.add_field(name="🏅 Top Servers", value=top_guilds_text, inline=False)
    
    embed.set_footer(text=f"Thank you for an amazing {year}! 💜")
    
    chart = generate_yearly_wrapped_chart()
    if chart:
        file = discord.File(chart, filename="wrapped.png")
        embed.set_image(url="attachment://wrapped.png")
        await channel.send(embed=embed, file=file)
    else:
        await channel.send(embed=embed)
    
    reset_yearly_stats()

async def daily_recap_loop():
    await bot.wait_until_ready()
    denmark_tz = zoneinfo.ZoneInfo("Europe/Copenhagen")
    last_date = datetime.now(denmark_tz).date()
    while not bot.is_closed():
        await asyncio.sleep(300)  # every 5 minutes
        
        now = datetime.now(denmark_tz)
        current_date = now.date()
        
        if current_date != last_date:
            if now.month == 1 and now.day == 1:
                await send_yearly_wrapped()
            reset_daily_stats()
            last_date = current_date
        
        await send_daily_recap()

# === Event handlers ===
@bot.event
async def on_ready():
    logger.info(f"{bot.user} is ready and online! Registering commands...")
    
    # Pre-load cached resources
    load_card_resources()
    logger.info("Pre-loaded fonts and templates")
    
    # Sync commands
    await bot.sync_commands()
    logger.info(f"{bot.user} commands synced!")
    
    # Start daily recap loop
    bot.loop.create_task(daily_recap_loop())
    
    # Send online status
    try:
        status_channel = bot.get_channel(BOT_STATUS_CHANNEL) or await bot.fetch_channel(BOT_STATUS_CHANNEL)
        if status_channel:
            await status_channel.send("🟢 **Archie is now online!**")
    except Exception as e:
        logger.error(f"Failed to send online status: {e}")
    
    # Notify commands synced
    try:
        channel = bot.get_channel(1454137711710703783)
        if channel:
            await channel.send("✅ Archie slash commands are now fully synced and ready to use!")
            guilds = list(bot.guilds)
            if guilds:
                guild_list = "\n".join([f"- {g.name} (ID: {g.id})" for g in guilds])
                msg = f"Archie is currently in the following servers ({len(guilds)}):\n{guild_list}"
            else:
                msg = "Archie is not in any servers."
            await channel.send(msg)
    except Exception as e:
        logger.error(f"Failed to send guild list: {e}")

@bot.event
async def on_application_command(ctx):
    logger.info(f"/{ctx.command.name} used by {ctx.author} in {getattr(ctx.guild, 'name', 'DM')}")
    
    # Track daily stats
    daily_stats["commands"][ctx.command.name] += 1
    if ctx.guild:
        daily_stats["guilds"].add(ctx.guild.id)
        daily_stats["guild_usage"][ctx.guild.id] += 1
        daily_stats["guild_names"][ctx.guild.id] = ctx.guild.name
    
    # Track yearly stats
    yearly_stats["commands"][ctx.command.name] += 1
    yearly_stats["total_commands"] += 1
    if ctx.guild:
        yearly_stats["guild_usage"][str(ctx.guild.id)] += 1
        yearly_stats["guild_names"][str(ctx.guild.id)] = ctx.guild.name
    save_yearly_stats()

@bot.event
async def on_guild_join(guild):
    channel = bot.get_channel(GUILD_JOIN_CHANNEL)
    if channel:
        await channel.send(f"✅ Joined guild: **{guild.name}** (ID: {guild.id})")

@bot.event
async def on_guild_remove(guild):
    channel = bot.get_channel(GUILD_LEAVE_CHANNEL)
    if channel:
        await channel.send(f"❌ Left guild: **{guild.name}** (ID: {guild.id})")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    error_text = traceback.format_exc()
    logger.error(f"Error in event {event}:\n{error_text}")
    try:
        channel = bot.get_channel(BOT_ERRORS_CHANNEL)
        if channel:
            error_msg = f"⚠️ Error in event `{event}`:\n```py\n{error_text[:1800]}```"
            await asyncio.wait_for(channel.send(error_msg), timeout=5.0)
    except Exception as send_error:
        logger.error(f"Failed to send error notification: {send_error}")

# === Load cogs ===
cogs = [
    'cogs.lifesteal',
    'cogs.duels',
    'cogs.economy',
    'cogs.guilds',
    'cogs.utility',
    'cogs.stats',
    'cogs.serverstats',
]

for cog in cogs:
    try:
        bot.load_extension(cog)
        logger.info(f"Loaded cog: {cog}")
    except Exception as e:
        logger.error(f"Failed to load cog {cog}: {e}")

# === Run bot ===
if __name__ == "__main__":
    bot.run(os.getenv('TOKEN'))
