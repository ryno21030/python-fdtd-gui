"""
panels/pml.py
CPML 경계 파라미터 설정 패널.
각 파라미터에 물리적 의미 설명을 함께 제공한다.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel
)
from PyQt6.QtCore import Qt
from config import PMLConfig
from panels._base import (
    section_label, divider, spin, dspin, scrollable_panel
)


class PMLPanel(QWidget):
    def __init__(self, cfg: PMLConfig, parent=None):
        super().__init__(parent)
        self._build_ui(cfg)

    def _build_ui(self, cfg: PMLConfig):
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(10)

        vl.addWidget(section_label("CPML 경계 파라미터"))

        desc = QLabel(
            "CPML(Convolutional PML)은 시뮬레이션 영역 외곽에서 "
            "전자기파를 흡수하는 경계 조건입니다.\n"
            "반사율 R₀을 낮출수록 흡수 성능이 좋아지지만 두께가 충분해야 합니다."
        )
        desc.setStyleSheet("font-size: 13px; color: #6a6a6a; line-height: 1.6;")
        desc.setWordWrap(True)
        vl.addWidget(desc)
        vl.addWidget(divider())

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(12)

        # 두께
        self._thickness = spin(cfg.thickness, lo=2, hi=200)
        self._add_row(form, "두께  (셀 수)",
                      "흡수층 두께. 통상 격자 크기의 10% 권장.",
                      self._thickness)

        # R0
        self._R0 = dspin(cfg.R0, lo=1e-20, hi=1.0, step=1e-9, decimals=10)
        self._add_row(form, "목표 반사율  R₀",
                      "낮을수록 흡수 강도가 높아짐. 1e-8 ~ 1e-12 권장.",
                      self._R0)

        # m
        self._m = spin(cfg.m, lo=1, hi=8)
        self._add_row(form, "차수  m",
                      "σ 프로파일의 다항식 차수. 보통 3 또는 4.",
                      self._m)

        # kappa_max
        self._kappa_max = dspin(cfg.kappa_max, lo=1.0, hi=100.0, step=0.5, decimals=2)
        self._add_row(form, "κ_max",
                      "좌표 신장 계수. 1이면 표준 PML, 클수록 저주파 흡수 향상.",
                      self._kappa_max)

        # alpha_max
        self._alpha_max = dspin(cfg.alpha_max, lo=0.0, hi=1.0, step=0.01, decimals=4)
        self._add_row(form, "α_max",
                      "주파수 이동 계수. 0.05 ~ 0.2 권장. 0이면 표준 CPML.",
                      self._alpha_max)

        vl.addLayout(form)

        # sigma_max 자동 계산 표시
        vl.addWidget(divider())
        self._sigma_label = QLabel()
        self._sigma_label.setStyleSheet("font-size: 13px; color: #9d9d9d;")
        vl.addWidget(self._sigma_label)
        self._update_sigma()

        for w in (self._thickness, self._m, self._R0):
            w.valueChanged.connect(self._update_sigma)

        vl.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scrollable_panel(inner))

    @staticmethod
    def _add_row(form: QFormLayout, label: str, hint: str, widget: QWidget):
        """위젯 + 한 줄 힌트 레이블을 폼에 추가."""
        container = QWidget()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)
        vl.addWidget(widget)
        hint_lbl = QLabel(hint)
        hint_lbl.setStyleSheet("font-size: 13px; color: #5a5a5a;")
        vl.addWidget(hint_lbl)
        form.addRow(label, container)

    def _update_sigma(self):
        import math
        m   = self._m.value()
        R0  = self._R0.value() or 1e-20
        d   = self._thickness.value() or 1
        dx  = 1.0  # 단위 셀
        sigma_max = -(m + 1) * math.log(R0) / (2 * dx * d)
        self._sigma_label.setText(
            f"  자동 계산 σ_max ≈ {sigma_max:.4f}"
        )

    # ── apply / load ──────────────────────────────────────
    def apply_to(self, cfg: PMLConfig):
        cfg.thickness = self._thickness.value()
        cfg.R0        = self._R0.value()
        cfg.m         = self._m.value()
        cfg.kappa_max = self._kappa_max.value()
        cfg.alpha_max = self._alpha_max.value()

    def load_from(self, cfg: PMLConfig):
        self._thickness.setValue(cfg.thickness)
        self._R0.setValue(cfg.R0)
        self._m.setValue(cfg.m)
        self._kappa_max.setValue(cfg.kappa_max)
        self._alpha_max.setValue(cfg.alpha_max)
        self._update_sigma()
