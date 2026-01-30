import os
import logging
from typing import Dict, Optional
from PIL import Image, ImageFont

logger = logging.getLogger('archie-bot')

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "template.png")
DUEL_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "duel_template.png")
FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "MinecraftRegular.otf")

_cached_fonts: Dict[int, ImageFont.FreeTypeFont] = {}
_cached_templates: Dict[str, Image.Image] = {}

def _load_fonts():
    """Pre-load fonts at startup."""
    global _cached_fonts
    if _cached_fonts:
        return
    try:
        for size in [20, 26, 32, 40]:
            _cached_fonts[size] = ImageFont.truetype(FONT_PATH, size)
    except Exception as e:
        logger.warning(f"Failed to load fonts: {e}")
        default = ImageFont.load_default()
        for size in [20, 26, 32, 40]:
            _cached_fonts[size] = default

def _load_templates():
    """Pre-load template images at startup."""
    global _cached_templates
    if _cached_templates:
        return
    try:
        if os.path.exists(TEMPLATE_PATH):
            _cached_templates['lifesteal'] = Image.open(TEMPLATE_PATH).convert("RGBA")
        if os.path.exists(DUEL_TEMPLATE_PATH):
            _cached_templates['duels'] = Image.open(DUEL_TEMPLATE_PATH).convert("RGBA")
    except Exception as e:
        logger.warning(f"Failed to load templates: {e}")

def get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get cached font by size."""
    if not _cached_fonts:
        _load_fonts()
    return _cached_fonts.get(size, _cached_fonts.get(32))

def get_template(name: str) -> Optional[Image.Image]:
    """Get cached template (returns a copy to avoid mutation)."""
    if not _cached_templates:
        _load_templates()
    tpl = _cached_templates.get(name)
    return tpl.copy() if tpl else None

def load_all():
    """Pre-load all resources."""
    _load_fonts()
    _load_templates()
