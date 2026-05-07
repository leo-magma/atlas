# 00 — Abstract & positioning

## Abstract

**Atlas** is a small, line-oriented domain-specific language (DSL) for **risk scripting**. It is designed to execute a sequence of operations such as CSV ingestion, single-series transforms (returns, rolling volatility), and risk/statistics primitives (VaR/ES, covariance/correlation matrices, beta, Sharpe), while keeping intermediate artifacts explicit and easy to inspect.

Atlas is intentionally minimal in syntax:

- one statement per line
- assignments with `name = verb ...`
- `print name` for inspection
- comments with `#`

This document set treats Atlas not as a toy script format but as a **language artifact**: it specifies semantics, data conventions, and failure modes in enough detail that the language can be implemented independently, tested, and embedded into larger systems.

## Why a risk DSL?

Risk computations often fail not because models are unknown, but because:

- data alignment is wrong (dates, missingness, non-overlapping windows)
- transformations are inconsistent (simple vs log returns, window definitions)
- conventions are mixed (sign conventions for VaR/ES, annualization, tail probabilities)
- intermediate outputs are not examined, and errors propagate silently

Atlas is built around a single idea: **make the intermediate tables first-class**. Even when the final output is “a single number”, Atlas encourages workflows where the user explicitly defines each step (load → select → returns → var → print).

## Positioning within the Atlas Suite

In this repository, Atlas is one of several sibling DSLs:

- **Atlas**: risk scripting on equity-like time series (`.atl`)
- **Chronos**: time-series ETL/validation (`.chr`)
- **Hydra**: options analytics (`.hyd`)
- **Neptune**: fixed-income analytics (`.nep`)
- **Athena**: ML layer (`.ath`)

Atlas is deliberately “narrow but deep”: it provides a small set of verbs that cover a large fraction of day-to-day “first pass” risk and sanity checks. The other DSLs can be used as upstream/downstream components, but Atlas remains useful even in isolation.

## Core principles

### 1) Explicitness over cleverness

Atlas is not a vectorized expression language. It is a *pipeline language*. The user writes the pipeline explicitly, line by line.

### 2) Reproducible transformations

Every transformation has well-defined semantics. Ambiguities that are common in notebooks (“what did I compute here?”) are reduced by forcing named intermediate outputs.

### 3) Small surface syntax, richer semantics

Atlas avoids introducing complex syntax constructs (blocks, function definitions, operator precedence). Instead, it keeps syntax stable and expands capabilities through:

- additional verbs (standard library)
- well-documented conventions and diagnostics
- careful error taxonomy

### 4) “Inspection-first” ergonomics

Because `print` is always available, Atlas is meant to be executed iteratively. The language design assumes users will print intermediate objects and read them as part of the workflow.

## What “10k-word Atlas” means

“10k-word Atlas” does **not** mean a large grammar. It means:

- a stable, precisely specified language core
- a standard library with a coherent vocabulary
- risk-model semantics and diagnostics that are well-articulated
- a data model and execution model that can scale into product systems
- a cookbook and style guide that teach correct usage

When these are written down, Atlas becomes:

- implementable by third parties
- teachable as a standalone artifact
- easy for AI systems to generate reliably (stable syntax + rich vocabulary)

