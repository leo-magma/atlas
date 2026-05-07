# 05 — Runtime & execution model (IR-ish view)

This chapter explains how Atlas executes programs in a way that can be reasoned about, tested, and embedded. While Atlas does not expose an explicit intermediate representation (IR) in its surface syntax, it is still useful to describe its internal model as if it had one.

## 5.1 Why describe an “IR” for a tiny DSL?

Even for a small DSL, an IR viewpoint provides:

- precise semantics (“what is executed, when, and with what bindings?”)
- a foundation for instrumentation (progress reporting, logging, auditing)
- a path to optimizations that do not change syntax (caching, memoization)

In product settings, you often need:

- an execution plan you can log
- explainable errors with line/column context
- deterministic replay

Atlas’s current architecture already supports most of these ideas, even if they are not formalized as a separate IR layer.

## 5.2 Conceptual AST nodes

Each non-empty, non-comment line parses to one of:

- `Assign(name, verb, primary, pos_args, kw_args)`
- `Print(name)`

This is intentionally small.

### Assign node fields

- `name`: identifier string
- `verb`: identifier string
- `primary`: token string
- `pos_args`: list of token strings
- `kw_args`: map of string→string

## 5.3 Environment model

Atlas maintains an environment:

\[
E: \text{Name} \rightarrow \text{Value}
\]

Values are typically:

- frames (tables)
- series (labeled vectors)
- small dict-like metrics

Evaluation of `Assign` produces a value and updates the environment:

\[
E[name] \leftarrow \mathrm{eval}(verb, primary, pos, kw, E)
\]

`Print(name)` reads from \(E\) and prints.

## 5.4 Dispatch model

Atlas verbs are implemented as functions with a uniform signature:

- `arg`: primary token (often a variable name)
- `args`: positional tokens
- `kwargs`: keyword tokens (string→string)
- `env`: the environment
- `base_dir`: directory of the running script (for path resolution)

This uniformity is a key “product” feature:

- it simplifies embedding
- it makes it easy to add instrumentation
- it keeps the language stable while expanding vocabulary

## 5.5 Path resolution and reproducibility

`load "prices.csv"` resolves paths relative to the script’s directory, not the process working directory. This is crucial for reproducibility:

- scripts behave the same regardless of where the CLI is invoked
- scripts can be moved as folders, keeping relative data paths intact

This also enables UI systems to run scripts safely by controlling the upload directory.

## 5.6 Error attribution

For a DSL to feel “real”, error attribution matters:

- errors should include file path and line number
- errors should be classified (syntax vs runtime vs data)

Atlas already includes custom error types. A production-grade runner typically wraps errors with:

- file path
- line number
- original error message

This is also the basis for IDE integrations and UI “click-to-line” error displays.

## 5.7 Instrumentation hooks (progress, logging)

Because Atlas executes line-by-line, a runner can instrument execution without modifying the language:

- count effective lines (non-empty, non-comment)
- after each executed line, update progress as \(i/n\)
- capture stdout and errors

This is precisely how large systems provide:

- progress bars
- live logs
- job history and auditing

The fact that the syntax is line-oriented is a feature: it makes progress estimation simple and robust.

## 5.8 Deterministic replay and caching

Atlas’s deterministic nature allows caching at the command level:

- if the same command is executed on the same inputs, cache the output

However, caching must respect:

- input data identity (file contents, not file path)
- library versions
- runtime settings

In a “world-class” implementation, the execution model would record a run manifest:

- program text hash
- input file hashes
- dependency versions
- produced artifacts

This can be implemented at the runner/UI layer without changing Atlas syntax.

## 5.9 “Execution plan” as a first-class artifact (future direction)

Even without changing syntax, Atlas can expose an execution plan as data:

- a list of nodes with:
  - line number
  - verb
  - input variable names
  - output variable name
  - elapsed time
  - output shape summary

Such a plan is invaluable for:

- debugging
- performance tuning
- auditability

This repository already has the right structural constraints (flat lines, uniform dispatch) to implement this cleanly.

