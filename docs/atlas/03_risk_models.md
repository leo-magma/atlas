# 03 — Risk models & interpretation

This chapter focuses on **risk-model semantics**, not just formulas. Many “risk bugs” are not numerical issues; they are convention and data issues. Atlas aims to make those issues explicit and diagnosable.

## 3.1 Returns as the core modeling object

Most risk measures in Atlas are defined on a **return series** (not directly on prices). The recommended workflow is:

```text
prices = load "prices.csv"
close = select prices column=close
rets = returns close log
```

### Simple vs log returns

- **Simple returns**: \(r_t = P_t/P_{t-1} - 1\)
  - intuitive for small moves
  - composes multiplicatively over time: wealth \(W_t = \prod (1+r_t)\)
- **Log returns**: \(r_t = \ln(P_t/P_{t-1})\)
  - additive over time: \(\sum r_t = \ln(P_T/P_0)\)
  - often closer to normal in practice, but still heavy-tailed

Atlas supports both, but scripts should be consistent. A common anti-pattern is mixing log returns and simple returns within the same notebook without remembering which was used.

### Frequency and annualization

Atlas’s `sharpe` verb annualizes using `periods`. This should match data frequency:

- daily → 252 (commonly)
- weekly → 52
- monthly → 12

If you are working on intraday data, you must define your own “periods per year” convention.

## 3.2 VaR in Atlas

### Convention: left-tail quantile

Atlas defines VaR as the **left-tail quantile** of returns at tail mass \(q = 1-\text{level}\).

For `level=0.95`:

- \(q = 0.05\)
- VaR is the 5% quantile of returns

For typical equity returns, this quantile is negative. This is not a bug: it is consistent with “loss tail” being negative returns.

If your reporting system expects VaR as a **positive loss number**, you can post-process:

- loss-VaR \(= -\mathrm{VaR}\)

Atlas intentionally does not enforce a sign convention beyond defining the quantile.

### Historical VaR

Historical VaR is the empirical quantile of the return sample.

Properties:

- non-parametric
- sensitive to sample size and regime changes
- interpretable: “in the worst 5% of days, returns were at most X”

Failure modes:

- small sample size yields noisy quantiles
- missing data or non-overlapping series leads to biased tails

Atlas mitigations:

- encourage inspection with `summary`
- use `bind` + inner joins to enforce overlap before multivariate analysis

### Parametric Gaussian VaR

Parametric VaR uses a normal approximation:

\[
\mathrm{VaR} = \mu + \sigma \Phi^{-1}(q)
\]

where \(q = 1-\text{level}\).

Properties:

- fast, smooth
- often optimistic under heavy tails and skewness

Recommended diagnostic:

- run `jb` (Jarque–Bera) to test normality (as a *warning light*, not a proof)
- compare historical vs parametric VaR and investigate large differences

## 3.3 ES (Expected Shortfall) in Atlas

Expected Shortfall is a tail mean, not a quantile.

### Historical ES

Historical ES is the mean of returns in the left tail:

\[
\mathrm{ES} = \mathbb{E}[r \mid r \le \mathrm{VaR}]
\]

Properties:

- coherent risk measure under common assumptions
- more sensitive to extreme tail points than VaR

Failure modes:

- very sensitive to outliers if the dataset is small
- can become unstable when the tail has very few points

Recommended workflow:

- inspect `summary` to understand tail quantiles and dispersion
- consider stability checks via rolling windows (future expansion)

### Parametric Gaussian ES

Under the normal approximation:

Atlas computes the conditional left-tail mean using the standard normal pdf/cdf relationship. This provides a smooth analytic ES but inherits the normality assumption.

## 3.4 Dependence structure: covariance and correlation

Multi-asset risk is dominated by dependence. Atlas provides:

- `corr`: correlation matrix
- `cov`: covariance matrix

### Data alignment is the hidden risk model

The most common failure mode in correlation estimation is time alignment:

- one asset has missing dates
- another has holidays or stale data
- index is not properly parsed as dates

Atlas’s `bind` encourages the correct approach:

1) compute per-asset returns
2) `bind` them using inner join on index (overlap only)
3) estimate corr/cov on the resulting wide matrix

This sacrifices sample size for correctness.

## 3.5 Beta as sensitivity

Atlas’s `beta` is:

\[
\beta = \frac{\mathrm{Cov}(r_a, r_m)}{\mathrm{Var}(r_m)}
\]

Beta is a single-factor exposure measure. It is not a full risk model, but it is a useful diagnostic:

- a portfolio with beta far from expected might be mis-specified
- a strategy’s beta drift over time indicates regime change

Future expansions (without syntax changes) can provide rolling beta and confidence intervals.

## 3.6 Drawdown as a risk narrative

VaR and ES measure tail behavior in returns, but stakeholders often interpret risk through **drawdowns**:

- “How bad can it get peak-to-trough?”

Atlas includes:

- `drawdown`: the full drawdown series
- `maxdd`: the maximum drawdown

This provides a bridge between statistical risk measures and intuitive path-dependent risk.

## 3.7 Backtesting VaR exceedances

Atlas includes a minimal `var_backtest` primitive:

- count exceedances \(r_t \le \mathrm{VaR}\)
- compare the exceedance rate to expected \(1-\text{level}\)

This is not yet a full statistical backtest suite (Kupiec, Christoffersen, etc.), but it is:

- enough to catch gross miscalibration
- small enough to remain stable and easy to interpret

Future expansions can add:

- likelihood ratio tests
- independence tests
- rolling recalibration windows

## 3.8 Stress and scenario: semantics before syntax

Stress testing is often requested as a DSL feature, but it can mean many things:

- deterministic shocks (parallel shift, shock returns by X)
- scenario replay (use historical crisis windows)
- factor shocks (apply factor moves through exposures)

Atlas intentionally starts with the primitives that make stress/scenario implementable:

- clear return definitions
- linear combinations (`lincomb`)
- dependence primitives (`cov`, `corr`)
- diagnostics (`summary`, `drawdown`)

As the language grows, stress/scenario can be added as additional verbs without changing the core syntax.

