"""Classification models (v0: logistic regression for accuracy metric demos)."""

from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LogisticRegression


def fit_logistic(X: pd.DataFrame, y: pd.Series, random_state: int = 0) -> LogisticRegression:
    clf = LogisticRegression(max_iter=2000, random_state=random_state)
    clf.fit(X.fillna(0.0).to_numpy(), y.astype(int).to_numpy())
    return clf
