# 06 — Error taxonomy

Errors are part of the language. A DSL that cannot explain failure precisely will not scale beyond toy usage. This chapter documents error classes and recommended messaging patterns.

## 6.1 Error classes (conceptual)

Atlas errors can be grouped into:

- **Syntax errors**: invalid line structure, missing tokens, malformed keyword assignments
- **Name errors**: referencing an unknown variable
- **Dispatch errors**: calling an unknown verb
- **Type/shape errors**: wrong value type (expected frame), wrong shape (expected single-column)
- **Data errors**: missing columns, insufficient observations, non-finite values
- **Model errors**: invalid parameters (e.g., level outside (0,1)), undefined statistics
- **I/O errors**: file not found, unreadable file

In the codebase, these map to custom exceptions (e.g., `AtlasSyntaxError`, `AtlasRuntimeError`, and specific “Unknown…” variants). The exact class names are less important than:

- the classification
- the message clarity
- the inclusion of file/line context at the interpreter level

## 6.2 Principles for error messages

### 1) Tell the user what to do next

Bad:

- “Expected single-column DataFrame”

Good:

- “Expected a single-column DataFrame; use `select ... column=...` first”

### 2) Include the relevant label

If an error comes from a named intermediate, include the variable name:

- “`ra` must be a single-column frame; use select first”

### 3) Prefer deterministic failures to silent coercion

For example, correlation on a 1-column frame should fail loudly:

- “corr requires at least two columns”

### 4) Preserve the line number

When executing a file, wrap runtime errors with:

- `path:lineno: message`

This is essential for UI and CI contexts.

## 6.3 Common Atlas failure modes (with examples)

### Unknown variable

Script:

```text
rets = returns close log
```

If `close` is not defined:

- classification: Name error
- message: “Unknown variable: close”

Fix:

```text
close = select prices column=close
rets = returns close log
```

### Unknown verb

Script:

```text
x = varn rets 0.95
```

`varn` is not a verb:

- classification: Dispatch error
- message: “Unknown function: varn”

Fix:

```text
x = var rets 0.95
```

### Wrong shape: expected single-column frame

Script:

```text
prices = load "prices_wide.csv"
rets = returns prices log
```

If `prices` has multiple columns, `returns` fails:

- classification: Shape error
- message: “Expected a single-column DataFrame; use select ... column=... first”

Fix:

```text
close_a = select prices column=close_a
rets = returns close_a log
```

### Invalid parameters: level

If a user supplies `level=1.0` for parametric ES:

- classification: Model error
- message: “level must be strictly between 0 and 1 for parametric ES”

Fix:

- choose `level` in (0,1), e.g. 0.95, 0.99

### Insufficient observations

For beta or statistical measures, there may be minimum sample sizes.

Example:

- “Not enough overlapping observations for beta”

Fix:

- ensure data overlap, reduce missingness, or widen the sample window

## 6.4 Runner/UI considerations

When embedding Atlas in a UI:

- capture stdout and stderr separately
- show the error with file+line context
- keep the last N characters of output to prevent UI overload
- store job status transitions (queued → running → succeeded/failed)

These are not language changes. They are runtime integration decisions that make the language “product-grade”.

