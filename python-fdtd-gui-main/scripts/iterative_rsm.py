"""
iterative_rsm.py
Sequential Bayesian Optimization: 가우시안 프로세스(GP) 서로게이트 + Expected Improvement
획득 함수로 탐색/활용을 균형 있게 조절하며 광추출율 극점을 자동 탐색한다.

알고리즘:
  1. 기존 데이터 로드 (sweep_results_corrected.json)
  2. GP 적합 (RBF + WhiteKernel)
  3. Expected Improvement 최대 점 탐색 → 이미 시뮬레이션된 점 근처 제외
  4. (p*, h*, d*) 시뮬레이션 실행
  5. eta_clip 계산 후 데이터에 추가
  6. max_ei < ei_tol 이면 수렴 종료
  7. max_iter 까지 반복

사용: python scripts/iterative_rsm.py [--max-iter 10] [--ei-tol 1e-5] [--xi 0.01]
"""
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from tqdm import tqdm

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _SCRIPTS_DIR)

from recalc_efficiency import compute_corrected, SOURCE_BOX, EXT_SPEC

TEMPLATE         = os.path.join(_ROOT, "saves", "oled_sawtooth.json")
_WORKER          = os.path.join(_SCRIPTS_DIR, "sweep_worker.py")

# ── 탐색 범위 ────────────────────────────────────────────────────
BOUNDS = {
    "period": (15, 38),    # 셀 (정수) — 활성영역 76셀 기준 최소 2주기 보장 (76/38=2.0)
    "height": (8,  26),    # 셀 (정수) — air_extraction 검출기(z=118) - z_base(90) - 2셀 여유
    "duty":   (0.30, 0.90),
}

# 파라미터 스케일 (GP 입력 정규화용)
_SCALE = np.array([
    BOUNDS["period"][1] - BOUNDS["period"][0],
    BOUNDS["height"][1] - BOUNDS["height"][0],
    BOUNDS["duty"][1]   - BOUNDS["duty"][0],
], dtype=float)
_OFFSET = np.array([BOUNDS["period"][0], BOUNDS["height"][0], BOUNDS["duty"][0]], dtype=float)

# ── 그리드 탐색 해상도 ───────────────────────────────────────────
SEARCH_GRID = {
    "period": np.arange(BOUNDS["period"][0], BOUNDS["period"][1] + 1, 1, dtype=float),
    "height": np.arange(BOUNDS["height"][0], BOUNDS["height"][1] + 1, 1, dtype=float),
    "duty":   np.arange(BOUNDS["duty"][0],   BOUNDS["duty"][1]   + 0.01, 0.05),
}


def _normalize(X: np.ndarray) -> np.ndarray:
    return (X - _OFFSET) / _SCALE


def _denormalize(X_norm: np.ndarray) -> np.ndarray:
    return X_norm * _SCALE + _OFFSET


