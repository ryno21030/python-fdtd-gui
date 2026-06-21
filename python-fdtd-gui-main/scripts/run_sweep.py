"""
run_sweep.py
톱니 구조 파라미터 스윕 실행기.

PERIODS x HEIGHTS x DUTIES 의 3^3 = 27개 조합을 N_WORKERS개씩 병렬 실행하고
결과를 saves/sweep_results.json 에 저장한다.

사용: python scripts/run_sweep.py
"""
import json
import os
import subprocess
import sys
import time
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, _ROOT)

# ── 파라미터 그리드 ───────────────────────────────────────────
PERIODS = [15, 25, 35]      # 톱니 주기 (셀)  — 150 / 250 / 350 nm
HEIGHTS = [8,  15, 22]      # 톱니 높이 (셀)  — 80  / 150 / 220 nm
DUTIES  = [0.5, 0.65, 0.8]  # 비대칭 비율

N_WORKERS = 1               # 동시 실행 수 (RAM 부족으로 1로 제한)

# ── 경로 ────────────────────────────────────────────────────
TEMPLATE     = os.path.join(_ROOT, "saves", "oled_sawtooth.json")
CONFIGS_DIR  = os.path.join(_ROOT, "saves", "sweep_configs")
RESULTS_JSON = os.path.join(_ROOT, "saves", "sweep_results.json")
_WORKER      = os.path.join(_SCRIPTS_DIR, "sweep_worker.py")


def make_config(period: int, height: int, duty: float) -> str:
    """템플릿에서 파라미터만 교체한 새 JSON 파일을 생성하고 경로를 반환한다."""
    with open(TEMPLATE) as f:
        cfg = json.load(f)

    for m in cfg["materials"]:
        if m.get("shape") in ("AsymmetricSawtooth", "Sawtooth"):
            m["period"] = period
            m["height"] = height
            m["duty"]   = duty

    tag = f"p{period}_h{height}_d{str(duty).replace('.','')}"
    sweep_out = os.path.join(_ROOT, "saves", "sweep", tag)
    os.makedirs(sweep_out, exist_ok=True)
    cfg["output_dir"] = sweep_out

    os.makedirs(CONFIGS_DIR, exist_ok=True)
    cfg_path = os.path.join(CONFIGS_DIR, f"{tag}.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return cfg_path


def run_one(period, height, duty, cfg_path) -> dict:
    """subprocess로 sweep_worker.py 를 실행하고 결과 폴더를 반환한다."""
    tag = f"p={period} h={height} d={duty}"
    t0 = time.time()
    proc = subprocess.Popen(
        [sys.executable, _WORKER, cfg_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=_ROOT,
        encoding="utf-8",
        errors="replace",
    )
    stdout, stderr = proc.communicate()
    elapsed = time.time() - t0

    folder = None
    for line in stdout.splitlines():
        if line.startswith("RESULT "):
            folder = line[7:].strip()

    status = "ok" if folder else "fail"
    print(f"[{status}] {tag}  {elapsed:.0f}s  -> {folder or 'ERROR'}", flush=True)
    if stderr.strip():
        print(f"  stderr: {stderr.strip()[:200]}", flush=True)

    return {
        "period": period,
        "height": height,
        "duty":   duty,
        "folder": folder,
        "elapsed": round(elapsed, 1),
    }


def main():
    combos = list(itertools.product(PERIODS, HEIGHTS, DUTIES))
    total  = len(combos)
    print(f"파라미터 조합: {total}개  (병렬 {N_WORKERS}개씩)")
    print(f"예상 시간: {total * 25 / N_WORKERS / 60:.1f}시간\n")

    existing = {}
    if os.path.exists(RESULTS_JSON):
        with open(RESULTS_JSON) as f:
            for rec in json.load(f):
                if rec.get("folder"):
                    key = (rec["period"], rec["height"], rec["duty"])
                    existing[key] = rec

    todo = [c for c in combos if c not in existing]
    print(f"이미 완료: {total - len(todo)}개  남은 작업: {len(todo)}개\n")

    results = list(existing.values())
    done_count = len(results)

    def task(args):
        p, h, d = args
        cfg_path = make_config(p, h, d)
        return run_one(p, h, d, cfg_path)

    with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
        futures = {ex.submit(task, c): c for c in todo}
        for fut in as_completed(futures):
            rec = fut.result()
            results.append(rec)
            done_count += 1
            print(f"  진행: {done_count}/{total}", flush=True)

            with open(RESULTS_JSON, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n완료. 결과 저장: {RESULTS_JSON}")


if __name__ == "__main__":
    main()
