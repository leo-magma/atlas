# 07 — Cookbook (Atlas scripts)

This cookbook is written to be executable with the repository examples. For a runnable “all-in-one” script, see:

- `examples/atlas_cookbook.atl`

The goal here is to provide **narrative** and **patterns** that users can apply to new problems.

## 7.1 The canonical pipeline

Most Atlas work follows a canonical pipeline:

1) Load data
2) Select a series
3) Transform (returns, rolling stats)
4) Risk measure (VaR/ES, Sharpe, dependence)
5) Diagnostics (summary, normality test, drawdown, exceedance rate)
6) Print intermediate results

Example:

```text
prices = load "prices.csv"
close = select prices column=close
rets = returns close log
sum = summary rets
v = var rets level=0.99 method=historical
print sum
print v
```

## 7.2 “Don’t trust VaR until you trust your returns”

Before computing VaR:

- print the return series
- run `summary` and check:
  - mean/std magnitude
  - min/p05 tail magnitude
  - skew/kurtosis

Then compare:

- historical VaR vs parametric VaR

If parametric is much less severe than historical and JB p-value is small, you likely have fat tails.

## 7.3 Rolling volatility as regime detector

Rolling volatility often exposes:

- volatility clustering
- regime shifts
- data glitches (sudden spikes due to bad ticks)

Pattern:

```text
rets = returns close log
vol21 = vol rets 21
vol63 = vol rets 63
print vol21
print vol63
```

Even without plotting, printing the tail of `vol21` in an interactive run is often enough to notice anomalies.

## 7.4 Multi-asset risk: always align with `bind`

Anti-pattern:

- computing correlation on price levels rather than returns
- computing correlation on misaligned timestamps

Correct pattern:

```text
prices = load "prices_wide.csv"
ca = select prices column=close_a
cb = select prices column=close_b
ra = returns ca log
rb = returns cb log
R = bind ra rb
cr = corr R
cm = cov R
print cr
print cm
```

## 7.5 Beta as a “sanity check”

Beta is a good sanity check even when you do not believe CAPM:

```text
bet = beta ra mkt=rb
print bet
```

If `bet` is wildly unstable, it can indicate:

- bad data overlap
- noisy series
- structural breaks

## 7.6 Portfolio return stream with `lincomb`

While Atlas does not have full portfolio objects, you can still compute “portfolio risk” by creating a portfolio return stream.

```text
R = bind ra rb
port = lincomb R weights=0.6,0.4
v = var port level=0.95
print v
```

This pattern is intentionally minimal:

- it pushes portfolio modeling complexity to the data layer
- it keeps the DSL stable

## 7.7 Exceedance diagnostics (`var_backtest`)

`var_backtest` answers:

- “How often did returns fall below my VaR threshold?”

Pattern:

```text
v = var rets level=0.95
bt = var_backtest rets var=v level=0.95
print bt
```

Interpretation:

- expected exceedance rate is \(1-\text{level}\)
- observed rate far above expected suggests underestimation

This is intentionally a “first-line” diagnostic. More formal tests can be layered later.

## 7.8 Drawdown narrative

People often understand drawdown better than distributional metrics.

Pattern:

```text
dd = drawdown rets
mx = maxdd rets
print mx
print dd
```

If max drawdown is extreme but VaR is mild, it may indicate:

- serial correlation
- path-dependent risk
- regime shifts

## 7.9 Recommended workflow in practice

1) Write a small script with explicit names.
2) Run it.
3) Print intermediate values.
4) Add diagnostics (`summary`, `jb`, `drawdown`).
5) Only then “trust” the final VaR/ES number.

Atlas is designed to make this workflow natural and repeatable.

