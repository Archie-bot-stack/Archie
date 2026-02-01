import re
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

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
    "tranny", "trannie", "tr4nny",
}

# Regex patterns to catch letter substitutions and repeated variants
# Common substitutions: i=1/l/!/|, a=4/@, e=3, o=0, s=5/$, k=c, etc.
BLOCKED_REGEX_PATTERNS = [
    # N-word variants
    re.compile(r'n+[i1l!|]+g+[e3a4@]*r*[s5$]*', re.IGNORECASE),
    re.compile(r'n+[i1l!|]+g+[a4@]+[s5$]*', re.IGNORECASE),
    # F-slur variants
    re.compile(r'f+[a4@]+g+[o0]*t*[s5$]*', re.IGNORECASE),
    re.compile(r'f+[a4@]+g+[s5$]*', re.IGNORECASE),
    # R-word variants
    re.compile(r'r+[e3]+t+[a4@]+r+d*[s5$]*', re.IGNORECASE),
    # Kike variants
    re.compile(r'k+[i1l!|]+k+[e3]*[s5$]*', re.IGNORECASE),
    # Chink variants
    re.compile(r'ch+[i1l!|]+n+k+[s5$]*', re.IGNORECASE),
    # Spic variants
    re.compile(r'sp+[i1l!|]+c+[s5$]*', re.IGNORECASE),
    # Wetback variants
    re.compile(r'w+[e3]+t+b+[a4@]+c*k*[s5$]*', re.IGNORECASE),
    # Beaner variants
    re.compile(r'b+[e3]+[a4@]*n+[e3]*r*[s5$]*', re.IGNORECASE),
    # Coon variants
    re.compile(r'c+[o0]+[o0]+n+[s5$]*', re.IGNORECASE),
    # Gook variants
    re.compile(r'g+[o0]+[o0]+k+[s5$]*', re.IGNORECASE),
    # Dyke variants
    re.compile(r'd+y+k+[e3]*[s5$]*', re.IGNORECASE),
    # Paki variants
    re.compile(r'p+[a4@]+k+[i1l!|]+[s5$]*', re.IGNORECASE),
    # Jap (slur) variants
    re.compile(r'\bj+[a4@]+p+[s5$]*\b', re.IGNORECASE),
    # Tard variants
    re.compile(r'\b[a-z]*t+[a4@]+r+d+[s5$]*\b', re.IGNORECASE),
]

# URL/link detection patterns
URL_PATTERNS = [
    re.compile(r'https?://[^\s]+', re.IGNORECASE),
    re.compile(r'www\.[^\s]+', re.IGNORECASE),
    re.compile(r'[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s]*)?', re.IGNORECASE),
    re.compile(r'discord\.gg/[^\s]+', re.IGNORECASE),
    re.compile(r'discord\.com/invite/[^\s]+', re.IGNORECASE),
    re.compile(r'bit\.ly/[^\s]+', re.IGNORECASE),
    re.compile(r't\.co/[^\s]+', re.IGNORECASE),
]

# Discord mention patterns
MENTION_PATTERNS = [
    re.compile(r'<@!?\d+>'),           # User mentions
    re.compile(r'<@&\d+>'),            # Role mentions  
    re.compile(r'<#\d+>'),             # Channel mentions
    re.compile(r'@everyone', re.IGNORECASE),
    re.compile(r'@here', re.IGNORECASE),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r'\.\.'),               # Parent directory
    re.compile(r'[/\\]'),              # Path separators
    re.compile(r'%2e%2e', re.IGNORECASE),  # URL encoded ..
    re.compile(r'%2f', re.IGNORECASE),     # URL encoded /
    re.compile(r'%5c', re.IGNORECASE),     # URL encoded \
    re.compile(r'\.%2e', re.IGNORECASE),   # Mixed encoding
    re.compile(r'%2e\.', re.IGNORECASE),   # Mixed encoding
]


def is_username_blocked(username: str) -> bool:
    """Check if a username contains blocked/offensive terms."""
    lower = username.lower()
    if any(pattern in lower for pattern in BLOCKED_PATTERNS):
        return True
    return any(regex.search(lower) for regex in BLOCKED_REGEX_PATTERNS)


def sanitize_username(username: str) -> Optional[str]:
    """Validate and sanitize Minecraft username. Returns None if invalid."""
    username = username.strip()[:16]
    if USERNAME_REGEX.match(username):
        return username
    return None


def contains_url(text: str) -> bool:
    """Check if text contains any URLs or links."""
    return any(pattern.search(text) for pattern in URL_PATTERNS)


def contains_mention(text: str) -> bool:
    """Check if text contains Discord mentions (@user, @role, @everyone, @here)."""
    return any(pattern.search(text) for pattern in MENTION_PATTERNS)


def contains_path_traversal(text: str) -> bool:
    """Check if text contains path traversal attempts."""
    return any(pattern.search(text) for pattern in PATH_TRAVERSAL_PATTERNS)


def sanitize_path(path: str, base_dir: str) -> Optional[str]:
    """
    Sanitize and validate a file path to prevent path traversal.
    Returns the safe absolute path, or None if invalid/dangerous.
    """
    if not path or not base_dir:
        return None
    
    # Reject obvious traversal attempts
    if contains_path_traversal(path):
        return None
    
    # Normalize the base directory
    base_dir = os.path.abspath(base_dir)
    
    # Join and normalize the full path
    full_path = os.path.normpath(os.path.join(base_dir, path))
    
    # Ensure the result is within the base directory
    if not full_path.startswith(base_dir + os.sep) and full_path != base_dir:
        return None
    
    return full_path


def validate_input(text: str, allow_urls: bool = False, allow_mentions: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate user input for security issues.
    Returns (is_valid, error_message).
    """
    if not text:
        return True, None
    
    if not allow_urls and contains_url(text):
        return False, "Links/URLs are not allowed in this input."
    
    if not allow_mentions and contains_mention(text):
        return False, "Mentions (@user, @role, @everyone, @here) are not allowed."
    
    if contains_path_traversal(text):
        return False, "Invalid characters detected in input."
    
    return True, None


def sanitize_text_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize general text input by removing dangerous content.
    Use when you want to clean input rather than reject it.
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove URLs
    for pattern in URL_PATTERNS:
        text = pattern.sub('[link removed]', text)
    
    # Remove mentions
    for pattern in MENTION_PATTERNS:
        text = pattern.sub('[mention removed]', text)
    
    # Remove path traversal attempts
    for pattern in PATH_TRAVERSAL_PATTERNS:
        text = pattern.sub('', text)
    
    return text.strip()


def is_safe_filename(filename: str) -> bool:
    """Check if a filename is safe (no path components, valid chars)."""
    if not filename:
        return False
    
    # Must not contain path separators
    if '/' in filename or '\\' in filename:
        return False
    
    # Must not be or start with .
    if filename.startswith('.'):
        return False
    
    # Must not contain null bytes
    if '\x00' in filename:
        return False
    
    # Basic alphanumeric + safe chars only
    safe_pattern = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
    return bool(safe_pattern.match(filename))
