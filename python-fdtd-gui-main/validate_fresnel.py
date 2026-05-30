"""
[검증 실험 2] 프레넬 반사 계수 검증
────────────────────────────────────────
유전체 계면(eps=2.25, n=1.5)에서 반사파 진폭을 측정하여
이론 프레넬 계수 r = (n1-n2)/(n1+n2) = -0.2 → R=4% 와 비교합니다.

환경 설정
─────────────────────────────────────────────────────────────────────
 격자      : 60 × 180 × 60, dx=dy=dz=1
 PML       : 두께=12, R0=1e-8, kappa_max=3.0, alpha_max=0.05 (CFS-CPML)
 광원      : y=40 (PML에서 28셀), Ez, t0=30, τ=8
 재질      : eps=2.25 (n=1.5), y=90~179 (반무한 유전체)
 검광기R   : y=65 (입사·반사 측정)
 검광기T   : y=120 (투과파 측정)

시간 분리
─────────────────────────────────────────────────────────────────────
 입사파 피크  : t0 + (65-40)/1  = 55 시간단위
 반사파 피크  : t0 + 25 + 2×25 = 105 시간단위  → 간격 50 >> τ=8 ✓

이론값 (수직 입사, n1=1 → n2=1.5)
─────────────────────────────────────────────────────────────────────
 r = (1-1.5)/(1+1.5) = -0.2   →  |r| = 0.2
 R = r² = 0.04 (4%)           T = n2·t²/n1 = 1.5×0.64 = 0.96
 R + T = 1.00 (에너지 보존)
"""
import sys, os, math
import numpy as np

from PyQt6.QtCore import QCoreApplication
app = QCoreApplication.instance() or QCoreApplication(sys.argv)

from config import SimConfig, GridConfig, SourceConfig, MaterialConfig, DetectorConfig, PMLConfig
from runner import SimRunner

# ═══════════════════════════════════════════════════════════════════
# 파라미터
# ═══════════════════════════════════════════════════════════════════
Nx, Ny, Nz  = 60, 180, 60
PML_THICK   = 12
SRC_Y       = 40
INTERFACE_Y = 90
DET_REF_Y   = 65
DET_TRANS_Y = 120
EPS         = 2.25
N2          = EPS**0.5
T0, TAU     = 30.0, 8.0
SIM_TIME    = 200.0
C           = 1.0

DT = 0.5 / (C * math.sqrt(1.0/1.0**2 + 1.0/1.0**2 + 1.0/1.0**2))
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_saves")

