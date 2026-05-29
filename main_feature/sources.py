"""
sources.py
시뮬레이션에서 전자기파를 발생시키는 소스들을 정의하는 모듈입니다. 
소스의 위치, 진폭, 주파수 등을 설정하여 필드에 영향을 미치는 역할을 합니다.
"""
import numpy as np
class Sources:
        def __init__(self, sources:list=None):
                self.sources = sources if sources is not None else []

        def add_gaussian_pulse(
                self,
                x, y, z,
                t0, tau,
                amplitude,
                component
        ):
                self.sources.append({
                        "type": "gaussian_pulse",
                        "pos": (x, y, z),
                        "t0": t0,
                        "tau": tau,
                        "amplitude": amplitude,
                        "component": component,
                })

        def gaussian_pulse(self, s, t, field):

                val = (
                        -s["amplitude"]
                        * (t - s["t0"])
                        / s["tau"]**2
                        * np.exp(-((t - s["t0"]) / s["tau"])**2)
                        )

                arr = getattr(field, s["component"])

                arr[s["pos"]] += val

        def emit(self, field, grid):

                t = grid.t

                for s in self.sources:
                        getattr(self, s["type"])(s, t, field)