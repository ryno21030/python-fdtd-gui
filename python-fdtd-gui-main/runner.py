"""
runner.py
SimConfig를 받아 시뮬레이터를 별도 QThread에서 실행한다.

신호(signal) 목록
─────────────────
progress  (int)        : 0~100 진행률
status    (str)        : 현재 상태 메시지
finished  ()           : 정상 종료
error     (str)        : 예외 메시지
"""
from __future__ import annotations
import os
import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal
from config import SimConfig

from main_feature.field import Field
from main_feature.CPML import CPML
from main_feature.sources import Sources
from main_feature.engine import Engine
from main_feature.detectors import Detectors
from sub_feature.poynting import Poynting
from main_feature.materials import (
    Material, Box, Sphere, AsymmetricSawtooth, Scene,
    VACUUM, COPPER, GOLD, SILICON, GLASS, WATER
)


class SimRunner(QThread):
    progress = pyqtSignal(int)
    status   = pyqtSignal(str)
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, cfg: SimConfig, parent=None):
        super().__init__(parent)
        self._cfg  = cfg
        self._stop = False

    def stop(self):
        self._stop = True

    # ── 메인 실행 ──────────────────────────────────────────
    def run(self):
        try:
            self._execute()
        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())

    def _build_scene(self, cfg):
        self.grid = cfg.grid
        self.dt = cfg.grid.effective_dt()
        self.grid.dt = self.dt  # engine이 grid.dt를 직접 읽으므로 확정값으로 통일
        scene = Scene(cfg.grid.Nx, cfg.grid.Ny, cfg.grid.Nz)

        for m in cfg.materials:
            if m.shape == "Box":
                shape = Box(m.x0, m.x1, m.y0, m.y1, m.z0, m.z1)
            elif m.shape == "Sphere":
                shape = Sphere(m.cx, m.cy, m.cz, m.r)
            elif m.shape in ["Sawtooth", "AsymmetricSawtooth"]:
                shape = AsymmetricSawtooth(
                    z_base=m.z_base, height=m.height,
                    period=m.period, duty=m.duty
                )
            else:
                raise ValueError(f"지원하지 않는 재질 형태: {m.shape}")
            material = Material(eps_r=m.eps, mu_r=m.mu, cond=m.cond)
            scene.add(shape, material)
        self.baked = scene.bake(self.dt)

    def _build_field(self):
        g = self.grid
        return Field(
            Ex=np.zeros((g.Nx-1, g.Ny,   g.Nz)),
            Ey=np.zeros((g.Nx,   g.Ny-1, g.Nz)),
            Ez=np.zeros((g.Nx,   g.Ny,   g.Nz-1)),
            Hx=np.zeros((g.Nx,   g.Ny-1, g.Nz-1)),
            Hy=np.zeros((g.Nx-1, g.Ny,   g.Nz-1)),
            Hz=np.zeros((g.Nx-1, g.Ny-1, g.Nz)),
        )

    def _build_sources(self, cfg) -> Sources:
        s = Sources()
        for src in cfg.sources:
            if src.type == "gaussian_pulse":
                s.add_gaussian_pulse(
                    x=src.x, y=src.y, z=src.z,
                    t0=src.t0,
                    tau=src.tau,
                    amplitude=src.amplitude,
                    component=src.component,
                )
            elif src.type == "gaussian_plane_wave":
                s.add_gaussian_plane_wave(
                    axis=src.axis,
                    position=src.position,
                    t0=src.t0,
                    tau=src.tau,
                    amplitude=src.amplitude,
                    component=src.component,
                )
            elif src.type == "sinusoidal":
                # TODO: sources.py에 add_sinusoidal 구현 후 활성화
                raise NotImplementedError("sinusoidal 소스는 아직 구현되지 않았습니다.")
            else:
                raise ValueError(f"지원하지 않는 소스 타입: {src.type}")
        return s

    def _build_detectors(self, cfg) -> Detectors:
        seen = set()
        axis_max = {
            'x': self.grid.Nx - 2,
            'y': self.grid.Ny - 2,
            'z': self.grid.Nz - 2,
        }
        d = Detectors()
        for det in cfg.detectors:
            if det.name in seen:
                raise ValueError(f"중복된 검광기 이름: '{det.name}'")
            seen.add(det.name)
            
            if det.type == "plane":
                max_pos = axis_max.get(det.axis, 0)
                if not (0 <= det.position <= max_pos):
                    raise ValueError(
                        f"검광기 '{det.name}'의 position {det.position}이 "
                        f"범위를 벗어남 (0~{max_pos})"
                    )
                d.add_plane_detector(
                    name=det.name,
                    axis=det.axis,
                    position=det.position,
                    record_type=det.quantities,
                )

            elif det.type == "point":
                ix, iy, iz = det.x, det.y, det.z
                if not (0 <= ix < self.grid.Nx and 0 <= iy < self.grid.Ny and 0 <= iz < self.grid.Nz):
                    raise ValueError(
                        f"검광기 '{det.name}'의 position ({ix},{iy},{iz})이 "
                        f"설정한 범위를 벗어남"
                    )
                d.add_point_detector(
                    name=det.name,
                    position=(det.x, det.y, det.z),
                    record_type=det.quantities,
                )

            else:
                raise ValueError(f"지원하지 않는 검광기 타입: {det.type}")
        return d

    def _build_engine(self, cfg):
        self.f = self._build_field()
        self.c = CPML(
            self.grid,
            dt=self.dt,
            pml_thick=cfg.pml.thickness,
            sigma_max=cfg.pml.auto_sigma_max(self.grid),
            kappa_max=cfg.pml.kappa_max,
            alpha_max=cfg.pml.alpha_max,
            m=cfg.pml.m,
        )
        self.s = self._build_sources(cfg)
        self.d = self._build_detectors(cfg)

        needs_local = any(
            q in {"Sx", "Sy", "Sz"}
            for det in cfg.detectors
            for q in det.quantities
        )
        needs_global = cfg.visualize.save_poynting
        self.poynting = Poynting(save_global=needs_global) if (needs_local or needs_global) else None
        if needs_local:
            self.d.bake(self.grid.Nx, self.grid.Ny, self.grid.Nz)

        self.engine = Engine(
            self.f,
            self.baked,
            self.c,
            self.s,
            self.d,
            self.grid,
            poynting=self.poynting,
        )

    def save_results(self):
        buffer = self.d.buffer
        output_dir = self._cfg.output_dir
        dirname = f"save_{int(time.time() * 1000)}"
        path = os.path.join(output_dir, dirname)
        os.makedirs(path, exist_ok=True)

        # 각 detector 저장 (기록된 데이터가 있는 경우만)
        saved_any = False
        for detector in self.d.detectors:
            detname = detector["name"]
            buf = buffer.get(detname, {})
            recorded = [D for D in detector["record_type"] if buf.get(D)]
            if not recorded:
                continue
            saved_any = True
            meta = {"_det_position": detector["position"]}
            if detector["type"] == "plane":
                meta["_det_axis"] = detector["axis"]
            np.savez_compressed(
                os.path.join(path, detname),
                **{D: np.stack(buf[D]) for D in recorded},
                **meta,
            )

        if not saved_any:
            self.status.emit("기록된 데이터 없음 — 저장 건너뜀")
            return

        # metadata 저장
        meta_dict = dict(
            Nx=self.grid.Nx, Ny=self.grid.Ny, Nz=self.grid.Nz,
            dx=self.grid.dx, dy=self.grid.dy, dz=self.grid.dz,
            dt=self.grid.dt,
            T=self.grid.T,
            eps_Ex=self.baked["eps"]["Ex"],
            eps_Ey=self.baked["eps"]["Ey"],
            eps_Ez=self.baked["eps"]["Ez"],
            mu_Hx=self.baked["mu"]["Hx"],
            mu_Hy=self.baked["mu"]["Hy"],
            mu_Hz=self.baked["mu"]["Hz"],
            cond_Ex=self.baked["cond"]["Ex"],
            cond_Ey=self.baked["cond"]["Ey"],
            cond_Ez=self.baked["cond"]["Ez"],
            n_detectors=len(self.d.detectors),
            src_x=np.array([s.x if s.type == "gaussian_pulse" else -1 for s in self._cfg.sources]),
            src_y=np.array([s.y if s.type == "gaussian_pulse" else
                            (s.position if s.axis == "y" else -1) for s in self._cfg.sources]),
            src_z=np.array([s.z if s.type == "gaussian_pulse" else -1 for s in self._cfg.sources]),
        )
        # detector 정보 flatten해서 저장
        for i, det in enumerate(self.d.detectors):
            meta_dict[f"det{i}_name"]     = det["name"]
            meta_dict[f"det{i}_position"] = det["position"]
            if det["type"] == "plane":
                meta_dict[f"det{i}_axis"] = det["axis"]

        np.savez(os.path.join(path, "metadata.npz"), **meta_dict)

        # 전역 Poynting 저장 (save_poynting=True 일 때만)
        if self.poynting is not None and self.poynting.global_buffer:
            buf = self.poynting.global_buffer
            if buf["Sx"]:
                np.savez_compressed(
                    os.path.join(path, "poynting_global.npz"),
                    Sx=np.stack(buf["Sx"]),
                    Sy=np.stack(buf["Sy"]),
                    Sz=np.stack(buf["Sz"]),
                )


    def _execute(self):
        self._build_scene(self._cfg)
        self._build_engine(self._cfg)
        n_steps = self.grid.n_steps()
        for t_step in range(n_steps):
            if self._stop:
                break
            self.engine.step(t_step)
            self.grid.t += self.dt
            progress = int((t_step + 1) / n_steps * 100)
            self.progress.emit(progress)
            self.status.emit(f"진행률: {progress}%")

        self.save_results()
        self.finished.emit()