import re
from datetime import datetime
from typing import Dict, Optional

user_cooldowns: Dict[int, datetime] = {}
COOLDOWN_SECONDS = 3

def check_cooldown(user_id: int) -> bool:
    """Returns True if user is on cooldown (should be blocked)"""
    now = datetime.now()
    if user_id in user_cooldowns:
        elapsed = (now - user_cooldowns[user_id]).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            return True
    user_cooldowns[user_id] = now
    return False

USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{1,16}$')

BLOCKED_PATTERNS = {
    "nigger", "nigga", "n1gger", "n1gga", "nigg3r", "nigg4",
    "faggot", "f4ggot", "fag",
    "retard", "r3tard",
    "kike", "chink", "spic", "wetback", "beaner",
    "tranny", "trannie",
}

def is_username_blocked(username: str) -> bool:
    """Check if a username contains blocked/offensive terms."""
    lower = username.lower()
    return any(pattern in lower for pattern in BLOCKED_PATTERNS)

def sanitize_username(username: str) -> Optional[str]:
    """Validate and sanitize Minecraft username. Returns None if invalid."""
    username = username.strip()[:16]
    if USERNAME_REGEX.match(username):
        return username
    return None
