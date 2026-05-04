# Design

## Goals

Atlas is optimized for writing short risk experiments. It is not a general-purpose language: it provides an **environment of named DataFrames** and a **dictionary of common market-data transforms**.

## Layers

1. **parser**: Tokenizes each line into an immutable `Command` record (syntax errors → `AtlasSyntaxError`).
2. **core**: Holds the `env` map and dispatches each line.
3. **commands**: Maps DSL function names to implementations (thin layer at the interpreter/CLI boundary).
4. **std**: Real I/O and statistics (`std/io.py`, `std/stats.py`). Extend the language by growing this tree. Parametric VaR / ES use **SciPy** normal quantiles and densities; linear-risk summaries (`corr`, `cov`, `beta`, `sharpe`) are built on **pandas** / **NumPy**.

## Extension points

- New top-level functions: register them in `get_command_table()` in `atlas/commands.py` and implement logic under `atlas/std/`.
- New VaR models: interpret `method` on `var` and add kernels in `std/stats.py`.

## Reliability

- **pytest** locks parser behavior, dispatch, and VaR/ES formulas against regressions.
- In production finance, timezone handling, instrument identity, and return definitions dominate outcomes; the recommended flow is to **normalize to a single price column** (via `select`) before calling `returns`.
