import io
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter

from .resources import get_font, get_template


def generate_serverstats_card(
    current_players: int,
    max_players: int,
    peak_24h: int,
    peak_alltime: int,
    is_online: bool,
    version: str = "Unknown"
) -> io.BytesIO:
    GOLD = "#FFAA00"
    GREEN = "#55FF55"
    RED = "#FF5555"
    AQUA = "#55FFFF"
    WHITE = "#FFFFFF"
    GRAY = "#AAAAAA"
    BG_COLOR = (20, 20, 20, 200)
    BORDER_COLOR = (100, 100, 100, 255)

    card_width, card_height = 600, 380
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    draw.rounded_rectangle([0, 0, card_width - 1, card_height - 1], radius=12, fill=BG_COLOR, outline=BORDER_COLOR, width=2)

    font_large = get_font(40)
    font_medium = get_font(32)
    font_small = get_font(26)
    font_tiny = get_font(20)

    def mc_text(x, y, text, font, color):
        shadow = tuple(max(0, int(int(color.lstrip('#')[i:i+2], 16) * 0.3)) for i in (0, 2, 4))
        draw.text((x + 2, y + 2), text, font=font, fill=shadow)
        draw.text((x, y), text, font=font, fill=color)

    def mc_text_centered(x, y, text, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        mc_text(x - (bbox[2] - bbox[0]) // 2, y, text, font, color)

    # Header
    mc_text_centered(card_width // 2, 20, "ArchMC Server Stats", font_large, GOLD)
    draw.line([(20, 75), (card_width - 20, 75)], fill=BORDER_COLOR, width=1)

    # Status
    status_color = GREEN if is_online else RED
    status_text = "ONLINE" if is_online else "OFFLINE"
    mc_text_centered(card_width // 2, 85, status_text, font_medium, status_color)

    # Main stats row
    draw.line([(20, 140), (card_width - 20, 140)], fill=BORDER_COLOR, width=1)
    draw.line([(20, 220), (card_width - 20, 220)], fill=BORDER_COLOR, width=1)

    col3 = (card_width - 40) // 3

    # Row: Current | 24h Peak | All-Time Peak
    labels = ["Now Playing", "24h Peak", "All-Time Peak"]
    values = [f"{current_players}", f"{peak_24h}", f"{peak_alltime}"]
    colors = [GREEN, AQUA, GOLD]

    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        x_center = 20 + col3 * i + col3 // 2
        mc_text_centered(x_center, 150, label, font_small, GRAY)
        mc_text_centered(x_center, 180, value, font_large, color)

    for i in range(1, 3):
        draw.line([(20 + col3 * i, 145), (20 + col3 * i, 215)], fill=BORDER_COLOR, width=1)

    # Server info row
    draw.line([(20, 295), (card_width - 20, 295)], fill=BORDER_COLOR, width=1)

    col2 = (card_width - 40) // 2

    mc_text_centered(20 + col2 // 2, 235, "Max Players", font_small, GRAY)
    mc_text_centered(20 + col2 // 2, 260, f"{max_players}", font_medium, WHITE)

    mc_text_centered(20 + col2 + col2 // 2, 235, "Version", font_small, GRAY)
    mc_text_centered(20 + col2 + col2 // 2, 260, version, font_medium, WHITE)

    draw.line([(20 + col2, 230), (20 + col2, 290)], fill=BORDER_COLOR, width=1)

    # Footer
    mc_text_centered(card_width // 2, 310, "play.arch.mc", font_medium, AQUA)
    mc_text_centered(card_width // 2, 345, datetime.now().strftime("%Y-%m-%d %H:%M UTC"), font_tiny, GRAY)

    # Background
    bg = get_template('lifesteal')
    if bg is None:
        bg = Image.new("RGBA", (card_width, card_height), (30, 30, 30, 255))
    else:
        bg = bg.resize((card_width, card_height), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=3))
    dark_overlay = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 100))
    bg = Image.alpha_composite(bg, dark_overlay)

    final = Image.alpha_composite(bg, card)

    buf = io.BytesIO()
    final.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return buf


async def generate_serverstats_card_async(
    current_players: int,
    max_players: int,
    peak_24h: int,
    peak_alltime: int,
    is_online: bool,
    version: str = "Unknown"
) -> io.BytesIO:
    return await asyncio.get_event_loop().run_in_executor(
        None, generate_serverstats_card, current_players, max_players, peak_24h, peak_alltime, is_online, version
    )
