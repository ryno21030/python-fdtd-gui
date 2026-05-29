"""
config.py
시뮬레이터 전체 설정을 담는 dataclass.
GUI → Config → 시뮬레이터 / JSON 저장·불러오기 모두 이 파일을 경유한다.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict, fields
from typing import List
import numpy as np

# ── 기본 경로 (스크립트 디렉토리 기준) ──────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "saves")


# ── 유틸: 알 수 없는 키 무시하고 dataclass 생성 ─────────────
def _safe_init(cls, data: dict):
    """JSON에 불필요한 키가 있어도 무시하고 dataclass를 생성한다."""
    valid_keys = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in valid_keys})


# ── 격자 / 시간 ────────────────────────────────────────────
@dataclass
class GridConfig:
    Nx: int   = 100
    Ny: int   = 100
    Nz: int   = 100
    dx: float = 1.0
    dy: float = 1.0
    dz: float = 1.0
    T:  float = 120.0
    dt: float = 0.5 / (3**0.5)
    c: float  = 1.0
    t: float  = 0.0
    save_every: int = 5

    def auto_dt(self) -> float:
        import math
        return 0.5 / (self.c * math.sqrt(
            1/self.dx**2 + 1/self.dy**2 + 1/self.dz**2
        ))

    def effective_dt(self) -> float:
        return self.dt if self.dt > 0 else self.auto_dt()

    def n_steps(self) -> int:
        return int(self.T / self.effective_dt())


# ── 광원 ───────────────────────────────────────────────────
@dataclass
class SourceConfig:
    """
    지원 타입
    ─────────────────────────────────────────
    gaussian_pulse  : 가우시안 미분 펄스
        필수 필드: x, y, z, component, amplitude, tau, t0
    """
    type:      str   = "gaussian_pulse"
    name:      str   = "소스 #1"

    # 공통
    x:         int   = 50
    y:         int   = 15
    z:         int   = 50
    component: str   = "Ez"        # Ex | Ey | Ez
    amplitude: float = 3e-3

    # gaussian_pulse 전용
    tau:       float = 8.0
    t0:        float = 30.0

    # sinusoidal 전용 (추후 사용)
    frequency: float = 0.0
    phase:     float = 0.0


# ── 재질 / 구조 ────────────────────────────────────────────
@dataclass
class MaterialConfig:
    shape: str   = "Box"          # Box | Sphere | Sawtooth
    cond:  float = 0.0
    eps:   float = 1.0
    mu:    float = 1.0
    n:     float = 1.0
    # Box 전용
    x0: int = 0;  x1: int = 100
    y0: int = 0;  y1: int = 100
    z0: int = 0;  z1: int = 100
    # Sphere 전용
    cx: int = 50; cy: int = 50; cz: int = 50; r: int = 10
    # Sawtooth 전용
    z_base: int   = 70
    height: int   = 10
    period: int   = 15
    duty:   float = 0.8
    name:   str   = "구조 #1"

    def auto_n(self) -> float:
        self.n = (self.eps * self.mu) ** 0.5
        return self.n


# ── 검광기 ─────────────────────────────────────────────────
@dataclass
class DetectorConfig:
    """
    지원 타입
    ─────────────────────────────────────────
    plane   : 단면 전체를 기록
        필수 필드: axis, position, quantities
    """
    type:       str      = "plane"
    name:       str      = "검광기 #1"

    # plane 전용
    axis:       str      = "y"     # 법선 축: x | y | z
    position:   int      = 50       # 격자 인덱스 (구 이름: index)

    # point 전용 (추후 사용)
    x:          int      = 0
    y:          int      = 0
    z:          int      = 0

    # 공통
    quantities: List[str] = field(
        default_factory=lambda: ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]
    )


# ── PML ────────────────────────────────────────────────────
@dataclass
class PMLConfig:
    thickness:  int   = 10
    R0:         float = 1e-8
    m:          int   = 3
    kappa_max:  float = 1.0
    alpha_max:  float = 0.0
    sigma_max:  float = 1.0

    def auto_sigma_max(self, grid: GridConfig) -> float:
        if self.thickness <= 0:
            return 0.0
        dx = min(grid.dx, grid.dy, grid.dz)
        pml_phys_thickness = self.thickness * dx
        return (
            -(self.m + 1) * np.log(self.R0)
            / (2 * pml_phys_thickness)
        )


# ── Visualize ──────────────────────────────────────────────
@dataclass
class VisualizeConfig:
    quantities: List[str] = field(
        default_factory=lambda: ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]
    )


# ── 최상위 설정 ────────────────────────────────────────────
@dataclass
class SimConfig:
    grid:       GridConfig          = field(default_factory=GridConfig)
    sources:    List[SourceConfig]  = field(default_factory=list)
    materials:  List[MaterialConfig]= field(default_factory=list)
    detectors:  List[DetectorConfig]= field(default_factory=list)
    pml:        PMLConfig           = field(default_factory=PMLConfig)
    visualize:  VisualizeConfig     = field(default_factory=VisualizeConfig)
    output_dir: str                 = field(default_factory=lambda: _DEFAULT_OUTPUT_DIR)

    def validate(self) -> List[str]:
        errors: List[str] = []

        if self.grid.Nx <= 1 or self.grid.Ny <= 1 or self.grid.Nz <= 1:
            errors.append("격자 크기(Nx, Ny, Nz)는 2 이상이어야 합니다.")
        if self.grid.dx <= 0 or self.grid.dy <= 0 or self.grid.dz <= 0:
            errors.append("격자 간격(dx, dy, dz)은 양수여야 합니다.")
        if self.grid.T <= 0:
            errors.append("총 시뮬레이션 시간(T)은 양수여야 합니다.")
        if self.grid.c <= 0:
            errors.append("빛의 속도(c)는 양수여야 합니다.")
        if self.grid.dt < 0:
            errors.append("시간 간격(dt)은 음수일 수 없습니다.")
        if self.grid.save_every <= 0:
            errors.append("save_every는 1 이상의 정수여야 합니다.")

        valid_source_types = {"gaussian_pulse", "sinusoidal"}
        for s in self.sources:
            if s.type not in valid_source_types:
                errors.append(f"지원하지 않는 소스 타입: {s.type}")
            if s.component not in ["Ex", "Ey", "Ez"]:
                errors.append(f"지원하지 않는 소스 컴포넌트: {s.component}")

        valid_detector_types = {"plane", "point"}
        for d in self.detectors:
            if d.type not in valid_detector_types:
                errors.append(f"지원하지 않는 검광기 타입: {d.type}")
            if d.type == "plane" and d.axis not in ["x", "y", "z"]:
                errors.append(f"지원하지 않는 검광기 축: {d.axis}")
            for q in d.quantities:
                if q not in ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]:
                    errors.append(f"지원하지 않는 검광량: {q}")

        if self.pml.thickness < 0:
            errors.append("PML 두께는 음수일 수 없습니다.")
        if self.pml.R0 <= 0 or self.pml.R0 >= 1:
            errors.append("PML R0는 0과 1 사이여야 합니다.")
        if self.pml.m <= 0:
            errors.append("PML m은 양수여야 합니다.")
        if self.pml.kappa_max < 1.0:
            errors.append("PML kappa_max는 1.0 이상이어야 합니다.")
        if self.pml.sigma_max < 0.0:
            errors.append("PML sigma_max는 음수일 수 없습니다.")
        if self.pml.alpha_max < 0.0:
            errors.append("PML alpha_max는 음수일 수 없습니다.")

        return errors

    # ── JSON 직렬화 ────────────────────────────────────────
    def to_json(self, path: str) -> None:
        import math

        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(v) for v in obj]
            if isinstance(obj, float):
                if math.isinf(obj) or math.isnan(obj):
                    return None
            return obj

        with open(path, "w", encoding="utf-8") as f:
            json.dump(sanitize(asdict(self)), f, indent=4, ensure_ascii=False)

    @classmethod
    def from_json(cls, path: str) -> "SimConfig":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cfg = cls()
        cfg.grid      = _safe_init(GridConfig,      data.get("grid", {}))
        cfg.sources   = [_safe_init(SourceConfig,   s) for s in data.get("sources",   [])]
        cfg.materials = [_safe_init(MaterialConfig, m) for m in data.get("materials", [])]
        cfg.detectors = [_safe_init(DetectorConfig, d) for d in data.get("detectors", [])]
        cfg.pml       = _safe_init(PMLConfig,       data.get("pml", {}))
        cfg.visualize = _safe_init(VisualizeConfig, data.get("visualize", {}))
        cfg.output_dir = data.get("output_dir", cfg.output_dir)
        return cfg

    # ── 코드 생성 (디버깅용) ────────────────────────────────
    def correction(self) -> str:
        lines: List[str] = [
            "# 자동 생성된 시뮬레이터 설정 코드",
            "from config import SimConfig, GridConfig, SourceConfig, MaterialConfig, DetectorConfig, PMLConfig, VisualizeConfig",
            "",
            "cfg = SimConfig(",
            "    grid=GridConfig(",
            f"        Nx={self.grid.Nx}, Ny={self.grid.Ny}, Nz={self.grid.Nz},",
            f"        dx={self.grid.dx}, dy={self.grid.dy}, dz={self.grid.dz},",
            f"        T={self.grid.T}, dt={self.grid.dt}, c={self.grid.c},",
            f"        t={self.grid.t}, save_every={self.grid.save_every}",
            "    ),",
        ]

        if self.sources:
            lines.append("    sources=[")
            for s in self.sources:
                lines.append(
                    f"        SourceConfig(type=\"{s.type}\", name=\"{s.name}\", "
                    f"x={s.x}, y={s.y}, z={s.z}, component=\"{s.component}\", "
                    f"amplitude={s.amplitude}, tau={s.tau}, t0={s.t0}),"
                )
            lines.append("    ],")
        else:
            lines.append("    sources=[],")

        if self.materials:
            lines.append("    materials=[")
            for m in self.materials:
                material_fields = [
                    f"shape=\"{m.shape}\"", f"cond={m.cond}",
                    f"eps={m.eps}", f"mu={m.mu}",
                ]
                if m.shape == "Box":
                    material_fields += [f"x0={m.x0}", f"x1={m.x1}", f"y0={m.y0}",
                                        f"y1={m.y1}", f"z0={m.z0}", f"z1={m.z1}"]
                elif m.shape == "Sphere":
                    material_fields += [f"cx={m.cx}", f"cy={m.cy}", f"cz={m.cz}", f"r={m.r}"]
                else:
                    material_fields += [f"z_base={m.z_base}", f"height={m.height}",
                                        f"period={m.period}", f"duty={m.duty}"]
                material_fields.append(f"name=\"{m.name}\"")
                lines.append("        MaterialConfig(" + ", ".join(material_fields) + "),")
            lines.append("    ],")
        else:
            lines.append("    materials=[],")

        if self.detectors:
            lines.append("    detectors=[")
            for d in self.detectors:
                lines.append(
                    f"        DetectorConfig(type=\"{d.type}\", name=\"{d.name}\", "
                    f"axis=\"{d.axis}\", position={d.position}, quantities={d.quantities}),"
                )
            lines.append("    ],")
        else:
            lines.append("    detectors=[],")

        lines.extend([
            "    pml=PMLConfig(",
            f"        thickness={self.pml.thickness}, R0={self.pml.R0}, m={self.pml.m},",
            f"        kappa_max={self.pml.kappa_max}, alpha_max={self.pml.alpha_max}, sigma_max={self.pml.sigma_max}",
            "    ),",
            "    visualize=VisualizeConfig(quantities=["
                + ", ".join(repr(q) for q in self.visualize.quantities) + "]),",
            f"    output_dir={repr(self.output_dir)}",
            ")",
        ])

        return "\n".join(lines)
