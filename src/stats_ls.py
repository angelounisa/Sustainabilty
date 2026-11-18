"""Landslide-triggering vs non-triggering statistics (Chapter 4).

Univariate: ROC-AUC (direction-invariant AUC*), Mann-Whitney U, rank-biserial r,
median percentile of landslide events, Youden-optimal threshold and recall.
Multivariate: KDE background, vertical pre-event profile, Mahalanobis anomaly.
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def match_landslides(ev: pd.DataFrame, ls: pd.DataFrame, ext_h: float) -> pd.Series:
    """Return a Series (index = ev.index) with the landslide id(s) assigned to each event.

    A landslide is assigned to an event when the landslide time interval
    [t - u, t + u] overlaps the event window [t_start, t_end + ext_h].
    """
    lab = pd.Series("", index=ev.index, dtype=object)
    ext = pd.Timedelta(hours=ext_h)
    for r in ls.itertuples():
        u = pd.Timedelta(hours=r.uncertainty_h)
        a, b = r.t - u, r.t + u
        hit = ev.index[(ev.t_start <= b) & (ev.t_end + ext >= a)]
        if len(hit) > 1:   # keep the event whose window contains the central time, else the closest start
            inside = [i for i in hit if ev.t_start[i] <= r.t <= ev.t_end[i] + ext]
            hit = inside[:1] if inside else [min(hit, key=lambda i: abs(ev.t_start[i] - r.t))]
        for i in hit:
            lab[i] = (lab[i] + "," + r.id).strip(",")
    return lab


def univariate(x: pd.Series, y: pd.Series, inverse: bool) -> dict:
    """Discriminant metrics for one feature. y = 1 landslide, 0 no landslide.

    inverse=True for variables where LOWER values mean higher instability (suction):
    the Youden threshold is then searched as x <= tau and the percentile is 100 - pi.
    """
    m = x.notna()
    x, y = x[m].astype(float), y[m].astype(int)
    x1, x0 = x[y == 1].to_numpy(), x[y == 0].to_numpy()
    n1, n0 = len(x1), len(x0)
    res = dict(n_ls=n1, n_nols=n0)
    if n1 == 0 or n0 == 0:
        return res | dict(AUC=np.nan)
    U, p = stats.mannwhitneyu(x1, x0, alternative="two-sided", method="auto")
    auc = U / (n1 * n0)                       # P(X1 > X0) + 0.5 P(X1 = X0)
    rb = 2 * auc - 1                          # rank-biserial correlation (signed)
    # empirical percentile of each landslide value within the pooled distribution
    pooled = np.sort(x.to_numpy())
    pct = np.array([stats.percentileofscore(pooled, v, kind="weak") for v in x1])
    # Direction used for percentile and Youden threshold = the observed one (consistent
    # with AUC* = max(AUC, 1-AUC)); 'inverse' (expected physical direction) is reported
    # separately so that counter-intuitive directions are flagged, not hidden.
    lower = auc < 0.5
    med_pct = 100 - np.median(pct) if lower else np.median(pct)
    s = -x if lower else x
    s1, s0 = (-x1 if lower else x1), (-x0 if lower else x0)
    cand = np.unique(s.to_numpy())
    tpr = np.array([(s1 >= c).mean() for c in cand])
    fpr = np.array([(s0 >= c).mean() for c in cand])
    j = tpr - fpr
    k = int(np.argmax(j))
    tau = -cand[k] if lower else cand[k]
    return res | dict(direction="<=" if lower else ">=", physics_consistent=(lower == inverse),mean_ls=x1.mean(), mean_nols=x0.mean(), median_ls=np.median(x1),
                      median_nols=np.median(x0), AUC=auc, AUC_star=max(auc, 1 - auc), RB=rb,
                      U=U, p=p, median_pct=med_pct, youden_J=j[k], threshold=tau,
                      recall=tpr[k], FPR=fpr[k],
                      TP=int((s1 >= cand[k]).sum()), FP=int((s0 >= cand[k]).sum()))


def feature_table(df: pd.DataFrame, features: dict, ycol: str, method: str) -> pd.DataFrame:
    """features: {column: (label, inverse)}. Holm correction across features."""
    rows = []
    for c, (lab, inv) in features.items():
        rows.append(dict(feature=c, label=lab, inverse=inv) | univariate(df[c], df[ycol], inv))
    t = pd.DataFrame(rows)
    ok = t.p.notna()
    t.loc[ok, "p_adj"] = multipletests(t.loc[ok, "p"], method=method)[1]
    return t.sort_values("AUC_star", ascending=False).reset_index(drop=True)


def roc_curve(x: pd.Series, y: pd.Series, inverse: bool):
    m = x.notna()
    s = (-x[m] if inverse else x[m]).to_numpy(float)
    yy = y[m].to_numpy(int)
    cand = np.r_[np.inf, np.sort(np.unique(s))[::-1], -np.inf]
    tpr = np.array([(s[yy == 1] >= c).mean() for c in cand])
    fpr = np.array([(s[yy == 0] >= c).mean() for c in cand])
    return fpr, tpr


def mahalanobis(df: pd.DataFrame, feats: list[str], ycol: str, q: float):
    """Distance from the non-landslide distribution; threshold sqrt(chi2_k(q))."""
    d = df.dropna(subset=feats).copy()
    X0 = d.loc[d[ycol] == 0, feats].to_numpy(float)
    mu = X0.mean(axis=0)
    S = np.cov(X0, rowvar=False)
    assert np.linalg.cond(S) < 1e10, "ill-conditioned covariance"
    Si = np.linalg.inv(S)
    diff = d[feats].to_numpy(float) - mu
    d["D_M"] = np.sqrt(np.einsum("ij,jk,ik->i", diff, Si, diff))
    thr = np.sqrt(stats.chi2.ppf(q, df=len(feats)))
    return d, thr
