# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
