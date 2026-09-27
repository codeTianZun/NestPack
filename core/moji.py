"""控制台安全的颜文字。

Windows 中文控制台常用 GBK(cp936) 编码，部分颜文字无法直接输出。
这里使用 GBK 可编码的字符，供 CLI 和 GUI 共用。
"""

from __future__ import annotations

# 四个任务状态的颜文字。
IDLE = "(＾ω＾)"
WORKING = "(*≧ω≦)"
SUCCESS = "(≧▽≦)"
FAIL = "(；一_一)"

SIGNATURE = "NestPack · 多层嵌套压缩"

KAOMOJI = {
    "idle": IDLE,
    "working": WORKING,
    "success": SUCCESS,
    "fail": FAIL,
}
