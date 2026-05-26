from PyQt6.QtWidgets import (
    QWidget, QLabel, QSpinBox, QDoubleSpinBox,
    QComboBox, QLineEdit, QFrame, QScrollArea, QHBoxLayout
)
from PyQt6.QtCore import Qt

# ── 공통 스타일 상수 ───────────────────────────────────────
SECTION_STYLE = (
    "font-size: 12px; font-weight: bold; color: #9d9d9d; "
    "letter-spacing: 1px; margin-top: 6px;"
)
HINT_STYLE   = "font-size: 11px; color: #6a6a6a;"
LABEL_STYLE  = "font-size: 13px; color: #cccccc;"
INPUT_STYLE  = (
    "QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {"
    "  background: #3c3c3c; color: #d4d4d4;"
    "  border: 1px solid #555; border-radius: 4px;"
    "  padding: 3px 7px; font-size: 13px;"
    "}"
    "QSpinBox:focus, QDoubleSpinBox:focus,"
    "QLineEdit:focus, QComboBox:focus { border: 1px solid #007acc; }"
    "QComboBox QAbstractItemView {"
    "  background: #2d2d30; color: #d4d4d4;"
    "  selection-background-color: #264f78; border: 1px solid #555;"
    "}"
)
INPUT_H = 30   # 입력 위젯 높이

BTN_APPLY = (
    "QPushButton { background:#007acc; color:#fff; border:none; "
    "border-radius:4px; padding:5px 16px; font-size:13px; }"
    "QPushButton:hover { background:#1a8ad4; }"
    "QPushButton:pressed { background:#005a9e; }"
)
BTN_SMALL = (
    "QPushButton { background:#3c3c3c; color:#d4d4d4; "
    "border:1px solid #555; border-radius:4px; font-size:12px; }"
    "QPushButton:hover { background:#4a4a4a; border-color:#007acc; }"
)


def section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(SECTION_STYLE)
    return lbl

def hint_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(HINT_STYLE)
    lbl.setWordWrap(True)
    return lbl

def divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: #3c3c3c; margin: 6px 0;")
    return f

def spin(val: int, lo: int = 0, hi: int = 9999) -> QSpinBox:
    w = QSpinBox()
    w.setRange(lo, hi); w.setValue(val)
    w.setStyleSheet(INPUT_STYLE); w.setFixedHeight(INPUT_H)
    return w

def dspin(val: float, lo: float = 0.0, hi: float = 1e9,
          step: float = 0.1, decimals: int = 4) -> QDoubleSpinBox:
    w = QDoubleSpinBox()
    w.setRange(lo, hi); w.setSingleStep(step)
    w.setDecimals(decimals); w.setValue(val)
    w.setStyleSheet(INPUT_STYLE); w.setFixedHeight(INPUT_H)
    return w

def combo(options: list[str], current: str = "") -> QComboBox:
    w = QComboBox()
    w.addItems(options)
    if current in options:
        w.setCurrentText(current)
    w.setStyleSheet(INPUT_STYLE); w.setFixedHeight(INPUT_H)
    return w

def line_edit(text: str = "") -> QLineEdit:
    w = QLineEdit(text)
    w.setStyleSheet(INPUT_STYLE); w.setFixedHeight(INPUT_H)
    return w

def xyz_row(xv, yv, zv, lo=0, hi=9999, step=1.0, decimals=1, integer=False):
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(6)
    spins = []
    for v in (xv, yv, zv):
        sb = spin(int(v), int(lo), int(hi)) if integer \
             else dspin(v, lo, hi, step, decimals)
        spins.append(sb); hl.addWidget(sb)
    return row, spins

def scrollable_panel(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setWidget(inner)
    return sa
