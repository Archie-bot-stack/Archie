import io
import asyncio
from typing import Optional
from PIL import Image, ImageDraw, ImageFilter

from .resources import get_font, get_template


def generate_lifestats_card(username: str, uuid: str, statistics: dict, profile: dict, head_data: Optional[bytes] = None) -> io.BytesIO:
    GOLD = "#FFAA00"
    GREEN = "#55FF55"
    AQUA = "#55FFFF"
    PINK = "#FF55FF"
    WHITE = "#FFFFFF"
    GRAY = "#AAAAAA"
    BG_COLOR = (20, 20, 20, 200)
    BORDER_COLOR = (100, 100, 100, 255)
    
    card_width, card_height = 800, 520
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    
    draw.rounded_rectangle([0, 0, card_width-1, card_height-1], radius=12, fill=BG_COLOR, outline=BORDER_COLOR, width=2)
    
    font_large = get_font(40)
    font_medium = get_font(32)
    font_small = get_font(26)
    font_tiny = get_font(20)
    
    skin_img = None
    if head_data:
        try:
            skin_img = Image.open(io.BytesIO(head_data)).convert("RGBA")
            if skin_img.size[0] <= 0 or skin_img.size[1] <= 0:
                skin_img = None
        except:
            skin_img = None
    
    if skin_img is None:
        skin_img = Image.new("RGBA", (80, 80), (139, 90, 43, 255))
    
    def mc_text(x, y, text, font, color):
        shadow = tuple(max(0, int(int(color.lstrip('#')[i:i+2], 16) * 0.3)) for i in (0, 2, 4))
        draw.text((x+2, y+2), text, font=font, fill=shadow)
        draw.text((x, y), text, font=font, fill=color)
    
    def mc_text_centered(x, y, text, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        mc_text(x - (bbox[2] - bbox[0]) // 2, y, text, font, color)
    
    def get_stat_value(stat_name):
        stat = statistics.get(stat_name, {})
        return stat.get("value", 0) if isinstance(stat, dict) else (stat or 0)
    
    def get_stat_rank(stat_name):
        stat = statistics.get(stat_name, {})
        return stat.get("position") if isinstance(stat, dict) else None
    
    def format_number(n):
        if isinstance(n, float): return f"{n:.2f}"
        if isinstance(n, int):
            if n >= 1000000: return f"{n/1000000:.2f}M"
            return f"{n:,}"
        return str(n)
    
    # Header
    draw.line([(20, 100), (card_width - 20, 100)], fill=BORDER_COLOR, width=1)
    skin_img = skin_img.resize((80, 80), Image.Resampling.LANCZOS)
    card.paste(skin_img, (25, 12), skin_img)
    draw.rectangle([24, 11, 106, 93], outline=BORDER_COLOR, width=2)
    mc_text(120, 25, username, font_large, WHITE)
    mc_text(120, 60, "Lifesteal Player", font_small, GREEN)
    playtime_ms = profile.get("totalPlaytimeSeconds", 0) if profile else 0
    hours = int(playtime_ms // 1000 // 3600) if playtime_ms else 0
    mc_text(card_width - 200, 25, "Playtime", font_tiny, GRAY)
    mc_text(card_width - 200, 45, f"{hours//24}d {hours%24}h", font_medium, AQUA)
    
    # Row 1 - Combat stats
    draw.line([(20, 180), (card_width - 20, 180)], fill=BORDER_COLOR, width=1)
    col4 = (card_width - 40) // 4
    for i, (label, key) in enumerate([("Kills", "kills"), ("Deaths", "deaths"), ("K/D Ratio", "killDeathRatio"), ("Best Streak", "killstreak")]):
        mc_text_centered(20 + col4*i + col4//2, 115, label, font_small, GOLD)
        mc_text_centered(20 + col4*i + col4//2, 140, format_number(get_stat_value(key)), font_large, GOLD)
    for i in range(1, 4): draw.line([(20 + col4*i, 105), (20 + col4*i, 175)], fill=BORDER_COLOR, width=1)
    
    # Row 2 - Activity stats
    draw.line([(20, 260), (card_width - 20, 260)], fill=BORDER_COLOR, width=1)
    col3 = (card_width - 40) // 3
    for i, (label, key) in enumerate([("Blocks Mined", "blocksMined"), ("Blocks Walked", "blocksWalked"), ("Blocks Placed", "blocksPlaced")]):
        mc_text_centered(20 + col3*i + col3//2, 195, label, font_small, GREEN)
        mc_text_centered(20 + col3*i + col3//2, 220, format_number(get_stat_value(key)), font_large, GREEN)
    for i in range(1, 3): draw.line([(20 + col3*i, 185), (20 + col3*i, 255)], fill=BORDER_COLOR, width=1)
    
    # Row 3 - Combat ranks
    draw.line([(20, 340), (card_width - 20, 340)], fill=BORDER_COLOR, width=1)
    for i, (label, key) in enumerate([("Kills Rank", "kills"), ("Deaths Rank", "deaths"), ("K/D Rank", "killDeathRatio"), ("Streak Rank", "killstreak")]):
        rank = get_stat_rank(key)
        mc_text_centered(20 + col4*i + col4//2, 275, label, font_small, PINK)
        mc_text_centered(20 + col4*i + col4//2, 300, f"#{rank:,}" if rank else "N/A", font_large, PINK)
    for i in range(1, 4): draw.line([(20 + col4*i, 265), (20 + col4*i, 335)], fill=BORDER_COLOR, width=1)
    
    # Row 4 - Activity ranks
    draw.line([(20, 420), (card_width - 20, 420)], fill=BORDER_COLOR, width=1)
    for i, (label, key) in enumerate([("Mined Rank", "blocksMined"), ("Walked Rank", "blocksWalked"), ("Placed Rank", "blocksPlaced")]):
        rank = get_stat_rank(key)
        mc_text_centered(20 + col3*i + col3//2, 355, label, font_small, AQUA)
        mc_text_centered(20 + col3*i + col3//2, 380, f"#{rank:,}" if rank else "N/A", font_large, AQUA)
    for i in range(1, 3): draw.line([(20 + col3*i, 345), (20 + col3*i, 415)], fill=BORDER_COLOR, width=1)
    
    # Footer
    mc_text_centered(card_width // 2, 440, "ArchMC Lifesteal", font_small, GRAY)
    
    # Background with slight blur - use cached template
    bg = get_template('lifesteal')
    if bg is None:
        bg = Image.new("RGBA", (card_width, card_height), (30, 30, 30, 255))
    else:
        bg = bg.resize((card_width, card_height), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=3))
    dark_overlay = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 80))
    bg = Image.alpha_composite(bg, dark_overlay)
    
    final = Image.alpha_composite(bg, card)
    
    buf = io.BytesIO()
    final.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return buf


async def generate_lifestats_card_async(username: str, uuid: str, statistics: dict, profile: dict, head_data=None):
    return await asyncio.get_event_loop().run_in_executor(
        None, generate_lifestats_card, username, uuid, statistics, profile, head_data
    )
