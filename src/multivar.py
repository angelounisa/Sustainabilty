"""Multivariate discrimination of landslide-triggering events by feature combinations.

For every combination (1 rainfall + 1 water-content variable; 3-variable combinations)
two scores are computed, both WITHOUT fitting anything to the landslide events:

1. Mahalanobis distance D_M from the distribution of NON-landslide events
   (mean and covariance from Y = 0 only; draft Ch.3.3.4). For non-landslide events the
   distance is computed leave-one-out (the event is excluded from mu, Sigma), so that
   every event is scored against a reference it did not contribute to.
   Anomaly threshold: sqrt(chi2_k(q)).
   D_M is non-directional: an unusually DRY or unusually SMALL event is also anomalous.

2. Directional percentile score: each variable is converted to its empirical percentile
   within the non-landslide events, oriented in the physically expected direction
   (more rain / wetter soil / larger dVWC = more critical), and the k percentiles are
   averaged. This is a non-parametric, one-sided composite index.

AUC = P(score_landslide > score_non-landslide) (Mann-Whitney U / n1 n0).
"""
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


def _loo_mahalanobis(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """D_M of every row w.r.t. the y==0 rows; y==0 rows are scored leave-one-out."""
    X0 = X[y == 0]
    mu, S = X0.mean(axis=0), np.atleast_2d(np.cov(X0, rowvar=False))
    cond = np.linalg.cond(S)
    if cond > 1e10:
        return None                                   # degenerate covariance (reported as NaN)
    Si = np.linalg.inv(S)
    dm = np.sqrt(np.einsum("ij,jk,ik->i", X - mu, Si, X - mu))
    idx0 = np.where(y == 0)[0]
    for i in idx0:
        m = np.ones(len(X), bool); m[i] = False
        Xr = X[m & (y == 0)]
        mu_i, S_i = Xr.mean(axis=0), np.atleast_2d(np.cov(Xr, rowvar=False))
        d = X[i] - mu_i
        dm[i] = np.sqrt(d @ np.linalg.inv(S_i) @ d)
    return dm


def _percentile_score(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Mean empirical percentile (0-100) of each column within the y==0 rows.
    Columns must already be oriented so that larger = more critical."""
    X0 = X[y == 0]
    P = np.column_stack([[stats.percentileofscore(X0[:, j], v, kind="weak") for v in X[:, j]]
                         for j in range(X.shape[1])])
    return P.mean(axis=1)


def _auc(s, y):
    s1, s0 = s[y == 1], s[y == 0]
    U, p = stats.mannwhitneyu(s1, s0, alternative="greater")
    return U / (len(s1) * len(s0)), p


def score_combination(df: pd.DataFrame, feats: list[str], ycol: str, q: float) -> dict:
    d = df.dropna(subset=feats)
    y = d[ycol].to_numpy(int)
    X = d[feats].to_numpy(float)
    k = len(feats)
    out = dict(n=len(d), n_ls=int(y.sum()), n_nols=int((y == 0).sum()))
    if out["n_ls"] == 0 or out["n_nols"] < k + 5:
        return out
    thr = np.sqrt(stats.chi2.ppf(q, df=k))
    dm = _loo_mahalanobis(X, y)
    if dm is not None:
        a, p = _auc(dm, y)
        out |= dict(AUC_DM=a, p_DM=p, DM_thr=thr, LS_above_thr=int((dm[y == 1] > thr).sum()),
                    FP_above_thr=int((dm[y == 0] > thr).sum()),
                    FPR_thr=float((dm[y == 0] > thr).mean()),
                    min_DM_ls=float(dm[y == 1].min()), median_DM_nols=float(np.median(dm[y == 0])))
    # every candidate variable is "larger = more critical" by construction (see FEATURE sets)
    ps = _percentile_score(X, y)
    a, p = _auc(ps, y)
    out |= dict(AUC_PS=a, p_PS=p,
                recall_at_FPR10=float((ps[y == 1] > np.quantile(ps[y == 0], 0.90)).mean()))
    return out


def run(EV: pd.DataFrame, gauges: list[str], rain_vars: list[str], water_vars: list[str],
        ycol: str, q: float) -> dict[str, pd.DataFrame]:
    combos = {"2var_R+W": [(r, w) for r in rain_vars for w in water_vars],
              "3var_R+R+W": [(a, b, w) for a, b in combinations(rain_vars, 2) for w in water_vars],
              "3var_R+W+W": [(r, a, b) for r in rain_vars for a, b in combinations(water_vars, 2)],
              "1var": [(v,) for v in rain_vars + water_vars]}
    res = {}
    for name, cl in combos.items():
        rows = []
        for g in gauges:
            D = EV[EV.gauge == g]
            for c in cl:
                rows.append(dict(gauge=g, combo=" + ".join(c), k=len(c), **{f"x{i + 1}": v for i, v in enumerate(c)},
                                 **score_combination(D, list(c), ycol, q)))
        res[name] = pd.DataFrame(rows)
    return res


def summarise(T: pd.DataFrame, n_ls_expected: dict) -> pd.DataFrame:
    """Aggregate across gauges. 'complete' = all landslide events of the gauge have data."""
    T = T.copy()
    T["complete"] = T.apply(lambda r: r.n_ls == n_ls_expected[r.gauge], axis=1)
    agg = T.groupby("combo").agg(k=("k", "first"), AUC_DM_mean=("AUC_DM", "mean"), AUC_DM_min=("AUC_DM", "min"),
                                 AUC_PS_mean=("AUC_PS", "mean"), AUC_PS_min=("AUC_PS", "min"),
                                 LS_above_thr=("LS_above_thr", "sum"), n_ls=("n_ls", "sum"),
                                 FP_above_thr=("FP_above_thr", "sum"), n_nols=("n_nols", "sum"),
                                 complete_all_gauges=("complete", "all"))
    agg["FPR_thr"] = agg.FP_above_thr / agg.n_nols
    agg["recall_thr"] = agg.LS_above_thr / agg.n_ls
    return agg.sort_values(["AUC_DM_mean"], ascending=False).reset_index()
