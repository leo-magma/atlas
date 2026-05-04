# Atlas DSL

Atlas is a small domain-specific language (DSL) for financial risk scripting: CSV ingestion, return transforms, rolling volatility, historical and parametric VaR / ES, `corr` / `cov` / `beta` / `sharpe`, and `bind` for multi-asset columns. Runtime stack: NumPy, pandas, SciPy.

## Sibling DSLs (same repo layout)

**Atlas** (equity-style `.risk`), **Neptune** (bonds `.nep`), **Hydra** (options `.hyd`), **Chronos** (time-series `.chr`), and **Athena** (ML `.ath`) are **top-level Python packages** next to each other. After `pip install -e .`, run scripts with the matching CLI, for example:

```bash
atlas run examples/example1.risk
neptune run neptune/examples/example.nep
hydra run hydra/examples/example.hyd
chronos run chronos/examples/example.chr
athena run athena/examples/stock_prediction.ath
```

Or the module form: `python -m atlas run …`, `python -m neptune run …`, and so on.

## Quick start

```bash
pip install -e ".[dev]"
atlas run examples/example1.risk
```

If `atlas` is not on your `PATH` (often the case on Windows), run:

```bash
python -m atlas run examples/example1.risk
```

Relative paths in `load` are resolved from **the directory containing the script file**.

## Example

```text
prices = load "prices.csv"
close = select prices column=close
rets = returns close method=log
var95 = var rets level=0.95
print var95
```

## Documentation

The canonical README (also used as the package long description on PyPI) lives in [docs/README.md](docs/README.md). Additional specs:

- [Syntax](docs/syntax.md)
- [Commands](docs/commands.md)
- [Design](docs/design.md)
- [Roadmap](docs/roadmap.md)
- [Athena DSL](docs/athena-dsl.md) — ML pipeline grammar (`.ath`)

## License

MIT - see `pyproject.toml`.
