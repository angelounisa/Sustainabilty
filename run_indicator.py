"""Landslide / no-landslide indicator per rain gauge (Ch.4 extension).

Tests fixed feature combinations and nested-selected combinations with
leave-one-event-out cross-validation; writes tables T19-T21, figures Fig16-17
and docs/indicator.json for the dashboard.

Usage:  python run_indicator.py   (after run_analysis.py)
"""
import json
from pathlib import Path
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from src import indicator as ind

CFG = yaml.safe_load(open("config.yaml"))
P = {k: Path(v) for k, v in CFG["paths"].items()}
IC = CFG["indicator"]
EV = pd.read_pickle(P["processed"] / "events.pkl")
GAUGES = list(CFG["rain_gauges"].values())
FEAT = json.load(open(P["processed"] / "features.json"))


def sign(f):
    return -1.0 if "_s0_" in f else 1.0      # suction: low = critical


SIGNS = {f: sign(f) for f in FEAT}
fixed = {k: tuple(v) for k, v in IC["fixed"].items()}
R, W = IC["select_rain"], IC["select_water"]
families = {"SEL rain (1 var)": [(r,) for r in R],
            "SEL rain + VWC0 (2 var)": [(r, w) for r in R for w in W],
            "SEL 2 rain + VWC0 (3 var)": [(a, b, w) for a, b in combinations(R, 2) for w in W],
            "SEL 1 rain + 2 VWC0 (3 var)": [(x, a, b) for x in R for a, b in combinations(W, 2)],
            "SEL rain + VWC0 + NV s0 (3 var)": [(x, w, s) for x in R for w in W for s in ["NV_s0_15", "NV_s0_30"]],
            "SEL 2 rain + 2 VWC0 (4 var)": [(a, b, c, d) for a, b in combinations(R, 2) for c, d in combinations(W, 2)]}
need = sorted({f for c in fixed.values() for f in c} | set(R) | set(W))

rows, scores, chosen_all = [], [], []
for g in GAUGES:
    D = EV[EV.gauge == g].dropna(subset=need).reset_index(drop=True)   # common sample for all strategies
    y = D.Y.to_numpy(int)
    print(f"{g}: n={len(D)} events with all features, landslide events={y.sum()} "
          f"({', '.join(D.landslide[D.Y == 1])})")
    for name, c in fixed.items():
        X, sg = D[list(c)].to_numpy(float), np.array([SIGNS[f] for f in c])
        sc, tau, al = ind.loo_fixed(X, y, sg)
        _, tau_in, auc_in = ind.build_rule(X, y, sg)
        sc_in = ind._score(X[y == 0], X, sg)
        m_in = ind.metrics(y, sc_in >= tau_in, sc_in)
        rows.append(dict(gauge=g, strategy=name, kind="fixed", k=len(c), **ind.metrics(y, al, sc),
                         tau_median=float(np.median(tau)), TSS_insample=m_in["TSS"], POD_insample=m_in["POD"],
                         POFD_insample=m_in["POFD"]))
        scores += [dict(gauge=g, strategy=name, event_id=e, t_start=t, Y=int(yy), landslide=l, score=s, tau=tt,
                        alarm=bool(a)) for e, t, yy, l, s, tt, a in
                   zip(D.event_id, D.t_start, y, D.landslide, sc, tau, al)]
    for name, cl in families.items():
        sc, al, ch = ind.loo_selected(D, cl, SIGNS, "Y")
        rows.append(dict(gauge=g, strategy=name, kind="nested selection", k=len(cl[0]), **ind.metrics(y, al, sc)))
        chosen_all += [dict(gauge=g, strategy=name, combo=c) for c in ch]
        scores += [dict(gauge=g, strategy=name, event_id=e, t_start=t, Y=int(yy), landslide=l, score=s, tau=None,
                        alarm=bool(a)) for e, t, yy, l, s, a in zip(D.event_id, D.t_start, y, D.landslide, sc, al)]

T = pd.DataFrame(rows)
T.to_csv(P["tables"] / "T19_indicator_performance_by_gauge.csv", index=False, float_format="%.4g")
S = T.groupby(["strategy", "kind"], sort=False)[["TP", "FN", "FP", "TN"]].sum().reset_index()
S["POD"] = S.TP / (S.TP + S.FN); S["POFD"] = S.FP / (S.FP + S.TN)
S["FAR"] = S.FP / (S.TP + S.FP); S["TSS"] = S.POD - S.POFD; S["CSI"] = S.TP / (S.TP + S.FN + S.FP)
S = S.merge(T.groupby("strategy").agg(AUC_cv_mean=("AUC_cv", "mean"), TSS_min=("TSS", "min"),
                                      TSS_insample_mean=("TSS_insample", "mean")).reset_index(), on="strategy")
