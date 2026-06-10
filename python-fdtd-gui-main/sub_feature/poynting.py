import numpy as np


class Poynting:
        def __init__(self, save_global=False):
                self.save_global = save_global
                self.Sx = None
                self.Sy = None
                self.Sz = None
                self.global_buffer = {"Sx": [], "Sy": [], "Sz": []} if save_global else None

        def reshape(self, field):
                # E: 어긋난 두 축 방향으로 평균 → 셀 중심
                self.reshaped_Ex = 0.25 * (
                        field.Ex[:,:-1,:-1] + field.Ex[:,1:,:-1] +
                        field.Ex[:,:-1,1:] + field.Ex[:,1:,1:]
                )
                self.reshaped_Ey = 0.25 * (
                        field.Ey[:-1,:,:-1] + field.Ey[1:,:,:-1] +
                        field.Ey[:-1,:,1:] + field.Ey[1:,:,1:]
                )
                self.reshaped_Ez = 0.25 * (
                        field.Ez[:-1,:-1,:] + field.Ez[1:,:-1,:] +
                        field.Ez[:-1,1:,:] + field.Ez[1:,1:,:]
                )
                # H: 어긋난 두 축 방향으로 평균 → 셀 중심
                self.reshaped_Hx = 0.25 * (
                        field.Hx[:,:-1,:-1] + field.Hx[:,1:,:-1] +
                        field.Hx[:,:-1,1:] + field.Hx[:,1:,1:]
                )
                self.reshaped_Hy = 0.25 * (
                        field.Hy[:-1,:,:-1] + field.Hy[1:,:,:-1] +
                        field.Hy[:-1,:,1:] + field.Hy[1:,:,1:]
                )
                self.reshaped_Hz = 0.25 * (
                        field.Hz[:-1,:-1,:] + field.Hz[1:,:-1,:] +
                        field.Hz[:-1,1:,:] + field.Hz[1:,1:,:]
                )

        def compute(self, field):
                self.reshape(field)
                self.Sx = self.reshaped_Ey * self.reshaped_Hz - self.reshaped_Ez * self.reshaped_Hy
                self.Sy = self.reshaped_Ez * self.reshaped_Hx - self.reshaped_Ex * self.reshaped_Hz
                self.Sz = self.reshaped_Ex * self.reshaped_Hy - self.reshaped_Ey * self.reshaped_Hx
                return self.Sx, self.Sy, self.Sz

        def record_global(self):
                """전역 시각화용 버퍼에 현재 프레임 추가 (save_global=True 일 때만 동작)."""
                if self.global_buffer is None:
                        return
                self.global_buffer["Sx"].append(self.Sx.copy())
                self.global_buffer["Sy"].append(self.Sy.copy())
                self.global_buffer["Sz"].append(self.Sz.copy())
