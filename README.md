# Engine Component Fatigue & Failure Analyzer

A Python toolkit for fatigue life, safety factors and buckling of connecting rods,
crankshafts and connecting-rod bolts. It adds a guided failure-analysis workflow
and a material database in which every property is tracked to its source.

## Status

Phase 3: fatigue engine (v0.3.0). Engine load model (Phase 2) plus endurance
limit with Marin factors, notch sensitivity, mean-stress criteria, Basquin and
Morrow finite life, and Euler/Johnson column buckling. Component assessments
(connecting rod, crankshaft, bolts) are not yet implemented.

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
  units.py        display-unit conversions
  provenance.py   data status, sources, traced values and result notes
  sources.py      shared source ids (docs/sources.md)
  buckling.py     Euler and Johnson column buckling
  loads/          kinematics, gas and inertia forces, rod and crankpin loads
  stress/         nominal and equivalent stresses, notch factors
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

## Documentation

- Methods: [engine loads](docs/methods/engine_loads.md),
  [fatigue](docs/methods/fatigue.md), [buckling](docs/methods/buckling.md)
- Worked examples: [docs/worked_examples](docs/worked_examples/README.md)
  (WE-01 to WE-05)
- Sources: [docs/sources.md](docs/sources.md)
- Decisions: [docs/decisions](docs/decisions)

## Data policy

No invented data is presented as real. Every material property carries its
source, date and status (`cited`, `measured` or `assumed`). Raw research data,
such as photographs and measurements of real failed parts, stays outside this
repository; the `data/` folder is ignored and CI fails if any file under it is
committed. See [docs/data_policy.md](docs/data_policy.md).

## License

MIT — see [LICENSE](LICENSE).
