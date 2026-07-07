"""
analyze_sweep.py
스윕 + iterative 결과를 통합하여 가우시안 프로세스(GP) 서로게이트를 적합하고
최적 파라미터를 출력하며 등고선/OFAT 플롯을 생성한다.

사용:
  python scripts/analyze_sweep.py               # clip 방법 (기본)
  python scripts/analyze_sweep.py --method raw
  python scripts/analyze_sweep.py --method z-only
"""
import argparse
import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, r"C:\Users\ryno1\fdtd-for-light-extraction-experiment")
sys.path.insert(0, _SCRIPTS_DIR)

from extraction import compute_extraction_efficiency
from recalc_efficiency import SOURCE_BOX, EXT_SPEC
plt.rcParams['font.family'] = 'Malgun Gothic'

# ── 인수 파싱 ────────────────────────────────────────────────
# --method raw    : 기존 방식 (하위 호환)
# --method z-only : z 방향만으로 P_total 계산 (eta 상한)
# --method clip   : 소스 박스 경계로 슬라이싱 (권장 보정값)
ap = argparse.ArgumentParser()
ap.add_argument("--method", choices=["raw", "z-only", "clip"], default="clip",
                help="추출율 계산 방법 (기본: clip)")
ap.add_argument("--exp", default="ex", help="실험 네임스페이스 (기본: ex)")
args, _ = ap.parse_known_args()
METHOD = args.method
EXP    = args.exp

# ── 설정 ────────────────────────────────────────────────────
_CORRECTED_JSON = os.path.join(_ROOT, "saves", EXP, "sweep_results_corrected.json")
_RAW_JSON       = os.path.join(_ROOT, "saves", EXP, "sweep_results.json")
RESULTS_JSON    = _CORRECTED_JSON if (METHOD != "raw" and os.path.exists(_CORRECTED_JSON)) else _RAW_JSON
PLOTS_DIR       = os.path.join(_ROOT, "saves", EXP, "sweep_plots")

# 방법별 평판형 기준 추출율 (recalc_efficiency.py 로 사전 계산한 값)
ETA_FLAT_MAP = {
    "raw":    0.037694,
    "z-only": 0.142176,
    "clip":   0.082407,
}
ETA_FLAT = ETA_FLAT_MAP[METHOD]
ETA_KEY  = {"raw": "eta_raw", "z-only": "eta_z", "clip": "eta_clip"}[METHOD]

_ITER_JSON = os.path.join(_ROOT, "saves", EXP, "iterative_results.json")

print(f"[analyze_sweep] method={METHOD}  결과파일={os.path.basename(RESULTS_JSON)}")


# ── 결과 로드 및 효율 계산 ───────────────────────────────────
with open(RESULTS_JSON) as f:
    records = json.load(f)

if os.path.exists(_ITER_JSON):
    with open(_ITER_JSON) as f:
        iter_records = json.load(f)
    existing_keys = {(r["period"], r["height"], r["duty"]) for r in records}
    added = 0
    for r in iter_records:
        key = (r["period"], r["height"], r["duty"])
        if key not in existing_keys and r.get("folder") and r.get(ETA_KEY) and np.isfinite(r[ETA_KEY]):
            records.append(r)
            existing_keys.add(key)
            added += 1
    if added:
        print(f"  + iterative 결과 {added}개 병합 (총 {len(records)}개)")

X_raw, y = [], []
for rec in records:
    folder = rec.get("folder")
    if not folder:
        continue
    try:
        if ETA_KEY in rec:
            eta = float(rec[ETA_KEY])
        else:
            r = compute_extraction_efficiency(folder, SOURCE_BOX, EXT_SPEC)
            eta = r["eta"]
        if not np.isfinite(eta) or eta <= 0:
            continue
        X_raw.append([rec["period"], rec["height"], rec["duty"]])
        y.append(eta)
        print(f"p={rec['period']:2d} h={rec['height']:2d} d={rec['duty']:.2f}  "
              f"eta={eta*100:.3f}%  ({eta/ETA_FLAT:.2f}x)")
    except Exception as e:
        print(f"skip {folder}: {e}")

X_raw = np.array(X_raw, dtype=float)
y     = np.array(y,     dtype=float)
print(f"\n유효 데이터 수: {len(y)}")


