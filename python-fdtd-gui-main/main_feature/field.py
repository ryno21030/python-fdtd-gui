"""
field.py
field dataclass를 정의하는 파일입니다.
"""
import numpy as np
from dataclasses import dataclass

@dataclass
class Field:
        Ex: np.ndarray
        Ey: np.ndarray
        Ez: np.ndarray

        Hx: np.ndarray
        Hy: np.ndarray
        Hz: np.ndarray

        def allocate_fields(self, grid):
                self.Ex = np.zeros((grid.Nx-1, grid.Ny, grid.Nz))
                self.Ey = np.zeros((grid.Nx, grid.Ny-1, grid.Nz))
                self.Ez = np.zeros((grid.Nx, grid.Ny, grid.Nz-1))

                self.Hx = np.zeros((grid.Nx, grid.Ny-1, grid.Nz-1))
                self.Hy = np.zeros((grid.Nx-1, grid.Ny, grid.Nz-1))
                self.Hz = np.zeros((grid.Nx-1, grid.Ny-1, grid.Nz))


