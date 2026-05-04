"""Load serialized objects."""

from __future__ import annotations

from atlas.runtime import resolve_path


def load_object(path: str, base_dir: str | None) -> object:
    try:
        import joblib  # type: ignore
    except ImportError as e:
        raise ImportError("Model IO requires joblib: pip install joblib") from e

    resolved = resolve_path(path.strip('"').strip("'"), base_dir)
    return joblib.load(resolved)
