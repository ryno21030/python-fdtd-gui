"""
analyze_sweep.py
스윕 결과를 불러와 2차 다항식 RSM 회귀분석 후 최적 파라미터를 출력하고
등고선 플롯을 생성한다.

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
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

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
args, _ = ap.parse_known_args()
METHOD = args.method

# ── 설정 ────────────────────────────────────────────────────
_CORRECTED_JSON = os.path.join(_ROOT, "saves", "sweep_results_corrected.json")
_RAW_JSON       = os.path.join(_ROOT, "saves", "sweep_results.json")
RESULTS_JSON    = _CORRECTED_JSON if (METHOD != "raw" and os.path.exists(_CORRECTED_JSON)) else _RAW_JSON
PLOTS_DIR       = os.path.join(_ROOT, "saves", "sweep_plots")

# 방법별 평판형 기준 추출율 (recalc_efficiency.py 로 사전 계산한 값)
ETA_FLAT_MAP = {
    "raw":    0.01011,
    "z-only": 0.04137,
    "clip":   0.02184,
}
ETA_FLAT = ETA_FLAT_MAP[METHOD]
ETA_KEY  = {"raw": "eta_raw", "z-only": "eta_z", "clip": "eta_clip"}[METHOD]

print(f"[analyze_sweep] method={METHOD}  결과파일={os.path.basename(RESULTS_JSON)}")


# ── 결과 로드 및 효율 계산 ───────────────────────────────────
with open(RESULTS_JSON) as f:
    records = json.load(f)

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


# ── 2차 다항식 RSM 적합 ──────────────────────────────────────
poly  = PolynomialFeatures(degree=2, include_bias=True)
X_fit = poly.fit_transform(X_raw)
model = LinearRegression(fit_intercept=False)
model.fit(X_fit, y)
y_pred = model.predict(X_fit)
r2   = model.score(X_fit, y)
rmse = np.sqrt(np.mean((y - y_pred)**2))
print(f"\nRSM 적합 결과: R²={r2:.4f}  RMSE={rmse*100:.4f}%")
print("회귀 계수 (feature, coef):")
for name, coef in zip(poly.get_feature_names_out(["period","height","duty"]), model.coef_):
    if abs(coef) > 1e-8:
        print(f"  {name:25s} {coef*100:+.4f}%")


# ── 그리드 탐색으로 최적 파라미터 찾기 ──────────────────────
p_range = np.linspace(X_raw[:,0].min(), X_raw[:,0].max(), 300)
h_range = np.linspace(X_raw[:,1].min(), X_raw[:,1].max(), 300)
d_range = np.linspace(X_raw[:,2].min(), X_raw[:,2].max(), 300)

best_eta = -1
best_params = None
for p in np.linspace(X_raw[:,0].min()-5, X_raw[:,0].max()+5, 60):
    for h in np.linspace(X_raw[:,1].min()-2, X_raw[:,1].max()+2, 60):
        for d in np.linspace(0.3, 0.95, 30):
            pred = model.predict(poly.transform([[p, h, d]]))[0]
            if pred > best_eta:
                best_eta    = pred
                best_params = (p, h, d)

print(f"\n최적 파라미터 (RSM 예측):")
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
    Z = model.predict(poly.transform(pts)).reshape(xg.shape) * 100
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
    f"OLED 광 추출율 응답면 (RSM)  |  R²={r2:.3f}  |  최적 η={best_eta*100:.3f}%",
    fontsize=13, y=1.02
)
plt.tight_layout()
out_path = os.path.join(PLOTS_DIR, "rsm_contours.png")
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
    etas = model.predict(poly.transform(np.array(pts_list))) * 100

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
