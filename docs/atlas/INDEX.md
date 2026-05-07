# Atlas (10k-word) Documentation Set

This folder contains a **long-form** Atlas documentation set intended to be directly convertible into:

- a **language specification**
- a **technical book**
- an internal **whitepaper**
- a small **academic-style paper** describing a DSL + runtime

**Scope guarantee**: the Atlas *surface syntax* remains **unchanged** (line-oriented statements, `name = verb ...`, and `print name`). This documentation focuses on:

- precise semantics
- edge cases and conventions
- diagnostics and interpretation
- recommended workflows
- interoperability patterns (with the rest of the suite)

## Reading order

- Start here: **[00 — Abstract & positioning](00_abstract.md)**
- The language core: **[01 — Language specification](01_language_spec.md)**
- Standard library: **[02 — Standard library reference](02_stdlib_reference.md)**
- Risk methods and conventions: **[03 — Risk models & interpretation](03_risk_models.md)**
- Data model: **[04 — Data model](04_data_model.md)**
- Runtime design (IR-ish): **[05 — Runtime & execution model](05_runtime_execution.md)**
- Errors: **[06 — Error taxonomy](06_errors.md)**
- Cookbook: **[07 — Cookbook (scripts)](07_cookbook.md)**
- Style guide: **[08 — Authoring guide](08_authoring_guide.md)**

## Quick links

- Short docs entry point: `docs/README.md`
- Examples: `examples/*.atl` and `examples/atlas_cookbook.atl`

