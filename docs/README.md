# Atlas DSL

Atlas is a small domain-specific language (DSL) for describing financial risk calculations in short scripts. It runs CSV ingestion, return transforms, volatility, historical and **parametric (Gaussian)** VaR / ES, correlation and covariance matrices, CAPM-style beta, and Sharpe ratios, as a sequence of assignment statements. Runtime dependencies include **NumPy**, **pandas**, and **SciPy**.

## Installation

```bash
pip install -e ".[dev]"
```

## Running

Install the package (editable or normal), then use the **`atlas` console command** (provided by `[project.scripts]` in `pyproject.toml`):

```bash
pip install -e "."
atlas run examples/example1.atl
```

If `atlas` is not found (common on Windows when Python `Scripts` is not on `PATH`), use the module form instead:

```bash
python -m atlas run examples/example1.atl
```

Neptune, Hydra, Chronos, and Athena use the same pattern (`neptune run …`, `hydra run …`, `chronos run …`, `athena run …`, or `python -m neptune run …`, etc.).

Relative paths in `load "prices.csv"` are resolved relative to **the directory that contains the script file**.

## Minimal example

```text
prices = load "prices.csv"
close = select prices column=close
rets = returns close method=log
var95 = var rets level=0.95
print var95
```

## Documentation

- [Syntax](syntax.md)
- [Commands](commands.md)
- [Design](design.md)
- [Roadmap](roadmap.md)
- [Athena DSL](athena-dsl.md) — ML pipeline (`.ath`)
- [Atlas long-form spec (10k-word set)](atlas/INDEX.md)

## License

MIT - see `pyproject.toml`.
