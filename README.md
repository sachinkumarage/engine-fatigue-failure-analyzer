# Engine Component Fatigue & Failure Analyzer

A Python toolkit for fatigue life, safety factors and buckling of connecting rods,
crankshafts and connecting-rod bolts. It adds a guided failure-analysis workflow
and a material database in which every property is tracked to its source.

## Status

Phase 1 skeleton, v0.1.0 — no calculations yet.

## Install

Requires Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,app]"
```

## Run tests

```bash
pytest
```

## Run the app

```bash
streamlit run app/Home.py
```

## Project structure

```
src/efa/          core package (numpy, scipy only; never imports streamlit)
  loads/          gas and inertia forces over the crank cycle
  stress/         nominal and equivalent stresses
  fatigue/        endurance limit, Marin factors, mean-stress correction, life
  components/     connecting rod, crankshaft, connecting-rod bolts
  fea/            simple beam models and result post-processing
  materials/      source-tracked material properties
  failure/        guided failure-analysis workflow
  report/         HTML reports
app/              Streamlit user interface
tests/            unit tests, golden results, fixtures
docs/             methods, worked examples, decisions, data policy
examples/         example scripts and input files
scripts/          repository checks
```

## Data policy

No invented data is presented as real. Every material property carries its
source, date and status (`cited`, `measured` or `assumed`). Raw research data,
such as photographs and measurements of real failed parts, stays outside this
repository; the `data/` folder is ignored and CI fails if any file under it is
committed. See [docs/data_policy.md](docs/data_policy.md).

## License

MIT — see [LICENSE](LICENSE).
