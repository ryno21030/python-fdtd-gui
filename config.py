"""
config.py
시뮬레이터 전체 설정을 담는 dataclass.
GUI → Config → 시뮬레이터 / JSON 저장·불러오기 모두 이 파일을 경유한다.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

# ── 기본 경로 (스크립트 디렉토리 기준) ──────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "saves")


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
    dt: float = 0.5 / (3**0.5)       # 0이면 Courant 조건으로 자동 계산
    save_every: int = 5

    def auto_dt(self) -> float:
        """Courant 조건으로 dt 계산."""
        import math
        c = 1.0
        return 0.5 / (c * math.sqrt(
            1/self.dx**2 + 1/self.dy**2 + 1/self.dz**2
        ))

    def effective_dt(self) -> float:
        return self.dt if self.dt > 0 else self.auto_dt()

    def n_steps(self) -> int:
        return int(self.T / self.effective_dt())
    
    def validate(self) -> List[str]:
        errors = []
        if self.Nx <= 0: errors.append("Nx는 양수여야 합니다.")
        if self.Ny <= 0: errors.append("Ny는 양수여야 합니다.")
        if self.Nz <= 0: errors.append("Nz는 양수여야 합니다.")
        if self.dx <= 0: errors.append("dx는 양수여야 합니다.")
        if self.dy <= 0: errors.append("dy는 양수여야 합니다.")
        if self.dz <= 0: errors.append("dz는 양수여야 합니다.")
        if self.T <= 0:  errors.append("T는 양수여야 합니다.")
        return errors


# ── 광원 ───────────────────────────────────────────────────
@dataclass
class SourceConfig:
    x: int         = 50
    y: int         = 15
    z: int         = 50
    component: str = "Ez"       # Ex | Ey | Ez
    amplitude: float = 3e-3
    tau:  float    = 8.0
    t0:   float    = 30.0
    name: str      = "소스 #1"

    def validate(self) -> List[str]:
        errors = []
        if self.component not in ("Ex", "Ey", "Ez"):
            errors.append("component는 Ex, Ey, Ez 중 하나여야 합니다.")
        return errors


# ── 재질 / 구조 ────────────────────────────────────────────
@dataclass
class MaterialConfig:
    shape: str  = "Box"          # Box | Sphere | Sawtooth
    n:     float = 1.0
    cond:  float = 0.0
    eps:   float = 1.0           # 유전율
    mu:    float = 1.0           # 투자율
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
    name: str = "구조 #1"

    def validate(self) -> List[str]:
        errors = []

        if self.eps <= 0:
            errors.append("유전율 eps는 양수여야 합니다.")

        if self.mu <= 0:
            errors.append("투자율 mu는 양수여야 합니다.")

        if self.cond < 0:
            errors.append("전도도 cond는 음수일 수 없습니다.")

        if self.x0 < 0 or self.x1 <= self.x0 or self.x1 > self.grid.Nx:
            errors.append("Box의 x0, x1이 유효하지 않습니다.")

        if self.y0 < 0 or self.y1 <= self.y0 or self.y1 > self.grid.Ny:
            errors.append("Box의 y0, y1이 유효하지 않습니다.")

        if self.z0 < 0 or self.z1 <= self.z0 or self.z1 > self.grid.Nz:
            errors.append("Box의 z0, z1이 유효하지 않습니다.")

        if self.r <= 0:
            errors.append("Sphere의 반지름 r은 양수여야 합니다.")

        if self.period <= 0:
            errors.append("Sawtooth의 period는 양수여야 합니다.")

        if self.duty < 0 or self.duty > 1:
            errors.append("Sawtooth의 duty는 0과 1 사이여야 합니다.")
            
        if self.shape not in ("Box", "Sphere", "Sawtooth"):
            errors.append("shape는 Box, Sphere, Sawtooth 중 하나여야 합니다.")
        return errors

    def auto_n(self) -> float:
        self.n = (self.eps * self.mu) ** 0.5
        return self.n



# ── 검광기 ─────────────────────────────────────────────────
@dataclass
class DetectorConfig:
    axis: str = "y"  # 검광면의 법선 축: x | y | z
    index: int = 0   # 검광면의 격자 인덱스
    name: str = "검광기 #1"
    quantities: List[str] = field(
        default_factory=lambda: ["Ex","Ey","Ez","Hx","Hy","Hz"]
    )

    def validate(self) -> List[str]:
        errors = []
        if self.axis not in ("x", "y", "z"):
            errors.append("axis는 x, y, z 중 하나여야 합니다.")
        return errors

# ── PML ────────────────────────────────────────────────────
@dataclass
class PMLConfig:
    thickness:  int   = 10
    R0:         float = 1e-8
    m:          int   = 3
    kappa_max:  float = 5.0
    alpha_max:  float = 0.05

    def validate(self) -> List[str]:
        errors = []
        if self.thickness < 0:
            errors.append("PML 두께는 음수일 수 없습니다.")
        if self.R0 <= 0 or self.R0 >= 1:
            errors.append("R0는 0과 1 사이의 양수여야 합니다.")
        if self.m <= 0:
            errors.append("m은 양의 정수여야 합니다.")
        if self.kappa_max < 1.0:
            errors.append("kappa_max는 1.0 이상이어야 합니다.")
        if self.alpha_max < 0.0:
            errors.append("alpha_max는 음수일 수 없습니다.")
        return errors

# ── Visualize ─────────────────────────────────────────────
@dataclass
class VisualizeConfig:
    quantities: List[str] = field(
        default_factory=lambda: ["Ex","Ey","Ez","Hx","Hy","Hz"]
    )
    
# ── 최상위 설정 ────────────────────────────────────────────
@dataclass
class SimConfig:
    grid:      GridConfig                  = field(default_factory=GridConfig)
    sources:   List[SourceConfig]          = field(default_factory=list)
    materials: List[MaterialConfig]        = field(default_factory=list)
    detectors: List[DetectorConfig]        = field(default_factory=list)
    pml:       PMLConfig                   = field(default_factory=PMLConfig)
    visualize: VisualizeConfig             = field(default_factory=VisualizeConfig)
    output_dir: str = field(default_factory=lambda: _DEFAULT_OUTPUT_DIR)

# ── JSON 직렬화 ──────────────────────────────────────
    def to_json(self, path: str) -> None:
        import math

        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(v) for v in obj]
            if isinstance(obj, float):
                if math.isinf(obj) or math.isnan(obj):
                    return None   # 혹은 0.0으로 대체
            return obj

        data = sanitize(asdict(self))

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


    @classmethod
    def from_json(cls, path: str) -> "SimConfig":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cfg = cls()
        cfg.grid      = GridConfig(**data.get("grid", {}))
        cfg.sources   = [SourceConfig(**s)   for s in data.get("sources",   [])]
        cfg.materials = [MaterialConfig(**m) for m in data.get("materials", [])]
        cfg.detectors = [DetectorConfig(**d) for d in data.get("detectors", [])]
        cfg.pml       = PMLConfig(**data.get("pml", {}))
        cfg.output_dir = data.get("output_dir", cfg.output_dir)
        cfg.visualize = VisualizeConfig(**data.get("visualize", {}))
        return cfg

    # ── 시뮬레이터 코드 생성 ─────────────────────────────
    def to_python(self) -> str:
        """현재 설정으로 시뮬레이터를 구동하는 파이썬 코드 문자열 반환."""
        lines = [
            "# ── 자동 생성된 시뮬레이터 설정 ──",
            f"Nx, Ny, Nz = {self.grid.Nx}, {self.grid.Ny}, {self.grid.Nz}",
            f"dx, dy, dz = {self.grid.dx}, {self.grid.dy}, {self.grid.dz}",
            f"T          = {self.grid.T}",
            f"save_every = {self.grid.save_every}",
            "",
            "# 광원",
            "lights = light_source()",
        ]
        for s in self.sources:
            lines.append(
                f"lights.add(x={s.x}, y={s.y}, z={s.z}, "
                f"t0={s.t0}, tau={s.tau}, amplitude={s.amplitude}, "
                f"component='{s.component}')"
            )
        lines += ["", "# 재질 / 구조", "scene = Scene(Nx, Ny, Nz)"]
        for m in self.materials:
            mat = f"Material(n={m.n}, cond={m.cond})"
            if m.shape == "Box":
                shp = (f"Box({m.x0},{m.x1}, {m.y0},{m.y1}, {m.z0},{m.z1})")
            elif m.shape == "Sphere":
                shp = f"Sphere({m.cx},{m.cy},{m.cz}, {m.r})"
            else:
                shp = (f"AsymmetricSawtooth(z_base={m.z_base}, "
                       f"height={m.height}, period={m.period}, duty={m.duty})")
            lines.append(f"scene.add({shp}, {mat})")
        lines += [
            "",
            "# 검광기",
            "detectors = []",
        ]
        for d in self.detectors:
            lines.append(
                f"detectors.append(Detector(axis='{d.axis}', index={d.index}, "
                f"quantities={d.quantities}))"
                )
        lines += [
            "",
            "# PML",
            f"pml_thick = {self.pml.thickness}",
            f"R0        = {self.pml.R0}",
            f"m0        = {self.pml.m}",
            f"kappa_max = {self.pml.kappa_max}",
            f"alpha_max = {self.pml.alpha_max}",
        ]
        return "\n".join(lines)
