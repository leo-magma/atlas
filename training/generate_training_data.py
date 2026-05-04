"""Generate small instruction-style JSONL datasets for DSL fine-tuning.

PowerShell note: we keep this as a file so users don't need bash heredocs.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

N_PER_DSL = 100


def _jline(messages: list[dict[str, str]]) -> str:
    return json.dumps({"messages": messages}, ensure_ascii=False)


def _write_jsonl(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sysmsg(name: str, extra: str = "") -> dict[str, str]:
    base = (
        f"You are a {name} DSL assistant. "
        "Return only runnable DSL code. "
        "No explanations. No markdown fences."
    )
    if extra:
        base += " " + extra
    return {"role": "system", "content": base}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "training"
    random.seed(0)

    # ---------- Atlas (.atl) ----------
    atlas_lines: list[str] = []
    atlas_levels = [0.9, 0.95, 0.99]
    atlas_methods = ["historical", "parametric"]
    atlas_windows = [10, 21, 42]
    atlas_return_methods = [("log", "log"), ("simple", "simple")]
    atlas_templates = [
        (
            "Generate an Atlas .atl script to compute {ret_kind} returns from close "
            "and print VaR({level})."
        ),
        (
            "Write an Atlas .atl script that loads prices.csv, computes {ret_kind} returns, "
            "and prints ES at level={level}."
        ),
        (
            "Create an Atlas .atl script that computes rolling volatility (window={window}) "
            "and prints it."
        ),
        (
            "Generate an Atlas .atl script that computes parametric VaR and ES at level={level} "
            "and prints both."
        ),
        (
            "Create an Atlas .atl script that computes corr and cov between two assets "
            "using prices_wide.csv and prints both."
        ),
    ]

    for _i in range(N_PER_DSL):
        level = random.choice(atlas_levels)
        method = random.choice(atlas_methods)
        window = random.choice(atlas_windows)
        ret_tok, ret_kind = random.choice(atlas_return_methods)

        template = random.choice(atlas_templates)
        user = template.format(level=level, method=method, window=window, ret_kind=ret_kind)

        if "prices_wide.csv" in template or "corr and cov" in template:
            code_lines = [
                'prices = load "prices_wide.csv"',
                "a = select prices column=close_a",
                "b = select prices column=close_b",
                f"ra = returns a {ret_tok}",
                f"rb = returns b {ret_tok}",
                "rets = bind ra rb",
                "cm = cov rets",
                "cr = corr rets",
                "print cm",
                "print cr",
            ]
        elif "rolling volatility" in template:
            code_lines = [
                'prices = load "prices.csv"',
                "c = select prices column=close",
                f"r = returns c {ret_tok}",
                f"v = vol r window={window}",
                "print v",
            ]
        elif "parametric VaR and ES" in template:
            code_lines = [
                'prices = load "prices.csv"',
                "c = select prices column=close",
                f"r = returns c {ret_tok}",
                f"v = var r level={level} method=parametric",
                f"e = es r level={level} method=parametric",
                "print v",
                "print e",
            ]
        elif "prints ES" in template or "prints ES at level" in template:
            code_lines = [
                'prices = load "prices.csv"',
                "c = select prices column=close",
                f"r = returns c {ret_tok}",
                f"e = es r level={level} method={method}",
                "print e",
            ]
        else:
            code_lines = [
                'prices = load "prices.csv"',
                "c = select prices column=close",
                f"r = returns c {ret_tok}",
                f"v = var r level={level} method={method}",
                "print v",
            ]

        code = "\n".join(code_lines)
        atlas_lines.append(
            _jline(
                [
                    _sysmsg(
                        "Atlas",
                        "Assume line-oriented syntax: name = verb primary "
                        "[args...] [key=value ...].",
                    ),
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": code},
                ]
            )
        )

    # ---------- Neptune (.nep) ----------
    neptune_lines: list[str] = []
    neptune_as_of = ["2024-01-15", "2024-01-21", "2024-02-01"]
    neptune_templates = [
        "Generate Neptune code to price a bond off a curve as_of={as_of} and print price.",
        "Write Neptune code to compute yield and duration as_of={as_of}, then print both.",
        "Create Neptune code to compute dv01 and convexity as_of={as_of}, then print both.",
        (
            "Generate Neptune code to compute z-spread vs the benchmark curve as_of={as_of} "
            "and print it."
        ),
        "Write Neptune code that prints the loaded bond object (for inspection).",
    ]

    for _i in range(N_PER_DSL):
        as_of = random.choice(neptune_as_of)
        template = random.choice(neptune_templates)
        user = template.format(as_of=as_of)

        if "price a bond" in template:
            code_lines = [
                'curve = load_curve "jgb_curve.csv"',
                'bond = load_bond "jgb_10y.csv"',
                f"px = price bond curve=curve as_of={as_of}",
                "print px",
            ]
        elif "yield and duration" in template:
            code_lines = [
                'bond = load_bond "jgb_10y.csv"',
                f"y = yield bond as_of={as_of}",
                f"dur = duration bond as_of={as_of}",
                "print y",
                "print dur",
            ]
        elif "dv01 and convexity" in template:
            code_lines = [
                'bond = load_bond "jgb_10y.csv"',
                f"dv = dv01 bond as_of={as_of}",
                f"conv = convexity bond as_of={as_of}",
                "print dv",
                "print conv",
            ]
        elif "z-spread" in template:
            code_lines = [
                'curve = load_curve "jgb_curve.csv"',
                'bond = load_bond "jgb_10y.csv"',
                f"spr = spread bond benchmark=curve as_of={as_of}",
                "print spr",
            ]
        else:
            code_lines = [
                'bond = load_bond "jgb_10y.csv"',
                "print bond",
            ]
        code = "\n".join(code_lines)

        neptune_lines.append(
            _jline(
                [
                    _sysmsg(
                        "Neptune",
                        "Be strict about as_of being before cashflow dates.",
                    ),
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": code},
                ]
            )
        )

    # ---------- Hydra (.hyd) ----------
    hydra_lines: list[str] = []
    hydra_as_of = ["2024-01-02", "2024-01-03"]
    hydra_prices = [8.0, 10.5, 12.0]
    hydra_templates = [
        "Generate Hydra code to load options and a vol surface as_of={as_of}, then print Greeks.",
        (
            "Write Hydra code to price options with Black–Scholes using a vol surface "
            "as_of={as_of}, "
            "then print prices."
        ),
        "Create Hydra code to compute implied vol for market price={px} and print it.",
        "Generate Hydra code to print both Greeks and prices as_of={as_of}.",
    ]

    for _i in range(N_PER_DSL):
        as_of = random.choice(hydra_as_of)
        px = random.choice(hydra_prices)
        template = random.choice(hydra_templates)
        user = template.format(as_of=as_of, px=px)

        if "print Greeks" in template and "both" not in template:
            code_lines = [
                'opt = load_option "spx_options.csv"',
                f'vol = load_vol_surface "spx_vol.csv" as_of={as_of}',
                f"g = greeks opt model=bs vol_surface=vol as_of={as_of}",
                "print g",
            ]
        elif "price options" in template:
            code_lines = [
                'opt = load_option "spx_options.csv"',
                f'vol = load_vol_surface "spx_vol.csv" as_of={as_of}',
                f"p = price opt model=bs vol_surface=vol as_of={as_of}",
                "print p",
            ]
        elif "implied vol" in template:
            code_lines = [
                'opt = load_option "spx_options.csv"',
                f"iv = implied_vol opt price={px} model=bs as_of={as_of}",
                "print iv",
            ]
        else:
            code_lines = [
                'opt = load_option "spx_options.csv"',
                f'vol = load_vol_surface "spx_vol.csv" as_of={as_of}',
                f"g = greeks opt model=bs vol_surface=vol as_of={as_of}",
                f"p = price opt model=bs vol_surface=vol as_of={as_of}",
                "print g",
                "print p",
            ]
        code = "\n".join(code_lines)

        hydra_lines.append(
            _jline(
                [
                    _sysmsg(
                        "Hydra",
                        "Assume European vanilla options; as_of must be before maturity.",
                    ),
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": code},
                ]
            )
        )

    # ---------- Chronos (.chr) ----------
    chronos_lines: list[str] = []
    chronos_dropna = ["true", "false"]
    chronos_periods = [1, 5]
    chronos_windows = [5, 20]
    chronos_freq = ["1d", "1w"]
    chronos_norm = ["zscore", "minmax"]
    chronos_templates = [
        "Generate Chronos code to load prices.csv, clean dropna={dropna}, and print the result.",
        "Write Chronos code to diff column=close and normalize with method={norm}, then print.",
        "Create Chronos code to resample to freq={freq} (method=last) and print it.",
        "Generate Chronos code to shift by periods={p} and print the shifted frame.",
        "Write Chronos code to compute rolling_mean window={w} on column=close and print it.",
        "Generate Chronos code to describe the cleaned time series and print the summary.",
    ]

    for _i in range(N_PER_DSL):
        dropna = random.choice(chronos_dropna)
        p = random.choice(chronos_periods)
        w = random.choice(chronos_windows)
        freq = random.choice(chronos_freq)
        norm = random.choice(chronos_norm)
        template = random.choice(chronos_templates)
        user = template.format(dropna=dropna, p=p, w=w, freq=freq, norm=norm)

        if "diff column=close" in template:
            code_lines = [
                'ts = load "prices.csv"',
                f"clean = clean ts dropna={dropna}",
                "d = diff clean column=close",
                f"z = normalize d method={norm} column=close",
                "print z",
            ]
        elif "resample" in template:
            code_lines = [
                'ts = load "prices.csv"',
                f"clean = clean ts dropna={dropna}",
                f"r = resample clean freq={freq} method=last",
                "print r",
            ]
        elif "shift" in template:
            code_lines = [
                'ts = load "prices.csv"',
                f"clean = clean ts dropna={dropna}",
                f"s = shift clean periods={p}",
                "print s",
            ]
        elif "rolling_mean" in template:
            code_lines = [
                'ts = load "prices.csv"',
                f"clean = clean ts dropna={dropna}",
                f"rm = rolling_mean clean window={w} column=close",
                "print rm",
            ]
        elif "describe" in template:
            code_lines = [
                'ts = load "prices.csv"',
                f"clean = clean ts dropna={dropna}",
                "d = describe clean",
                "print d",
            ]
        else:
            code_lines = [
                'ts = load "prices.csv"',
                f"clean = clean ts dropna={dropna}",
                "print clean",
            ]
        code = "\n".join(code_lines)

        chronos_lines.append(
            _jline(
                [
                    _sysmsg(
                        "Chronos",
                        "Focus on ETL/transforms for downstream risk/ML.",
                    ),
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": code},
                ]
            )
        )

    # ---------- Athena (.ath) ----------
    athena_lines: list[str] = []
    athena_feature_sets = [
        "diff,rolling_mean",
        "rolling_mean,zscore",
        "diff,rolling_std",
        "rolling_std,zscore",
    ]
    athena_algos = ["linear", "ridge", "lasso", "rf", "isolation_forest", "garch"]
    athena_metrics = ["rmse", "mae", "r2", "mape"]
    athena_templates = [
        (
            "Generate Athena code to build features ({methods}), "
            "train algo={algo} on target=close, "
            "and print predictions."
        ),
        (
            "Write Athena code to train algo={algo} and evaluate metrics={metrics} on close, "
            "then print the score."
        ),
        (
            "Create Athena code to save a trained model to models/{tag}.pkl, load it, "
            "and export predictions to {tag}.csv."
        ),
    ]

    for _i in range(N_PER_DSL):
        methods = random.choice(athena_feature_sets)
        algo = random.choice(athena_algos)
        metrics = ",".join(random.sample(athena_metrics, k=2))
        tag = random.choice(["aapl", "msft", "demo"])
        template = random.choice(athena_templates)
        user = template.format(methods=methods, algo=algo, metrics=metrics, tag=tag)

        if "evaluate metrics" in template:
            code_lines = [
                'ts = load "../../examples/prices.csv"',
                f"feat = features ts methods={methods}",
                f"model = train feat target=close algo={algo}",
                f"score = evaluate model feat target=close metrics={metrics}",
                "print score",
            ]
        elif "save a trained model" in template:
            code_lines = [
                'ts = load "../../examples/prices.csv"',
                f"feat = features ts methods={methods}",
                f"model = train feat target=close algo={algo}",
                f'save model to="models/{tag}.pkl"',
                f'load model from="models/{tag}.pkl"',
                "pred = predict model feat",
                f'export pred to="{tag}.csv"',
            ]
        else:
            code_lines = [
                'ts = load "../../examples/prices.csv"',
                f"feat = features ts methods={methods}",
                f"model = train feat target=close algo={algo}",
                "pred = predict model feat",
                "print pred",
            ]
        code = "\n".join(code_lines)

        athena_lines.append(
            _jline(
                [
                    _sysmsg(
                        "Athena",
                        (
                            "Treat this as a cross-asset ML orchestration DSL; "
                            "keep code minimal and "
                            "runnable."
                        ),
                    ),
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": code},
                ]
            )
        )

    _write_jsonl(out / "atlas" / "train.jsonl", atlas_lines)
    _write_jsonl(out / "neptune" / "train.jsonl", neptune_lines)
    _write_jsonl(out / "hydra" / "train.jsonl", hydra_lines)
    _write_jsonl(out / "chronos" / "train.jsonl", chronos_lines)
    _write_jsonl(out / "athena" / "train.jsonl", athena_lines)

    (out / "README.md").write_text(
        """# Training data (JSONL)

This folder contains small instruction-style datasets for fine-tuning small LLMs (SLMs)
to act as DSL copilots.

## Structure

- `training/atlas/train.jsonl` — Atlas `.atl`
- `training/neptune/train.jsonl` — Neptune `.nep`
- `training/hydra/train.jsonl` — Hydra `.hyd`
- `training/chronos/train.jsonl` — Chronos `.chr`
- `training/athena/train.jsonl` — Athena `.ath`

Each line is a single JSON object:

```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."},
{"role": "assistant", "content": "..."}]}
```

Notes:
- The assistant responses are **code-only** (no prose) for code-generation fine-tuning.
- Paths in examples are written relative to the sample scripts (matching the repo examples).

## Colab

See `training/colab/train_5_adapters_from_drive.py` for a ready-to-run Colab script that:
- mounts Google Drive
- reads the 5 JSONL datasets from Drive
- trains 5 LoRA adapters (1 base SLM + 5 adapters)
- saves adapters back to Drive
""",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

