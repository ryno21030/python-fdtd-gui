"""
detectors.py
검광기 클래스 정의
검광기는 시뮬레이션에서 특정 위치의 필드 값을 기록하는 역할을 합니다.
"""
class Detectors:
        def __init__(self, detectors:list=None):
                self.detectors = detectors if detectors is not None else []
                self.buffer = {detector["name"]: {} for detector in self.detectors}
                self.axis_map = {
                        "x": lambda arr, p: arr[p, :, :],
                        "y": lambda arr, p: arr[:, p, :],
                        "z": lambda arr, p: arr[:, :, p],
                }

        def detect(self, field):
                self.detect_plane(field)

        def detect_plane(self, field):
                for detector in self.detectors:
                        for D_type in detector["record_type"]:
                                arr = getattr(field, D_type)
                                value = self.axis_map[detector["axis"]](arr, detector["position"])

                                if D_type not in self.buffer[detector["name"]]:
                                        self.buffer[detector["name"]][D_type] = []
                                self.buffer[detector["name"]][D_type].append(value.copy())

        def add_plane_detector(self, name, axis, position, record_type):
                self.detectors.append({
                        "name": name,
                        "axis": axis,
                        "position": position,
                        "record_type": record_type,
                        "type": "plane"
                })
                self.buffer[name] = {}
