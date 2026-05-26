"""
panels/source.py
광원(light_source) 목록 관리 + 개별 편집 패널.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QFormLayout, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from config import SimConfig, SourceConfig
from panels._base import (
    section_label, divider, spin, dspin, combo, line_edit, xyz_row
)


class SourcePanel(QWidget):
    def __init__(self, cfg: SimConfig, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 왼쪽: 목록 ────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(200)
        left.setStyleSheet("background: #252526; border-right: 1px solid #3c3c3c;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 14, 10, 10)
        ll.setSpacing(6)

        ll.addWidget(section_label("광원 목록"))

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { border: 1px solid #555; border-radius: 4px; "
            "background: #3c3c3c; font-size: 13px; }"
            "QListWidget::item:selected { background: #264f78; color: #d4d4d4; }"
        )
        self._list.currentRowChanged.connect(self._on_select)
        ll.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("+ 추가")
        self._btn_del = QPushButton("삭제")
        for btn in (self._btn_add, self._btn_del):
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { border: 1px solid #555; border-radius: 4px; "
                "background: #3c3c3c; font-size: 13px; }"
                "QPushButton:hover { background: #2d2d30; }"
            )
        self._btn_add.clicked.connect(self._add_source)
        self._btn_del.clicked.connect(self._del_source)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_del)
        ll.addLayout(btn_row)

        root.addWidget(left)

        # ── 오른쪽: 편집 (QScrollArea를 self에 저장) ───────
        self._editor_sa = self._build_editor()
        root.addWidget(self._editor_sa, stretch=1)

    def _build_editor(self) -> QScrollArea:
        # inner 위젯
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(10)

        vl.addWidget(section_label("선택된 광원 편집"))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._name = line_edit("소스 #1")
        form.addRow("이름", self._name)

        pos_row, self._pos = xyz_row(50, 15, 50, lo=0, hi=9999, integer=True)
        form.addRow("위치  x / y / z", pos_row)

        self._comp = combo(["Ez", "Ex", "Ey"], "Ez")
        form.addRow("성분  (component)", self._comp)

        self._amp = dspin(3e-3, lo=0, hi=1e3, step=1e-3, decimals=6)
        form.addRow("진폭  (amplitude)", self._amp)

        self._tau = dspin(8.0, lo=0.1, hi=1e4, step=0.5, decimals=2)
        form.addRow("τ  (tau)", self._tau)

        self._t0  = dspin(30.0, lo=0.0, hi=1e6, step=1.0, decimals=1)
        form.addRow("t0", self._t0)

        vl.addLayout(form)

        self._btn_apply = QPushButton("변경 적용")
        self._btn_apply.setFixedHeight(30)
        self._btn_apply.setStyleSheet(
            "QPushButton { border: 1px solid #aaa; border-radius: 5px; "
            "background: #007acc; color: #fff; font-size: 13px; }"
            "QPushButton:hover { background: #1a8ad4; }"
        )
        self._btn_apply.clicked.connect(self._apply_edit)
        vl.addWidget(self._btn_apply)
        vl.addStretch()

        # QScrollArea를 직접 생성하고 반환 (scrollable_panel 대신)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setWidget(inner)
        return sa

    # ── 목록 ──────────────────────────────────────────────
    def _refresh_list(self):
        self._list.clear()
        for s in self._cfg.sources:
            self._list.addItem(f"{s.name}  [{s.component}]")
        if self._cfg.sources:
            self._list.setCurrentRow(0)

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._cfg.sources):
            return
        s = self._cfg.sources[row]
        self._name.setText(s.name)
        for sb, v in zip(self._pos, (s.x, s.y, s.z)):
            sb.setValue(v)
        self._comp.setCurrentText(s.component)
        self._amp.setValue(s.amplitude)
        self._tau.setValue(s.tau)
        self._t0.setValue(s.t0)

    def _apply_edit(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cfg.sources):
            return
        s = self._cfg.sources[row]
        s.name         = self._name.text()
        s.x, s.y, s.z = (sb.value() for sb in self._pos)
        s.component    = self._comp.currentText()
        s.amplitude    = self._amp.value()
        s.tau          = self._tau.value()
        s.t0           = self._t0.value()
        self._list.currentItem().setText(f"{s.name}  [{s.component}]")

    def _add_source(self):
        n = len(self._cfg.sources) + 1
        s = SourceConfig(name=f"소스 #{n}")
        self._cfg.sources.append(s)
        self._list.addItem(f"{s.name}  [{s.component}]")
        self._list.setCurrentRow(len(self._cfg.sources) - 1)

    def _del_source(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cfg.sources):
            return
        self._cfg.sources.pop(row)
        self._list.takeItem(row)

    # ── apply / load ──────────────────────────────────────
    def apply_to(self, cfg: SimConfig):
        pass  # 직접 cfg.sources 수정

    def load_from(self, cfg: SimConfig):
        self._cfg = cfg
        self._refresh_list()
