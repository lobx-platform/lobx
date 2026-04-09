import re
from typing import Dict, Optional, Tuple

from core.treatment_manager import treatment_manager

# Pattern: T{treatment}_P{participant} (1-based)
_TOKEN_PATTERN = re.compile(r'^T(\d+)_P(\d+)$')


def validate_lab_token(token: str) -> Tuple[bool, Optional[dict]]:
    """Parse a lab token like T1_P1 directly — no pre-generation needed."""
    match = _TOKEN_PATTERN.match(token)
    if not match:
        return False, None

    t_num, p_num = int(match.group(1)), int(match.group(2))
    treatment_group = t_num - 1  # 0-based internally
    group_index = p_num - 1

    if treatment_group < 0:
        return False, None

    trader_id = f"HUMAN_LAB_{token}"
    user = {
        "uid": f"lab_{token}",
        "email": f"lab_{token}@lab.local",
        "gmail_username": f"LAB_{token}",
        "is_admin": False,
        "is_lab": True,
        "lab_token": token,
        "trader_id": trader_id,
        "treatment_group": treatment_group,
        "group_index": group_index,
    }
    return True, user


# Global mapping of lab trader_ids to user data (populated on login)
lab_trader_map: Dict[str, dict] = {}
