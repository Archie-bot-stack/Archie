import os
import json
import logging
import filelock


def safe_json_load(filepath: str, default: dict) -> dict:
    """Safely load JSON with file locking to prevent corruption."""
    lock = filelock.FileLock(f"{filepath}.lock", timeout=5)
    try:
        with lock:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
    except (json.JSONDecodeError, filelock.Timeout, Exception) as e:
        logging.getLogger('archie-bot').error(f"Failed to load {filepath}: {e}")
    return default


def safe_json_save(filepath: str, data: dict) -> bool:
    """Safely save JSON with file locking and atomic write."""
    lock = filelock.FileLock(f"{filepath}.lock", timeout=5)
    try:
        with lock:
            tmp_path = f"{filepath}.tmp"
            with open(tmp_path, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, filepath)
            return True
    except (filelock.Timeout, Exception) as e:
        logging.getLogger('archie-bot').error(f"Failed to save {filepath}: {e}")
    return False