# ── GP 적합 ──────────────────────────────────────────────────────
def fit_gp(records):
    X, y = [], []
    for r in records:
        eta = r.get("eta_clip")
        if eta is None or not np.isfinite(eta) or eta <= 0:
            continue
        X.append([r["period"], r["height"], r["duty"]])
        y.append(eta)
    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)

    X_norm = _normalize(X)

    kernel = RBF(length_scale=1.0, length_scale_bounds=(1e-2, 10.0)) \
           + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-8, 1e-1))
    gp = GaussianProcessRegressor(
        kernel=kernel,
        normalize_y=True,
        n_restarts_optimizer=10,
        random_state=42,
    )
    gp.fit(X_norm, y)

    mu_train = gp.predict(X_norm)
    ss_res = np.sum((y - mu_train) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return gp, X, y, r2


# ── Expected Improvement 획득 함수 ────────────────────────────────
def expected_improvement(mu: np.ndarray, sigma: np.ndarray, best: float, xi: float = 0.01) -> np.ndarray:
    z = (mu - best - xi) / (sigma + 1e-12)
    ei = (mu - best - xi) * norm.cdf(z) + sigma * norm.pdf(z)
    ei[sigma < 1e-12] = 0.0
    return ei


# ── 다음 탐색점 선택 (최대 EI) ──────────────────────────────────
def find_next_ei(gp, best_eta: float, existing_params, xi: float = 0.01, min_dist: float = 2.0):
    pg = SEARCH_GRID["period"]
    hg = SEARCH_GRID["height"]
    dg = SEARCH_GRID["duty"]

    pp, hh, dd = np.meshgrid(pg, hg, dg, indexing="ij")
    pts = np.column_stack([pp.ravel(), hh.ravel(), dd.ravel()])
    pts_norm = _normalize(pts)

    mu, sigma = gp.predict(pts_norm, return_std=True)
    ei = expected_improvement(mu, sigma, best_eta, xi=xi)

    # 이미 시뮬레이션한 점 근처 제외
    if len(existing_params) > 0:
        existing = np.array([[r["period"], r["height"], r["duty"]]
                             for r in existing_params])
        existing_norm = _normalize(existing)
        dists_matrix = np.linalg.norm(
            pts_norm[:, None, :] - existing_norm[None, :, :], axis=2
        )
        too_close = dists_matrix.min(axis=1) < (min_dist / np.mean(_SCALE))
        ei[too_close] = 0.0

    best_idx = np.argmax(ei)
    p, h, d = pts[best_idx]
    return float(p), float(h), float(d), float(mu[best_idx]), float(sigma[best_idx]), float(ei[best_idx])


# ── 최종 요약용 GP 최적점 탐색 ──────────────────────────────────
def find_gp_optimum(gp):
    pg = SEARCH_GRID["period"]
    hg = SEARCH_GRID["height"]
    dg = SEARCH_GRID["duty"]

    pp, hh, dd = np.meshgrid(pg, hg, dg, indexing="ij")
    pts = np.column_stack([pp.ravel(), hh.ravel(), dd.ravel()])
    mu = gp.predict(_normalize(pts))
    best_idx = np.argmax(mu)
    p, h, d = pts[best_idx]
    return float(p), float(h), float(d), float(mu[best_idx])


# ── config 생성 ──────────────────────────────────────────────────
def make_config(period: int, height: int, duty: float, tag: str, configs_dir: str, exp: str) -> str:
    with open(TEMPLATE) as f:
        cfg = json.load(f)
    for m in cfg["materials"]:
        if m.get("shape") in ("AsymmetricSawtooth", "Sawtooth"):
            m["period"] = int(period)
            m["height"] = int(height)
            m["duty"]   = round(float(duty), 4)
    out_dir = os.path.join(_ROOT, "saves", exp, "iterative", tag)
    os.makedirs(out_dir, exist_ok=True)
    cfg["output_dir"] = out_dir
    os.makedirs(configs_dir, exist_ok=True)
    cfg_path = os.path.join(configs_dir, f"{tag}.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return cfg_path


# ── 시뮬레이션 실행 (PROGRESS 스트리밍 → pbar 업데이트) ──────────
def run_sim(cfg_path: str, sim_pbar=None) -> str | None:
    proc = subprocess.Popen(
        [sys.executable, _WORKER, cfg_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=_ROOT,
        encoding="utf-8",
        errors="replace",
    )
    result_path = None
    prev_pct = 0

    for line in proc.stdout:
        line = line.rstrip()
        if line.startswith("PROGRESS "):
            try:
                pct = int(line.split()[1])
                if sim_pbar is not None:
                    sim_pbar.update(pct - prev_pct)
                    prev_pct = pct
            except (ValueError, IndexError):
                pass
        elif line.startswith("RESULT "):
            result_path = line[7:].strip()
        elif line.startswith("ERROR "):
            tqdm.write(f"  [오류] {line[6:]}")

    if sim_pbar is not None and prev_pct < 100:
        sim_pbar.update(100 - prev_pct)

    proc.wait()
    stderr_out = proc.stderr.read()
    if stderr_out.strip():
        tqdm.write(f"  stderr: {stderr_out.strip()[:300]}")

    return result_path


# ── 메인 루프 ────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-iter", type=int, default=10)
    ap.add_argument("--ei-tol",  type=float, default=1e-9,
                    help="최대 EI 값이 이 값 미만이면 수렴 종료 (기본 1e-9)")
    ap.add_argument("--xi",      type=float, default=0.01,
                    help="EI 탐색 파라미터 xi (클수록 탐색↑, 기본 0.01)")
    ap.add_argument("--exp",     default="ex",
                    help="실험 네임스페이스 (기본: ex)")
    args = ap.parse_args()
    EXP = args.exp

    CONFIGS_DIR  = os.path.join(_ROOT, "saves", EXP, "iterative_configs")
    ITER_RESULTS = os.path.join(_ROOT, "saves", EXP, "iterative_results.json")
    CORRECTED_JSON = os.path.join(_ROOT, "saves", EXP, "sweep_results_corrected.json")

    # 기존 sweep 데이터 로드
    with open(CORRECTED_JSON) as f:
        records = json.load(f)

    # 이전 iterative 결과 있으면 병합
    if os.path.exists(ITER_RESULTS):
        with open(ITER_RESULTS) as f:
            iter_records = json.load(f)
        existing_tags = {(r["period"], r["height"], r["duty"]) for r in records}
        for r in iter_records:
            key = (r["period"], r["height"], r["duty"])
            if key not in existing_tags:
                records.append(r)
                existing_tags.add(key)
        tqdm.write(f"이전 iterative 결과 {len(iter_records)}개 병합 완료")
    else:
        iter_records = []

    iter_records = [r for r in records if r.get("_iterative")]
    best_eta = max((r["eta_clip"] for r in records if r.get("eta_clip") and np.isfinite(r["eta_clip"])),
                   default=0.0)

    # 초기 GP 적합
    gp, _, _, r2 = fit_gp(records)

    tqdm.write(f"초기 데이터: {len(records)}개  현재 최고 eta_clip: {best_eta*100:.3f}%")
    tqdm.write(f"탐색 범위: period={BOUNDS['period']}, height={BOUNDS['height']}, duty={BOUNDS['duty']}")
    tqdm.write(f"서로게이트: Gaussian Process (RBF + WhiteKernel)  초기 R²={r2:.4f}")
    tqdm.write(f"획득 함수: Expected Improvement (xi={args.xi})")
    tqdm.write(f"수렴 기준: max_EI < {args.ei_tol:.2e}  (최대 {args.max_iter}회)\n")

    outer_pbar = tqdm(range(1, args.max_iter + 1), desc="베이즈 최적화", unit="iter")

    for iteration in outer_pbar:
        outer_pbar.set_postfix(R2=f"{r2:.4f}", eta=f"{best_eta*100:.3f}%")
        tqdm.write(f"\n{'='*60}")
        tqdm.write(f"반복 {iteration}/{args.max_iter}")

        # GP 적합
        gp, X, y, r2 = fit_gp(records)
        tqdm.write(f"GP 적합: R²={r2:.4f}  데이터 수={len(y)}  커널={gp.kernel_}")

        # EI 최대점 탐색
        p_opt, h_opt, d_opt, mu_pred, sigma_pred, ei_max = find_next_ei(
            gp, best_eta, records, xi=args.xi
        )
        p_int = int(round(p_opt))
        h_int = int(round(h_opt))

        tqdm.write(f"다음 점 (max EI={ei_max:.2e}): p={p_int}, h={h_int}, d={d_opt:.2f}"
                   f"  μ={mu_pred*100:.3f}%  σ={sigma_pred*100:.4f}%")

        # 수렴 판정 (시뮬레이션 전)
        if ei_max < args.ei_tol:
            tqdm.write(f"\n수렴 조건 달성 (max_EI={ei_max:.2e} < {args.ei_tol:.2e})")
            break

        # config 생성 및 시뮬레이션
        tag = f"iter{iteration:02d}_p{p_int}_h{h_int}_d{str(round(d_opt,2)).replace('.','')}"
        cfg_path = make_config(p_int, h_int, d_opt, tag, CONFIGS_DIR, EXP)
        tqdm.write(f"시뮬레이션 실행 중... ({tag})")

        t0 = time.time()
        with tqdm(total=100, desc=f"  시뮬 {tag}", unit="%", leave=False) as sim_pbar:
            folder = run_sim(cfg_path, sim_pbar)
        elapsed = time.time() - t0

        if folder is None:
            tqdm.write(f"  [오류] 시뮬레이션 실패. 이 점을 건너뜁니다.")
            records.append({
                "period": p_int, "height": h_int, "duty": round(d_opt, 4),
                "folder": None, "elapsed": round(elapsed, 1),
                "_iterative": True, "eta_clip": float("nan"),
            })
            continue

        tqdm.write(f"  완료: {elapsed:.0f}초  →  {folder}")

        # eta 계산
        r = compute_corrected(folder, SOURCE_BOX, EXT_SPEC)
        eta_new = r["eta_clip"]
        tqdm.write(f"  eta_clip = {eta_new*100:.3f}%  (GP 예측 μ={mu_pred*100:.3f}%)")

        rec = {
            "period":  p_int,
            "height":  h_int,
            "duty":    round(d_opt, 4),
            "folder":  folder,
            "elapsed": round(elapsed, 1),
            "_iterative": True,
            **r,
        }
        records.append(rec)
        iter_records.append(rec)

        # iterative 결과 저장
        with open(ITER_RESULTS, "w", encoding="utf-8") as f:
            json.dump(iter_records, f, indent=2, ensure_ascii=False)

        if np.isfinite(eta_new):
            best_eta = max(best_eta, eta_new)

        outer_pbar.set_postfix(R2=f"{r2:.4f}", eta=f"{best_eta*100:.3f}%", EI=f"{ei_max:.1e}")

    outer_pbar.close()

    # 최종 요약
    print(f"\n{'='*60}")
    print("최종 요약")
    print(f"{'='*60}")
    gp_final, _, y_final, r2_final = fit_gp(records)
    p_f, h_f, d_f, eta_f = find_gp_optimum(gp_final)
    print(f"최종 GP 예측 최적: p={int(round(p_f))}, h={int(round(h_f))}, d={d_f:.2f}  η={eta_f*100:.3f}%")

    best_actual = max(records, key=lambda r: r.get("eta_clip") or 0)
    print(f"실측 최고: p={best_actual['period']}, h={best_actual['height']}, "
          f"d={best_actual['duty']:.2f}  η_clip={best_actual.get('eta_clip',0)*100:.3f}%")
    print(f"최종 R²: {r2_final:.4f}  데이터 수: {len(y_final)}")
    print(f"\niterative 결과 저장: {ITER_RESULTS}")


if __name__ == "__main__":
    main()
