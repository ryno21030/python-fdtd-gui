"""
[검증 실험 1] 자유공간 전파 속도 검증
────────────────────────────────────────
빈 공간에서 가우시안 펄스를 쏜 뒤, 두 검광기의 피크 도달 시간 차이로
실제 전파 속도를 측정하여 이론값 c=1.0과 비교합니다.

환경 설정
─────────────────────────────────────────────────────────────────────
 격자      : 60 × 200 × 60, dx=dy=dz=1
 PML       : 두께=12, R0=1e-8, kappa_max=3.0, alpha_max=0.05 (CFS-CPML)
 광원      : y=50 (왼쪽 PML에서 38셀 이격), Ez, t0=30, τ=8
 검광기 1  : y=90  (광원에서 40셀)
 검광기 2  : y=150 (광원에서 100셀)

개선 포인트
─────────────────────────────────────────────────────────────────────
 - Nx=Nz=60: x,z 내부 영역(60-24=36셀)을 확보하여 PML 상호작용 완화
 - kappa_max=3: 좌표 신장으로 소멸파(evanescent wave) 흡수 개선
 - alpha_max=0.05: CFS-CPML 적용, 저주파·소멸파 성분 반사 억제
 - SRC_Y=50: 이전 25보다 PML에서 충분히 이격 (3τ ≈ 24셀 이상)
 - 탐색 창: 이론 도달 프레임 ±4τ 내로 한정 → 후반 잡음 무시
"""
import sys, os, math
import numpy as np

from PyQt6.QtCore import QCoreApplication
app = QCoreApplication.instance() or QCoreApplication(sys.argv)

from config import SimConfig, GridConfig, SourceConfig, DetectorConfig, PMLConfig
from runner import SimRunner

# ═══════════════════════════════════════════════════════════════════
# 파라미터
# ═══════════════════════════════════════════════════════════════════
Nx, Ny, Nz  = 60, 200, 60
PML_THICK   = 12
SRC_Y       = 50
DET1_Y      = 90
DET2_Y      = 150
T0, TAU     = 30.0, 8.0
SIM_TIME    = 200.0
C           = 1.0

DT = 0.5 / (C * math.sqrt(1.0/1.0**2 + 1.0/1.0**2 + 1.0/1.0**2))
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_saves")

# ═══════════════════════════════════════════════════════════════════
# SimConfig 구성
# ═══════════════════════════════════════════════════════════════════
cfg = SimConfig(
    grid=GridConfig(
        Nx=Nx, Ny=Ny, Nz=Nz,
        dx=1.0, dy=1.0, dz=1.0,
        T=SIM_TIME, dt=DT, c=C,
        save_every=1,
    ),
    sources=[
        SourceConfig(
            type="gaussian_pulse", name="src",
            x=Nx//2, y=SRC_Y, z=Nz//2,
            component="Ez",
            amplitude=1.0, tau=TAU, t0=T0,
        )
    ],
    materials=[],
    detectors=[
        DetectorConfig(type="plane", name="det1",
                       axis="y", position=DET1_Y, quantities=["Ez"]),
        DetectorConfig(type="plane", name="det2",
                       axis="y", position=DET2_Y, quantities=["Ez"]),
    ],
    pml=PMLConfig(
        thickness=PML_THICK,
        R0=1e-8,
        m=3,
        kappa_max=3.0,    # 소멸파 흡수 개선
        alpha_max=0.05,   # CFS-CPML: 저주파·소멸파 반사 억제
        sigma_max=1.0,    # runner가 auto_sigma_max()로 덮어씀
    ),
    output_dir=OUT_DIR,
)

