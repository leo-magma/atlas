# 02 — Standard library reference (Atlas verbs)

This chapter documents Atlas verbs as a **language-level standard library**. It is intended to be a more formal companion to `docs/commands.md`.

The **canonical** list of verbs is the dispatch table in `atlas/commands.py`.

## 2.1 Conventions shared by many verbs

### Frames and single-column frames

Many verbs expect a **single-column frame** (a table with exactly one column). When a CSV contains multiple columns, use:

```text
close = select prices column=close
```

### Index alignment

Whenever frames are combined (e.g., `bind`), the default is an **inner join** on the index to guarantee overlapping observations. This prevents “silent mismatch” bugs where one asset’s data leaks into another’s missing periods.

### Numerical cleaning

Many operations:

- drop leading missing data introduced by shifting
- treat non-finite values (`inf`, `-inf`) as missing

These behaviors are documented per verb.

## 2.2 Data ingestion

### `load`

```text
df = load "path/to/file.csv"
```

**Purpose**: Load CSV into a frame.

**Primary argument**: file path (quoted recommended).

**Semantics**:

- reads using `pandas.read_csv`
- path is resolved relative to the running script’s directory
- returns a frame

**Failure modes**:

- file not found
- invalid CSV format

## 2.3 Column selection

### `select`

```text
col = select prices column=close
col = select prices close
```

**Purpose**: Extract a single column from a frame, returning a single-column frame.

**Primary argument**: variable name bound to a frame.

**Keyword args**:

- `column`: column name

**Positional args**:

- if `column=` is omitted, the first positional arg is treated as the column name

**Semantics**:

- returns `df[[column]]` (single-column frame)

**Failure modes**:

- missing column
- primary is not a frame

## 2.4 Wide binding

### `bind`

```text
wide = bind r1 r2 r3
```

**Purpose**: Horizontally concatenate single-column frames, producing a wide frame.

**Primary argument**: first frame variable name.

**Positional args**: additional frame variable names.

**Semantics**:

- each input must be a single-column frame
- each column is renamed to the variable name used in the binding (`r1`, `r2`, ...)
- frames are concatenated with an inner join on index

**Failure modes**:

- any input is not a single-column frame
- fewer than 2 inputs

## 2.5 Return transforms

### `returns`

```text
rets = returns close method=log
rets = returns close log
rets = returns close simple
```

**Purpose**: Compute return series from price series.

**Primary argument**: single-column price frame.

**Method parameter**:

- `log` / `ln`: \(\ln(P_t / P_{t-1})\)
- `simple` / `pct` / `arithmetic`: \(P_t/P_{t-1} - 1\)

**Semantics**:

- returns are computed using a 1-step lag
- leading missing value is dropped
- returns are returned as a single-column frame named `return` or inherited name when available

**Failure modes**:

- unknown method
- primary is not a single-column frame

## 2.6 Volatility

### `vol`

```text
v = vol rets window=21
v = vol rets 21
```

**Purpose**: Rolling sample standard deviation over a return series.

**Primary argument**: single-column return frame.

**Window**:

- `window=21` or positional `21`
- default `21`

**Semantics**:

- rolling sample std (ddof depends on pandas default behavior)
- returns a single-column frame named `vol_<window>`

## 2.7 Risk measures

### `var`

```text
q = var rets level=0.95 method=historical
q = var rets 0.99 method=parametric
```

**Purpose**: Value-at-Risk at confidence `level`.

**Conventions**:

- `level=0.95` means left-tail mass is \(1 - 0.95 = 0.05\)
- VaR is returned as the corresponding left-tail quantile of the return distribution
- for typical return series, VaR is often negative (loss tail)

**Methods**:

- `historical` / `hist` / `empirical`: empirical quantile at \(q = 1-\text{level}\)
- `parametric` / `normal` / `gaussian`: Gaussian VaR using sample mean/std with SciPy `norm.ppf`

**Return type**:

- a Series whose index corresponds to input columns
- the Series name includes the level (e.g., `var_0.95`)

### `es`

```text
m = es rets level=0.95
m = es rets level=0.99 method=parametric
```

**Purpose**: Expected Shortfall (Conditional VaR) at confidence `level`.

**Methods**:

- historical: mean of returns \(r_t\) such that \(r_t \le \mathrm{VaR}\)
- parametric: Gaussian conditional mean of the left tail

**Return type**:

- a Series named like `es_0.95`

## 2.8 Dependence structure

### `corr`

```text
c = corr wide_rets
```

**Purpose**: Pearson correlation matrix.

**Primary argument**: wide frame with ≥2 columns.

### `cov`

```text
v = cov wide_rets
```

**Purpose**: sample covariance matrix.

**Primary argument**: wide frame with ≥2 columns.

## 2.9 Single-factor sensitivity

### `beta`

```text
b = beta ra mkt=rb
```

**Purpose**: CAPM-style beta computed as \(\mathrm{Cov}(r_a, r_m) / \mathrm{Var}(r_m)\) using overlapping data.

**Operands**:

- primary: asset return series (single-column frame)
- keyword `mkt`: market/benchmark return series (single-column frame)

**Return type**:

- Series `{beta: ...}`

## 2.10 Performance metrics

### `sharpe`

```text
s = sharpe rets periods=252
s = sharpe rets 252
```

**Purpose**: annualized Sharpe ratio \((\mu/\sigma)\sqrt{\text{periods}}\).

**Notes**:

- this is a basic implementation; it assumes returns are already excess returns if needed

## 2.11 Diagnostics (added for “production-grade” workflows)

### `summary`

```text
stats = summary rets
```

**Purpose**: distribution diagnostics for a single return series.

Returns a Series with:

- `n`, `mean`, `std`, `skew`, `kurt`
- `min`, `p05`, `p50`, `p95`, `max`

### `jb`

```text
j = jb rets
```

**Purpose**: Jarque–Bera normality test.

Returns a Series with:

- `jb`, `pvalue`

### `drawdown`

```text
dd = drawdown rets
```

**Purpose**: compute drawdown series from a return stream.

Returns a frame with a single column `drawdown`.

### `maxdd`

```text
m = maxdd rets
```

Returns a Series `{max_drawdown: ...}`.

### `lincomb`

```text
port = lincomb wide_rets weights=0.6,0.4
```

Purpose: build a single portfolio return series as a weighted linear combination of columns in a wide frame.

Notes:

- `weights=` must have the same length as number of columns in the wide frame
- the result column name is `portfolio`

### `var_backtest`

```text
v = var port level=0.95
bt = var_backtest port var=v level=0.95
```

Purpose: basic exceedance diagnostics for a VaR threshold.

Returns:

- `n` (observations)
- `exceed` (number of exceedances \(r_t \le \mathrm{VaR}\))
- `rate` (exceedances / n)
- `expected` (expected exceedance rate \(1-\text{level}\))

## 2.12 `print`

```text
print x
```

Purpose: print bound value.

Notes:

- special-case formatting may exist for scalar-like Series results (e.g., `var: -0.0123`)

