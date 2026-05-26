"""
theme.py
VS Code Dark+ 계열 팔레트를 QApplication에 적용한다.
main.py에서 app 생성 직후 apply(app) 호출.
"""
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


# ── 색상 토큰 ──────────────────────────────────────────────
BG_BASE      = QColor("#1e1e1e")   # 윈도우/패널 바탕
BG_ALT       = QColor("#252526")   # 사이드바, 인풋 바탕
BG_HIGHLIGHT = QColor("#2d2d30")   # 호버, 선택
BG_BUTTON    = QColor("#3c3c3c")   # 버튼 배경

FG_PRIMARY   = QColor("#d4d4d4")   # 기본 텍스트
FG_SECONDARY = QColor("#9d9d9d")   # 보조 텍스트
FG_DISABLED  = QColor("#5a5a5a")   # 비활성

ACCENT       = QColor("#007acc")   # 파란 강조 (VS Code 시그니처)
ACCENT_HOVER = QColor("#1a8ad4")
BORDER       = QColor("#3c3c3c")   # 테두리

SELECTION_BG = QColor("#264f78")   # 선택 영역 배경
SELECTION_FG = QColor("#ffffff")


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")

    pal = QPalette()

    # 윈도우 배경
    pal.setColor(QPalette.ColorRole.Window,          BG_BASE)
    pal.setColor(QPalette.ColorRole.WindowText,      FG_PRIMARY)

    # 위젯 배경 (QLineEdit, QSpinBox 등)
    pal.setColor(QPalette.ColorRole.Base,            BG_ALT)
    pal.setColor(QPalette.ColorRole.AlternateBase,   BG_HIGHLIGHT)
    pal.setColor(QPalette.ColorRole.Text,            FG_PRIMARY)

    # 버튼
    pal.setColor(QPalette.ColorRole.Button,          BG_BUTTON)
    pal.setColor(QPalette.ColorRole.ButtonText,      FG_PRIMARY)

    # 툴팁
    pal.setColor(QPalette.ColorRole.ToolTipBase,     BG_HIGHLIGHT)
    pal.setColor(QPalette.ColorRole.ToolTipText,     FG_PRIMARY)

    # 선택
    pal.setColor(QPalette.ColorRole.Highlight,       SELECTION_BG)
    pal.setColor(QPalette.ColorRole.HighlightedText, SELECTION_FG)

    # 링크
    pal.setColor(QPalette.ColorRole.Link,            ACCENT)

    # 비활성 그룹
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.WindowText,       FG_DISABLED)
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.Text,             FG_DISABLED)
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.ButtonText,       FG_DISABLED)

    app.setPalette(pal)

    # ── 글로벌 StyleSheet (팔레트로 안 잡히는 세부 위젯) ──
    app.setStyleSheet("""
        /* 기본 폰트 */
        * { font-size: 13px; color: #d4d4d4; }

        /* 입력 위젯 */
        QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QTextEdit {
            background: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 3px 7px;
            selection-background-color: #264f78;
        }
        QSpinBox:focus, QDoubleSpinBox:focus,
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #007acc;
        }
        QComboBox QAbstractItemView {
            background: #2d2d30;
            color: #d4d4d4;
            selection-background-color: #264f78;
            border: 1px solid #555;
        }
        QComboBox::drop-down { border: none; }
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background: #4a4a4a;
            border: none;
            width: 16px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
            background: #007acc;
        }

        /* 버튼 */
        QPushButton {
            background: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 5px 14px;
        }
        QPushButton:hover  { background: #4a4a4a; border-color: #007acc; }
        QPushButton:pressed{ background: #264f78; }
        QPushButton:disabled { color: #5a5a5a; background: #2a2a2a; }

        /* 리스트 */
        QListWidget {
            background: #252526;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            outline: none;
        }
        QListWidget::item { padding: 5px 8px; }
        QListWidget::item:hover    { background: #2d2d30; }
        QListWidget::item:selected { background: #264f78; color: #fff; }

        /* 스크롤바 */
        QScrollBar:vertical {
            background: #1e1e1e; width: 10px; margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #4a4a4a; border-radius: 5px; min-height: 20px;
        }
        QScrollBar::handle:vertical:hover { background: #007acc; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            background: #1e1e1e; height: 10px; margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: #4a4a4a; border-radius: 5px; min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover { background: #007acc; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

        /* 그룹박스 */
        QGroupBox {
            color: #9d9d9d;
            border: 1px solid #3c3c3c;
            border-radius: 5px;
            margin-top: 8px;
            padding-top: 10px;
            font-size: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            color: #9d9d9d;
        }

        /* 체크박스 */
        QCheckBox { color: #d4d4d4; spacing: 6px; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #555; border-radius: 3px;
            background: #3c3c3c;
        }
        QCheckBox::indicator:checked {
            background: #007acc; border-color: #007acc;
        }
        QCheckBox::indicator:hover { border-color: #007acc; }

        /* 프로그레스바 */
        QProgressBar {
            background: #3c3c3c; border: 1px solid #555;
            border-radius: 4px; text-align: center; color: #d4d4d4;
        }
        QProgressBar::chunk { background: #007acc; border-radius: 3px; }

        /* 다이얼로그 */
        QDialog { background: #1e1e1e; }
        QMessageBox { background: #1e1e1e; }
        QMessageBox QLabel { color: #d4d4d4; }

        /* 구분선 */
        QFrame[frameShape="4"],   /* HLine */
        QFrame[frameShape="5"] {  /* VLine */
            color: #3c3c3c;
        }
    """)


# ── 개별 위젯용 스타일 상수 (각 파일에서 import해 사용) ──
BTN_PRIMARY = (
    "QPushButton { background:#007acc; color:#fff; border:none; "
    "border-radius:4px; padding:6px 16px; font-size:13px; font-weight:bold; }"
    "QPushButton:hover { background:#1a8ad4; }"
    "QPushButton:pressed { background:#005a9e; }"
)
BTN_DANGER = (
    "QPushButton { background:#3c3c3c; color:#f48771; border:1px solid #555; "
    "border-radius:4px; padding:5px 14px; }"
    "QPushButton:hover { background:#5a1d1d; border-color:#f48771; }"
)
NAV_STYLE = """
    QPushButton {
        text-align: left;
        padding: 0 18px;
        border: none;
        border-left: 3px solid transparent;
        background: transparent;
        font-size: 13px;
        color: #9d9d9d;
    }
    QPushButton:hover {
        background: #2d2d30;
        color: #d4d4d4;
    }
    QPushButton:checked {
        background: #37373d;
        border-left: 3px solid #007acc;
        color: #ffffff;
        font-weight: bold;
    }
"""
