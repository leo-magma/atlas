# Athena — cross-asset ML layer for the Atlas suite

**Athena** is a **v0 scaffold** for chaining feature engineering, training, prediction, evaluation, and persistence in a single **`.ath` DSL**, using tabular data compatible with **Atlas**, **Neptune**, **Hydra**, and **Chronos**.

## Layout

- The package lives at repo root in **`athena/`**, alongside **`atlas/`**, **`neptune/`**, **`hydra/`**, and **`chronos/`**.
- Line syntax matches **Atlas** (`name = verb …` and `print name`). Lines starting with **`export`**, **`save`**, or **`load`** are parsed as **directives** (see [docs/athena-dsl.md](../docs/athena-dsl.md)).

## Running

```bash
pip install -e ".[dev]"
athena run athena/examples/stock_prediction.ath
python -m athena run athena/examples/stock_prediction.ath
```

## Python API

```python
from athena import AthenaInterpreter

AthenaInterpreter().run_file("athena/examples/stock_prediction.ath")
```

## v0 scope

- **`features`**: `diff`, `pct_change`, `rolling_mean`, `rolling_std`, `zscore`, `normalize`, `volatility`, `correlation`, `pca`, plus **`duration`**, **`convexity`**, **`spread`** when those columns already exist on the frame.
- **`train`**: `linear`, `ridge`, `lasso`, `rf`, `garch` (EWMA volatility proxy), `kmeans`, `isolation_forest`, `logistic`. **`lightgbm`** / **`xgboost`** are optional dependencies (clear error if missing).
- **`predict`**: with `horizon=10d`-style kwargs, v0 uses a **naive constant-level** forecast.

Full specification: [SPEC.md](SPEC.md). Grammar reference: [../docs/athena-dsl.md](../docs/athena-dsl.md).

## Package tree

```
athena/
  core.py parser.py commands.py cli.py
  features/   models/   io/
  examples/
```