# ── GP 정규화 ────────────────────────────────────────────────
P_MIN, P_MAX = 15, 38   # 활성영역 76셀 기준 최소 2주기 (76/38=2.0)
H_MIN, H_MAX = 8,  26   # air_extraction 검출기(z=118) - z_base(90) - 2셀 여유
D_MIN, D_MAX = 0.30, 0.90
_OFFSET = np.array([P_MIN, H_MIN, D_MIN], dtype=float)
_SCALE  = np.array([P_MAX - P_MIN, H_MAX - H_MIN, D_MAX - D_MIN], dtype=float)

def _norm(X): return (X - _OFFSET) / _SCALE

# ── GP 적합 ──────────────────────────────────────────────────
kernel = RBF(length_scale=1.0, length_scale_bounds=(1e-2, 10.0)) \
       + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-8, 1e-1))
gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                               n_restarts_optimizer=10, random_state=42)
gp.fit(_norm(X_raw), y)

y_pred = gp.predict(_norm(X_raw))
r2   = 1.0 - np.sum((y - y_pred)**2) / np.sum((y - y.mean())**2)
rmse = np.sqrt(np.mean((y - y_pred)**2))
print(f"\nGP 적합 결과: R²={r2:.4f}  RMSE={rmse*100:.4f}%")
print(f"커널: {gp.kernel_}")


# ── 그리드 탐색으로 최적 파라미터 찾기 ──────────────────────
p_range = np.linspace(P_MIN, P_MAX, 300)
h_range = np.linspace(H_MIN, H_MAX, 300)
d_range = np.linspace(D_MIN, D_MAX, 300)

pp, hh, dd = np.meshgrid(
    np.linspace(P_MIN, P_MAX, 60),
    np.linspace(H_MIN, H_MAX, 60),
    np.linspace(D_MIN, D_MAX, 30),
    indexing="ij",
)
grid_pts = np.column_stack([pp.ravel(), hh.ravel(), dd.ravel()])
preds = gp.predict(_norm(grid_pts))
best_idx = np.argmax(preds)
best_eta = preds[best_idx]
best_params = tuple(grid_pts[best_idx])

print(f"\n최적 파라미터 (GP 예측):")
print(f"  period = {best_params[0]:.1f} cells  ({best_params[0]*10:.0f} nm)")
print(f"  height = {best_params[1]:.1f} cells  ({best_params[1]*10:.0f} nm)")
print(f"  duty   = {best_params[2]:.3f}")
print(f"  η_pred = {best_eta*100:.3f}%  ({best_eta/ETA_FLAT:.2f}x vs flat)")


# ── 등고선 플롯 ──────────────────────────────────────────────
os.makedirs(PLOTS_DIR, exist_ok=True)
p_opt, h_opt, d_opt = best_params


def predict_grid(ax_x, ax_y, fixed_idx, fixed_val):
    xg, yg = np.meshgrid(ax_x, ax_y)
    pts = np.zeros((xg.size, 3))
    pts[:, fixed_idx] = fixed_val
    a, b = [i for i in range(3) if i != fixed_idx]
    pts[:, a] = xg.ravel()
    pts[:, b] = yg.ravel()
    Z = gp.predict(_norm(pts)).reshape(xg.shape) * 100
    return xg, yg, Z


fig, axes = plt.subplots(1, 3, figsize=(16, 5))
cmap = "plasma"

xg, yg, Z = predict_grid(p_range, h_range, fixed_idx=2, fixed_val=d_opt)
cf = axes[0].contourf(xg, yg, Z, levels=20, cmap=cmap)
cs = axes[0].contour(xg, yg, Z, levels=10, colors="white", linewidths=0.4, alpha=0.5)
axes[0].clabel(cs, inline=True, fontsize=7, fmt="%.2f%%")
axes[0].scatter(X_raw[:,0], X_raw[:,1], c="cyan", s=25, zorder=5, label="측정값")
axes[0].scatter([p_opt], [h_opt], c="red", s=80, marker="*", zorder=6, label="최적점")
axes[0].set_xlabel("Period (cells)", fontsize=11)
axes[0].set_ylabel("Height (cells)", fontsize=11)
axes[0].set_title(f"duty = {d_opt:.2f} 고정", fontsize=11)
axes[0].legend(fontsize=8)
plt.colorbar(cf, ax=axes[0], label="η (%)")

