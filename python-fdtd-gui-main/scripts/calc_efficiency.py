"""
calc_efficiency.py
특정 시뮬레이션 폴더 두 개(flat/sawtooth)의 추출율을 직접 비교한다.
사용: python scripts/calc_efficiency.py
"""
import sys
import os

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)
sys.path.insert(0, r'C:\Users\ryno1\fdtd-for-light-extraction-experiment')

from extraction import compute_extraction_efficiency

source_box = [
    {"name": "box_top_z",    "component": "Sz", "sign": +1},
    {"name": "box_bottom_z", "component": "Sz", "sign": -1},
    {"name": "box_right_x",  "component": "Sx", "sign": +1},
    {"name": "box_left_x",   "component": "Sx", "sign": -1},
    {"name": "box_front_y",  "component": "Sy", "sign": +1},
    {"name": "box_back_y",   "component": "Sy", "sign": -1},
]
ext_spec = {"name": "air_extraction", "component": "Sz", "sign": +1}

# 비교할 폴더 경로 (절대 경로 또는 saves/ 하위 경로)
FLAT_FOLDER = os.path.join(_ROOT, r"saves\save_1781760465202")
SAW_FOLDER  = os.path.join(_ROOT, r"saves\save_1781761966469")

flat = compute_extraction_efficiency(FLAT_FOLDER, source_box, ext_spec)
saw  = compute_extraction_efficiency(SAW_FOLDER,  source_box, ext_spec)

print("=== light extraction efficiency ===")
print("flat:     P_total={:.4e}  P_out={:.4e}  eta={:.4f} ({:.2f}%)".format(
    flat["P_total"], flat["P_out"], flat["eta"], flat["eta"]*100))
print("sawtooth: P_total={:.4e}  P_out={:.4e}  eta={:.4f} ({:.2f}%)".format(
    saw["P_total"], saw["P_out"], saw["eta"], saw["eta"]*100))
if flat["eta"] > 0:
    ratio = saw["eta"] / flat["eta"]
    print("enhancement: {:.3f}x  ({:+.1f}%)".format(ratio, (ratio - 1) * 100))
