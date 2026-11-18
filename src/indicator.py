"""Landslide / no-landslide indicator per rain gauge, evaluated by leave-one-event-out CV.

Indicator (no model fitting, transparent rule usable in a LEWS):
    I(event) = mean over the k features of the empirical percentile (0-100) of the
               feature value within the NON-landslide events of the training set,
               each feature oriented so that larger = more critical
               (rain, VWC, dVWC: +1; suction s0: -1).
    alarm    = I >= tau, tau chosen on the training set by maximising the Youden
               index J = TPR - FPR (ties -> lowest tau, i.e. favour detection).

Evaluation: leave-one-event-out. For every event the percentile reference AND the
threshold are computed without that event, then the event is classified. The
'selected' strategies also choose the feature combination inside each fold
(nested), so the reported performance includes the cost of choosing among
combinations.
"""
import numpy as np
import pandas as pd


def _score(train_neg: np.ndarray, X: np.ndarray, sign: np.ndarray) -> np.ndarray:
    """Mean oriented percentile of rows of X w.r.t. train_neg (n0 x k)."""
    A, B = train_neg * sign, X * sign
    # 'weak' percentile = 100 * fraction of reference values <= v (same as scipy kind="weak")
    P = np.column_stack([100 * np.searchsorted(np.sort(A[:, j]), B[:, j], side="right") / len(A)
                         for j in range(X.shape[1])])
    return P.mean(axis=1)


def _youden_tau(s: np.ndarray, y: np.ndarray) -> float:
    cand = np.unique(s)
    tpr = np.array([(s[y == 1] >= c).mean() for c in cand])
    fpr = np.array([(s[y == 0] >= c).mean() for c in cand])
    j = tpr - fpr
    return float(cand[np.flatnonzero(j == j.max())[0]])   # cand sorted ascending -> lowest tau


def _auc(s, y):
    s1, s0 = s[y == 1][:, None], s[y == 0][None, :]
    return float(((s1 > s0) + 0.5 * (s1 == s0)).mean())


def build_rule(X, y, sign):
    """Return (reference negatives, tau) from training data."""
    neg = X[y == 0]
    s = _score(neg, X, sign)
    return neg, _youden_tau(s, y), _auc(s, y)


def loo_fixed(X: np.ndarray, y: np.ndarray, sign: np.ndarray):
    """LOO-CV for one fixed feature combination. Returns held-out scores, taus, alarms."""
    n = len(y)
    sc, tau, alarm = np.empty(n), np.empty(n), np.empty(n, bool)
    for i in range(n):
        m = np.arange(n) != i
        neg, t, _ = build_rule(X[m], y[m], sign)
        sc[i] = _score(neg, X[i:i + 1], sign)[0]
        tau[i], alarm[i] = t, sc[i] >= t
    return sc, tau, alarm


def loo_selected(D: pd.DataFrame, combos: list[tuple], signs: dict, ycol: str):
    """Nested LOO: in each fold choose the combination with the highest training AUC."""
    y = D[ycol].to_numpy(int)
    n = len(y)
    sc, alarm, chosen = np.empty(n), np.empty(n, bool), []
    Xs = {c: D[list(c)].to_numpy(float) for c in combos}
    sg = {c: np.array([signs[f] for f in c]) for c in combos}
    for i in range(n):
        m = np.arange(n) != i
        best = max(combos, key=lambda c: build_rule(Xs[c][m], y[m], sg[c])[2])
        neg, t, _ = build_rule(Xs[best][m], y[m], sg[best])
        sc[i] = _score(neg, Xs[best][i:i + 1], sg[best])[0]
        alarm[i] = sc[i] >= t
        chosen.append(" + ".join(best))
    return sc, alarm, chosen


def metrics(y: np.ndarray, alarm: np.ndarray, score: np.ndarray) -> dict:
    """Contingency-table skill scores (landslide early-warning convention)."""
    TP = int(((alarm) & (y == 1)).sum()); FN = int(((~alarm) & (y == 1)).sum())
    FP = int(((alarm) & (y == 0)).sum()); TN = int(((~alarm) & (y == 0)).sum())
    POD = TP / (TP + FN)                       # probability of detection = recall
    POFD = FP / (FP + TN)                      # probability of false detection = FPR
    FAR = FP / (TP + FP) if TP + FP else np.nan  # false alarm ratio
    return dict(n=len(y), n_ls=int(y.sum()), TP=TP, FN=FN, FP=FP, TN=TN, POD=POD, POFD=POFD, FAR=FAR,
                TSS=POD - POFD, CSI=TP / (TP + FN + FP), accuracy=(TP + TN) / len(y),
                AUC_cv=_auc(score, y))