xg, yg, Z = predict_grid(p_range, d_range, fixed_idx=1, fixed_val=h_opt)
cf = axes[1].contourf(xg, yg, Z, levels=20, cmap=cmap)
cs = axes[1].contour(xg, yg, Z, levels=10, colors="white", linewidths=0.4, alpha=0.5)
axes[1].clabel(cs, inline=True, fontsize=7, fmt="%.2f%%")
axes[1].scatter(X_raw[:,0], X_raw[:,2], c="cyan", s=25, zorder=5)
axes[1].scatter([p_opt], [d_opt], c="red", s=80, marker="*", zorder=6)
axes[1].set_xlabel("Period (cells)", fontsize=11)
axes[1].set_ylabel("Duty ratio",     fontsize=11)
axes[1].set_title(f"height = {h_opt:.1f} 고정", fontsize=11)
plt.colorbar(cf, ax=axes[1], label="η (%)")

xg, yg, Z = predict_grid(h_range, d_range, fixed_idx=0, fixed_val=p_opt)
cf = axes[2].contourf(xg, yg, Z, levels=20, cmap=cmap)
cs = axes[2].contour(xg, yg, Z, levels=10, colors="white", linewidths=0.4, alpha=0.5)
axes[2].clabel(cs, inline=True, fontsize=7, fmt="%.2f%%")
axes[2].scatter(X_raw[:,1], X_raw[:,2], c="cyan", s=25, zorder=5)
axes[2].scatter([h_opt], [d_opt], c="red", s=80, marker="*", zorder=6)
axes[2].set_xlabel("Height (cells)", fontsize=11)
axes[2].set_ylabel("Duty ratio",     fontsize=11)
axes[2].set_title(f"period = {p_opt:.1f} 고정", fontsize=11)
plt.colorbar(cf, ax=axes[2], label="η (%)")

fig.suptitle(
    f"OLED 광 추출율 응답면 (GP)  |  R²={r2:.3f}  |  최적 η={best_eta*100:.3f}%",
    fontsize=13, y=1.02
)
plt.tight_layout()
out_path = os.path.join(PLOTS_DIR, "gp_contours.png")
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\n등고선 플롯 저장: {out_path}")


# ── OFAT 1차원 효과 플롯 ──────────────────────────────────────
fig2, axes2 = plt.subplots(1, 3, figsize=(14, 4))
param_labels = ["Period (cells)", "Height (cells)", "Duty ratio"]
param_ranges = [p_range, h_range, d_range]
opt_vals     = list(best_params)

for ax, i, label, rng in zip(axes2, range(3), param_labels, param_ranges):
    pts_list = []
    for v in rng:
        pt = list(opt_vals)
        pt[i] = v
        pts_list.append(pt)
    etas = gp.predict(_norm(np.array(pts_list))) * 100

    ax.plot(rng, etas, "b-", lw=2)
    ax.axvline(opt_vals[i], color="red", ls="--", lw=1.5, label="최적값")
    ax.axhline(ETA_FLAT * 100, color="gray", ls=":", lw=1.2,
               label=f"평판형 {ETA_FLAT*100:.2f}%")

    mask = np.ones(len(X_raw), dtype=bool)
    for j in range(3):
        if j == i:
            continue
        mask &= np.isclose(X_raw[:, j], opt_vals[j], atol=5.0)
    if mask.any():
        ax.scatter(X_raw[mask, i], y[mask] * 100, c="cyan", s=40, zorder=5,
                   edgecolors="black", lw=0.5, label="측정값 (근사)")

    ax.set_xlabel(label, fontsize=11)
    ax.set_ylabel("η (%)", fontsize=11)
    ax.set_title(f"{label} 효과", fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

fig2.suptitle("각 파라미터의 단독 효과 (나머지는 최적값 고정)", fontsize=12, y=1.02)
plt.tight_layout()
out2 = os.path.join(PLOTS_DIR, "ofat_curves.png")
plt.savefig(out2, dpi=150, bbox_inches="tight")
print(f"OFAT 곡선 플롯 저장: {out2}")