S = S.sort_values("TSS", ascending=False)
S.to_csv(P["tables"] / "T20_indicator_performance_pooled.csv", index=False, float_format="%.4g")
CH = pd.DataFrame(chosen_all).value_counts(["gauge", "strategy", "combo"]).rename("n_folds").reset_index()
CH.to_csv(P["tables"] / "T21_indicator_nested_selected_combos.csv", index=False)
SC = pd.DataFrame(scores)
SC.to_pickle(P["processed"] / "indicator_scores.pkl")

# ------------------------------------------------------------------ figures
F = P["figures"]
plt.rcParams.update({"font.size": 9, "savefig.dpi": 300, "savefig.bbox": "tight", "axes.grid": True,
                     "grid.alpha": .3, "axes.spines.top": False, "axes.spines.right": False})
order = S.strategy.tolist()
fig, axs = plt.subplots(1, 4, figsize=(19, 11), sharey=True)
y = np.arange(len(order))[::-1]
cols = plt.cm.tab10(np.arange(len(GAUGES)))
for a, met, ttl in zip(axs, ["TSS", "POD", "POFD", "AUC_cv"],
                       ["TSS = POD − POFD", "POD (frane rilevate)", "POFD (falsi allarmi / eventi senza frana)",
                        "AUC (punteggi in CV)"]):
    for k, g in enumerate(GAUGES):
        t = T[T.gauge == g].set_index("strategy").loc[order, met]
        a.scatter(t.to_numpy(), y + (k - 2) * .1, s=16, color=cols[k], label=g)
    if met in S:
        a.scatter(S.set_index("strategy").loc[order, met], y, marker="|", s=250, color="k", label="pooled")
    a.set_title(ttl)
    a.set_xlim(-.05 if met != "AUC_cv" else .4, 1.05)
axs[0].set_yticks(y, order)
axs[0].legend(fontsize=7, loc="upper left")
fig.suptitle("Landslide indicator — leave-one-event-out performance per rain gauge (sorted by pooled TSS)")
fig.tight_layout()
fig.savefig(F / "Fig16_indicator_performance.png"); plt.close(fig)

best_fixed = S[S.kind == "fixed"].strategy.iloc[0]
fig, axs = plt.subplots(len(GAUGES), 1, figsize=(13, 11), sharex=True)
for a, g in zip(axs, GAUGES):
    d = SC[(SC.gauge == g) & (SC.strategy == best_fixed)]
    a.vlines(d.t_start, 0, d.score, color=np.where(d.Y == 1, "#c62828", "#9e9e9e"), lw=2)
    a.scatter(d.t_start[d.alarm & (d.Y == 0)], d.score[d.alarm & (d.Y == 0)], marker="x", color="orange",
              label="falso allarme")
    a.scatter(d.t_start[d.Y == 1], d.score[d.Y == 1], marker="*", s=120,
              color=np.where(d.alarm[d.Y == 1], "#c62828", "white"), edgecolor="#c62828", label="frana")
    a.step(d.t_start, d.tau, where="mid", color="k", lw=.8, ls="--", label="soglia (CV)")
    a.set_ylabel(f"{g}\nI (0–100)"); a.set_ylim(0, 105)
axs[0].legend(fontsize=7, ncol=3, loc="upper left")
fig.suptitle(f"Indicator '{best_fixed}': cross-validated value of each event (red = landslide event; "
             "hollow star = missed landslide)")
fig.tight_layout(); fig.savefig(F / "Fig17_indicator_timeline_best.png"); plt.close(fig)

# TSS vs number of variables (pooled, cross-validated)
S["k"] = S.strategy.map(T.groupby("strategy").k.first())
fig, ax = plt.subplots(figsize=(10, 5.5))
for kind, mk, col in [("fixed", "o", "#2e6b4f"), ("nested selection", "s", "#e8834c")]:
    d = S[S.kind == kind]
    ev = d.strategy.str.contains("event")
    ax.scatter(d.k[~ev], d.TSS[~ev], marker=mk, s=60, color=col, label=f"{kind} (pre-event variables)")
    ax.scatter(d.k[ev], d.TSS[ev], marker=mk, s=60, facecolor="none", edgecolor=col, label=f"{kind} (with ΔVWC)")
    for r_ in d.itertuples():
        ax.annotate(r_.strategy, (r_.k, r_.TSS), xytext=(5, 2), textcoords="offset points", fontsize=6.5)
ax.set_xscale("log", base=2); ax.set_xticks([1, 2, 3, 4, 5, 8, 11, 15], [1, 2, 3, 4, 5, 8, 11, 15])
ax.set_xlabel("number of variables in the indicator"); ax.set_ylabel("pooled TSS (leave-one-event-out)")
ax.set_title("Does adding variables help? Cross-validated TSS vs indicator size (5 gauges pooled)")
ax.legend(fontsize=7); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(F / "Fig19_indicator_TSS_vs_nvars.png"); plt.close(fig)

