"""
CPML.py
CPML 경계 조건을 구현하는 파일입니다.
"""
import numpy as np
class CPML:
        def __init__(self, grid, dt, pml_thick, sigma_max=1.0, kappa_max=1.0, alpha_max=0.0, m=3):
                self.sigma_max = sigma_max
                self.kappa_max = kappa_max
                self.alpha_max = alpha_max
                self.m = m
                self.pml_thick = pml_thick
                self.dt = dt

                Nx, Ny, Nz = grid.Nx, grid.Ny, grid.Nz

                self.psi = {}
                self.coeff = {}

                self.psi["Ex_y"] = np.zeros((Nx-1, Ny-2, Nz  ))
                self.psi["Ex_z"] = np.zeros((Nx-1, Ny,   Nz-2))
                self.psi["Ey_x"] = np.zeros((Nx-2, Ny-1, Nz  ))
                self.psi["Ey_z"] = np.zeros((Nx,   Ny-1, Nz-2))
                self.psi["Ez_x"] = np.zeros((Nx-2, Ny,   Nz-1))
                self.psi["Ez_y"] = np.zeros((Nx,   Ny-2, Nz-1))

                self.psi["Hx_y"] = np.zeros((Nx,   Ny-1, Nz-1))
                self.psi["Hx_z"] = np.zeros((Nx,   Ny-1, Nz-1))
                self.psi["Hy_x"] = np.zeros((Nx-1, Ny,   Nz-1))
                self.psi["Hy_z"] = np.zeros((Nx-1, Ny,   Nz-1))
                self.psi["Hz_x"] = np.zeros((Nx-1, Ny-1, Nz  ))
                self.psi["Hz_y"] = np.zeros((Nx-1, Ny-1, Nz  ))

                self.build_coeff(grid)

        def make_sigma(self, N, eorh): #E면 eorh=0, H면 eorh=1
                pml = self.pml_thick
                sigma_max = self.sigma_max
                m = self.m
                sigma = np.zeros(N)
                for i in range(pml):
                        x = (pml - i - 0.5 * eorh) / pml
                        sigma[i] = sigma_max * x**m
                        sigma[-1-i] = sigma_max * x**m
                return sigma
        
        def make_kappa(self, N, eorh=0):  # ← eorh 추가
                pml = self.pml_thick
                kappa_max = self.kappa_max
                m = self.m
                kappa = np.ones(N)
                for i in range(pml):
                        x = (pml - i - 0.5 * eorh) / pml  # ← 스태거 적용
                        x = max(x, 0.0)
                        kappa[i] = 1 + (kappa_max - 1) * (x**m)
                        kappa[-1-i] = 1 + (kappa_max - 1) * (x**m)
                return kappa

        def make_alpha(self, N, eorh=0):  # ← eorh 추가
                pml = self.pml_thick
                alpha_max = self.alpha_max
                alpha = np.zeros(N)
                for i in range(pml):
                        x = (pml - i - 0.5 * eorh) / pml  # ← 스태거 적용
                        x = max(x, 0.0)
                        alpha[i] = alpha_max * x
                        alpha[-1-i] = alpha_max * x
                return alpha

        def make_b(self, sigma, kappa, alpha):
                dt = self.dt
                b = np.exp(
                        -(sigma / kappa + alpha) * dt
                )
                return b
        
        def make_c(self, b, sigma, kappa, alpha):
                denom = sigma * kappa + alpha * kappa**2
                c = np.zeros_like(b)
                mask = denom != 0
                c[mask] = sigma[mask] * (b[mask] - 1) / denom[mask]
                return c
        
        def reshape_x(self, arr):
                return arr.reshape(len(arr), 1, 1)

        def reshape_y(self, arr):
                return arr.reshape(1, len(arr), 1)

        def reshape_z(self, arr):
                return arr.reshape(1, 1, len(arr))
        
        def make_cpml_coeff(self, N, stagger, axis):
                sigma = self.make_sigma(N, stagger)
                kappa = self.make_kappa(N, stagger)
                alpha = self.make_alpha(N, stagger)
                b     = self.make_b    (sigma, kappa, alpha)
                c     = self.make_c    (b, sigma, kappa, alpha)

                reshape = {
                        "x": self.reshape_x,
                        "y": self.reshape_y,
                        "z": self.reshape_z
                }[axis]

                sigma, kappa, alpha, b, c = [
                        reshape(arr)
                        for arr in (sigma, kappa, alpha, b, c)
                ]

                return  {
                        "sigma": sigma,
                        "kappa": kappa,
                        "alpha": alpha,
                        "b": b,
                        "c": c
                }

        def build_coeff(self,grid):
                Nx, Ny, Nz = grid.Nx, grid.Ny, grid.Nz
                cpml_configs = {
                "Ex_y": (Ny, 0, "y"), "Ex_z": (Nz, 0, "z"), 
                "Ey_x": (Nx, 0, "x"), "Ey_z": (Nz, 0, "z"), 
                "Ez_x": (Nx, 0, "x"), "Ez_y": (Ny, 0, "y"),

                "Hx_y": (Ny-1, 1, "y"), "Hx_z": (Nz-1, 1, "z"),
                "Hy_x": (Nx-1, 1, "x"), "Hy_z": (Nz-1, 1, "z"),
                "Hz_x": (Nx-1, 1, "x"), "Hz_y": (Ny-1, 1, "y"),
                }

                for key, (N, stagger, axis) in cpml_configs.items():
                        self.coeff[key] = self.make_cpml_coeff(N=N, stagger=stagger, axis=axis)