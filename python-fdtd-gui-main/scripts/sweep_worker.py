"""
sweep_worker.py
단일 시뮬레이션 실행 후 결과 폴더 경로를 출력한다.
run_sweep.py 에서 subprocess로 호출된다.

출력 형식:
  PROGRESS <int>   진행률 (20% 단위)
  RESULT <path>    완료 후 저장 폴더 (절대 경로)
  ERROR <msg>      오류 발생 시
"""
import sys
import os

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, _ROOT)

from PyQt6.QtCore import QCoreApplication, QEventLoop
from config import SimConfig
from runner import SimRunner


def main():
    if len(sys.argv) < 2:
        print("ERROR no config path", flush=True)
        sys.exit(1)

    cfg_path = sys.argv[1]
    cfg = SimConfig.from_json(cfg_path)

    errors = cfg.validate()
    if errors:
        print("ERROR validate: " + "; ".join(errors), flush=True)
        sys.exit(1)

    app = QCoreApplication([])
    loop = QEventLoop()

    last_pct = [-1]

    def on_progress(p):
        if p // 20 > last_pct[0]:
            last_pct[0] = p // 20
            print(f"PROGRESS {p}", flush=True)

    def on_done():
        loop.quit()

    def on_error(msg):
        print(f"ERROR {msg}", flush=True)
        loop.quit()

    runner = SimRunner(cfg)
    runner.progress.connect(on_progress)
    runner.finished.connect(on_done)
    runner.error.connect(on_error)
    runner.start()
    loop.exec()

    # QThread가 완전히 종료될 때까지 대기 (PyQt 정리 데드락 방지)
    runner.wait()

    # 가장 최근에 생성된 save_* 폴더 반환
    output_dir = cfg.output_dir
    if os.path.isdir(output_dir):
        folders = sorted(
            [f for f in os.listdir(output_dir) if f.startswith("save_")],
            key=lambda f: os.path.getmtime(os.path.join(output_dir, f)),
        )
        if folders:
            result = os.path.join(output_dir, folders[-1])
            print(f"RESULT {result}", flush=True)
            os._exit(0)  # Qt 정리 단계 hang 방지를 위해 즉시 종료

    print("ERROR no save folder found", flush=True)
    os._exit(1)


if __name__ == "__main__":
    main()
