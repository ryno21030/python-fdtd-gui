"""
[검증 실험 3] CPML 흡수 경계 반사율 검증
────────────────────────────────────────
빈 공간에서 한쪽 PML 경계로 파동을 입사시키고,
경계에서 반사된 신호의 진폭 비율로 실제 반사율을 측정합니다.

환경 설정
─────────────────────────────────────────────────────────────────────
 격자      : 60 × 160 × 60
 PML       : 두께=12, R0=1e-8, kappa_max=3.0, alpha_max=0.05 (CFS-CPML)
 광원      : y=80 (중앙), Ez, t0=30, τ=8
 검광기    : y=35 (광원↔왼쪽 PML 사이)

시간 분리
─────────────────────────────────────────────────────────────────────
 입사파(−y) 피크 : t0 + (80-35) = 75 시간단위  (프레임 ≈ 260)
 PML 반사 피크   : t0 + 45 + 2×(35-12) = 121 시간단위  (프레임 ≈ 419)
 두 피크 간격 = 46 시간단위 >> τ=8 → 겹침 없음 ✓

이론값
─────────────────────────────────────────────────────────────────────
 목표 반사율 R0 = 1e-8 (설정값)
 실제 측정값은 FDTD 수치 분산으로 R0보다 크게 나타남
 → R_meas < 1e-4 이면 실용적으로 우수

개선 포인트
─────────────────────────────────────────────────────────────────────
 - kappa_max=3.0: 소멸파·사면 입사 성분 흡수 개선
 - alpha_max=0.05: 저주파 성분의 누적 반사 억제
 - Nx=Nz=60: 내부 공간 확보로 x,z 경계 상호작용 감소
 - 탐색 창: 이론 피크 ±4τ 이내로 한정
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
Nx, Ny, Nz  = 60, 160, 60
PML_THICK   = 12
SRC_Y       = 80
DET_Y       = 35
T0, TAU     = 30.0, 8.0
SIM_TIME    = 160.0
C           = 1.0
R0_TARGET   = 1e-8

DT = 0.5 / (C * math.sqrt(1.0/1.0**2 + 1.0/1.0**2 + 1.0/1.0**2))
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_saves")

dist_inc     = SRC_Y - DET_Y
pml_inner    = PML_THICK
dist_to_pml  = DET_Y - pml_inner

t_inc_peak = T0 + dist_inc / C
t_ref_peak = T0 + dist_inc / C + 2 * dist_to_pml / C

# 오른쪽 PML 반사가 검광기에 도달하는 시각 (탐색 창 상한)
t_right_echo = T0 + 2*(Ny - PML_THICK - SRC_Y) / C + (SRC_Y - DET_Y) / C

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
        DetectorConfig(type="plane", name="det",
                       axis="y", position=DET_Y, quantities=["Ez"]),
    ],
    pml=PMLConfig(
        thickness=PML_THICK,
        R0=R0_TARGET,
        m=3,
        kappa_max=3.0,
        alpha_max=0.05,
        sigma_max=1.0,
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
print("  검증 실험 3 : CPML 흡수 경계 반사율")
print("=" * 60)
print(f"  격자              : {Nx}×{Ny}×{Nz}")
print(f"  PML 두께          : {PML_THICK}  (kappa={cfg.pml.kappa_max}, α={cfg.pml.alpha_max})")
print(f"  목표 반사율 R0    : {R0_TARGET:.0e}")
print(f"  광원              : y={SRC_Y}")
print(f"  검광기            : y={DET_Y}")
print()

runner = SimRunner(cfg)
dt = cfg.grid.dt
n_steps = cfg.grid.n_steps()
print(f"  dt (Courant)      : {dt:.6f}")
print(f"  총 스텝           : {n_steps}")
print(f"  입사 피크 예상    : t={t_inc_peak:.1f}  (프레임 ≈ {int(t_inc_peak/dt)})")
print(f"  반사 피크 예상    : t={t_ref_peak:.1f}  (프레임 ≈ {int(t_ref_peak/dt)})")
print(f"  우측 PML 에코 예상: t={t_right_echo:.1f}  (탐색 창 상한)")
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
ez  = np.array(buf["det"]["Ez"])

# 소스 축(중앙점) 신호만 사용 — 공간 max는 PML 잡음을 선택할 수 있음
cx = Nx // 2
cz = Nz // 2
sig = np.abs(ez[:, cx, cz])

# ── 이론 피크 ±4τ 창에서 탐색 ────────────────────────────────────
MARGIN       = int(4 * TAU / dt)
t_cutoff     = (t_inc_peak + t_ref_peak) / 2
frame_cut    = int(t_cutoff / dt)
frame_ref_end = min(len(sig), int(t_right_echo / dt))

f_inc_c = int(t_inc_peak / dt)
f_ref_c = int(t_ref_peak / dt)

w_inc = (max(0, f_inc_c - MARGIN),        min(frame_cut,     f_inc_c + MARGIN))
w_ref = (max(frame_cut, f_ref_c - MARGIN), min(frame_ref_end, f_ref_c + MARGIN))

win_inc = sig[w_inc[0]:w_inc[1]]
win_ref = sig[w_ref[0]:w_ref[1]]

A_inc = float(np.max(win_inc)) if len(win_inc) > 0 else float("nan")
A_ref = float(np.max(win_ref)) if len(win_ref) > 0 else float("nan")

r_meas = A_ref / A_inc if A_inc > 0 else float("nan")
R_meas = r_meas**2

peak_inc_f = int(np.argmax(win_inc)) + w_inc[0] if len(win_inc) > 0 else -1
peak_ref_f = int(np.argmax(win_ref)) + w_ref[0] if len(win_ref) > 0 else -1

print("-" * 60)
print("  [분석 결과]")
print("-" * 60)
print(f"  입사파 탐색 창    : 프레임 {w_inc[0]}~{w_inc[1]}  (이론: {f_inc_c})")
print(f"  반사파 탐색 창    : 프레임 {w_ref[0]}~{w_ref[1]}  (이론: {f_ref_c})")
print(f"  입사 피크 프레임  : {peak_inc_f}")
print(f"  반사 피크 프레임  : {peak_ref_f}")
print()
print(f"  입사 진폭 A_inc   : {A_inc:.6e}")
print(f"  반사 진폭 A_ref   : {A_ref:.6e}")
print()
print(f"  진폭 반사율 |r|   : {r_meas:.4e}")
print(f"  에너지 반사율 R   : {R_meas:.4e}")
print(f"  목표 반사율 R0    : {R0_TARGET:.4e}")

if not math.isnan(R_meas):
    decades = math.log10(R_meas) if R_meas > 0 else float("-inf")
    print(f"  R / R0            : {R_meas/R0_TARGET:.1f}배  (log: 10^{decades:.1f})")

print()
if not math.isnan(R_meas) and R_meas < 1e-4:
    grade = "✓ 우수  (R < 10⁻⁴)"
elif not math.isnan(R_meas) and R_meas < 1e-2:
    grade = "△ 양호  (R < 10⁻²)"
else:
    grade = "✗ 미흡"
print(f"  평가              : {grade}")
print()
print("  ※ FDTD 수치 분산으로 R > R0 는 정상입니다.")
print("     kappa_max·alpha_max 조정으로 R0에 더 근접시킬 수 있습니다.")
print("=" * 60)
