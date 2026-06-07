"""测字与灵签 MVP 规则。"""

from __future__ import annotations

import random
from typing import Dict


_LEVELS = ["上吉", "中吉", "小吉", "平", "谨慎"]


def draw_sign(sign_no: int | None = None) -> Dict[str, object]:
    if sign_no is None:
        sign_no = random.randint(1, 100)
    if sign_no < 1 or sign_no > 100:
        raise ValueError("sign_no must be between 1 and 100")
    return {"sign_no": sign_no, "level": _LEVELS[(sign_no - 1) % len(_LEVELS)]}
