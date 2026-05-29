"""
panels/detector.py
검광기(Detector) 설정 패널.
axis / position / 기록 물리량 체크박스를 제공한다.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QCheckBox, QLabel, QGroupBox, QListWidget, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt
from config import DetectorConfig, SimConfig
from panels._base import (
    section_label, divider, spin, combo, line_edit, scrollable_panel
)

ALL_QUANTITIES = ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]


class DetectorPanel(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg_list: list[DetectorConfig] = []
        if isinstance(cfg, SimConfig):
            default_cfg = cfg.detectors[0] if cfg.detectors else DetectorConfig()
        else:
            default_cfg = cfg if isinstance(cfg, DetectorConfig) else DetectorConfig()
        self._build_ui(default_cfg)

    def _build_ui(self, cfg: DetectorConfig):

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

        ll.addWidget(section_label("검광기 목록"))

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
        self._btn_add.clicked.connect(self._add_detector)
        self._btn_del.clicked.connect(self._del_detector)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_del)
        ll.addLayout(btn_row)

        root.addWidget(left)

        self._editor_sa = self._build_editor()
        root.addWidget(self._editor_sa, stretch=1)

    def _build_editor(self) -> QScrollArea:
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(10)

        dummy = DetectorConfig()

        # ── 기본 설정 ──────────────────────────────────────
        vl.addWidget(section_label("검광기 위치"))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._name     = line_edit(dummy.name)
        self._axis     = combo(["y", "x", "z"], dummy.axis)
        self._position = spin(dummy.position, lo=0, hi=9999)  # index → position

        form.addRow("이름",          self._name)
        form.addRow("법선 축",       self._axis)
        form.addRow("격자 인덱스",   self._position)
        vl.addLayout(form)

        self._axis_hint = QLabel()
        self._axis_hint.setStyleSheet("font-size: 13px; color: #6a6a6a;")
        vl.addWidget(self._axis_hint)
        self._axis.currentTextChanged.connect(self._update_hint)
        self._update_hint(self._axis.currentText())

        vl.addWidget(divider())

        # ── 기록 물리량 ────────────────────────────────────
        vl.addWidget(section_label("기록할 물리량"))

        hint = QLabel("시뮬레이션 루프 내에서 save_every 스텝마다 해당 면을 저장합니다.")
        hint.setStyleSheet("font-size: 13px; color: #6a6a6a;")
        hint.setWordWrap(True)
        vl.addWidget(hint)

        check_grid = QWidget()
        cg_layout = QHBoxLayout(check_grid)
        cg_layout.setContentsMargins(0, 4, 0, 0)
        cg_layout.setSpacing(0)

        self._checks: dict[str, QCheckBox] = {}

        e_box = QGroupBox("E 성분")
        e_box.setStyleSheet(
            "QGroupBox { font-size: 13px; border: 1px solid #555; "
            "border-radius: 5px; padding-top: 12px; margin-top: 4px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }"
        )
        e_vl = QVBoxLayout(e_box)
        e_vl.setSpacing(4)
        for q in ["Ex", "Ey", "Ez"]:
            cb = QCheckBox(q)
            cb.setChecked(q in dummy.quantities)
            cb.setStyleSheet("font-size: 13px;")
            self._checks[q] = cb
            e_vl.addWidget(cb)

        h_box = QGroupBox("H 성분")
        h_box.setStyleSheet(
            "QGroupBox { font-size: 13px; border: 1px solid #555; "
            "border-radius: 5px; padding-top: 12px; margin-top: 4px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }"
        )
        h_vl = QVBoxLayout(h_box)
        h_vl.setSpacing(4)
        for q in ["Hx", "Hy", "Hz"]:
            cb = QCheckBox(q)
            cb.setChecked(q in dummy.quantities)
            cb.setStyleSheet("font-size: 13px;")
            self._checks[q] = cb
            h_vl.addWidget(cb)

        cg_layout.addWidget(e_box)
        cg_layout.addSpacing(12)
        cg_layout.addWidget(h_box)
        cg_layout.addStretch()
        vl.addWidget(check_grid)

        sel_row = QHBoxLayout()
        btn_all  = _small_btn("전체 선택")
        btn_none = _small_btn("전체 해제")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none.clicked.connect(lambda: self._set_all(False))
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        vl.addLayout(sel_row)

        vl.addWidget(divider())

        self._btn_apply = QPushButton("변경 적용")
        self._btn_apply.setFixedHeight(30)
        self._btn_apply.setStyleSheet(
            "QPushButton { border: 1px solid #555; border-radius: 5px; "
            "background: #007acc; color: #fff; font-size: 13px; }"
            "QPushButton:hover { background: #1a8ad4; }"
        )
        self._btn_apply.clicked.connect(self._apply_edit)
        vl.addWidget(self._btn_apply)

        vl.addWidget(divider())

        vl.addWidget(section_label("출력 파일"))
        info = QLabel(
            "시뮬레이션 종료 후  <output_dir>/<dirname>/<name>.npz  로 저장됩니다.\n"
            "배열 shape: (N_frames, dim1, dim2)  —  np.load()로 바로 읽을 수 있습니다."
        )
        info.setStyleSheet("font-size: 13px; color: #6a6a6a; line-height: 1.6;")
        info.setWordWrap(True)
        vl.addWidget(info)

        vl.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidget(inner)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return scroll_area

    def _list_label(self, d: DetectorConfig) -> str:
        return f"{d.name}  [{d.axis}={d.position}]"  # index → position

    def _refresh_list(self):
        self._list.clear()
        for d in self._cfg_list:
            self._list.addItem(self._list_label(d))
        if self._cfg_list:
            self._list.setCurrentRow(0)

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._cfg_list):
            return
        d = self._cfg_list[row]
        self._name.setText(d.name)
        self._axis.setCurrentText(d.axis)
        self._position.setValue(d.position)  # index → position
        for q, cb in self._checks.items():
            cb.setChecked(q in d.quantities)

    def _apply_edit(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cfg_list):
            return
        d = self._cfg_list[row]
        d.name       = self._name.text()
        d.axis       = self._axis.currentText()
        d.position   = self._position.value()  # index → position
        d.quantities = [q for q, cb in self._checks.items() if cb.isChecked()]
        self._list.currentItem().setText(self._list_label(d))

    def _add_detector(self):
        n = len(self._cfg_list) + 1
        d = DetectorConfig(name=f"검광기 #{n}")
        self._cfg_list.append(d)
        self._list.addItem(self._list_label(d))
        self._list.setCurrentRow(len(self._cfg_list) - 1)

    def _del_detector(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cfg_list):
            return
        self._cfg_list.pop(row)
        self._list.takeItem(row)

    # ── 헬퍼 ──────────────────────────────────────────────
    def _update_hint(self, axis: str):
        hints = {
            "x": "YZ 평면  —  shape: (Ny, Nz)",
            "y": "XZ 평면  —  shape: (Nx, Nz)",
            "z": "XY 평면  —  shape: (Nx, Ny)",
        }
        self._axis_hint.setText(f"  → {hints.get(axis, '')}")

    def _set_all(self, state: bool):
        for cb in self._checks.values():
            cb.setChecked(state)

    # ── apply / load ──────────────────────────────────────
    def apply_to(self, cfg):
        if hasattr(cfg, 'detectors'):
            cfg.detectors = self._cfg_list

    def load_from(self, cfg):
        if hasattr(cfg, 'detectors'):
            self._cfg_list = cfg.detectors
        else:
            self._cfg_list = [cfg]
        self._refresh_list()


def _small_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(26)
    btn.setStyleSheet(
        "QPushButton { border: 1px solid #555; border-radius: 4px; "
        "background: #3c3c3c; font-size: 13px; padding: 0 10px; }"
        "QPushButton:hover { background: #2d2d30; }"
    )
    return btn