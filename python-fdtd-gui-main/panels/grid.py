"""
panels/grid.py
격자 크기(Nx/Ny/Nz), 셀 간격(dx/dy/dz), 시간(T/dt/save_every) 설정 패널.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from config import GridConfig
from panels._base import (
    section_label, divider, spin, dspin, xyz_row, scrollable_panel
)


class GridPanel(QWidget):
    def __init__(self, cfg: GridConfig, parent=None):
        super().__init__(parent)
        self._build_ui(cfg)

    def _build_ui(self, cfg: GridConfig):
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(10)

        # ── 격자 크기 ──────────────────────────────────────
        vl.addWidget(section_label("격자 크기"))

        form1 = QFormLayout()
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form1.setSpacing(8)

        nrow, self._N = xyz_row(cfg.Nx, cfg.Ny, cfg.Nz,
                                lo=4, hi=2000, integer=True)
        form1.addRow("Nx / Ny / Nz", nrow)

        drow, self._d = xyz_row(cfg.dx, cfg.dy, cfg.dz,
                                lo=0.01, hi=100, step=0.1, decimals=3)
        form1.addRow("dx / dy / dz", drow)
        vl.addLayout(form1)

        # 격자 크기 요약 레이블
        self._grid_info = QLabel()
        self._grid_info.setStyleSheet("font-size: 13px; color: #6a6a6a;")
        vl.addWidget(self._grid_info)
        self._update_grid_info()

        for sb in self._N + self._d:
            sb.valueChanged.connect(self._update_grid_info)

        vl.addWidget(divider())

        # ── 시간 설정 ──────────────────────────────────────
        vl.addWidget(section_label("시간"))

        form2 = QFormLayout()
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form2.setSpacing(8)

        self._T          = dspin(cfg.T,  lo=1,    hi=1e6, step=10, decimals=1)
        self._dt         = dspin(cfg.effective_dt(), lo=1e-6, hi=10, step=0.001, decimals=6)
        self._save_every = spin(cfg.save_every, lo=1, hi=1000)

        form2.addRow("T  (총 시뮬레이션 시간)", self._T)

        dt_row = QWidget()
        dt_hl  = QHBoxLayout(dt_row)
        dt_hl.setContentsMargins(0, 0, 0, 0)
        dt_hl.setSpacing(6)
        dt_hl.addWidget(self._dt, stretch=1)
        btn_auto = QPushButton("Courant 자동계산")
        btn_auto.setFixedHeight(28)
        btn_auto.setStyleSheet(
            "QPushButton { border: 1px solid #555; border-radius: 4px; "
            "background: #3c3c3c; font-size: 13px; padding: 0 8px; }"
            "QPushButton:hover { background: #2d2d30; }"
        )
        btn_auto.clicked.connect(self._auto_dt)
        dt_hl.addWidget(btn_auto)
        form2.addRow("dt", dt_row)
        form2.addRow("save_every  (스텝)", self._save_every)
        vl.addLayout(form2)

        # 스텝 수 요약
        self._step_info = QLabel()
        self._step_info.setStyleSheet("font-size: 13px; color: #6a6a6a;")
        vl.addWidget(self._step_info)
        self._update_step_info()

        for w in (self._T, self._dt, self._save_every):
            w.valueChanged.connect(self._update_step_info)

        vl.addStretch()

        # 스크롤 래핑
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scrollable_panel(inner))

    # ── 헬퍼 ──────────────────────────────────────────────
    def _update_grid_info(self):
        Nx = self._N[0].value()
        Ny = self._N[1].value()
        Nz = self._N[2].value()
        total = Nx * Ny * Nz
        self._grid_info.setText(
            f"  총 셀 수: {total:,}  ({Nx}×{Ny}×{Nz})"
        )

    def _update_step_info(self):
        T  = self._T.value()
        dt = self._dt.value() or 1e-9
        n  = int(T / dt)
        saved = n // max(self._save_every.value(), 1)
        self._step_info.setText(
            f"  총 {n:,} 스텝 · 저장 {saved:,} 프레임"
        )

    def _auto_dt(self):
        dx = self._d[0].value() or 1e-9
        dy = self._d[1].value() or 1e-9
        dz = self._d[2].value() or 1e-9
        import math
        dt = 0.5 / (1.0 * math.sqrt(1/dx**2 + 1/dy**2 + 1/dz**2))
        self._dt.setValue(dt)

    # ── apply / load ──────────────────────────────────────
    def apply_to(self, cfg: GridConfig):
        cfg.Nx, cfg.Ny, cfg.Nz = (sb.value() for sb in self._N)
        cfg.dx, cfg.dy, cfg.dz = (sb.value() for sb in self._d)
        cfg.T          = self._T.value()
        cfg.dt         = self._dt.value()
        cfg.save_every = self._save_every.value()

    def load_from(self, cfg: GridConfig):
        for sb, v in zip(self._N, (cfg.Nx, cfg.Ny, cfg.Nz)):
            sb.setValue(v)
        for sb, v in zip(self._d, (cfg.dx, cfg.dy, cfg.dz)):
            sb.setValue(v)
        self._T.setValue(cfg.T)
        self._dt.setValue(cfg.effective_dt())
        self._save_every.setValue(cfg.save_every)
