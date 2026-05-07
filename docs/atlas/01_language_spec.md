# 01 — Language specification

This chapter specifies the Atlas language core (surface syntax, tokenization model, binding, and evaluation rules). It intentionally mirrors the current implementation choices (line-oriented, `shlex`-style tokenization) while describing behavior in implementable terms.

## 1. Script structure

An Atlas program is a UTF-8 text file consisting of **lines**. Each non-empty, non-comment line is executed sequentially in order.

### 1.1 Comments

- A `#` character begins a comment.
- Everything from `#` to end of line is ignored.
- Comments may appear on otherwise-empty lines or after code (inline comments).

### 1.2 Blank lines

- Blank lines (after trimming whitespace) are ignored.

## 2. Tokenization

Atlas uses a shell-like tokenization model:

- tokens are separated by whitespace
- quoted strings (`"..."` or `'...'`) are treated as a single token
- escaping rules follow common shell conventions

In practice, this is close to POSIX `shlex.split` behavior. The primary reason is to support file paths with spaces and to avoid needing a full parser for complex grammars.

**Non-goal**: Atlas does not define an expression grammar. There are no infix operators, parentheses grouping, or nested expressions. Every line is a flat sequence of tokens.

## 3. Statements

Atlas has two statement forms:

1) **Assignment**
2) **Print**

### 3.1 Assignment statement

Form:

```text
NAME = VERB PRIMARY [POS... ] [KW...]
```

- `NAME` is an identifier used to bind the result into the environment.
- `=` is a literal token (either as `=` or as part of `key=value` tokens for keyword args).
- `VERB` selects an operation (a command).
- `PRIMARY` is the primary argument to the verb (a variable name or a quoted literal, depending on the verb).
- `POS` are optional positional arguments.
- `KW` are optional keyword arguments.

Examples:

```text
prices = load "prices.csv"
close = select prices column=close
rets = returns close log
v = var rets level=0.99 method=historical
```

### 3.2 Print statement

Form:

```text
print NAME
```

The print statement does not bind a new value. It prints the object currently bound to `NAME`.

## 4. Identifiers

Identifiers are used for variable names and verbs.

Recommended identifier characters:

- letters `a-zA-Z`
- digits `0-9` (not as the first character)
- underscore `_`

Atlas implementations may accept broader identifiers (depending on tokenizer and environment), but users should prefer simple names.

## 5. Arguments

### 5.1 Primary argument

The meaning of the primary argument depends on the verb:

- `load`: primary is typically a quoted file path.
- most other verbs: primary is a variable name referring to a DataFrame-like object.

### 5.2 Positional arguments

Positional arguments are interpreted by the verb. Many verbs support a “convenience positional override” for a single option:

- `returns close log` (positional method override)
- `vol rets 21` (positional window override)
- `var rets 0.95` (positional level override)

### 5.3 Keyword arguments

Keyword arguments can be written in either of two equivalent forms:

1) Single token: `key=value`
2) Three tokens: `key` `=` `value`

Implementations should normalize these into a dictionary mapping `key` → `value`.

Keyword argument values are raw tokens (strings). The verb is responsible for parsing numbers and interpreting lists.

## 6. Environment and binding

Atlas maintains an environment \(E\) mapping `NAME` → value.

- On assignment, `NAME` is bound to the evaluated result.
- Variables are immutable by convention but can be overwritten by reusing the same `NAME`.

Example:

```text
rets = returns close log
rets = returns close simple
```

The second line overwrites `rets`.

## 7. Data types (conceptual)

Atlas is dynamically typed at runtime. Conceptually, the core value types are:

- **Frame**: a table with index + columns (typically a pandas `DataFrame`)
- **Series**: a labeled vector (pandas `Series`) — often used for scalar-like results too
- **Scalar**: numbers or strings (occasionally)

Verbs typically accept a Frame and return a Frame or Series.

## 8. Evaluation model

Atlas is a sequential interpreter. Each line is processed as follows:

1) tokenize line into a list of tokens
2) parse tokens into a statement object:
   - assignment: `(name, verb, primary, pos_args, kw_args)`
   - print: `(verb="print", primary=name)`
3) resolve primary variable references from the environment when needed
4) dispatch to the command implementation for `verb`
5) bind the result (assignment) or print (print statement)

There is no implicit parallelism, lazy evaluation, or query optimizer.

## 9. Determinism and reproducibility

Atlas operations are deterministic given:

- identical input data
- identical numerical libraries (pandas/numpy/scipy versions)
- identical runtime configuration

In the current scope, Atlas avoids stochastic algorithms. When stochastic algorithms are added (e.g., Monte Carlo VaR), the language should expose explicit seeding and record it in output metadata (see later chapters).

## 10. Reserved words and verb namespace

The set of verbs is determined by the dispatch table in `atlas/commands.py`. Users should avoid using verb names as variable names for readability.

Atlas intentionally uses a flat namespace of verbs. Rather than adding submodules into the surface syntax (e.g., `risk.var`), Atlas keeps verbs short and uses documentation to define conventions and workflows.

