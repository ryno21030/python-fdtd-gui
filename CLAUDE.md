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

**Simulation Layer** (`main_feature/`, `runner.py`)
- `runner.py`: `SimRunner(QThread)` builds the scene, runs the time loop, emits `progress(int)` and `status(str)` signals
- `main_feature/engine.py`: Yee-grid FDTD — `Hupdate()` then `Eupdate()` each timestep using curl of adjacent fields
- `main_feature/field.py`: `Field` dataclass holding 6 NumPy arrays (Ex, Ey, Ez, Hx, Hy, Hz)
- `main_feature/materials.py`: `Scene.bake()` stamps material properties (eps, mu, sigma) into the field grid; shapes are `Box`, `Sphere`, `AsymmetricSawtooth`
- `main_feature/CPML.py`: Convolutional PML absorbing boundaries — thickness/order/reflection controlled by `PMLConfig`
- `main_feature/sources.py`: Gaussian pulse injection; `main_feature/detectors.py`: plane field recording → NPZ output

**Data flow:**
```
GUI panels → SimConfig → SimRunner → Engine time loop → NPZ files → VisualizePanel
```

## Communication

Always respond in Korean. The user is a native Korean speaker and prefers Korean responses regardless of prompt language.

## Key Conventions

- Panel classes collect their values into a config dataclass via a `get_config()` method and restore state via `set_config(cfg)`.
- `SimRunner` is constructed fresh each run; it is not reused across simulations.
- Output files are NumPy `.npz` archives written to the user-selected directory; `VisualizePanel` reads these directly.
- The README (`README.md`) is written in Korean and serves as the end-user manual.
