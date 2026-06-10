"""
engine.py
FDTD 시뮬레이터의 핵심 엔진을 구현하는 파일입니다.
필드 업데이트, 소스 주입, 검출기 기록 등의 주요 기능을 담당합니다.
"""
class Engine:
        def __init__(self, field, scene,
                        cpml, sources, detectors, grid, poynting=None):
                self.field = field
                self.cpml = cpml
                self.sources = sources
                self.detectors = detectors
                self.grid = grid
                self.scene = scene
                self.poynting = poynting

        def step(self, t_step):
                self.Hupdate(self.grid.dt)
                self.Eupdate(self.grid.dt)
                self.inject_sources()
                if t_step % self.grid.save_every == 0:
                        self.record_detectors()

        def inject_sources(self):
                self.sources.emit(self.field, self.grid)

        def record_detectors(self):
                self.detectors.detect(self.field)
                if self.poynting is not None:
                        Sx, Sy, Sz = self.poynting.compute(self.field)
                        self.detectors.detect_poynting(Sx, Sy, Sz)
                        self.poynting.record_global()

        def update_psi(self, b, psi, c, d):
                psi *= b
                psi += c * d
        
        def Hupdate(self, dt):

                f = self.field
                c = self.cpml
                s = self.scene
                g = self.grid

                self.dEz_dy = (f.Ez[:,1:,:] - f.Ez[:,:-1,:]) / g.dy
                self.dEy_dz = (f.Ey[:,:,1:] - f.Ey[:,:,:-1]) / g.dz
                self.dEx_dz = (f.Ex[:,:,1:] - f.Ex[:,:,:-1]) / g.dz
                self.dEz_dx = (f.Ez[1:,:,:] - f.Ez[:-1,:,:]) / g.dx
                self.dEy_dx = (f.Ey[1:,:,:] - f.Ey[:-1,:,:]) / g.dx
                self.dEx_dy = (f.Ex[:,1:,:] - f.Ex[:,:-1,:]) / g.dy

                self.update_psi(c.coeff["Hx_y"]["b"], c.psi["Hx_y"], c.coeff["Hx_y"]["c"], self.dEz_dy)
                self.update_psi(c.coeff["Hx_z"]["b"], c.psi["Hx_z"], c.coeff["Hx_z"]["c"], self.dEy_dz)
                self.update_psi(c.coeff["Hy_x"]["b"], c.psi["Hy_x"], c.coeff["Hy_x"]["c"], self.dEz_dx)
                self.update_psi(c.coeff["Hy_z"]["b"], c.psi["Hy_z"], c.coeff["Hy_z"]["c"], self.dEx_dz)
                self.update_psi(c.coeff["Hz_x"]["b"], c.psi["Hz_x"], c.coeff["Hz_x"]["c"], self.dEy_dx)
                self.update_psi(c.coeff["Hz_y"]["b"], c.psi["Hz_y"], c.coeff["Hz_y"]["c"], self.dEx_dy)

                f.Hx -= dt / s["mu"]["Hx"] * (
                        (self.dEz_dy / c.coeff["Hx_y"]["kappa"] + c.psi["Hx_y"])
                        -
                        (self.dEy_dz / c.coeff["Hx_z"]["kappa"] + c.psi["Hx_z"])
                )
                f.Hy -= dt / s["mu"]["Hy"] * (
                        (self.dEx_dz / c.coeff["Hy_z"]["kappa"] + c.psi["Hy_z"])
                        -
                        (self.dEz_dx / c.coeff["Hy_x"]["kappa"] + c.psi["Hy_x"])
                )
                f.Hz -= dt / s["mu"]["Hz"] * (
                        (self.dEy_dx / c.coeff["Hz_x"]["kappa"] + c.psi["Hz_x"])
                        -
                        (self.dEx_dy / c.coeff["Hz_y"]["kappa"] + c.psi["Hz_y"])
                )
        
        def Eupdate(self,dt):
                f = self.field
                c = self.cpml
                s = self.scene
                g = self.grid

                self.dHz_dy = (f.Hz[:,1:,:] - f.Hz[:,:-1,:]) / g.dy
                self.dHy_dz = (f.Hy[:,:,1:] - f.Hy[:,:,:-1]) / g.dz
                self.dHz_dx = (f.Hz[1:,:,:] - f.Hz[:-1,:,:]) / g.dx
                self.dHx_dz = (f.Hx[:,:,1:] - f.Hx[:,:,:-1]) / g.dz
                self.dHy_dx = (f.Hy[1:,:,:] - f.Hy[:-1,:,:]) / g.dx
                self.dHx_dy = (f.Hx[:,1:,:] - f.Hx[:,:-1,:]) / g.dy

                self.update_psi(c.coeff["Ex_y"]["b"][:, 1:-1, :], c.psi["Ex_y"], c.coeff["Ex_y"]["c"][:, 1:-1, :], self.dHz_dy)
                self.update_psi(c.coeff["Ex_z"]["b"][:, :, 1:-1], c.psi["Ex_z"], c.coeff["Ex_z"]["c"][:, :, 1:-1], self.dHy_dz)
                self.update_psi(c.coeff["Ey_x"]["b"][1:-1, :, :], c.psi["Ey_x"], c.coeff["Ey_x"]["c"][1:-1, :, :], self.dHz_dx)
                self.update_psi(c.coeff["Ey_z"]["b"][:, :, 1:-1], c.psi["Ey_z"], c.coeff["Ey_z"]["c"][:, :, 1:-1], self.dHx_dz)
                self.update_psi(c.coeff["Ez_x"]["b"][1:-1, :, :], c.psi["Ez_x"], c.coeff["Ez_x"]["c"][1:-1, :, :], self.dHy_dx)
                self.update_psi(c.coeff["Ez_y"]["b"][:, 1:-1, :], c.psi["Ez_y"], c.coeff["Ez_y"]["c"][:, 1:-1, :], self.dHx_dy)

                f.Ex[:,1:-1,1:-1] = (
                        s["Ca"]["Ex"][:,1:-1,1:-1] * f.Ex[:,1:-1,1:-1]
                        + s["Cb"]["Ex"][:,1:-1,1:-1] * (
                                (self.dHz_dy[:, :, 1:-1] / c.coeff["Ex_y"]["kappa"][:, 1:-1, :] + c.psi["Ex_y"][:, :, 1:-1])
                                -
                                (self.dHy_dz[:, 1:-1, :] / c.coeff["Ex_z"]["kappa"][:, :, 1:-1] + c.psi["Ex_z"][:, 1:-1, :])
                        )
                )

                f.Ey[1:-1,:,1:-1] = (
                        s["Ca"]["Ey"][1:-1,:,1:-1] * f.Ey[1:-1,:,1:-1]
                        + s["Cb"]["Ey"][1:-1,:,1:-1] * (
                                (self.dHx_dz[1:-1, :, :] / c.coeff["Ey_z"]["kappa"][:, :, 1:-1] + c.psi["Ey_z"][1:-1, :, :])
                                -
                                (self.dHz_dx[:, :, 1:-1] / c.coeff["Ey_x"]["kappa"][1:-1, :, :] + c.psi["Ey_x"][:, :, 1:-1])
                        )
                )

                f.Ez[1:-1,1:-1,:] = (
                        s["Ca"]["Ez"][1:-1,1:-1,:] * f.Ez[1:-1,1:-1,:]
                        + s["Cb"]["Ez"][1:-1,1:-1,:] * (
                                (self.dHy_dx[:, 1:-1, :] / c.coeff["Ez_x"]["kappa"][1:-1, :, :] + c.psi["Ez_x"][:, 1:-1, :])
                                -
                                (self.dHx_dy[1:-1, :, :] / c.coeff["Ez_y"]["kappa"][:, 1:-1, :] + c.psi["Ez_y"][1:-1, :, :])
                        )
                )