N1 = 1.0
r_theory     = (N1 - N2) / (N1 + N2)
t_amp_theory = 2*N1 / (N1 + N2)
R_theory     = r_theory**2
T_theory     = N2/N1 * t_amp_theory**2

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
    materials=[
        MaterialConfig(
            shape="Box", name="glass_slab",
            eps=EPS, mu=1.0, cond=0.0,
            x0=0, x1=Nx, y0=INTERFACE_Y, y1=Ny,
            z0=0, z1=Nz,
        )
    ],
    detectors=[
        DetectorConfig(type="plane", name="det_ref",
                       axis="y", position=DET_REF_Y,  quantities=["Ez"]),
        DetectorConfig(type="plane", name="det_trans",
                       axis="y", position=DET_TRANS_Y, quantities=["Ez"]),
    ],
    pml=PMLConfig(
        thickness=PML_THICK,
        R0=1e-8,
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
print("  검증 실험 2 : 프레넬 반사 계수")
print("=" * 60)
print(f"  격자              : {Nx}×{Ny}×{Nz}")
print(f"  PML 두께          : {PML_THICK}  (kappa={cfg.pml.kappa_max}, α={cfg.pml.alpha_max})")
print(f"  광원 위치         : y={SRC_Y}  (PML에서 {SRC_Y-PML_THICK}셀)")
print(f"  유전체 eps        : {EPS}  (n = {N2:.4f})")
print(f"  계면 위치         : y={INTERFACE_Y}")
print(f"  검광기 (반사용)   : y={DET_REF_Y}")
print(f"  검광기 (투과용)   : y={DET_TRANS_Y}")
print()
print(f"  이론 |r|          : {abs(r_theory):.4f}")
print(f"  이론 R            : {R_theory:.4f}  ({R_theory*100:.2f}%)")
print(f"  이론 T            : {T_theory:.4f}  ({T_theory*100:.2f}%)")
print(f"  이론 R+T          : {R_theory+T_theory:.4f}")
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

ez_ref   = np.array(buf["det_ref"]["Ez"])
ez_trans = np.array(buf["det_trans"]["Ez"])

# 소스 축(중앙점) 신호만 사용 — 공간 max는 PML 잡음을 선택할 수 있음
cx = Nx // 2
cz = Nz // 2
sig_ref   = np.abs(ez_ref  [:, cx, cz])
sig_trans = np.abs(ez_trans[:, cx, cz])

# ── 각 피크를 이론값 주변 ±4τ 창에서 탐색 ───────────────────────
MARGIN = int(4 * TAU / dt)

t_inc_expected   = T0 + (DET_REF_Y - SRC_Y) / C
t_ref_expected   = T0 + (DET_REF_Y - SRC_Y) / C + 2*(INTERFACE_Y - DET_REF_Y) / C
t_cutoff         = (t_inc_expected + t_ref_expected) / 2
t_trans_expected = T0 + (INTERFACE_Y - SRC_Y) / C + (DET_TRANS_Y - INTERFACE_Y) * N2 / C

frame_cut   = int(t_cutoff / dt)
f_inc       = int(t_inc_expected / dt)
f_ref       = int(t_ref_expected / dt)
f_trans     = int(t_trans_expected / dt)

w_inc   = (max(0, f_inc - MARGIN),   min(frame_cut,      f_inc + MARGIN))
w_ref   = (max(frame_cut, f_ref - MARGIN), min(len(sig_ref),   f_ref + MARGIN))
w_trans = (max(0, f_trans - MARGIN), min(len(sig_trans), f_trans + MARGIN))

A_inc   = float(np.max(sig_ref  [w_inc[0]:w_inc[1]]))   if w_inc[1]  > w_inc[0]  else 0.0
A_ref   = float(np.max(sig_ref  [w_ref[0]:w_ref[1]]))   if w_ref[1]  > w_ref[0]  else 0.0
A_trans = float(np.max(sig_trans[w_trans[0]:w_trans[1]])) if w_trans[1]> w_trans[0] else 0.0

peak_inc_f   = int(np.argmax(sig_ref  [w_inc[0]:w_inc[1]]))   + w_inc[0]
peak_ref_f   = int(np.argmax(sig_ref  [w_ref[0]:w_ref[1]]))   + w_ref[0]
peak_trans_f = int(np.argmax(sig_trans[w_trans[0]:w_trans[1]])) + w_trans[0]

r_meas   = A_ref / A_inc if A_inc > 0 else float("nan")
R_meas   = r_meas**2
r_err    = abs(r_meas - abs(r_theory)) / abs(r_theory) * 100
R_err    = abs(R_meas - R_theory) / R_theory * 100

# 투과 (3D 퍼짐 보정 없이 참고용)
t_amp_meas = A_trans / A_inc if A_inc > 0 else float("nan")

print("-" * 60)
print("  [분석 결과]")
print("-" * 60)
print(f"  입사파  창        : 프레임 {w_inc[0]}~{w_inc[1]}  (이론: {f_inc})")
print(f"  반사파  창        : 프레임 {w_ref[0]}~{w_ref[1]}  (이론: {f_ref})")
print(f"  투과파  창        : 프레임 {w_trans[0]}~{w_trans[1]}  (이론: {f_trans})")
print(f"  입사 피크 프레임  : {peak_inc_f}")
print(f"  반사 피크 프레임  : {peak_ref_f}")
print(f"  투과 피크 프레임  : {peak_trans_f}")
print()
print(f"  입사 진폭 A_inc   : {A_inc:.6e}")
print(f"  반사 진폭 A_ref   : {A_ref:.6e}")
print(f"  투과 진폭 A_trans : {A_trans:.6e}")
print()
print(f"  측정 |r|          : {r_meas:.4f}   (이론: {abs(r_theory):.4f}, 오차: {r_err:.2f}%)")
print(f"  측정 R            : {R_meas:.4f}   (이론: {R_theory:.4f}, 오차: {R_err:.2f}%)")
print(f"  투과 진폭비 (참고): {t_amp_meas:.4f}   (이론 t_amp: {t_amp_theory:.4f})")
print()
if r_err < 5.0:
    print("  결과 : ✓ 통과  (반사 계수 오차 < 5%)")
elif r_err < 15.0:
    print("  결과 : △ 허용  (오차 < 15%, 격자 조밀화 권장)")
else:
    print("  결과 : ✗ 오차 큼")
print()
print("  ※ 반사 계수(동일 위치 측정)는 3D 퍼짐 영향 없음.")
print("     투과 진폭비는 참고용 (거리 차이로 인한 3D 퍼짐 미보정).")
print("=" * 60)
