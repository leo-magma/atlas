# Hydra — derivatives risk DSL (design)

## Purpose and scope

- **Goal**: Declaratively compute vanilla **equity/index option** risk and pricing metrics.
- **Scope (v0)**: European vanilla options; Black–Scholes baseline.
- **Primary outputs**: Delta, Gamma, Vega, Theta, Rho; implied vol; optional surface interpolation; Monte Carlo deferred.

## Architecture

| Module | Responsibility |
|--------|----------------|
| `core.py` | Interpreter and environment. |
| `parser.py` | Atlas-compatible line grammar. |
| `commands.py` | Verbs: `load_option`, `load_vol_surface`, `greeks`, `implied_vol`, `price`, … |
| `data/option.py` | Option record (S, K, T, r, q, σ, type). |
| `data/vol_surface.py` | Surface grid + `interp(maturity, strike)`. |
| `data/analytics.py` | BS price, Greeks, IV solvers. |

## Data model (interfaces)

### `Option`

- `underlying: str`, `kind: str` (`call` / `put`; loaders may map CSV ``type``)
- `spot`, `strike`, `maturity`, `rate`, `div_yield`
- optional `vol`, optional `market_price`

### `VolSurface`

- `points` or grid: `(maturity, strike, iv)`
- `interp(maturity, strike) -> float`

## Planned commands

```text
opt = load_option "spx_options.csv"
vol = load_vol_surface "spx_vol.csv"
g = greeks opt model=bs vol_surface=vol
iv = implied_vol opt price=10.5 model=bs
px = price opt model=bs vol_surface=vol
print g
```

## Non-goals (v0)

- American / exotic payoffs, local vol calibration.
