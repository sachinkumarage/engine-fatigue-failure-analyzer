# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-18

### Added

- Engine load model in `efa.loads`:
  - `kinematics`: crank radius, crank ratio, angular speed (K1), exact piston
    displacement (K2), piston acceleration series (K3), rod angle (K4).
  - `gas`: `PressureTable` with validation and periodic linear
    interpolation; piston area and gas force (L1).
  - `inertia`: two-mass rod split and reciprocating mass (L2), inertia force
    (L3), rotating-mass centrifugal force (L7).
  - `cycle`: net piston force (L4), rod force and side thrust (L5), crankpin
    forces and torque (L6); `EngineSpec`, `evaluate_cycle`, `peak_load` and
    `CycleResult` with extremes, mean torque and a result note.
- `efa.units` for display-unit conversions and `efa.provenance` with
  `Status`, `Source` and `ResultNote`.
- Engine Loads page: pressure-table and peak-only modes, charts of p_cyl,
  F_g, F_i, F_rod and T, key metrics and the result note.
- Method document `docs/methods/engine_loads.md` and worked examples WE-01 and
  WE-02 with golden tests.
- Unit tests for kinematics, cycle identities, validation and units, and an
  app test that runs every Streamlit page.

### Changed

- CI installs the `app` extra so the app pages are tested.
- Author name set to "S. Kumarage" in LICENSE and package metadata.

## [0.1.0] - 2026-11-18

### Added

- Package skeleton `efa` with subpackages `loads`, `stress`, `fatigue`,
  `components`, `fea`, `materials`, `failure` and `report`.
- Streamlit app shell with a home page and placeholder pages for each module.
- Unit tests for the package version, the architecture rule (no streamlit
  imports in the core package) and the raw-data guard.
- Raw-data guard script `scripts/check_no_raw_data.py`.
- GitHub Actions CI: ruff lint, ruff format check, pytest and raw-data guard.
- Documentation: data policy, Phase 0 decision record, and placeholders for
  methods, worked examples and examples.
- MIT license.
