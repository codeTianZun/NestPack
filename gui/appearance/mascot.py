"""NestPack 吉祥物：程序化绘制的猫耳小助手。

使用 QPainter 绘制透明背景图像，表情随任务状态切换：
空闲 / 打包中 / 打包完成 / 打包失败。
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)

# 浅色柔和主题配色：奶油毛色 + 雾蓝描边 + 粉嫩腮红。
_FUR = QColor("#FFFBF2")
_EAR_INNER = QColor("#FFC9D6")
_EYE = QColor("#5A7396")
_BLUSH = QColor(255, 166, 188, 120)
_SPARKLE = QColor("#8FD0F5")
_TEAR = QColor("#7EC8F2")
_OUTLINE = QColor("#8CA3C2")


class MascotState(Enum):
    """吉祥物表情状态。"""

    IDLE = "idle"
    WORKING = "working"
    SUCCESS = "success"
    FAIL = "fail"


def _outline_pen(size: float) -> QPen:
    pen = QPen(_OUTLINE, max(2.0, size * 0.035))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw_ears(painter: QPainter, size: float) -> None:
    """外耳（带描边）与内耳（粉色）。"""
    painter.setPen(_outline_pen(size))
    painter.setBrush(_FUR)
    for sign in (-1, 1):
        ear = QPolygonF(
            [
                QPointF(sign * 0.36 * size, -0.06 * size),
                QPointF(sign * 0.27 * size, -0.48 * size),
                QPointF(sign * 0.01 * size, -0.20 * size),
            ]
        )
        painter.drawPolygon(ear)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_EAR_INNER)
    for sign in (-1, 1):
        inner = QPolygonF(
            [
                QPointF(sign * 0.33 * size, -0.10 * size),
                QPointF(sign * 0.27 * size, -0.40 * size),
                QPointF(sign * 0.06 * size, -0.23 * size),
            ]
        )
        painter.drawPolygon(inner)


def _draw_head(painter: QPainter, size: float) -> None:
    painter.setPen(_outline_pen(size))
    painter.setBrush(_FUR)
    painter.drawEllipse(QPointF(0, 0.02 * size), 0.40 * size, 0.36 * size)


def _draw_blush(painter: QPainter, size: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_BLUSH)
    for sign in (-1, 1):
        painter.drawEllipse(
            QPointF(sign * 0.265 * size, 0.15 * size), 0.055 * size, 0.028 * size
        )


def _open_eye(painter: QPainter, cx: float, cy: float, radius: float) -> None:
    """水汪汪的大眼睛：深色圆 + 高光。"""
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_EYE)
    painter.drawEllipse(QPointF(cx, cy), radius, radius)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(
        QPointF(cx - radius * 0.34, cy - radius * 0.34), radius * 0.30, radius * 0.30
    )
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(
        QPointF(cx + radius * 0.28, cy + radius * 0.30), radius * 0.13, radius * 0.13
    )


def _closed_eye(painter: QPainter, cx: float, cy: float, radius: float, *, happy: bool) -> None:
    """闭合眼：happy 为上弯 ∩，sad 为下弯 ∪。"""
    rect = QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius)
    path = QPainterPath()
    if happy:
        path.arcMoveTo(rect, 180)
        path.arcTo(rect, 180, 180)
    else:
        path.arcMoveTo(rect, 0)
        path.arcTo(rect, 0, 180)
    painter.setPen(_outline_pen(radius * 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def _stroke_smile(painter: QPainter, cx: float, cy: float, radius: float) -> None:
    """小微笑：∪ 形状的下弯弧线。"""
    rect = QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius)
    path = QPainterPath()
    path.arcMoveTo(rect, 0)
    path.arcTo(rect, 0, 180)
    painter.setPen(_outline_pen(radius))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def _open_smile(painter: QPainter, cx: float, cy: float, radius: float) -> None:
    """咧嘴大笑：填充的 ∪ 半圆。"""
    rect = QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius)
    path = QPainterPath()
    path.arcMoveTo(rect, 0)
    path.arcTo(rect, 0, 180)
    path.closeSubpath()
    painter.setPen(_outline_pen(radius))
    painter.setBrush(_EYE)
    painter.drawPath(path)


def _frown(painter: QPainter, cx: float, cy: float, radius: float) -> None:
    """撇嘴难过：∩ 形状的上弯弧线。"""
    rect = QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius)
    path = QPainterPath()
    path.arcMoveTo(rect, 180)
    path.arcTo(rect, 180, 180)
    painter.setPen(_outline_pen(radius))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def _o_mouth(painter: QPainter, cx: float, cy: float, radius: float) -> None:
    """认真的小 o 嘴。"""
    painter.setPen(_outline_pen(radius))
    painter.setBrush(_EYE)
    painter.drawEllipse(QPointF(cx, cy), radius * 0.85, radius)


def _sparkle(painter: QPainter, cx: float, cy: float, radius: float) -> None:
    """四角星光。"""
    path = QPainterPath()
    points = (
        (0, -1), (0.3, -0.3), (1, 0), (0.3, 0.3),
        (0, 1), (-0.3, 0.3), (-1, 0), (-0.3, -0.3),
    )
    for index, (dx, dy) in enumerate(points):
        px = cx + dx * radius
        py = cy + dy * radius
        if index == 0:
            path.moveTo(px, py)
        else:
            path.lineTo(px, py)
    path.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_SPARKLE)
    painter.drawPath(path)


def _drop(painter: QPainter, cx: float, cy: float, radius: float) -> None:
    """泪滴 / 汗滴。"""
    path = QPainterPath()
    path.addEllipse(QPointF(cx, cy + radius * 0.35), radius * 0.55, radius * 0.65)
    path.moveTo(cx, cy - radius * 0.55)
    path.lineTo(cx + radius * 0.55, cy + radius * 0.1)
    path.lineTo(cx - radius * 0.55, cy + radius * 0.1)
    path.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_TEAR)
    painter.drawPath(path)


def render_mascot(state: MascotState, size: int = 256) -> QPixmap:
    """把吉祥物画进一个透明背景的方形 QPixmap。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(size / 2, size / 2)

    s = float(size)
    eye_y = 0.06 * s
    eye_x = 0.155 * s
    eye_r = 0.072 * s
    mouth_y = 0.19 * s

    _draw_ears(painter, s)
    _draw_head(painter, s)
    _draw_blush(painter, s)

    if state is MascotState.IDLE:
        _open_eye(painter, -eye_x, eye_y, eye_r)
        _open_eye(painter, eye_x, eye_y, eye_r)
        _stroke_smile(painter, 0, mouth_y, 0.045 * s)
    elif state is MascotState.WORKING:
        _closed_eye(painter, -eye_x, eye_y, eye_r, happy=True)
        _closed_eye(painter, eye_x, eye_y, eye_r, happy=True)
        _o_mouth(painter, 0, mouth_y, 0.028 * s)
        _drop(painter, 0.30 * s, -0.10 * s, 0.055 * s)
    elif state is MascotState.SUCCESS:
        _closed_eye(painter, -eye_x, eye_y, eye_r, happy=True)
        _closed_eye(painter, eye_x, eye_y, eye_r, happy=True)
        _open_smile(painter, 0, mouth_y + 0.01 * s, 0.05 * s)
        _sparkle(painter, -0.36 * s, -0.24 * s, 0.05 * s)
        _sparkle(painter, 0.37 * s, -0.12 * s, 0.04 * s)
        _sparkle(painter, 0, -0.38 * s, 0.03 * s)
    elif state is MascotState.FAIL:
        _closed_eye(painter, -eye_x, eye_y, eye_r, happy=False)
        _closed_eye(painter, eye_x, eye_y, eye_r, happy=False)
        _frown(painter, 0, mouth_y, 0.04 * s)
        _drop(painter, -eye_x, eye_y + 0.10 * s, 0.035 * s)

    painter.end()
    return pixmap
