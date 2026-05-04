# Chronos — time-series ETL DSL (design)

## Purpose and scope

- **Goal**: Centralize **time-series preparation** for Atlas / Neptune / Hydra pipelines.
- **Scope (v0)**: Tabular OHLCV (and friends) keyed by `date` (+ optional `ticker`).
- **Primary capabilities**: load, clean (missing rules), resample, shift/lag, diff/returns-like ops, normalization.

## Architecture

| Area | Module | Responsibility |
|------|--------|----------------|
| ETL | `etl/load.py` | CSV / table ingest → `TimeSeries` / DataFrame contract. |
| ETL | `etl/clean.py` | `dropna`, forward-fill policy, outlier flags (TBD). |
| ETL | `etl/join.py` | As-of / inner joins between series (TBD). |
| ETL | `etl/normalize.py` | z-score, min-max, etc. |
| TS | `ts/resample.py` | Calendar / business rules (`1d`, `1w`, …). |
| TS | `ts/shift.py` | Lag / lead. |
| TS | `ts/diff.py` | Differences on selected column(s). |
| TS | `ts/rolling.py` | Rolling mean / std (windowed). |
| TS | `ts/stats.py` | Summary stats, correlation helpers. |
| Shell | `core.py` / `commands.py` / `parser.py` | Same interpreter pattern as Atlas. |

## Data model (interface)

### `TimeSeries`

- **Index**: ordered datetime (timezone policy TBD).
- **Columns**: OHLCV + identifiers; Chronos commands select by `column=`.

## Planned commands

```text
ts = load "prices.csv"
clean = clean ts dropna=true
daily = resample clean freq=1d method=last
lag1 = shift daily periods=1
ret = diff daily column=close
z = normalize ret method=zscore
print z
```

## Boundary

- Chronos **does not** compute regulatory VaR; it shapes data for **Atlas** (and others).
