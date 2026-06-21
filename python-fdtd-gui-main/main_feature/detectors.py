"""
detectors.py
검광기 클래스 정의
검광기는 시뮬레이션에서 특정 위치의 필드 값을 기록하는 역할을 합니다.
"""
import numpy as np

_POYNTING = {"Sx", "Sy", "Sz"}


class Detectors:
        def __init__(self, detectors: list = None):
                self.detectors = detectors if detectors is not None else []
                self.buffer = {detector["name"]: {} for detector in self.detectors}
                self.axis_map = {
                        "x": lambda arr, p: arr[p, :, :],
                        "y": lambda arr, p: arr[:, p, :],
                        "z": lambda arr, p: arr[:, :, p],
                }
                self.baked = {}  # bake() 호출 후 채워짐

        # ── 셀 중심 마스크 사전 계산 ────────────────────────────
        def bake(self, Nx, Ny, Nz):
                """Poynting 성분이 필요한 검광기에 대해 셀 중심 마스크를 생성한다.

                셀 중심 격자 크기: (Nx-1, Ny-1, Nz-1)
                plane 검광기: 해당 축 슬라이스 전체를 True
                point 검광기: 해당 셀 1개를 True
                """
                cx, cy, cz = Nx - 1, Ny - 1, Nz - 1
                for det in self.detectors:
                        if not any(q in _POYNTING for q in det["record_type"]):
                                continue
                        mask = np.zeros((cx, cy, cz), dtype=bool)
                        if det["type"] == "plane":
                                axis, pos = det["axis"], det["position"]
                                if axis == "x":
                                        mask[pos, :, :] = True
                                        shape = (cy, cz)
                                elif axis == "y":
                                        mask[:, pos, :] = True
                                        shape = (cx, cz)
                                else:  # z
                                        mask[:, :, pos] = True
                                        shape = (cx, cy)
                        else:  # point
                                x, y, z = det["position"]
                                mask[x, y, z] = True
                                shape = ()
                        self.baked[det["name"]] = {"mask": mask, "shape": shape}

        # ── 필드 기록 ───────────────────────────────────────────
        def detect(self, field):
                self.detect_plane(field)
                self.detect_point(field)

        def detect_plane(self, field):
                for detector in self.detectors:
                        if detector["type"] != "plane":
                                continue
                        for D_type in detector["record_type"]:
                                if D_type in _POYNTING:
                                        continue  # detect_poynting()에서 처리
                                arr = getattr(field, D_type)
                                value = self.axis_map[detector["axis"]](arr, detector["position"])
                                if D_type not in self.buffer[detector["name"]]:
                                        self.buffer[detector["name"]][D_type] = []
                                self.buffer[detector["name"]][D_type].append(value.copy())

        def detect_point(self, field):
                for detector in self.detectors:
                        if detector["type"] != "point":
                                continue
                        for D_type in detector["record_type"]:
                                if D_type in _POYNTING:
                                        continue
                                arr = getattr(field, D_type)
                                value = arr[detector["position"]]
                                if D_type not in self.buffer[detector["name"]]:
                                        self.buffer[detector["name"]][D_type] = []
                                self.buffer[detector["name"]][D_type].append(value)

        # ── Poynting 기록 ────────────────────────────────────────
        def detect_poynting(self, Sx, Sy, Sz):
                """사전 계산된 마스크로 각 검광기 위치의 Poynting 성분을 추출해 버퍼에 기록한다."""
                s_map = {"Sx": Sx, "Sy": Sy, "Sz": Sz}
                for det in self.detectors:
                        if det["name"] not in self.baked:
                                continue
                        baked = self.baked[det["name"]]
                        mask, shape = baked["mask"], baked["shape"]
                        for q, arr in s_map.items():
                                if q not in det["record_type"]:
                                        continue
                                val = arr[mask]
                                if shape:
                                        val = val.reshape(shape)
                                if q not in self.buffer[det["name"]]:
                                        self.buffer[det["name"]][q] = []
                                self.buffer[det["name"]][q].append(val.copy())

        # ── 검광기 추가 ─────────────────────────────────────────
        def add_plane_detector(self, name, axis, position, record_type):
                self.detectors.append({
                        "name": name,
                        "axis": axis,
                        "position": position,
                        "record_type": record_type,
                        "type": "plane",
                })
                self.buffer[name] = {}

        def add_point_detector(self, name, position, record_type):
                self.detectors.append({
                        "name": name,
                        "position": position,
                        "record_type": record_type,
                        "type": "point",
                })
                self.buffer[name] = {}