# ------------------------------------------------ every 3-variable indicator (exhaustive)
V3 = R + W + ["NV_s0_15", "NV_s0_30"]
def vtype(f):
    return "rain" if f in R else ("suction" if "_s0_" in f else "VWC0")
tri_rows = []
for g in GAUGES:
    D = EV[EV.gauge == g].dropna(subset=need).reset_index(drop=True)
    y = D.Y.to_numpy(int)
    for c in combinations(V3, 3):
        X, sg = D[list(c)].to_numpy(float), np.array([SIGNS[f] for f in c])
        sc, tau, al = ind.loo_fixed(X, y, sg)
        tri_rows.append(dict(gauge=g, combo=" + ".join(c), type=" + ".join(sorted(vtype(f) for f in c)),
                             **ind.metrics(y, al, sc)))
TRI = pd.DataFrame(tri_rows)
TRI.to_csv(P["tables"] / "T22_indicator_all_3var_by_gauge.csv", index=False, float_format="%.4g")
TP_ = TRI.groupby(["combo", "type"])[["TP", "FN", "FP", "TN"]].sum().reset_index()
TP_["POD"] = TP_.TP / (TP_.TP + TP_.FN); TP_["POFD"] = TP_.FP / (TP_.FP + TP_.TN)
TP_["FAR"] = TP_.FP / (TP_.TP + TP_.FP); TP_["TSS"] = TP_.POD - TP_.POFD
TP_ = TP_.merge(TRI.groupby("combo").agg(TSS_min=("TSS", "min"), AUC_cv_mean=("AUC_cv", "mean")).reset_index(), on="combo")
TP_ = TP_.sort_values("TSS", ascending=False)
TP_.to_csv(P["tables"] / "T23_indicator_all_3var_pooled.csv", index=False, float_format="%.4g")
print(f"3-variable indicators: {len(TP_)} combinations; best pooled TSS {TP_.TSS.max():.3f}; "
      f"median {TP_.TSS.median():.3f}")

fig, axs = plt.subplots(1, 2, figsize=(17, 6.5), gridspec_kw=dict(width_ratios=[1, 1.4]))
types = TP_.groupby("type").TSS.median().sort_values().index.tolist()
axs[0].boxplot([TP_.TSS[TP_.type == t] for t in types], orientation="horizontal", widths=.6, showfliers=True)
axs[0].set_yticks(range(1, len(types) + 1), [f"{t}\n(n={int((TP_.type == t).sum())})" for t in types], fontsize=7)
ref = S.set_index("strategy").TSS
for name, col in [("E", "#c62828"), ("E + NV VWC0 15", "#2e6b4f"), ("SEL 2 rain + VWC0 (3 var)", "#e8834c")]:
    if name in ref:
        axs[0].axvline(ref[name], color=col, ls="--", lw=1, label=f"{name}: {ref[name]:.2f}")
axs[0].set_xlabel("pooled TSS (leave-one-event-out)"); axs[0].legend(fontsize=7, loc="upper left")
axs[0].set_title("All 3-variable indicators by variable type")
top = TP_.head(20).iloc[::-1]
axs[1].barh(range(len(top)), top.TSS, color="#5c8f74")
axs[1].scatter(top.TSS_min, range(len(top)), marker="|", s=120, color="k", label="worst gauge")
axs[1].set_yticks(range(len(top)), [" + ".join(FEAT[f][0] for f in c.split(" + ")) for c in top.combo], fontsize=7)
axs[1].set_xlim(0, 1); axs[1].set_xlabel("pooled TSS"); axs[1].legend(fontsize=7)
axs[1].set_title("Top 20 of 455 (selected on the same data: optimistic)")
fig.tight_layout(); fig.savefig(F / "Fig20_indicator_all_3var.png"); plt.close(fig)

# ------------------------------------------------------------------ dashboard export
def rec(df):
    return json.loads(df.to_json(orient="records", date_format="iso"))
json.dump(dict(by_gauge=rec(T), pooled=rec(S), triples=rec(TP_), triples_by_gauge=rec(TRI[["gauge", "combo", "TP", "FN", "FP", "TN", "TSS", "AUC_cv"]]), chosen=rec(CH), scores=rec(SC), fixed={k: list(v) for k, v in fixed.items()},
               best_fixed=best_fixed), open("docs/indicator.json", "w"), separators=(",", ":"))
for f in ["Fig16_indicator_performance.png", "Fig17_indicator_timeline_best.png", "Fig19_indicator_TSS_vs_nvars.png", "Fig20_indicator_all_3var.png"]:
    (Path("docs/figures") / f).write_bytes((F / f).read_bytes())
pd.set_option("display.width", 250)
print(S.round(3).to_string(index=False))
