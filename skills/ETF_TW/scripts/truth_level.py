"""
Truth levels for the ETF_TW project.
Defines levels of information source to help users understand data reliability.
"""

LEVEL_1 = "LIVE"
LEVEL_2 = "VERIFYING"
LEVEL_3 = "SNAPSHOT"

# Level aliases
LEVEL_1_LIVE = LEVEL_1
LEVEL_2_VERIFYING = LEVEL_2
LEVEL_3_SNAPSHOT = LEVEL_3

# Compatibility with plan names
LEVEL_1_LIVE_DIRECT = LEVEL_1
LEVEL_2_LIVE_UNCONFIRMED = LEVEL_2
LEVEL_3_SECONDARY = LEVEL_3

def format_with_level(text: str, level: str) -> str:
    """
    Format a text with a truth level tag.
    Example: "[LIVE] 0050: 100 股"
    """
    return f"[{level}] {text}"
