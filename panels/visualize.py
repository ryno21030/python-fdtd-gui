"""
visualize.py
saves에서 원하는 파일을 
선택, 시각화한다
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QFileDialog, QSlider, QComboBox, QDoubleSpinBox
)

from PyQt6.QtCore import Qt, QTimer
from config import (
        GridConfig, SimConfig
        )
from panels._base import (
    section_label, divider, spin, dspin, xyz_row, scrollable_panel
)
import pyqtgraph as pg
import numpy as np
import os

class VisualizePanel(QWidget):
        def __init__(self, cfg: SimConfig, parent=None):
                super().__init__(parent)
                self.config = cfg
                self.frames = None
                self.index = 0
                self.data = None
                self.file_path = None
                self.metadata = None
                self.sensitivity = 1.0  # 민감도 (1.0 = 정상)
                self.timer = QTimer()
                self.timer.timeout.connect(self.next_frame)
                self._build_ui()
        
        def _build_ui(self):
                root = QVBoxLayout(self)

                # 상단 컨트롤 패널
                top = QHBoxLayout()
                self.btn_open = QPushButton("파일 선택")
                self.label_file = QLabel("선택된 파일: 없음")
                top.addWidget(self.btn_open)
                top.addWidget(self.label_file, 1)
                root.addLayout(top)

                # 필드 선택
                field_layout = QHBoxLayout()
                field_layout.addWidget(QLabel("필드:"))
                self.field_combo = QComboBox()
                self.field_combo.addItems(["Ez", "Ex", "Ey", "Hx", "Hy", "Hz"])
                self.field_combo.currentTextChanged.connect(self.on_field_changed)
                field_layout.addWidget(self.field_combo)

                # 재생 컨트롤
                control_layout = QHBoxLayout()
                self.btn_play = QPushButton("재생")
                self.btn_stop = QPushButton("정지")
                self.slider = QSlider(Qt.Orientation.Horizontal)
                self.label_frame = QLabel("0/0")
                control_layout.addWidget(self.btn_play)
                control_layout.addWidget(self.btn_stop)
                control_layout.addWidget(self.slider, 1)
                control_layout.addWidget(self.label_frame)
                root.addLayout(control_layout)
                
                # 색상맵 선택
                colormap_layout = QHBoxLayout()
                colormap_layout.addWidget(QLabel("색상맵:"))
                self.colormap_combo = QComboBox()
                self.colormap_combo.addItems([
                    "coolwarm", "hot", "viridis", "plasma", "cool", "CET-L4", "gray"
                ])
                self.colormap_combo.currentTextChanged.connect(self.on_colormap_changed)
                colormap_layout.addWidget(self.colormap_combo)
                # 민감도 조절
                sensitivity_layout = QHBoxLayout()
                sensitivity_layout.addWidget(QLabel("민감도:"))
                self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
                self.sensitivity_slider.setMinimum(1)
                self.sensitivity_slider.setMaximum(100)
                self.sensitivity_slider.setValue(10)
                self.sensitivity_slider.setMaximumWidth(150)
                self.sensitivity_slider.valueChanged.connect(self.on_sensitivity_changed)
                sensitivity_layout.addWidget(self.sensitivity_slider)
                self.sensitivity_label = QLabel("1.0x")
                self.sensitivity_label.setMaximumWidth(50)
                sensitivity_layout.addWidget(self.sensitivity_label)

                root2 = QHBoxLayout()
                root2.setContentsMargins(0, 0, 0, 0)
                root2.setSpacing(20)
                root2.addLayout(field_layout)
                root2.addLayout(colormap_layout)
                root2.addLayout(sensitivity_layout)
                root2.addStretch()

                root.addLayout(root2)

                # 이미지 뷰어
                self.viewer = pg.ImageView()
                root.addWidget(self.viewer)

                vb = self.viewer.getView()
                vb.setAspectLocked(True)  # 픽셀 비율 유지

                self.eps_overlay = pg.ImageItem()
                self.eps_overlay.setOpacity(0.35)
                self.eps_overlay.setColorMap(pg.colormap.get("CET-L4"))
                vb.addItem(self.eps_overlay)

                self.src_marker = pg.ScatterPlotItem(
                        size=10, symbol='o',
                        pen=pg.mkPen(color='cyan', width=1.5), 
                        brush=pg.mkBrush(0, 255, 255, 120)
                )
                vb.addItem(self.src_marker)
        
                # 신호 연결
                self.btn_open.clicked.connect(self.open_file)
                self.btn_play.clicked.connect(self.play)
                self.btn_stop.clicked.connect(self.stop)
                self.slider.valueChanged.connect(self.set_frame)
        
        def open_file(self):
                # saves 폴더를 기본 디렉터리로 설정
                # panels/visualize.py -> panels -> fdtd_gui (프로젝트 루트)
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                saves_path = os.path.join(project_root, "saves")
                
                path, _ = QFileDialog.getOpenFileName(
                        self,
                        "npz 파일 선택",
                        saves_path,
                        "NumPy (*.npz)"
                        )

                if not path:
                        return
                
                try:
                    # NpzFile 객체를 일반 dict로 변환
                    npz_file = np.load(path)
                    self.data = {k: npz_file[k] for k in npz_file.files}
                    npz_file.close()
                    self.file_path = path
                    
                    # 파일명 표시
                    filename = os.path.basename(path)
                    self.label_file.setText(f"선택된 파일: {filename}")
                    
                    # 해당 폴더에서 metadata.npz 자동으로 로드
                    self._load_metadata_from_folder(os.path.dirname(path))
                    
                    print(f"DEBUG: Data converted to dict, keys = {list(self.data.keys())}")
                    
                    # 첫 번째 필드부터 표시
                    field_name = self.field_combo.currentText()
                    print(f"DEBUG: Loading field = {field_name}")
                    if field_name in self.data:
                        self.load_field(field_name)
                    else:
                        print(f"DEBUG: Field {field_name} not found. Available: {list(self.data.keys())}")
                except Exception as e:
                    error_msg = f"오류: {str(e)}"
                    print(f"DEBUG: Exception = {error_msg}")
                    import traceback
                    traceback.print_exc()
                    self.label_file.setText(error_msg)
        
        def _apply_overlays(self,meta):
                """EPS, 검출기, 광원 오버레이 적용"""
                if meta is None:
                        return
                
                # EPS 오버레이
                if "eps_vol" in meta:
                        eps_slice = meta["eps_vol"][meta["eps_vol"].shape[0] // 2]
                        self.eps_overlay.setImage(eps_slice, autoLevels=True)
                        self.eps_overlay.setVisible(True)
                else:
                        self.eps_overlay.setVisible(False)

                # 광원 위치 표시
                if "src_x" in meta and "src_y" in meta and "src_z" in meta and "det_axis" in meta and "det_index" in meta:
                        src_x = meta["src_x"]
                        src_y = meta["src_y"]
                        src_z = meta["src_z"]
                        det_axis = meta["det_axis"]
                        det_index = meta["det_index"]

                        # 광원 위치 표시
                        spots = []
                        for x, y, z in zip(src_x, src_y, src_z):
                                if det_axis == 'x' and det_index == y:
                                        spots.append({'pos': (z, x), 'data': 1})
                                elif det_axis == 'y' and det_index == x:
                                        spots.append({'pos': (z, y), 'data': 1})
                                elif det_axis == 'z' and det_index == x:
                                        spots.append({'pos': (y, z), 'data': 1})
                        self.src_marker.setData(spots)
                        self.src_marker.setVisible(True)
                else:
                        self.src_marker.setVisible(False)

        def _load_metadata_from_folder(self, folder):
                """metadata.npz 자동 로드"""
                meta_path = os.path.join(folder, "metadata.npz")
                if os.path.exists(meta_path):
                        try:
                                meta_npz = np.load(meta_path)
                                self.metadata = {k: meta_npz[k] for k in meta_npz.files}
                                meta_npz.close()
                                print(f"DEBUG: Metadata loaded, keys = {list(self.metadata.keys())}")
                                self._apply_overlays(self.metadata)
                        except Exception as e:
                                print(f"DEBUG: Failed to load metadata: {str(e)}")
                                self.metadata = None
                else:
                        print("DEBUG: No metadata.npz found")
                        self.metadata = None
                
        def load_field(self, field_name):
                """특정 필드 로드"""
                if self.data is None or field_name not in self.data:
                        return
                
                self.frames = self.data[field_name]
                self.index = 0
                self.slider.blockSignals(True)
                self.slider.setMinimum(0)
                self.slider.setMaximum(len(self.frames) - 1)
                self.slider.setValue(0)
                self.slider.blockSignals(False)
                self.show_frame(0)
        
        def on_field_changed(self):
                """필드 선택 변경"""
                if not hasattr(self, 'data'):
                        return
                field_name = self.field_combo.currentText()
                self.load_field(field_name)
        
        def play(self):
                self.timer.start(33)
        
        def stop(self):
                self.timer.stop()

        def next_frame(self):
                if self.frames is None:
                        return

                self.index +=1

                if self.index >= len(self.frames):
                        self.timer.stop()
                        return
                
                self.slider.blockSignals(True)
                self.slider.setValue(self.index)
                self.slider.blockSignals(False)
                self.show_frame(self.index)

        def set_frame(self, value):
                self.index = value
                self.show_frame(value)

        def show_frame(self, idx):
                """프레임 표시 - 색상맵 적용 및 민감도 적용"""
                if self.frames is None:
                        return
                
                frame = self.frames[idx-1]
                
                # 2D 슬라이스가 필요한 경우 (3D 데이터의 경우 중간 슬라이스)
                if frame.ndim == 2:
                        image = frame
                else:
                        # 3D 데이터는 중간 슬라이스 사용
                        image = frame[frame.shape[0] // 2]
                
                # float32로 변환
                image = image.astype(np.float32)
                
                # NaN/Inf 제거 및 안전한 범위로 정규화
                image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)
                
                # 필드 값의 절대값 기반 색상화 (propagation 시각화)
                img_abs = np.abs(image)
                img_max = img_abs.max()
                if img_max > 1e-10:
                        # 민감도를 적용하여 약한 신호 증폭
                        image = (img_abs / img_max) ** (1.0 / self.sensitivity)
                else:
                        image = np.zeros_like(image)
                
                self.viewer.setImage(image, autoLevels=False)
                
                # 색상맵 적용
                cmap_name = self.colormap_combo.currentText()
                try:
                    cmap = pg.colormap.get(cmap_name)
                    self.viewer.imageItem.setColorMap(cmap)
                except:
                    pass
                
                # 프레임 번호 표시
                self.label_frame.setText(f"{idx+1}/{len(self.frames)}")
        
        def on_colormap_changed(self):
                """색상맵 변경"""
                if self.frames is None:
                        return
                self.show_frame(self.index)
        
        def on_sensitivity_changed(self):
                """민감도 변경"""
                slider_value = self.sensitivity_slider.value()
                self.sensitivity = slider_value / 10.0
                self.sensitivity_label.setText(f"{self.sensitivity:.1f}x")
                
                # 현재 프레임 다시 표시
                if self.frames is not None:
                        self.show_frame(self.index)
                
        def apply_to(self, cfg: SimConfig):
                pass

        def load_from(self, cfg: SimConfig):
                self._cfg = cfg