errors = cfg.validate()
if errors:
    print("설정 오류:")
    for e in errors: print(f"  {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════
# 시뮬레이션 실행
# ═══════════════════════════════════════════════════════════════════
print("=" * 60)
print("  검증 실험 1 : 자유공간 전파 속도")
print("=" * 60)
print(f"  격자              : {Nx}×{Ny}×{Nz}")
print(f"  PML 두께          : {PML_THICK}  (kappa={cfg.pml.kappa_max}, α={cfg.pml.alpha_max})")
print(f"  광원 위치         : y={SRC_Y}  (PML 경계로부터 {SRC_Y-PML_THICK}셀)")
print(f"  검광기 1          : y={DET1_Y}  (광원으로부터 {DET1_Y-SRC_Y}셀)")
print(f"  검광기 2          : y={DET2_Y}  (광원으로부터 {DET2_Y-SRC_Y}셀)")
print()

runner = SimRunner(cfg)
dt = cfg.grid.dt
n_steps = cfg.grid.n_steps()
print(f"  dt (Courant)      : {dt:.6f}")
print(f"  총 스텝           : {n_steps}")
print()

last = [0]
def _prog(p):
    if p - last[0] >= 20:
        print(f"  진행 {p:3d}% ...", flush=True)
        last[0] = p

runner.progress.connect(_prog)
runner.error.connect(lambda e: (print(f"\n  오류: {e}"), sys.exit(1)))
runner.run()
print()

# ═══════════════════════════════════════════════════════════════════
# 분석
# ═══════════════════════════════════════════════════════════════════
buf = runner.d.buffer

ez1 = np.array(buf["det1"]["Ez"])    # (n_frames, Nx, Nz-1)
ez2 = np.array(buf["det2"]["Ez"])

# ── 소스 축(중앙점) 신호만 사용 ──────────────────────────────────
# 공간 최댓값은 PML 경계 잡음을 선택할 수 있으므로,
# 소스와 검광기가 동일 y-축 위에 있는 중앙점 (Nx//2, Nz//2)만 사용한다.
cx = Nx // 2          # x 중앙 인덱스 (소스와 동일)
cz = Nz // 2          # z 중앙 인덱스 (소스와 동일, Ez z축 범위: 0~Nz-2)

sig1 = np.abs(ez1[:, cx, cz])   # (n_frames,)
sig2 = np.abs(ez2[:, cx, cz])

# ── 이론 도달 프레임 주변 ±4τ 창에서 탐색 ────────────────────────
MARGIN = int(4 * TAU / dt)

f1_theory = int((T0 + (DET1_Y - SRC_Y) / C) / dt)
f2_theory = int((T0 + (DET2_Y - SRC_Y) / C) / dt)

w1 = (max(0, f1_theory - MARGIN), min(len(sig1), f1_theory + MARGIN))
w2 = (max(0, f2_theory - MARGIN), min(len(sig2), f2_theory + MARGIN))

peak1 = int(np.argmax(sig1[w1[0]:w1[1]])) + w1[0]
peak2 = int(np.argmax(sig2[w2[0]:w2[1]])) + w2[0]

t1 = peak1 * dt
t2 = peak2 * dt
delta_y = (DET2_Y - DET1_Y) * cfg.grid.dy
delta_t  = t2 - t1

v_meas  = delta_y / delta_t if delta_t > 0 else float("nan")
err_pct = abs(v_meas - C) / C * 100

print("-" * 60)
print("  [분석 결과]")
print("-" * 60)
print(f"  탐색 창 det1      : 프레임 {w1[0]}~{w1[1]}  (이론 중심: {f1_theory})")
print(f"  탐색 창 det2      : 프레임 {w2[0]}~{w2[1]}  (이론 중심: {f2_theory})")
print(f"  det1 피크 프레임  : {peak1}")
print(f"  det2 피크 프레임  : {peak2}")
print(f"  피크 시간 t1      : {t1:.4f}")
print(f"  피크 시간 t2      : {t2:.4f}")
print(f"  Δy                : {delta_y:.1f} 셀")
print(f"  Δt                : {delta_t:.4f} 시간단위")
print()
print(f"  측정 전파 속도    : {v_meas:.6f}")
print(f"  이론값 (c)        : {C:.6f}")
print(f"  오차율            : {err_pct:.4f} %")
print()
if err_pct < 2.0:
    print("  결과 : ✓ 통과  (오차 < 2%)")
elif err_pct < 5.0:
    print("  결과 : △ 허용  (오차 < 5%, 격자 조밀화 고려)")
else:
    print("  결과 : ✗ 오차 큼")
print("=" * 60)
