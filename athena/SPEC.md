# Athena — cross-asset ML layer (specification, v0)

## Role

Athena is the **machine-learning orchestration layer** for the Atlas suite. It consumes tabular inputs produced or compatible with **Atlas** (equity), **Neptune** (bonds), **Hydra** (options), and **Chronos** (time series), and runs a unified **line-oriented DSL** (`.ath`) for:

1. Loading data  
2. Feature engineering  
3. Training  
4. Prediction  
5. Evaluation, export, and model persistence  

## Syntax (v0)

- **Assignments** (same tokenizer as Atlas):  
  `name = load "path.csv"`  
  `name = load_curve "path.csv"` · `load_bond` · `load_option` (all resolve to CSV load in v0).  
  `feat = features ts methods=diff,rolling_mean,zscore`  
  `model = train feat target=close algo=rf`  
  `pred = predict model feat`  
  `score = evaluate model feat target=close metrics=rmse,r2`  
  `m = load_model "models/m.pkl"` (assignment form).

- **Directives** (no `name =`):  
  `export pred to="out.csv"`  
  `save model to="models/m.pkl"`  
  `load model from="models/m.pkl"` (binds into `model`).

- **Print**: `print pred`

## Algorithms and metrics

See implementation in `athena/commands.py`, `athena/models/`, and `athena/features/`. Optional third-party trainers (`lightgbm`, `xgboost`) raise a clear runtime error if not installed.

## Roadmap

Tighter integration with Neptune/Hydra native objects, richer GARCH, walk-forward CV, and plugin hooks for custom `features` / `train` backends.
