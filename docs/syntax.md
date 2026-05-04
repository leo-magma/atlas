# Atlas DSL syntax

## Line-oriented scripts

- One statement per line. Blank lines are ignored.
- Everything from `#` to end of line is a comment.

## Assignment

```text
name = func primary [positional-args ...] [keyword-args ...]
```

- **Primary argument**: For most commands, the input variable name, or for `load`, the file path.
- **Positional arguments**: e.g. the `21` in `vol rets 21`.
- **Keyword arguments**:
  - Write `key=value` as a single token (e.g. `method=log`), or
  - Use three tokens: `key` `=` `value`.

## print statement

```text
print variable_name
```

Prints the object bound in the environment (no assignment).

## Identifiers and quoting

- Wrap file paths that contain spaces in double quotes (POSIX `shlex` rules).
- Variable names: prefer letters, digits, and underscores.

## Reserved words (function names)

`load`, `select`, `bind`, `returns`, `vol`, `var`, `es`, `corr`, `cov`, `beta`, `sharpe`, `print`

When new functions are added, the dispatch table in `atlas/commands.py` is the source of truth.
