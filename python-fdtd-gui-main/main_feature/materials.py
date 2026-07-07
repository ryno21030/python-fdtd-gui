"""
materials.py
재료 특성을 정의하는 파일입니다.
각 재료의 유전율, 투자율, 전도도 등을 포함하여 시뮬레이션에서 사용되는 물질의 특성을 관리합니다.
"""

import numpy as np

class Material:
        def __init__(self, eps_r=1.0, mu_r=1.0, cond=0.0):
                self.eps_r = eps_r
                self.mu_r  = mu_r
                self.n = np.sqrt(eps_r * mu_r)
                self.cond = cond

VACUUM  = Material(eps_r=1.0)
COPPER  = Material(eps_r=1.0,  mu_r=1.0, cond=5.96e7)
GOLD    = Material(eps_r=1.0,  mu_r=1.0, cond=4.1e7)
SILICON = Material(eps_r=11.7, mu_r=1.0, cond=0.0)
GLASS   = Material(eps_r=2.25, mu_r=1.0, cond=0.0)
WATER   = Material(eps_r=80.1, mu_r=1.0, cond=0.0)

class Box:
    def __init__(self, x0, x1, y0, y1, z0, z1):
        self.bounds = (x0, x1, y0, y1, z0, z1)

    def mask(self, shape):
        """
        component: 'Ex'|'Ey'|'Ez'|'Hx'|'Hy'|'Hz'
        반환: bool 배열, True인 곳에 매질 적용
        """
        Nx, Ny, Nz = shape[0], shape[1], shape[2]
        x0, x1, y0, y1, z0, z1 = self.bounds
        m = np.zeros(shape, dtype=bool)
        m[x0:x1, y0:y1, z0:z1] = True
        return m


class Sphere:
    def __init__(self, cx, cy, cz, r):
        self.cx, self.cy, self.cz, self.r = cx, cy, cz, r

    def mask(self, shape):
        Nx, Ny, Nz = shape[0], shape[1], shape[2]
        x = np.arange(Nx).reshape(-1, 1, 1)
        y = np.arange(Ny).reshape(1, -1, 1)
        z = np.arange(Nz).reshape(1, 1, -1)
        return (x-self.cx)**2 + (y-self.cy)**2 + (z-self.cz)**2 <= self.r**2
    

class AsymmetricSawtooth:
    """반딧불이 큐티클 비대칭 톱니 구조"""
    def __init__(self, z_base, height, period, duty=0.8, nx_repeat=None):
        # duty: 완만한 쪽 비율 (0.8 = 80% 완만, 20% 급경사)
        self.z_base  = z_base
        self.height  = height
        self.period  = period
        self.duty    = duty  # 비대칭 핵심 파라미터
        self.nx_repeat = nx_repeat

    def mask(self, shape):
        Nx, Ny, Nz = shape[0], shape[1], shape[2]
        x = np.arange(Nx, dtype=float)
        x_mod = x % self.period
        z_surface = np.where(
            x_mod < self.period * self.duty,
            self.height * x_mod / (self.period * self.duty),
            self.height * (1.0 - (x_mod - self.period * self.duty)
                           / (self.period * (1.0 - self.duty)))
        )
        z_surf_3d = z_surface.reshape(Nx, 1, 1)
        z_idx     = np.arange(Nz, dtype=float).reshape(1, 1, Nz)
        base      = float(self.z_base)
    
        mask_2d = z_idx < (base + z_surf_3d)           # (Nx, 1, Nz)
        return np.broadcast_to(mask_2d, (Nx, Ny, Nz)).copy()  # (Nx, Ny, Nz)

class Scene:
        def __init__(self, Nx, Ny, Nz, eps0=1.0, mu0=1.0):
                self.Nx, self.Ny, self.Nz = Nx, Ny, Nz
                self.eps0 = eps0
                self.mu0  = mu0
                self.objects = []

        def add(self, shape, material):
                self.objects.append((shape, material))
                return self
        
        @staticmethod
        def make_Ca(sigma, eps, dt):
                return (1 - sigma * dt / (2 * eps)) / (1 + sigma * dt / (2 * eps))

        @staticmethod
        def make_Cb(sigma, eps, dt):
                return (dt / eps) / (1 + sigma * dt / (2 * eps))

        def bake(self,dt):
                grid_shape = [self.Nx, self.Ny, self.Nz]
                reshaped_eps  = {}
                reshaped_mu   = {}
                reshaped_cond = {}

                eps  = np.ones ((self.Nx, self.Ny, self.Nz), dtype=np.float32) * self.eps0
                mu   = np.ones ((self.Nx, self.Ny, self.Nz), dtype=np.float32) * self.mu0
                cond = np.zeros((self.Nx, self.Ny, self.Nz), dtype=np.float32)

                for shape, mat in self.objects:
                        mask = shape.mask(grid_shape)
                        eps[mask] = mat.eps_r * self.eps0
                        cond[mask] = mat.cond

                        mask = shape.mask(grid_shape)
                        mu[mask] = mat.mu_r * self.mu0

                reshaped_eps['Ex'] = 0.5 * (eps[:-1,:,:] + eps[1:,:,:])   # x엣지: (Nx-1, Ny, Nz)
                reshaped_eps['Ey'] = 0.5 * (eps[:,:-1,:] + eps[:,1:,:])   # y엣지: (Nx, Ny-1, Nz)
                reshaped_eps['Ez'] = 0.5 * (eps[:,:,:-1] + eps[:,:,1:])   # z엣지: (Nx, Ny, Nz-1)
                
                reshaped_mu["Hx"] = 0.25 * (mu[:,:-1,:-1] + mu[:,1:,:-1]   # x면: (Nx, Ny-1, Nz-1)
                    + mu[:,:-1,1:]  + mu[:,1:,1:])
                reshaped_mu["Hy"] = 0.25 * (mu[:-1,:,:-1] + mu[1:,:,:-1]   # y면: (Nx-1, Ny, Nz-1)
                    + mu[:-1,:,1:]  + mu[1:,:,1:])
                reshaped_mu["Hz"] = 0.25 * (mu[:-1,:-1,:] + mu[1:,:-1,:]   # z면: (Nx-1, Ny-1, Nz)
                    + mu[:-1,1:,:]  + mu[1:,1:,:])
                
                reshaped_cond['Ex'] = 0.5 * (cond[:-1,:,:] + cond[1:,:,:])   # x엣지: (Nx-1, Ny, Nz)
                reshaped_cond['Ey'] = 0.5 * (cond[:,:-1,:] + cond[:,1:,:])   # y엣지: (Nx, Ny-1, Nz)
                reshaped_cond['Ez'] = 0.5 * (cond[:,:,:-1] + cond[:,:,1:])   # z엣지: (Nx, Ny, Nz-1)

                Ca = {k: self.make_Ca(reshaped_cond[k], reshaped_eps[k], dt) for k in ('Ex','Ey','Ez')}
                Cb = {k: self.make_Cb(reshaped_cond[k], reshaped_eps[k], dt) for k in ('Ex','Ey','Ez')}

                return {
                        "eps" : reshaped_eps,
                        "mu"  : reshaped_mu,
                        "cond": reshaped_cond,
                        "Ca"  : Ca,
                        "Cb"  : Cb,
                }