# Neptune — fixed income risk DSL (v0 implementation)

## Purpose and scope

- **Goal**: Declaratively compute vanilla **fixed-income** risk metrics.
- **Scope (v0)**: Plain coupon-bearing bonds (sovereign / corporate), one currency per run.
- **Primary outputs**: curve PV (`price`), flat YTM (`yield`), Macaulay / modified duration, convexity, DV01 bump, parallel **z-spread** on top of curve zeros (continuous compounding).
- **Valuation**: pass `as_of=YYYY-MM-DD` (default: today). `as_of` must be strictly before all cashflow dates.

## Architecture

| Module | Responsibility |
|--------|----------------|
| `core.py` | Interpreter: environment, `run_line` / `run_file`, dispatch. |
| `parser.py` | Re-exports `atlas.parser` (same surface syntax). |
| `commands.py` | Register Neptune verbs (`load_bond`, `yield`, …). |
| `data/bond.py` | `Bond` + CSV row loader. |
| `data/cashflows.py` | Coupon schedule from issue (step in months). |
| `data/yield_curve.py` | Tenor labels (`1Y`, `6M`, …), linear interpolation in years. |
| `data/analytics.py` | PV, YTM (Brent), durations, convexity, DV01, z-spread. |

## Data model (interfaces)

### `Bond`

- `isin: str`, `ticker: str`, `name: str`
- `coupon: float` (annual), `issue_date`, `maturity`, `frequency` (coupons/year)
- `face_value: float`, optional `price`, optional `yield_`, `currency: str`

### `YieldCurve`

- `points: list[tuple[float, float]]` — `(tenor_years, rate)` or `(label, rate)` resolved to years in loader
- `interpolate(t: float) -> float` — continuous rate for tenor `t`

## Implemented commands

```text
bond  = load_bond  "jgb_10y.csv"
curve = load_curve "jgb_curve.csv"
px    = price bond curve=curve as_of=2024-01-21
yld   = yield bond as_of=2024-01-21
dur   = duration bond as_of=2024-01-21
conv  = convexity bond as_of=2024-01-21
dv    = dv01 bond as_of=2024-01-21
spr   = spread bond benchmark=curve as_of=2024-01-21
print yld
```

## Non-goals (v0)

- Callable / structured bonds, inflation-linked, OAS tree models.
