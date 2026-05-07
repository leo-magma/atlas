# Command reference

## load

```text
df = load "path/to/file.csv"
```

- Reads the file with `pandas.read_csv`.
- Relative paths are resolved from **the directory of the script being executed**.

## select

```text
col_df = select prices column=close
# or (column name as a single positional argument)
col_df = select prices close
```

- Takes one column from an existing DataFrame and returns a **single-column DataFrame**.
- `returns` and `vol` expect a single price or return column; use `select` first when the table has multiple columns.

## bind

```text
wide = bind ra rb
wide = bind r1 r2 r3
```

- Horizontally concatenates **single-column** frames with an **inner join on the index**.
- Column names in the result are the variable names (`ra`, `rb`, …). Use before `corr` / `cov` on multiple return series.

## returns

```text
rets = returns close method=log
rets = returns close log
```

- **method** (or the first positional argument after the primary):
  - `log` / `ln`: log returns \(\ln(P_t / P_{t-1})\)
  - `simple` (default) / `pct` / `arithmetic`: simple returns
- Leading missing rows are dropped with `dropna`.

## vol

```text
v = vol rets window=21
v = vol rets 21
```

- Rolling sample standard deviation of a single-column return series (default window 21).

## var

```text
q = var rets level=0.95
q = var rets 0.95 method=parametric
```

- **method** (optional, default `historical`):
  - `historical` / `hist` / `empirical`: empirical quantile at \(q = 1 - \text{level}\) (same convention as `pandas.Series.quantile`).
  - `parametric` / `normal` / `gaussian`: Gaussian VaR using sample mean and (ddof=1) standard deviation; left-tail mass is \(1 - \text{level}\). Implemented with **SciPy** `scipy.stats.norm`.

## es

```text
m = es rets level=0.95
m = es rets level=0.95 method=parametric
```

- **Historical** (default): sample mean of returns at or below the historical VaR threshold (per column).
- **Parametric**: Gaussian expected shortfall for the same left-tail mass (conditional mean under a normal fit).

## corr

```text
c = corr rets
```

- Pearson correlation matrix. Requires **at least two columns** (typically a `bind` of single-asset return columns).

## cov

```text
v = cov rets
```

- Sample covariance matrix (same shape requirements as `corr`).

## beta

```text
b = beta ra mkt=rb
```

- OLS-style beta: \(\mathrm{Cov}(r_{\text{asset}}, r_{\text{mkt}}) / \mathrm{Var}(r_{\text{mkt}})\) on overlapping, non-missing rows. Both operands must be single-column frames.

## sharpe

```text
s = sharpe rets periods=252
s = sharpe rets 252
```

- Annualized Sharpe ratio \((\mu / \sigma) \sqrt{\text{periods}}\) on a single-column return series. Default `periods=252`.

## summary

```text
s = summary rets
```

- Basic distribution diagnostics for a single return series: `n`, `mean`, `std`, `skew`, `kurt`, `min`, `p05`, `p50`, `p95`, `max`.
- Use this before `var` / `es` to sanity-check scale, skewness, and tails.

## jb

```text
j = jb rets
```

- Jarque–Bera normality test on a single series.
- Returns `jb` statistic and `pvalue`.

## drawdown

```text
dd = drawdown rets
```

- Drawdown series computed from cumulative wealth \(\prod_t (1 + r_t)\).
- Returns a single-column frame named `drawdown`.

## maxdd

```text
m = maxdd rets
```

- Minimum of the `drawdown` series (most negative drawdown).

## lincomb

```text
port = lincomb wide weights=0.6,0.4
```

- Linear combination of columns in a **wide** return matrix (e.g., output of `bind`).
- `weights=` is a comma-separated list; its length must match the number of columns.
- Result is a single-column frame named `portfolio`.

## var_backtest

```text
v = var port level=0.95
bt = var_backtest port var=v level=0.95
```

- Simple exceedance diagnostics for a VaR threshold.
- Convention: VaR is the left-tail quantile (typically negative). An exceedance is \(r_t \le \mathrm{VaR}\).
- Returns `n`, `exceed`, `rate`, `expected` (expected is \(1-\text{level}\)).

## print

```text
print var95
```
