"""
panels/source.py
광원(light_source) 목록 관리 + 개별 편집 패널.
타입: gaussian_pulse(점광원) | gaussian_plane_wave(면광원)
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QFormLayout, QScrollArea, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt
from config import SimConfig, SourceConfig
from panels._base import (
    section_label, divider, spin, dspin, combo, line_edit, xyz_row
)

_TYPES: list[str] = ["gaussian_pulse", "gaussian_plane_wave"]
_TYPE_DISPLAY: list[str] = ["가우시안 펄스 (점광원)", "가우시안 평면파 (면광원)"]
_TYPE_SHORT: list[str] = ["점광원", "면광원"]


def _type_index(type_str: str) -> int:
    try:
        return _TYPES.index(type_str)
    except ValueError:
        return 0


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

        # ── 오른쪽: 편집 ──────────────────────────────────
        root.addWidget(self._build_editor(), stretch=1)

    def _build_editor(self) -> QScrollArea:
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(10)

        vl.addWidget(section_label("선택된 광원 편집"))

        top_form = QFormLayout()
        top_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        top_form.setSpacing(8)

        self._name = line_edit("소스 #1")
        self._type = combo(_TYPE_DISPLAY, _TYPE_DISPLAY[0])
        self._comp = combo(["Ez", "Ex", "Ey"], "Ez")
        self._amp  = dspin(3e-3, lo=0.0, hi=1e3,  step=1e-3, decimals=6)
        self._tau  = dspin(8.0,  lo=0.1, hi=1e4,  step=0.5,  decimals=2)
        self._t0   = dspin(30.0, lo=0.0, hi=1e6,  step=1.0,  decimals=1)

        top_form.addRow("이름",            self._name)
        top_form.addRow("타입",            self._type)
        top_form.addRow("성분 (component)", self._comp)
        top_form.addRow("진폭 (amplitude)", self._amp)
        top_form.addRow("τ  (tau)",         self._tau)
        top_form.addRow("t0",              self._t0)
        vl.addLayout(top_form)

        vl.addWidget(divider())
        vl.addWidget(section_label("위치 파라미터"))

        # 타입별 스택
        self._pos_stack = QStackedWidget()
        self._pos_stack.addWidget(self._build_pulse_fields())
        self._pos_stack.addWidget(self._build_plane_fields())
        self._type.currentIndexChanged.connect(self._pos_stack.setCurrentIndex)
        vl.addWidget(self._pos_stack)

        self._btn_apply = QPushButton("변경 적용")
        self._btn_apply.setFixedHeight(30)
        self._btn_apply.setStyleSheet(
            "QPushButton { border: none; border-radius: 5px; "
            "background: #007acc; color: #fff; font-size: 13px; }"
            "QPushButton:hover { background: #1a8ad4; }"
        )
        self._btn_apply.clicked.connect(self._apply_edit)
        vl.addWidget(self._btn_apply)
        vl.addStretch()

        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setWidget(inner)
        return sa

    def _build_pulse_fields(self) -> QWidget:
        """gaussian_pulse 전용: 점 위치 x, y, z"""
        w = QWidget()
        fl = QFormLayout(w)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fl.setSpacing(8)
        fl.setContentsMargins(0, 0, 0, 0)

        pos_row, self._pos = xyz_row(50, 15, 50, lo=0, hi=9999, integer=True)
        fl.addRow("위치  x / y / z", pos_row)
        return w

    def _build_plane_fields(self) -> QWidget:
        """gaussian_plane_wave 전용: 법선 축 + 슬라이스 위치"""
        w = QWidget()
        fl = QFormLayout(w)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fl.setSpacing(8)
        fl.setContentsMargins(0, 0, 0, 0)

        self._plane_axis = combo(["x", "y", "z"], "y")
        self._plane_pos  = spin(15, 0, 9999)
        fl.addRow("법선 축 (axis)",     self._plane_axis)
        fl.addRow("위치 (position)",    self._plane_pos)
        return w

    # ── 목록 ──────────────────────────────────────────────
    def _list_label(self, s: SourceConfig) -> str:
        return f"{s.name}  [{s.component} | {_TYPE_SHORT[_type_index(s.type)]}]"

    def _refresh_list(self):
        self._list.clear()
        for s in self._cfg.sources:
            self._list.addItem(self._list_label(s))
        if self._cfg.sources:
            self._list.setCurrentRow(0)

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._cfg.sources):
            return
        s = self._cfg.sources[row]
        self._name.setText(s.name)
        self._type.setCurrentIndex(_type_index(s.type))
        self._comp.setCurrentText(s.component)
        self._amp.setValue(s.amplitude)
        self._tau.setValue(s.tau)
        self._t0.setValue(s.t0)
        # 타입별 위치 필드
        for sb, v in zip(self._pos, (s.x, s.y, s.z)):
            sb.setValue(v)
        self._plane_axis.setCurrentText(s.axis)
        self._plane_pos.setValue(s.position)

    def _apply_edit(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cfg.sources):
            return
        s = self._cfg.sources[row]
        s.name      = self._name.text()
        s.type      = _TYPES[self._type.currentIndex()]
        s.component = self._comp.currentText()
        s.amplitude = self._amp.value()
        s.tau       = self._tau.value()
        s.t0        = self._t0.value()
        if s.type == "gaussian_pulse":
            s.x, s.y, s.z = (sb.value() for sb in self._pos)
        else:
            s.axis     = self._plane_axis.currentText()
            s.position = self._plane_pos.value()
        self._list.currentItem().setText(self._list_label(s))

    def _add_source(self):
        n = len(self._cfg.sources) + 1
        s = SourceConfig(name=f"소스 #{n}")
        self._cfg.sources.append(s)
        self._list.addItem(self._list_label(s))
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
