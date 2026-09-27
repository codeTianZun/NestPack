"""随机密码生成（无 Qt 依赖，可由 GUI 直接调用）。"""

from __future__ import annotations

import secrets
import string

PASSWORD_LENGTH = 16
# 避开引号、反斜杠等在手抄、聊天工具里易出错的字符。
PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*-_=+"


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """生成随机强密码；用 secrets 而非 random，适合密码学用途。"""
    return "".join(
        secrets.choice(PASSWORD_ALPHABET) for _ in range(length)
    )
