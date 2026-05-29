"""
panels/material.py
Box / Sphere / Sawtooth 구조 목록 관리 + 개별 편집 패널.
형태 선택에 따라 입력 필드가 동적으로 전환된다.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QFormLayout, QLabel, QStackedWidget,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from config import SimConfig, MaterialConfig
from panels._base import (
    section_label, divider, spin, dspin, combo, line_edit, xyz_row, scrollable_panel
)


class MaterialPanel(QWidget):
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

        ll.addWidget(section_label("구조 목록"))

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
        self._btn_add.clicked.connect(self._add_mat)
        self._btn_del.clicked.connect(self._del_mat)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_del)
        ll.addLayout(btn_row)
        root.addWidget(left)

        # ── 오른쪽: 편집 ──────────────────────────────────
        root.addWidget(self._build_editor(), stretch=1)

    def _build_editor(self) -> QWidget:
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(10)

        vl.addWidget(section_label("선택된 구조 편집"))

        top_form = QFormLayout()
        top_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        top_form.setSpacing(8)

        self._name  = line_edit("구조 #1")
        self._shape = combo(["Box", "Sphere", "Sawtooth"], "Box")
        self._eps   = dspin(1.0,  lo=0.1, hi=100.0, step=0.1, decimals=3)
        self._mu    = dspin(1.0,  lo=0.1, hi=100.0, step=0.1, decimals=3)
        self._n     = dspin(1.0,  lo=0.0, hi=10.0, step=0.01, decimals=3)
        self._cond  = dspin(0.0,  lo=0.0, hi=1e6,   step=0.001, decimals=4)

        # n 읽기 전용으로 설정 (자동 계산)
        self._n.setReadOnly(True)
        self._n.setStyleSheet(
            "QDoubleSpinBox { background: #3c3c3c; color: #858585; }"
        )

        top_form.addRow("이름",       self._name)
        top_form.addRow("형태",       self._shape)
        top_form.addRow("굴절률 n",   self._n)  # n = sqrt(eps*mu) 자동 계산
        top_form.addRow("유전율 ε",   self._eps)
        top_form.addRow("투자율 μ",   self._mu)
        top_form.addRow("전도율 σ",   self._cond)

        # eps, mu 변경 시 n 자동 갱신
        self._eps.valueChanged.connect(self._update_n)
        self._mu.valueChanged.connect(self._update_n)
        vl.addLayout(top_form)

        vl.addWidget(divider())
        vl.addWidget(section_label("형태 파라미터"))

        # 형태별 스택
        self._shape_stack = QStackedWidget()
        self._shape_stack.addWidget(self._build_box_fields())
        self._shape_stack.addWidget(self._build_sphere_fields())
        self._shape_stack.addWidget(self._build_sawtooth_fields())
        self._shape.currentIndexChanged.connect(self._shape_stack.setCurrentIndex)
        vl.addWidget(self._shape_stack)

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

        from PyQt6.QtWidgets import QScrollArea
        self._editor_sa = QScrollArea()
        self._editor_sa.setWidgetResizable(True)
        self._editor_sa.setFrameShape(QFrame.Shape.NoFrame)
        self._editor_sa.setWidget(inner)
        return self._editor_sa

    def _build_box_fields(self) -> QWidget:
        w = QWidget()
        fl = QFormLayout(w)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fl.setSpacing(8)
        fl.setContentsMargins(0, 0, 0, 0)

        def range_row(a, b):
            rw = QWidget()
            hl = QHBoxLayout(rw)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(4)
            s0 = spin(a, 0, 9999)
            s1 = spin(b, 0, 9999)
            hl.addWidget(s0); hl.addWidget(QLabel("~")); hl.addWidget(s1)
            return rw, s0, s1

        rw_x, self._bx0, self._bx1 = range_row(10, 90)
        rw_y, self._by0, self._by1 = range_row(40, 55)
        rw_z, self._bz0, self._bz1 = range_row(10, 90)
        fl.addRow("x  범위", rw_x)
        fl.addRow("y  범위", rw_y)
        fl.addRow("z  범위", rw_z)
        return w

    def _build_sphere_fields(self) -> QWidget:
        w = QWidget()
        fl = QFormLayout(w)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fl.setSpacing(8)
        fl.setContentsMargins(0, 0, 0, 0)

        cen_row, self._scen = xyz_row(50, 50, 50, lo=0, hi=9999, integer=True)
        self._sr = spin(10, 1, 9999)
        fl.addRow("중심  cx/cy/cz", cen_row)
        fl.addRow("반지름  r",       self._sr)
        return w

    def _build_sawtooth_fields(self) -> QWidget:
        w = QWidget()
        fl = QFormLayout(w)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fl.setSpacing(8)
        fl.setContentsMargins(0, 0, 0, 0)

        self._st_zbase  = spin(70, 0, 9999)
        self._st_height = spin(10, 1, 9999)
        self._st_period = spin(15, 1, 9999)
        self._st_duty   = dspin(0.8, 0.01, 0.99, step=0.05, decimals=2)

        fl.addRow("z_base  (기저면)",  self._st_zbase)
        fl.addRow("height  (높이)",    self._st_height)
        fl.addRow("period  (주기)",    self._st_period)
        fl.addRow("duty  (비대칭비)",  self._st_duty)
        return w

    # ── 목록 ──────────────────────────────────────────────
    def _update_n(self):
        """eps와 mu로부터 n 자동 계산 (n = sqrt(eps*mu))"""
        eps = self._eps.value()
        mu = self._mu.value()
        n = (eps * mu) ** 0.5
        self._n.blockSignals(True)
        self._n.setValue(n)
        self._n.blockSignals(False)

    def _refresh_list(self):
        self._list.clear()
        for m in self._cfg.materials:
            self._list.addItem(f"{m.name}  [{m.shape}  n={m.n}]")
        if self._cfg.materials:
            self._list.setCurrentRow(0)

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._cfg.materials):
            return
        m = self._cfg.materials[row]
        self._name.setText(m.name)
        self._shape.setCurrentText(m.shape)
        self._eps.setValue(m.eps)
        self._mu.setValue(m.mu)
        self._cond.setValue(m.cond)
        self._update_n()  # eps, mu 설정 후 n 자동 갱신
        # Box
        self._bx0.setValue(m.x0); self._bx1.setValue(m.x1)
        self._by0.setValue(m.y0); self._by1.setValue(m.y1)
        self._bz0.setValue(m.z0); self._bz1.setValue(m.z1)
        # Sphere
        for sb, v in zip(self._scen, (m.cx, m.cy, m.cz)):
            sb.setValue(v)
        self._sr.setValue(m.r)
        # Sawtooth
        self._st_zbase.setValue(m.z_base)
        self._st_height.setValue(m.height)
        self._st_period.setValue(m.period)
        self._st_duty.setValue(m.duty)

    def _apply_edit(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cfg.materials):
            return
        m = self._cfg.materials[row]
        m.name  = self._name.text()
        m.shape = self._shape.currentText()
        m.eps   = self._eps.value()
        m.mu    = self._mu.value()
        m.cond  = self._cond.value()
        m.n     = (m.eps * m.mu) ** 0.5  # n 자동 계산
        m.x0, m.x1 = self._bx0.value(), self._bx1.value()
        m.y0, m.y1 = self._by0.value(), self._by1.value()
        m.z0, m.z1 = self._bz0.value(), self._bz1.value()
        m.cx, m.cy, m.cz = (sb.value() for sb in self._scen)
        m.r       = self._sr.value()
        m.z_base  = self._st_zbase.value()
        m.height  = self._st_height.value()
        m.period  = self._st_period.value()
        m.duty    = self._st_duty.value()
        self._list.currentItem().setText(f"{m.name}  [{m.shape}  n={m.n}]")

    def _add_mat(self):
        n = len(self._cfg.materials) + 1
        m = MaterialConfig(name=f"구조 #{n}")
        self._cfg.materials.append(m)
        self._list.addItem(f"{m.name}  [{m.shape}  n={m.auto_n()}]")
        self._list.setCurrentRow(len(self._cfg.materials) - 1)

    def _del_mat(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cfg.materials):
            return
        self._cfg.materials.pop(row)
        self._list.takeItem(row)

    # ── apply / load ──────────────────────────────────────
    def apply_to(self, cfg: SimConfig):
        pass  # 직접 cfg.materials 수정

    def load_from(self, cfg: SimConfig):
        self._cfg = cfg
        self._refresh_list()
