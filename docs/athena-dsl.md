# Athena DSL — grammar reference (v0)

## Line forms

1. **Assignment** — `NAME = VERB PRIMARY [ARGS...] [KEY=VAL ...]`  
   Same rules as Atlas: `PRIMARY` is the first operand (often a quoted path or variable name).  
   Example: `ts = load "../../examples/prices.csv"`

2. **Print** — `print NAME`

3. **Directives** (no `=` on the line in the assignment sense):

   - `export NAME to=PATH` — write a pandas `DataFrame` or `Series` to CSV.
   - `save VARNAME to=PATH` — `joblib` dump the object (e.g. a trained model wrapper).
   - `load VARNAME from=PATH` — `joblib` load into `VARNAME`.

## Verbs (summary)

| Verb | Example | Notes |
|------|---------|--------|
| `load` | `ts = load "x.csv"` | Resolves paths from the script directory. |
| `load_curve` / `load_bond` / `load_option` | `curve = load_curve "c.csv"` | v0: same as CSV load. |
| `features` | `feat = features ts methods=diff,rolling_mean` | Comma-separated `methods=` list. |
| `train` | `model = train feat target=close algo=rf` | `window=` optional (rolling / garch). |
| `predict` | `pred = predict model feat` | Or `predict model horizon=10d` (naive v0). |
| `evaluate` | `s = evaluate model feat target=close metrics=rmse,r2` | |
| `load_model` | `m = load_model "m.pkl"` | Or `from=` as keyword if extended later. |

## Metrics (evaluate)

Comma-separated in `metrics=`: `rmse`, `mae`, `mape`, `r2`, `sharpe`, `drawdown`, `accuracy`.
