"""Classification models (v0: logistic regression for accuracy metric demos)."""

from __future__ import annotations

import pandas as pd

from athena.errors import AthenaRuntimeError


def fit_logistic(X: pd.DataFrame, y: pd.Series, random_state: int = 0):
    try:
        from sklearn.linear_model import LogisticRegression  # type: ignore
    except ImportError as e:
        raise AthenaRuntimeError("algo requires scikit-learn: pip install scikit-learn") from e

    aligned = pd.concat([X, y.rename("target")], axis=1).dropna()
    if aligned.empty:
        raise AthenaRuntimeError("logistic requires complete feature and target rows")
    clf = LogisticRegression(max_iter=2000, random_state=random_state)
    clf.fit(aligned[X.columns].to_numpy(), aligned["target"].astype(int).to_numpy())
    return clf
