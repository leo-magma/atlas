# 04 — Data model

This chapter defines the conceptual data model that Atlas scripts operate on. While the current runtime uses pandas, the model is defined abstractly so the language can be re-implemented.

## 4.1 The Frame

A **Frame** is a rectangular table:

- an **index** (often a time index)
- one or more **columns**
- each cell holds a value (often numeric)

In the Atlas runtime, a Frame is typically represented by a pandas `DataFrame`.

### 4.1.1 Index semantics

Atlas does not require a DatetimeIndex at the language level, but most financial workflows assume:

- observations ordered in time
- stable frequency (daily/weekly/monthly)

Because `load` is generic CSV, the index semantics depend on the dataset. Good practice is:

- include a `date` column in CSV
- parse it into a DatetimeIndex upstream (or via suite tools)

Chronos can be used to enforce time-series index rules before risk computation.

### 4.1.2 Column semantics

In typical equity-style datasets:

- `close`: closing price
- `volume`: traded volume
- other columns: open/high/low/adj_close, etc.

Atlas intentionally avoids hardcoding column names. Instead:

- `select` is used to explicitly pick the column to treat as “price” or “return”

## 4.2 Single-column frames as typed streams

Atlas frequently treats single-column frames as typed streams:

- **price stream** (input to `returns`)
- **return stream** (input to `vol`, `var`, `es`, `sharpe`, `drawdown`)

This is a design choice: rather than creating explicit type syntax, Atlas uses *shape* as a type proxy. The runtime enforces shape constraints:

- “Expected a single-column DataFrame; use select first”

This provides safety without complicating the grammar.

## 4.3 Series as scalar-ish results

Some computations return a Series even when there is conceptually a single scalar. Examples:

- VaR for a single return column
- Sharpe ratio for a single series
- Beta

Why Series?

- consistent handling of multi-column vs single-column inputs
- retains labels
- easy to print and to extend (more metrics later)

Atlas’s `print` may format a length-1 Series as `label: value` for readability.

## 4.4 Wide return matrices

For multi-asset analysis, Atlas encourages a “wide return matrix” representation:

- each column corresponds to an asset return series
- index corresponds to time

Workflow:

1) compute returns per asset as single-column frames
2) bind them into a wide frame using `bind`

This representation is used for:

- `corr`
- `cov`
- portfolio linear combination (`lincomb`)

## 4.5 Portfolio representation (minimal)

Atlas does not yet include a full portfolio object with holdings, currency, transaction costs, etc.

However, a portfolio return stream can be represented as:

- a single-column frame `portfolio` created by `lincomb` from a wide return matrix

This is deliberately minimal but surprisingly powerful:

- you can compute VaR/ES/Sharpe/drawdown on the portfolio return stream
- you can backtest exceedance rates for its VaR

More complex portfolio models can be layered on later without changing Atlas’s core syntax, by adding additional verbs and keeping data representations explicit.

## 4.6 Scenario representation (future-proofing)

Even though Atlas does not yet have scenario primitives, the data model anticipates a scenario table representation:

- scenario name/id
- shocked returns or factor moves
- mapping from scenario to transformed return streams

This can be implemented by defining verbs that:

- generate scenario return frames
- compute risk measures per scenario

Because Atlas’s grammar is flat, scenarios would likely be expressed as:

- a scenario frame produced by a verb
- followed by a risk computation verb

## 4.7 Data quality assumptions (and how to surface them)

Risk results are only as good as the data assumptions. Atlas scripts should ideally surface:

- what return definition was used
- what sample window was used
- what alignment rules were used for multi-asset data

In this repository, Chronos provides `validate` to make these assumptions checkable before risk computation. Atlas itself focuses on correct transformations given a frame.

