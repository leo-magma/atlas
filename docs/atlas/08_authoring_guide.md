# 08 — Authoring guide (style, naming, and “AI-friendly Atlas”)

This chapter is a style and authoring guide for writing Atlas scripts that are:

- readable by humans
- robust under change
- easy for AI systems to generate reliably

The key idea is that **stable syntax + rich vocabulary** is the winning combination for AI-era DSLs.

## 8.1 Naming conventions

Use short but meaningful variable names:

- frames: `prices`, `wide`, `R`
- single series: `close`, `ra`, `rb`, `rets`
- metrics: `v`, `es`, `jb`, `sum`, `mx`

Prefer consistent suffixes:

- returns: `rets`, `ra`, `rb`
- rolling vol: `vol21`, `vol63`
- VaR/ES: `var95`, `es99`, or `v_hist`, `v_norm`

## 8.2 Script structure pattern

A reliable structure:

1) load/select
2) transformation
3) risk measure
4) diagnostics
5) prints

Example:

```text
prices = load "prices.csv"
close = select prices column=close
rets = returns close log
sum = summary rets
v = var rets level=0.99
print sum
print v
```

This structure is easy for AI to reproduce and for humans to review.

## 8.3 Avoid hidden conventions

Write what you mean:

- `returns close log` is better than relying on defaults if the convention matters.
- `var rets level=0.99 method=historical` is better than omitting `method=` if you might later switch.

## 8.4 Multi-asset: always bind

Never run `corr` or `cov` on a set of independent frames. Always bind them first so alignment is explicit:

```text
R = bind ra rb
cr = corr R
```

## 8.5 Diagnostics-first as a policy

Before producing a “final” VaR/ES:

- print `summary`
- run `jb` (as a warning light)
- compute `drawdown` / `maxdd` to expose path risk
- compare historical vs parametric risk if possible

This turns Atlas scripts into **auditable artifacts** rather than “magic numbers”.

## 8.6 Making Atlas AI-friendly

AI systems generate better DSL scripts when:

- verbs are stable and well documented
- workflows are compositional and repetitive
- there are many examples

Atlas deliberately uses:

- flat, explicit pipelines
- named intermediates

To further improve AI generation quality:

- include a short comment header with the objective
- use consistent variable names
- keep one concept per line

Example header:

```text
# Objective: compute historical VaR(0.99) and show diagnostics
```

## 8.7 Testable scripts

Scripts should be runnable in CI. Prefer:

- relative paths to example data in the same folder
- deterministic computations (no randomness unless seed is explicit)

If a script depends on optional libraries, document it. For Atlas, core dependencies are stable.

## 8.8 When to extend the language vs the examples

Not every new idea needs a new verb.

Add a new verb when:

- it prevents repeated error-prone boilerplate
- it clarifies semantics (e.g., `drawdown` vs ad-hoc wealth calculations)
- it enables diagnostics that users would otherwise skip

Add new examples when:

- the language can already express the concept, but users need a pattern
- you want to teach a workflow (e.g., multi-asset alignment)

The “10k-word” approach is to use both:

- a stable, minimal syntax
- a rich, well-documented vocabulary + examples

