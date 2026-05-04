"""Classification models (v0: logistic regression for accuracy metric demos)."""

from __future__ import annotations

import pandas as pd

from athena.errors import AthenaRuntimeError


def fit_logistic(X: pd.DataFrame, y: pd.Series, random_state: int = 0):
    try:
        from sklearn.linear_model import LogisticRegression  # type: ignore
    except ImportError as e:
        raise AthenaRuntimeError("algo requires scikit-learn: pip install scikit-learn") from e

    clf = LogisticRegression(max_iter=2000, random_state=random_state)
    clf.fit(X.fillna(0.0).to_numpy(), y.astype(int).to_numpy())
    return clf
