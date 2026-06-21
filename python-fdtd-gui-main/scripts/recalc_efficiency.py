"""
recalc_efficiency.py
기존 시뮬레이션 결과에 대해 보정된 추출율을 재계산한다.

문제: 기존 source_box 는 전체 평면(full-plane) 검광기를 사용해
      닫힌 폐곡면이 아니어서 P_total 이 과대 계산됨.

두 가지 보정 방법:
  Method A (z-only): box_top_z + box_bottom_z 만 P_total 로 사용.
                     측면 방출(guided mode)을 무시 → eta 상한값.
  Method B (clip)  : 측면 검광기를 소스 박스 경계 안쪽으로 슬라이싱.
                     이중 계산 제거 → eta 참값에 가장 가까운 추정.

사용: python scripts/recalc_efficiency.py
"""
import sys
import os
import json
import numpy as np

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, r'C:\Users\ryno1\fdtd-for-light-extraction-experiment')

# ── 소스 박스 경계 (모든 sweep config 공통) ──────────────────
# 검광기 위치: x=[38,62], y=[38,62], z=[65,89]
BOX = {
    "x": (38, 62),
    "y": (38, 62),
    "z": (65, 89),
}

SOURCE_BOX = [
    {"name": "box_top_z",    "component": "Sz", "sign": +1},
    {"name": "box_bottom_z", "component": "Sz", "sign": -1},
    {"name": "box_right_x",  "component": "Sx", "sign": +1},
    {"name": "box_left_x",   "component": "Sx", "sign": -1},
    {"name": "box_front_y",  "component": "Sy", "sign": +1},
    {"name": "box_back_y",   "component": "Sy", "sign": -1},
]

SOURCE_BOX_Z_ONLY = [
    {"name": "box_top_z",    "component": "Sz", "sign": +1},
    {"name": "box_bottom_z", "component": "Sz", "sign": -1},
]

EXT_SPEC = {"name": "air_extraction", "component": "Sz", "sign": +1}


# ── 내부 유틸 ──────────────────────────────────────────────────
def _load(folder, name):
    path = os.path.join(folder, f"{name}.npz")
    f = np.load(path)
    d = {k: f[k] for k in f.files}
    f.close()
    return d


def _flux_raw(folder, face, dx, dy, dz):
    """기존 방식: 전체 평면 합산."""
    area_map = {"x": dy * dz, "y": dx * dz, "z": dx * dy}
    d = _load(folder, face["name"])
    frames = d[face["component"]]
    axis = str(d.get("_det_axis", "y"))
    return face["sign"] * float(frames.sum()) * area_map[axis]


def _flux_clipped(folder, face, dx, dy, dz, box):
    """
    Method B: 측면 검광기를 소스 박스 경계로 클리핑.
    z-plane  → x 와 y 를 box 범위로 슬라이싱
    x-plane  → y 와 z 를 box 범위로 슬라이싱
    y-plane  → x 와 z 를 box 범위로 슬라이싱
    """
    area_map = {"x": dy * dz, "y": dx * dz, "z": dx * dy}
    d = _load(folder, face["name"])
    frames = d[face["component"]]   # (N_frames, dim1, dim2)
    axis = str(d.get("_det_axis", "y"))

    x0, x1 = box["x"]
    y0, y1 = box["y"]
    z0, z1 = box["z"]

    if axis == "x":
        frames = frames[:, y0:y1, z0:z1]
    elif axis == "y":
        frames = frames[:, x0:x1, z0:z1]
    else:  # "z"
        frames = frames[:, x0:x1, y0:y1]

    return face["sign"] * float(frames.sum()) * area_map[axis]


def compute_corrected(folder, source_box, ext_spec, dx=1.0, dy=1.0, dz=1.0):
    """세 가지 방법으로 eta 를 계산해 반환."""
    P_total_raw = sum(_flux_raw(folder, f, dx, dy, dz) for f in source_box)
    P_out_raw   = _flux_raw(folder, ext_spec, dx, dy, dz)
    eta_raw     = P_out_raw / P_total_raw if P_total_raw > 0 else float("nan")

    P_total_z = sum(_flux_raw(folder, f, dx, dy, dz) for f in SOURCE_BOX_Z_ONLY)
    eta_z     = P_out_raw / P_total_z if P_total_z > 0 else float("nan")

    P_total_clip = sum(_flux_clipped(folder, f, dx, dy, dz, BOX) for f in source_box)
    eta_clip     = P_out_raw / P_total_clip if P_total_clip > 0 else float("nan")

    return {
        "P_total_raw":  P_total_raw,
        "P_total_z":    P_total_z,
        "P_total_clip": P_total_clip,
        "P_out":        P_out_raw,
        "eta_raw":      eta_raw,
        "eta_z":        eta_z,
        "eta_clip":     eta_clip,
    }


# ── 단독 실행 ──────────────────────────────────────────────────
if __name__ == "__main__":
    RESULTS_JSON = os.path.join(_ROOT, "saves", "sweep_results.json")

    with open(RESULTS_JSON) as f:
        records = json.load(f)

    rows = []
    for rec in records:
        folder = rec.get("folder")
        if not folder:
            continue
        try:
            r = compute_corrected(folder, SOURCE_BOX, EXT_SPEC)
        except FileNotFoundError as e:
            print(f"skip {folder}: {e}")
            continue

        if not np.isfinite(r["eta_raw"]):
            continue

        row = {**rec, **r}
        rows.append(row)
        print(
            f"p={rec['period']:2d} h={rec['height']:2d} d={rec['duty']:.2f} | "
            f"raw={r['eta_raw']*100:.3f}%  "
            f"z-only={r['eta_z']*100:.3f}%  "
            f"clip={r['eta_clip']*100:.3f}%"
        )

    out_path = os.path.join(_ROOT, "saves", "sweep_results_corrected.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"\n보정 결과 저장: {out_path}")

    if rows:
        print("\n방법별 요약 (모든 케이스 평균):")
        print(f"  원본(raw)  : {np.mean([r['eta_raw']*100  for r in rows]):.3f}%")
        print(f"  z-only (A) : {np.mean([r['eta_z']*100    for r in rows]):.3f}%")
        print(f"  clip   (B) : {np.mean([r['eta_clip']*100 for r in rows]):.3f}%")
