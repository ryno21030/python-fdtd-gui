# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A PyQt6-based 3D FDTD (Finite-Difference Time-Domain) electromagnetic simulation GUI. Users configure grid/source/material/detector/PML parameters through a tabbed dark-themed interface, run the simulation on a background thread, and visualize results via animated field plots.

## Running the App

```bash
pip install -r requirements.txt
python main.py
```

No build step. No test suite or linting config exists in this project.

## Architecture

The codebase follows a strict three-layer separation:

**GUI Layer** (`mainwindow.py`, `panels/`, `theme.py`)

- `MainWindow` is a sidebar + `QStackedWidget` with 6 panels (Grid, Source, Material, Detector, PML, Visualize)
- `panels/_base.py` provides factory helpers (`spin()`, `dspin()`, `combo()`, `xyz_row()`, etc.) used by all panels — add widget helpers here, not inline in panel files
- `theme.py` applies a VS Code Dark+ `QApplication` stylesheet globally; all color/font decisions live there

**Configuration Layer** (`config.py`)

- Dataclass hierarchy: `SimConfig` → `GridConfig`, `SourceConfig`, `MaterialConfig`, `DetectorConfig`, `PMLConfig`, `VisualizeConfig`
- `SimConfig.validate()` is the single validation entry point — called before simulation starts
- `SimConfig.to_json()` / `SimConfig.from_json()` handle persistence; saved files go in the user-chosen output directory

**Simulation Layer** (`main_feature/`, `runner.py`, `sub_feature/`)

- `runner.py`: `SimRunner(QThread)` builds the scene, runs the time loop, emits `progress(int)`, `status(str)`, `finished()`, `error(str)` signals
- `main_feature/engine.py`: Yee-grid FDTD — `Hupdate()` then `Eupdate()` each timestep using curl of adjacent fields
- `main_feature/field.py`: `Field` dataclass holding 6 NumPy arrays (Ex, Ey, Ez, Hx, Hy, Hz)
- `main_feature/materials.py`: `Scene.bake()` stamps material properties (eps, mu, sigma) into the field grid; shapes are `Box`, `Sphere`, `AsymmetricSawtooth`
- `main_feature/CPML.py`: Convolutional PML — thickness/order/reflection controlled by `PMLConfig`; E-field coefficients use stagger=0, H-field use stagger=1
- `main_feature/sources.py`: Gaussian pulse (`gaussian_pulse`) and plane wave (`gaussian_plane_wave`) injection
- `main_feature/detectors.py`: plane/point field recording; `bake()` pre-computes boolean masks for Poynting extraction
- `sub_feature/poynting.py`: `Poynting` class averages E/H to cell centers on the Yee grid and computes cross products (Sx=Ey×Hz−Ez×Hy, etc.)

**Data flow:**

```text
GUI panels → SimConfig → SimRunner → Engine time loop → NPZ files → VisualizePanel
```

## Key Conventions

- Panel classes restore state via `load_from(cfg)` (config → widgets). For Grid and PML, `apply_to(cfg)` writes back widgets → config. Source/Material/Detector panels **directly mutate** `cfg.sources`/`cfg.materials`/`cfg.detectors` in real-time; their `apply_to()` is a no-op.
- `SimRunner` is constructed fresh each run; it is not reused across simulations.
- Output files are NumPy `.npz` archives written to `{output_dir}/save_{unix_ms}/`; `VisualizePanel` reads these directly.
- Source injection uses `grid.t` (the running absolute time accumulated in `GridConfig.t`), not the integer step index.
- The README (`README.md`) is written in Korean and serves as the end-user manual.

## Yee Grid Array Shapes

Field components are staggered on the Yee grid. The 6 arrays in `Field` have these shapes:

| Component | Shape |
| --- | --- |
| `Ex` | `(Nx-1, Ny,   Nz  )` |
| `Ey` | `(Nx,   Ny-1, Nz  )` |
| `Ez` | `(Nx,   Ny,   Nz-1)` |
| `Hx` | `(Nx,   Ny-1, Nz-1)` |
| `Hy` | `(Nx-1, Ny,   Nz-1)` |
| `Hz` | `(Nx-1, Ny-1, Nz  )` |

Poynting averaging produces a cell-centre grid of size `(Nx-1, Ny-1, Nz-1)`.

## Scene / Bake Output Format

`Scene.bake(dt)` returns a dict used by the engine and stored in `runner.baked`:

```python
{
  "Ca":   {"Ex": ..., "Ey": ..., "Ez": ...},   # lossy E-field decay coefficient
  "Cb":   {"Ex": ..., "Ey": ..., "Ez": ...},   # E-field curl coefficient
  "eps":  {"Ex": ..., "Ey": ..., "Ez": ...},
  "mu":   {"Hx": ..., "Hy": ..., "Hz": ...},
  "cond": {"Ex": ..., "Ey": ..., "Ez": ...},
}
```

## Preset Materials

`main_feature/materials.py` exports ready-made `Material` instances: `VACUUM`, `COPPER`, `GOLD`, `SILICON`, `GLASS`, `WATER`. These are available to import in `runner.py` but are not yet exposed in the GUI.

## Unimplemented Features

- `sinusoidal` source type: fields exist in `SourceConfig` (`frequency`, `phase`) but `runner.py` raises `NotImplementedError` — do not wire it to the GUI without implementing `Sources.add_sinusoidal`.

## NPZ Output Format

Per-detector file (`{name}.npz`): arrays keyed by field name (`Ex`, `Ey`, `Ez`, `Hx`, `Hy`, `Hz`, `Sx`, `Sy`, `Sz`) — each shaped `[time_frame, ...]`. Metadata file (`metadata.npz`): grid dims/spacing/dt, per-component eps/mu/cond arrays, source positions, detector metadata. Global Poynting file (`poynting_global.npz`): `Sx/Sy/Sz` time-stacked 3D arrays, written only when `VisualizeConfig.save_poynting=True`.

## Config Fields Reference

| Dataclass | Notable fields |
| --- | --- |
| `GridConfig` | `Nx/Ny/Nz`, `dx/dy/dz`, `T`, `dt` (auto via Courant), `save_every` |
| `SourceConfig` | `type` (`gaussian_pulse`\|`gaussian_plane_wave`), `component` (Ex\|Ey\|Ez), `tau`, `t0` |
| `MaterialConfig` | `shape` (Box\|Sphere\|Sawtooth), `eps`, `mu`, `cond`; Box: `x0–z1`; Sphere: `cx/cy/cz/r`; Sawtooth: `z_base/height/period/duty` |
| `DetectorConfig` | `type` (`plane`\|`point`), `axis` (x\|y\|z), `position`; `quantities` list supports `"Sx"/"Sy"/"Sz"` in addition to E/H components |
| `PMLConfig` | `thickness`, `R0`, `m`, `kappa_max`, `alpha_max`, `sigma_max`; `auto_sigma_max(grid)` derives σ_max from spacing |

## SimRunner Execution Sequence

1. `_build_scene()` — create `Scene`, apply material shapes, call `bake()` → Ca/Cb update coefficients
2. `_build_engine()` — assemble Field, CPML, Sources, Detectors, optional Poynting buffer
3. Time loop: `engine.step(t_step)` each timestep, emit `progress` every step
4. `save_results()` — write detector NPZ files + `metadata.npz`
