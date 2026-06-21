"""
run_headless.py
GUI 없이 시뮬레이션을 순서대로 실행한다.
사용: python scripts/run_headless.py config1.json [config2.json ...]
"""
import sys
import os
import time

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, _ROOT)

from PyQt6.QtCore import QCoreApplication, QEventLoop
from config import SimConfig
from runner import SimRunner


def run_one(json_path: str) -> str:
    cfg = SimConfig.from_json(json_path)
    errors = cfg.validate()
    if errors:
        print(f"[설정 오류] {json_path}")
        for e in errors:
            print(f"  {e}")
        return None

    print(f"\n{'='*60}")
    print(f"실행: {os.path.basename(json_path)}")
    print(f"  격자: {cfg.grid.Nx}×{cfg.grid.Ny}×{cfg.grid.Nz}  T={cfg.grid.T}")
    print(f"  재질: {[m.name for m in cfg.materials]}")
    print(f"  검광기: {[d.name for d in cfg.detectors]}")
    print(f"{'='*60}")

    loop = QEventLoop()
    runner = SimRunner(cfg)
    result_folder = [None]

    def on_status(msg):
        if "%" in msg:
            try:
                pct = int(msg.split("%")[0].split()[-1])
                if pct % 10 == 0:
                    print(f"  {msg}", flush=True)
            except Exception:
                pass

    def on_finished():
        print("  완료!")
        loop.quit()

    def on_error(msg):
        print(f"  [오류] {msg}")
        loop.quit()

    runner.status.connect(on_status)
    runner.finished.connect(on_finished)
    runner.error.connect(on_error)

    t0 = time.time()
    runner.start()
    loop.exec()
    elapsed = time.time() - t0
    print(f"  소요 시간: {elapsed:.1f}초")

    output_dir = cfg.output_dir
    if os.path.isdir(output_dir):
        folders = sorted(
            [f for f in os.listdir(output_dir) if f.startswith("save_")],
            key=lambda f: os.path.getmtime(os.path.join(output_dir, f))
        )
        if folders:
            result_folder[0] = os.path.join(output_dir, folders[-1])
            print(f"  저장 폴더: {result_folder[0]}")

    return result_folder[0]


if __name__ == "__main__":
    configs = sys.argv[1:] if len(sys.argv) > 1 else []
    if not configs:
        print("사용: python scripts/run_headless.py config1.json [config2.json ...]")
        sys.exit(1)

    app = QCoreApplication(sys.argv)
    results = {}
    for cfg_path in configs:
        folder = run_one(cfg_path)
        results[cfg_path] = folder

    print("\n\n" + "="*60)
    print("전체 결과 요약")
    print("="*60)
    for path, folder in results.items():
        name = os.path.basename(path)
        status = folder if folder else "실패"
        print(f"  {name:30s}  →  {status}")
