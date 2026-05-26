"""
runner.py
SimConfig를 받아 시뮬레이터를 별도 QThread에서 실행한다.

신호(signal) 목록
─────────────────
progress  (int)        : 0~100 진행률
status    (str)        : 현재 상태 메시지
finished  ()           : 정상 종료
error     (str)        : 예외 메시지
"""
from __future__ import annotations
import os, time, math
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from config import SimConfig


class SimRunner(QThread):
    progress = pyqtSignal(int)
    status   = pyqtSignal(str)
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, cfg: SimConfig, parent=None):
        super().__init__(parent)
        self._cfg  = cfg
        self._stop = False

    def stop(self):
        self._stop = True

    # ── 메인 실행 ─────────────────────────────────────────
    def run(self):
        try:
            self._execute()
        except Exception as e:
            import traceback
            self.error.emit(traceback.format_exc())

    def _execute(self):
        cfg = self._cfg
        g   = cfg.grid
        p   = cfg.pml

        # ── 상수 ──────────────────────────────────────────
        Nx, Ny, Nz   = g.Nx, g.Ny, g.Nz
        dx, dy, dz   = g.dx, g.dy, g.dz
        dt           = g.effective_dt()
        T            = g.T
        save_every   = g.save_every
        c            = 1.0
        eps0 = mu0   = 1.0

        pml_thick  = p.thickness
        R0         = p.R0
        m0         = p.m
        sigma_max  = -(m0+1)*math.log(R0)/(2*dx*pml_thick)
        kappa_max  = p.kappa_max
        alpha_max  = p.alpha_max

        # ── 필드 초기화 ────────────────────────────────────
        Ex = np.zeros((Nx-1, Ny,   Nz  ))
        Ey = np.zeros((Nx,   Ny-1, Nz  ))
        Ez = np.zeros((Nx,   Ny,   Nz-1))
        Hx = np.zeros((Nx,   Ny-1, Nz-1))
        Hy = np.zeros((Nx-1, Ny,   Nz-1))
        Hz = np.zeros((Nx-1, Ny-1, Nz  ))

        psi_Ex_y = np.zeros((Nx-1, Ny-2, Nz  ))
        psi_Ex_z = np.zeros((Nx-1, Ny,   Nz-2))
        psi_Ey_x = np.zeros((Nx-2, Ny-1, Nz  ))
        psi_Ey_z = np.zeros((Nx,   Ny-1, Nz-2))
        psi_Ez_x = np.zeros((Nx-2, Ny,   Nz-1))
        psi_Ez_y = np.zeros((Nx,   Ny-2, Nz-1))

        psi_Hx_y = np.zeros((Nx,   Ny-1, Nz-1))
        psi_Hx_z = np.zeros((Nx,   Ny-1, Nz-1))
        psi_Hy_x = np.zeros((Nx-1, Ny,   Nz-1))
        psi_Hy_z = np.zeros((Nx-1, Ny,   Nz-1))
        psi_Hz_x = np.zeros((Nx-1, Ny-1, Nz  ))
        psi_Hz_y = np.zeros((Nx-1, Ny-1, Nz  ))

        # ── CPML 계수 ──────────────────────────────────────
        def make_sigma(N, stagger):
            s = np.zeros(N)
            for i in range(pml_thick):
                x = (pml_thick - i - 0.5*stagger) / pml_thick
                s[i] = sigma_max * x**m0
                s[-1-i] = sigma_max * x**m0
            return s

        def make_kappa(N):
            k = np.ones(N)
            for i in range(pml_thick):
                x = (pml_thick - i) / pml_thick
                k[i] = k[-1-i] = 1 + (kappa_max-1)*x**m0
            return k

        def make_alpha(N):
            a = np.zeros(N)
            for i in range(pml_thick):
                x = (pml_thick - i) / pml_thick
                a[i] = a[-1-i] = alpha_max * x
            return a

        def cpml(N, stagger, axis):
            sig = make_sigma(N, stagger)
            kap = make_kappa(N)
            alp = make_alpha(N)
            b   = np.exp(-(sig/kap + alp)*dt)
            den = sig*kap + alp*kap**2
            cc  = np.divide(sig*(b-1), den, where=den!=0, out=np.zeros_like(den, dtype=float))
            r   = {"x": lambda a: a.reshape(-1,1,1),
                   "y": lambda a: a.reshape(1,-1,1),
                   "z": lambda a: a.reshape(1,1,-1)}[axis]
            return b, cc, kap, r

        # E용
        bExy,cExy,kExy,rExy = cpml(Ny,   0,"y"); kExy=rExy(kExy); bExy=rExy(bExy); cExy=rExy(cExy)
        bExz,cExz,kExz,rExz = cpml(Nz,   0,"z"); kExz=rExz(kExz); bExz=rExz(bExz); cExz=rExz(cExz)
        bEyx,cEyx,kEyx,rEyx = cpml(Nx,   0,"x"); kEyx=rEyx(kEyx); bEyx=rEyx(bEyx); cEyx=rEyx(cEyx)
        bEyz,cEyz,kEyz,rEyz = cpml(Nz,   0,"z"); kEyz=rEyz(kEyz); bEyz=rEyz(bEyz); cEyz=rEyz(cEyz)
        bEzx,cEzx,kEzx,rEzx = cpml(Nx,   0,"x"); kEzx=rEzx(kEzx); bEzx=rEzx(bEzx); cEzx=rEzx(cEzx)
        bEzy,cEzy,kEzy,rEzy = cpml(Ny,   0,"y"); kEzy=rEzy(kEzy); bEzy=rEzy(bEzy); cEzy=rEzy(cEzy)
        # H용
        bHxy,cHxy,kHxy,rHxy = cpml(Ny-1, 1,"y"); kHxy=rHxy(kHxy); bHxy=rHxy(bHxy); cHxy=rHxy(cHxy)
        bHxz,cHxz,kHxz,rHxz = cpml(Nz-1, 1,"z"); kHxz=rHxz(kHxz); bHxz=rHxz(bHxz); cHxz=rHxz(cHxz)
        bHyx,cHyx,kHyx,rHyx = cpml(Nx-1, 1,"x"); kHyx=rHyx(kHyx); bHyx=rHyx(bHyx); cHyx=rHyx(cHyx)
        bHyz,cHyz,kHyz,rHyz = cpml(Nz-1, 1,"z"); kHyz=rHyz(kHyz); bHyz=rHyz(bHyz); cHyz=rHyz(cHyz)
        bHzx,cHzx,kHzx,rHzx = cpml(Nx-1, 1,"x"); kHzx=rHzx(kHzx); bHzx=rHzx(bHzx); cHzx=rHzx(cHzx)
        bHzy,cHzy,kHzy,rHzy = cpml(Ny-1, 1,"y"); kHzy=rHzy(kHzy); bHzy=rHzy(bHzy); cHzy=rHzy(cHzy)

        # ── 재질 / Ca Cb ───────────────────────────────────
        from config import MaterialConfig
        eps_vol = np.ones((Nx,Ny,Nz))*eps0
        mu_vol  = np.ones((Nx,Ny,Nz))*mu0
        sig_vol = np.zeros((Nx,Ny,Nz))

        for m_cfg in cfg.materials:
            mask = self._shape_mask(m_cfg, (Nx,Ny,Nz))
            eps_vol[mask] = (m_cfg.n ** 2) * eps0   # n² × ε₀
            sig_vol[mask] = m_cfg.cond
        
        eps_Ex = 0.5*(eps_vol[:-1,:,:]+eps_vol[1:,:,:])
        eps_Ey = 0.5*(eps_vol[:,:-1,:]+eps_vol[:,1:,:])
        eps_Ez = 0.5*(eps_vol[:,:,:-1]+eps_vol[:,:,1:])
        sig_Ex = 0.5*(sig_vol[:-1,:,:]+sig_vol[1:,:,:])
        sig_Ey = 0.5*(sig_vol[:,:-1,:]+sig_vol[:,1:,:])
        sig_Ez = 0.5*(sig_vol[:,:,:-1]+sig_vol[:,:,1:])
        mu_Hx  = 0.25*(mu_vol[:,:-1,:-1]+mu_vol[:,1:,:-1]+mu_vol[:,:-1,1:]+mu_vol[:,1:,1:])
        mu_Hy  = 0.25*(mu_vol[:-1,:,:-1]+mu_vol[1:,:,:-1]+mu_vol[:-1,:,1:]+mu_vol[1:,:,1:])
        mu_Hz  = 0.25*(mu_vol[:-1,:-1,:]+mu_vol[1:,:-1,:]+mu_vol[:-1,1:,:]+mu_vol[1:,1:,:])

        def Ca(sig,eps): return (1-sig*dt/(2*eps))/(1+sig*dt/(2*eps))
        def Cb(sig,eps): return (dt/eps)/(1+sig*dt/(2*eps))
        Ca_Ex=Ca(sig_Ex,eps_Ex); Cb_Ex=Cb(sig_Ex,eps_Ex)
        Ca_Ey=Ca(sig_Ey,eps_Ey); Cb_Ey=Cb(sig_Ey,eps_Ey)
        Ca_Ez=Ca(sig_Ez,eps_Ez); Cb_Ez=Cb(sig_Ez,eps_Ez)

        # ── 버퍼 ───────────────────────────────────────────
        det_bufs = [
            {q: [] for q in d.quantities}
            for d in cfg.detectors
        ]

        def psi_update(b,psi,c,d): return b*psi + c*d

        # ── 루프 ───────────────────────────────────────────
        n_steps = int(T/dt)
        t = 0.0

        self.status.emit("시뮬레이션 시작...")

        for step in range(n_steps):
            if self._stop:
                self.status.emit("중단됨")
                return

            # H update
            t += dt/2
            dEz_dy=(Ez[:,1:,:]-Ez[:,:-1,:])/dy; dEy_dz=(Ey[:,:,1:]-Ey[:,:,:-1])/dz
            dEx_dz=(Ex[:,:,1:]-Ex[:,:,:-1])/dz; dEz_dx=(Ez[1:,:,:]-Ez[:-1,:,:])/dx
            dEy_dx=(Ey[1:,:,:]-Ey[:-1,:,:])/dx; dEx_dy=(Ex[:,1:,:]-Ex[:,:-1,:])/dy

            psi_Hx_y=psi_update(bHxy,psi_Hx_y,cHxy,dEz_dy)
            psi_Hx_z=psi_update(bHxz,psi_Hx_z,cHxz,dEy_dz)
            psi_Hy_x=psi_update(bHyx,psi_Hy_x,cHyx,dEz_dx)
            psi_Hy_z=psi_update(bHyz,psi_Hy_z,cHyz,dEx_dz)
            psi_Hz_x=psi_update(bHzx,psi_Hz_x,cHzx,dEy_dx)
            psi_Hz_y=psi_update(bHzy,psi_Hz_y,cHzy,dEx_dy)

            Hx -= dt/mu_Hx*((dEz_dy/kHxy+psi_Hx_y)-(dEy_dz/kHxz+psi_Hx_z))
            Hy -= dt/mu_Hy*((dEx_dz/kHyz+psi_Hy_z)-(dEz_dx/kHyx+psi_Hy_x))
            Hz -= dt/mu_Hz*((dEy_dx/kHzx+psi_Hz_x)-(dEx_dy/kHzy+psi_Hz_y))

            # E update
            t += dt/2
            dHz_dy=(Hz[:,1:,:]-Hz[:,:-1,:])/dy; dHy_dz=(Hy[:,:,1:]-Hy[:,:,:-1])/dz
            dHx_dz=(Hx[:,:,1:]-Hx[:,:,:-1])/dz; dHz_dx=(Hz[1:,:,:]-Hz[:-1,:,:])/dx
            dHy_dx=(Hy[1:,:,:]-Hy[:-1,:,:])/dx; dHx_dy=(Hx[:,1:,:]-Hx[:,:-1,:])/dy

            psi_Ex_y=psi_update(bExy[:,1:-1,:],psi_Ex_y,cExy[:,1:-1,:],dHz_dy)
            psi_Ex_z=psi_update(bExz[:,:,1:-1],psi_Ex_z,cExz[:,:,1:-1],dHy_dz)
            psi_Ey_x=psi_update(bEyx[1:-1,:,:],psi_Ey_x,cEyx[1:-1,:,:],dHz_dx)
            psi_Ey_z=psi_update(bEyz[:,:,1:-1],psi_Ey_z,cEyz[:,:,1:-1],dHx_dz)
            psi_Ez_x=psi_update(bEzx[1:-1,:,:],psi_Ez_x,cEzx[1:-1,:,:],dHy_dx)
            psi_Ez_y=psi_update(bEzy[:,1:-1,:],psi_Ez_y,cEzy[:,1:-1,:],dHx_dy)

            Ex[:,1:-1,1:-1]=Ca_Ex[:,1:-1,1:-1]*Ex[:,1:-1,1:-1]+Cb_Ex[:,1:-1,1:-1]*(
                (dHz_dy[:,:,1:-1]/kExy[:,1:-1,:]+psi_Ex_y[:,:,1:-1])
               -(dHy_dz[:,1:-1,:]/kExz[:,:,1:-1]+psi_Ex_z[:,1:-1,:]))
            Ey[1:-1,:,1:-1]=Ca_Ey[1:-1,:,1:-1]*Ey[1:-1,:,1:-1]+Cb_Ey[1:-1,:,1:-1]*(
                (dHx_dz[1:-1,:,:]/kEyz[:,:,1:-1]+psi_Ey_z[1:-1,:,:])
               -(dHz_dx[:,:,1:-1]/kEyx[1:-1,:,:]+psi_Ey_x[:,:,1:-1]))
            Ez[1:-1,1:-1,:]=Ca_Ez[1:-1,1:-1,:]*Ez[1:-1,1:-1,:]+Cb_Ez[1:-1,1:-1,:]*(
                (dHy_dx[:,1:-1,:]/kEzx[1:-1,:,:]+psi_Ez_x[:,1:-1,:])
               -(dHx_dy[1:-1,:,:]/kEzy[:,1:-1,:]+psi_Ez_y[1:-1,:,:]))

            # 광원
            for s in cfg.sources:
                # Smooth ramping: 초기에 천천히 시작하고 점진적으로 증가
                ramp_start = s.t0 - 3 * s.tau  # 3τ 전부터 시작
                ramp_end = s.t0 + 3 * s.tau    # 3τ 후까지 ramping
                
                if t < ramp_start:
                    ramp = 0.0
                elif t > ramp_end:
                    ramp = 1.0
                else:
                    # Smooth step (ease-in)
                    x = (t - ramp_start) / (ramp_end - ramp_start)
                    ramp = x * x * (3 - 2*x)  # Smoothstep 함수
                
                val = ramp * (-s.amplitude*(t-s.t0)/s.tau**2*math.exp(-((t-s.t0)/s.tau)**2))
                
                if   s.component=="Ex": Ex[s.x, s.y, s.z] += val
                elif s.component=="Ey": Ey[s.x, s.y, s.z] += val
                else:                   Ez[s.x, s.y, s.z] += val

            # 저장
            if step % save_every == 0:
                for det_buf, d_cfg in zip(det_bufs, cfg.detectors):
                    self._record_detector(det_buf, d_cfg, Ex, Ey, Ez, Hx, Hy, Hz)

            if step % max(n_steps//100, 1) == 0:
                pct = int(100*step/n_steps)
                self.progress.emit(pct)
                self.status.emit(f"  스텝 {step:,} / {n_steps:,}  ({pct}%)")

        # ── 저장 ───────────────────────────────────────────
        self.status.emit("파일 저장 중...")
        import time as _time
        dirname = f"frames_{int(_time.time())}"
        out_dir = os.path.join(cfg.output_dir, dirname)
        os.makedirs(out_dir, exist_ok=True)

        # 검광기
        for d in cfg.detectors:
            if d.name == "":
                d.name = f"detector_{cfg.detectors.index(d)}"
        if any(any(buf.values()) for buf in det_bufs):
            for det_buf, d in zip(det_bufs, cfg.detectors):
                if any(det_buf.values()):
                    np.savez_compressed(
                        os.path.join(out_dir, f"{d.name}.npz"),
                        **{q: np.stack(det_buf[q]) for q in d.quantities if det_buf[q]},
                        _axis=np.array(d.axis),
                        _index=np.array(d.index),
                )

        # 메타데이터
        np.savez(
            os.path.join(out_dir,"metadata.npz"),
            Nx=Nx,Ny=Ny,Nz=Nz,dx=dx,dy=dy,dz=dz,dt=dt,T=T,
            eps_vol=eps_vol, mu_vol=mu_vol, sig_vol=sig_vol,
            src_x=np.array([s.x for s in cfg.sources]),
            src_y=np.array([s.y for s in cfg.sources]),
            src_z=np.array([s.z for s in cfg.sources]),
            det_axis=np.array([d.axis for d in cfg.detectors]),
            det_index=np.array([d.index for d in cfg.detectors]),
            det_quantities=np.array([d.quantities for d in cfg.detectors], dtype=object),
        )

        self.progress.emit(100)
        self.status.emit(f"  완료 → {out_dir}")
        self.finished.emit()

    # ── 헬퍼: 도형 마스크 ────────────────────────────────
    @staticmethod
    def _shape_mask(m, shape):
        Nx,Ny,Nz = shape
        if m.shape == "Box":
            mask = np.zeros(shape, dtype=bool)
            mask[m.x0:m.x1, m.y0:m.y1, m.z0:m.z1] = True
            return mask
        elif m.shape == "Sphere":
            x=np.arange(Nx).reshape(-1,1,1)
            y=np.arange(Ny).reshape(1,-1,1)
            z=np.arange(Nz).reshape(1,1,-1)
            return (x-m.cx)**2+(y-m.cy)**2+(z-m.cz)**2 <= m.r**2
        else:  # Sawtooth
            x=np.arange(Nx,dtype=float)
            xm=x%m.period
            zs=np.where(xm<m.period*m.duty,
                        m.height*xm/(m.period*m.duty),
                        m.height*(1-(xm-m.period*m.duty)/(m.period*(1-m.duty))))
            z_idx=np.arange(Nz,dtype=float).reshape(1,1,Nz)
            return np.broadcast_to(z_idx<(float(m.z_base)+zs.reshape(Nx,1,1)),(Nx,Ny,Nz)).copy()

    # ── 헬퍼: 검광기 기록 ─────────────────────────────────
    @staticmethod
    def _record_detector(buf, d_cfg, Ex, Ey, Ez, Hx, Hy, Hz):
        ax  = d_cfg.axis
        idx = d_cfg.index

        def sl(arr):
            mi = arr.shape[{"x":0,"y":1,"z":2}[ax]]-1
            i  = max(0, min(idx, mi))
            if ax=="x": return arr[i,:,:]
            if ax=="y": return arr[:,i,:]
            return arr[:,:,i]

        field_map = {"Ex":Ex,"Ey":Ey,"Ez":Ez,"Hx":Hx,"Hy":Hy,"Hz":Hz}
        for q in d_cfg.quantities:
            if q in field_map:
                buf[q].append(sl(field_map[q]).astype(np.float32))
