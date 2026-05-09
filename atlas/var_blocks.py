"""Block syntax for named VaR models, validations, and model comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

from .errors import AtlasRuntimeError, AtlasSyntaxError
from .runtime import as_dataframe
from .std import stats

Env = dict[str, Any]


@dataclass(frozen=True)
class VarModelSpec:
    """Declarative VaR model (used by ``model`` blocks)."""

    name: str
    type: str
    level: float
    window: int | None = None
    dist: str | None = None

    def describe(self) -> str:
        w = f" window={self.window}" if self.window is not None else ""
        d = f" dist={self.dist}" if self.dist else ""
        return f"VarModelSpec({self.name} type={self.type} level={self.level}{w}{d})"

    def __str__(self) -> str:
        return self.describe()


_MODEL_DATA_BINDING_KEY = "__atlas_model_validation_data__"


def _remember_model_data(env: Env, model_name: str, data_name: str) -> None:
    b = env.setdefault(_MODEL_DATA_BINDING_KEY, {})
    assert isinstance(b, dict)
    b[model_name] = data_name


def _resolve_compare_data(env: Env, model_names: list[str]) -> str:
    b = env.get(_MODEL_DATA_BINDING_KEY)
    if not isinstance(b, dict):
        raise AtlasRuntimeError(
            "compare block needs data= when no prior validation recorded model→data bindings"
        )
    datas = {str(b[m]) for m in model_names if m in b}
    if len(datas) != 1:
        raise AtlasRuntimeError(
            "compare without data= requires each model to have been validated "
            "against the same returns frame; supply data= explicitly"
        )
    return datas.pop()


def _lookup(env: Env, name: str) -> Any:
    if name not in env:
        raise AtlasRuntimeError(f"Unknown variable or block: {name}")
    return env[name]


def parse_list_literal(raw: str) -> list[str]:
    s = raw.strip()
    if not (s.startswith("[") and s.endswith("]")):
        raise AtlasSyntaxError(f"Expected list literal like [a, b], got {raw!r}")
    inner = s[1:-1].strip()
    if not inner:
        return []
    out: list[str] = []
    for part in inner.split(","):
        p = part.strip()
        if not p:
            continue
        if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")):
            p = p[1:-1]
        out.append(p)
    return out


def parse_block_body(lines: list[str]) -> dict[str, str]:
    body: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise AtlasSyntaxError(f"Invalid block line (expected key = value): {line!r}")
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if not key:
            raise AtlasSyntaxError(f"Invalid block line: {line!r}")
        body[key] = val
    return body


def _normalize_model_type(s: str) -> str:
    t = s.strip().strip('"').strip("'").lower()
    if t in ("historical_var", "historical", "hist", "empirical"):
        return "historical_var"
    if t in ("parametric_var", "parametric", "normal", "gaussian"):
        return "parametric_var"
    raise AtlasRuntimeError(f"Unknown model type: {s!r}")


def _spec_from_body(name: str, body: dict[str, str]) -> VarModelSpec:
    if "type" not in body or "level" not in body:
        raise AtlasRuntimeError("model block requires type= and level=")
    mt = _normalize_model_type(body["type"])
    level = float(body["level"].strip().strip('"').strip("'"))
    window: int | None = None
    if "window" in body:
        window = int(body["window"].strip())
    dist: str | None = None
    if "dist" in body:
        dist = body["dist"].strip().strip('"').strip("'").lower()
    if mt == "parametric_var":
        if dist in (None, "", "normal", "gaussian"):
            dist = "normal"
        else:
            raise AtlasRuntimeError(f"parametric_var only supports dist=normal (got {dist!r})")
    return VarModelSpec(name=name, type=mt, level=level, window=window, dist=dist)


def _series_returns(env: Env, data_name: str) -> pd.Series:
    df = as_dataframe(_lookup(env, data_name))
    return stats._series_from_frame(df).astype(float)


def _var_forecast_for_model(
    spec: VarModelSpec,
    s: pd.Series,
    rolling_window: int | None,
) -> float | pd.Series:
    """VaR forecast used for backtesting: rolling series is shifted to avoid same-day lookahead."""
    use_window = rolling_window if rolling_window is not None else spec.window
    if use_window is not None and int(use_window) >= 2:
        w = int(use_window)
        if spec.type == "historical_var":
            ser = stats.rolling_historical_var_series(s, w, spec.level)
        else:
            ser = stats.rolling_parametric_var_series(s, w, spec.level)
        return ser.shift(1)

    s_clean = s.dropna()
    if len(s_clean) < 2:
        raise AtlasRuntimeError("Not enough returns to estimate VaR")
    df = s_clean.to_frame(name="r")
    if spec.type == "historical_var":
        q = 1.0 - float(spec.level)
        return float(df.quantile(q).iloc[0])
    mu, sigma = float(s_clean.mean()), float(s_clean.std(ddof=1))
    if sigma == 0.0 or not np.isfinite(sigma):
        raise AtlasRuntimeError("parametric VaR requires positive finite return volatility")
    tau = 1.0 - float(spec.level)
    return float(mu + sigma * float(norm.ppf(tau)))


def run_model_block(name: str, body_lines: list[str], env: Env) -> None:
    body = parse_block_body(body_lines)
    env[name] = _spec_from_body(name, body)


def run_validation_block(name: str, body_lines: list[str], env: Env) -> None:
    body = parse_block_body(body_lines)
    for key in ("data", "model", "metric"):
        if key not in body:
            raise AtlasRuntimeError(f"validation block {name!r} requires {key}=")
    data_name = body["data"].strip().strip('"').strip("'")
    model_name = body["model"].strip().strip('"').strip("'")
    metrics = parse_list_literal(body["metric"])
    rolling: int | None = None
    if "rolling" in body:
        rolling = int(body["rolling"].strip())

    spec = _lookup(env, model_name)
    if not isinstance(spec, VarModelSpec):
        raise AtlasRuntimeError(f"validation model= must name a model block (got {model_name!r})")

    s = _series_returns(env, data_name)
    df_ret = s.to_frame(name=s.name or "return")
    v = _var_forecast_for_model(spec, s, rolling)
    env[name] = stats.var_validation_metrics(df_ret, v, spec.level, metrics)
    _remember_model_data(env, model_name, data_name)


def run_compare_block(name: str, body_lines: list[str], env: Env) -> None:
    body = parse_block_body(body_lines)
    if "models" not in body or "metric" not in body:
        raise AtlasRuntimeError("compare block requires models= and metric=")
    model_names = parse_list_literal(body["models"])
    metrics = parse_list_literal(body["metric"])
    if "data" in body:
        data_name = body["data"].strip().strip('"').strip("'")
    else:
        data_name = _resolve_compare_data(env, model_names)
    rolling: int | None = None
    if "rolling" in body:
        rolling = int(body["rolling"].strip())

    s = _series_returns(env, data_name)
    df_ret = s.to_frame(name=s.name or "return")

    rows: list[pd.Series] = []
    idx: list[str] = []
    for mname in model_names:
        spec = _lookup(env, mname)
        if not isinstance(spec, VarModelSpec):
            raise AtlasRuntimeError(f"compare models= entries must be model blocks (got {mname!r})")
        v = _var_forecast_for_model(spec, s, rolling)
        rows.append(stats.var_validation_metrics(df_ret, v, spec.level, metrics))
        idx.append(mname)
    env[name] = pd.DataFrame(rows, index=idx)


def dispatch_block(kind: str, block_name: str, body_lines: list[str], env: Env) -> None:
    if kind == "model":
        run_model_block(block_name, body_lines, env)
    elif kind == "validation":
        run_validation_block(block_name, body_lines, env)
    elif kind == "compare":
        run_compare_block(block_name, body_lines, env)
    else:
        raise AtlasSyntaxError(f"Unknown block kind: {kind!r}")
