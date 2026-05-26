"""
mainwindow.py
좌측 네비게이션 + 우측 QStackedWidget 구조의 메인 윈도우.
"""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFileDialog,
    QMessageBox, QFrame, QLineEdit, QDialog,
    QProgressBar, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt

from config import SimConfig
from theme import NAV_STYLE, BTN_PRIMARY
from panels.grid      import GridPanel
from panels.source    import SourcePanel
from panels.material  import MaterialPanel
from panels.detector  import DetectorPanel
from panels.pml       import PMLPanel
from panels.visualize import VisualizePanel


class NavButton(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setStyleSheet(NAV_STYLE)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FDTD 시뮬레이터")
        self.setMinimumSize(860, 620)
        self.resize(1000, 700)
        self.config = SimConfig()
        self._build_ui()
        self._connect_signals()
        self._nav_buttons[0].setChecked(True)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self._build_sidebar())
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        rl.addWidget(sep)
        rl.addWidget(self._build_main_area(), stretch=1)

    # ── 사이드바 ──────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background: #252526;")
        ll = QVBoxLayout(sidebar)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        title = QLabel("  FDTD 시뮬레이터")
        title.setFixedHeight(48)
        title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #cccccc; "
            "background: #252526; border-bottom: 1px solid #3c3c3c;"
        )
        ll.addWidget(title)

        self._nav_buttons: list[NavButton] = []
        for label in ("  격자 / 시간", "  광원", "  재질 / 구조", "  검광기", "  PML 경계", "  시각화"):
            btn = NavButton(label)
            self._nav_buttons.append(btn)
            ll.addWidget(btn)

        ll.addStretch()

        # 하단 영역
        bottom = QWidget()
        bottom.setStyleSheet("background: #252526; border-top: 1px solid #3c3c3c;")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(12, 10, 12, 14)
        bl.setSpacing(7)

        # 출력 경로
        path_lbl = QLabel("출력 경로")
        path_lbl.setStyleSheet("font-size: 12px; color: #9d9d9d;")
        bl.addWidget(path_lbl)

        path_row = QWidget()
        pr = QHBoxLayout(path_row)
        pr.setContentsMargins(0, 0, 0, 0)
        pr.setSpacing(4)
        self._out_path = QLineEdit(self.config.output_dir)
        self._out_path.setFixedHeight(28)
        self._out_path.textChanged.connect(
            lambda t: setattr(self.config, "output_dir", t)
        )
        btn_browse = QPushButton("…")
        btn_browse.setFixedSize(28, 28)
        btn_browse.clicked.connect(self._browse_output)
        pr.addWidget(self._out_path)
        pr.addWidget(btn_browse)
        bl.addWidget(path_row)

        self.btn_save = QPushButton("설정 저장")
        self.btn_load = QPushButton("설정 불러오기")
        self.btn_run  = QPushButton("▶  시뮬레이션 실행")
        self.btn_run.setFixedHeight(36)
        self.btn_run.setStyleSheet(BTN_PRIMARY)

        for btn in (self.btn_save, self.btn_load):
            btn.setFixedHeight(30)
        bl.addWidget(self.btn_save)
        bl.addWidget(self.btn_load)
        bl.addWidget(self.btn_run)
        ll.addWidget(bottom)
        return sidebar

    # ── 메인 영역 ─────────────────────────────────────────
    def _build_main_area(self) -> QWidget:
        area = QWidget()
        al = QVBoxLayout(area)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(0)

        self._topbar_label = QLabel("격자 / 시간 설정")
        self._topbar_label.setFixedHeight(48)
        self._topbar_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; padding-left: 22px; "
            "color: #cccccc; background: #1e1e1e; "
            "border-bottom: 1px solid #3c3c3c;"
        )
        al.addWidget(self._topbar_label)

        self._stack = QStackedWidget()
        self._panels = [
            GridPanel(self.config.grid),
            SourcePanel(self.config),
            MaterialPanel(self.config),
            DetectorPanel(self.config),
            PMLPanel(self.config.pml),
            VisualizePanel(self.config.visualize)
        ]
        self._panel_titles = [
            "격자 / 시간 설정", "광원 설정", "재질 / 구조 설정",
            "검광기 설정", "PML 경계 설정", "시각화"
        ]
        for p in self._panels:
            self._stack.addWidget(p)
        al.addWidget(self._stack, stretch=1)

        self._statusbar = QLabel("  준비됨")
        self._statusbar.setFixedHeight(26)
        self._statusbar.setStyleSheet(
            "font-size: 12px; color: #9d9d9d; background: #252526; "
            "border-top: 1px solid #3c3c3c; padding-left: 8px;"
        )
        al.addWidget(self._statusbar)
        return area

    # ── 시그널 ────────────────────────────────────────────
    def _connect_signals(self):
        for i, btn in enumerate(self._nav_buttons):
            btn.clicked.connect(lambda _, idx=i: self._switch_panel(idx))
        self.btn_save.clicked.connect(self._save_config)
        self.btn_load.clicked.connect(self._load_config)
        self.btn_run.clicked.connect(self._run_simulation)

    def _switch_panel(self, idx: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)
        self._topbar_label.setText(self._panel_titles[idx])

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if path:
            self._out_path.setText(path)
            self.config.output_dir = path

    # ── 설정 저장/불러오기 ────────────────────────────────
    def _collect_config(self):
        self._panels[0].apply_to(self.config.grid)
        self._panels[1].apply_to(self.config)
        self._panels[2].apply_to(self.config)
        self._panels[3].apply_to(self.config)
        self._panels[4].apply_to(self.config.pml)

    def _save_config(self):
        self._collect_config()
        path, _ = QFileDialog.getSaveFileName(self, "설정 저장", "", "JSON (*.json)")
        if path:
            self.config.to_json(path)
            self._statusbar.setText(f"  저장 완료: {path}")

    def _load_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "설정 불러오기", "", "JSON (*.json)")
        if not path:
            return
        try:
            self.config = SimConfig.from_json(path)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 파일 오류:\n{e}")
            return
        self._panels[0].load_from(self.config.grid)
        self._panels[1].load_from(self.config)
        self._panels[2].load_from(self.config)
        self._panels[3].load_from(self.config)
        self._panels[4].load_from(self.config.pml)
        self._panels[5].load_from(self.config.visualize)
        self._statusbar.setText(f"  불러옴: {path}")

    # ── 실행 ─────────────────────────────────────────────
    def _run_simulation(self):
        self._collect_config()
        if not self.config.output_dir:
            QMessageBox.warning(self, "경고", "출력 경로를 설정하세요.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("시뮬레이션 설정 확인")
        dlg.resize(640, 440)
        vl = QVBoxLayout(dlg)
        info = QLabel("아래 설정으로 시뮬레이션을 실행합니다.")
        info.setStyleSheet("font-size: 13px; color: #9d9d9d; padding: 4px 0;")
        vl.addWidget(info)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(self.config.to_python())
        te.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 13px; "
            "background: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c;"
        )
        vl.addWidget(te)
        bb = QDialogButtonBox()
        btn_ok  = bb.addButton("실행", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_ok.setStyleSheet(BTN_PRIMARY)
        bb.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        vl.addWidget(bb)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self._prog_dlg = _ProgressDialog(self)
        self._prog_dlg.show()

        from runner import SimRunner
        self._runner = SimRunner(self.config, parent=self)
        self._runner.progress.connect(self._prog_dlg.set_progress)
        self._runner.status.connect(self._prog_dlg.set_status)
        self._runner.status.connect(self._statusbar.setText)
        self._runner.finished.connect(self._on_sim_finished)
        self._runner.error.connect(self._on_sim_error)
        self._prog_dlg.btn_cancel.clicked.connect(self._runner.stop)
        self._runner.start()
        self.btn_run.setEnabled(False)

    def _on_sim_finished(self):
        self.btn_run.setEnabled(True)
        if hasattr(self, "_prog_dlg"):
            self._prog_dlg.accept()
        QMessageBox.information(self, "완료", "시뮬레이션이 정상 종료되었습니다.")

    def _on_sim_error(self, msg: str):
        self.btn_run.setEnabled(True)
        if hasattr(self, "_prog_dlg"):
            self._prog_dlg.reject()
        QMessageBox.critical(self, "오류", f"시뮬레이션 오류:\n\n{msg}")


# ── 진행률 다이얼로그 ──────────────────────────────────────
class _ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("시뮬레이션 실행 중")
        self.setFixedSize(440, 160)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        vl = QVBoxLayout(self)
        vl.setSpacing(12)
        vl.setContentsMargins(24, 20, 24, 20)

        self._status = QLabel("초기화 중...")
        self._status.setStyleSheet("font-size: 13px; color: #9d9d9d;")
        vl.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(18)
        vl.addWidget(self._bar)

        self.btn_cancel = QPushButton("중단")
        self.btn_cancel.setFixedHeight(30)
        self.btn_cancel.setStyleSheet(
            "QPushButton { background:#3c3c3c; color:#f48771; "
            "border:1px solid #555; border-radius:4px; }"
            "QPushButton:hover { background:#5a1d1d; border-color:#f48771; }"
        )
        vl.addWidget(self.btn_cancel, alignment=Qt.AlignmentFlag.AlignRight)

    def set_progress(self, val: int): self._bar.setValue(val)
    def set_status(self, msg: str):   self._status.setText(msg)
