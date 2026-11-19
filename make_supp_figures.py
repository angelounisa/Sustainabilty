"""Supplementary figures (paper/supplementary/figures, same style as the main figures).

Usage:  python make_supp_figures.py   (after run_analysis.py, run_indicator.py)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import make_paper_figures as M          # shares style, colours and loaded data
from src import stats_ls, indicator as ind

OUT = Path("paper/supplementary/figures"); OUT.mkdir(parents=True, exist_ok=True)
EV, DT, GAUGES, GC, C, W = M.EV, M.DT, M.GAUGES, M.GC, M.C, M.W
FEAT = M.json.load(open(M.P["processed"] / "features.json"))
LAB = {"E_mm": "E", "D_h": "D", "Imax_mmh": "$I_{max}$", "P6h_mm": "$P_{6h}$", "A7d_mm": "$A_{7d}$",
       "NV_VWC0_15": "VWC$_0$ NV 15", "NV_VWC0_60": "VWC$_0$ NV 60", "NV_s0_15": "$s_0$ NV 15",
       "V_dVWC_60": "ΔVWC V 60"}


def save(fig, name):
    fig.savefig(OUT / f"{name}.png"); plt.close(fig); print("saved", name)


def figS1_timeline():
    d = M.rain.resample("D").sum()
    fig, axs = plt.subplots(len(GAUGES), 1, figsize=(W, 7.2), sharex=True, sharey=True)
    for a, g in zip(axs, GAUGES):
        a.bar(d.index, d[g], width=1, color="#4a7fb5")
        for e in EV[EV.gauge == g].itertuples():
            a.axvspan(e.t_start, e.t_end, color=C["ls"] if e.Y else "#d9d9d9", alpha=.45 if e.Y else .6, lw=0, zorder=0)
        M.ls_lines(a)
        a.set_ylabel(f"{g}\n(mm d$^{{-1}}$)", fontsize=8)
    axs[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axs[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    fig.legend(handles=[Patch(color="#4a7fb5", label="daily rainfall"), Patch(color="#d9d9d9", label="rainfall event (E ≥ 10 mm)"),
                        Patch(color=C["ls"], alpha=.45, label="landslide-triggering event"),
                        Line2D([], [], color=C["ls"], ls="--", label="landslide")],
               loc="lower center", ncol=4, bbox_to_anchor=(.5, 0))
    fig.tight_layout(rect=(0, .05, 1, 1))
    save(fig, "FigS1_event_timeline")


def figS2_ED_all():
    R = EV[EV.gauge == M.REF]
    fig, axs = plt.subplots(2, 3, figsize=(W, 4.9), sharex=True, sharey=True)
    for i, site in enumerate(["NV", "V"]):
        for j, d in enumerate(M.SITES[site]["depths_cm"]):
            a = axs[i, j]; cl = R[f"{site}_class_{d}"]
            for k in ["irrelevant", "relevant", "extreme"]:
                m = cl == k
                a.scatter(R.D_h[m], R.E_mm[m], s=18, c=C[k], edgecolor="k", lw=.3, label=k, zorder=3)
            m = R.Y == 1
            a.scatter(R.D_h[m], R.E_mm[m], marker="*", s=150, facecolor="none", edgecolor=C["ls"], lw=1, zorder=4,
                      label="landslide event")
            a.set_xscale("log"); a.set_yscale("log")
            a.set_title(f"({'abcdef'[3 * i + j]}) {site}, {d} cm", loc="left", fontweight="bold", fontsize=9)
    for a in axs[1]: a.set_xlabel("D (h)")
    for a in axs[:, 0]: a.set_ylabel("E (mm)")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.legend(h, l, loc="lower center", ncol=4, bbox_to_anchor=(.5, 0))
    save(fig, "FigS2_ED_classes_all_depths")


def figS3_roc():
    feats = ["E_mm", "D_h", "Imax_mmh", "A7d_mm", "NV_VWC0_15", "NV_VWC0_60", "NV_s0_15", "V_dVWC_60"]
    cols = plt.cm.tab10(np.arange(len(feats)))
    fig, axs = plt.subplots(2, 3, figsize=(W, 4.6), sharex=True, sharey=True)
    for a, g in zip(axs.ravel(), GAUGES):
        D = EV[EV.gauge == g]; T = DT[DT.gauge == g].set_index("feature")
        for c, col in zip(feats, cols):
            fpr, tpr = stats_ls.roc_curve(D[c], D.Y, T.loc[c, "direction"] == "<=")
            a.plot(fpr, tpr, color=col, drawstyle="steps-post", lw=1.1, label=LAB[c])
        a.plot([0, 1], [0, 1], "k:", lw=.7)
        a.set_title(g, loc="left"); a.set_aspect("equal")
    for a in axs[1]: a.set_xlabel("FPR")
    for a in axs[:, 0]: a.set_ylabel("TPR")
    axs[1, 2].axis("off")
    h, l = axs[0, 0].get_legend_handles_labels()
    axs[1, 2].legend(h + [Line2D([], [], color="k", ls=":")], l + ["no skill"], loc="center", ncol=2, title="feature")
    fig.tight_layout()
    save(fig, "FigS3_ROC_curves")


def figS4_windows_mahal():
    win = ["P1h_mm", "P3h_mm", "P6h_mm", "P12h_mm", "P24h_mm", "E_mm", "A3d_mm", "A7d_mm", "A14d_mm", "A30d_mm"]
    lab = ["1 h", "3 h", "6 h", "12 h", "24 h", "E", "3 d", "7 d", "14 d", "30 d"]
    MD = pd.read_pickle(M.P["processed"] / "mahalanobis.pkl")
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.0), gridspec_kw=dict(width_ratios=[1.3, 1]))
    a = axs[0]
    for g in GAUGES:
        t = DT[DT.gauge == g].set_index("feature").loc[win, "AUC_star"].to_numpy()
        a.plot(range(6), t[:6], "-o", ms=3, color=GC[g], label=g)
        a.plot(range(6, 10), t[6:], "-s", ms=3, color=GC[g])
    a.axvline(5.5, color="k", lw=.6)
    a.set_xticks(range(10), lab)
    a.text(2.5, 1.035, "maximum within event", ha="center", fontsize=7.5); a.text(7.5, 1.035, "antecedent", ha="center", fontsize=7.5)
    a.set_ylim(.5, 1.07); a.set_ylabel("AUC*")
    a.set_title("(a) Rainfall accumulation windows", loc="left", fontweight="bold", fontsize=9)
    a.legend(loc="lower left", fontsize=7)
    b = axs[1]; rng = np.random.default_rng(0)
    for k, g in enumerate(GAUGES):
        d = MD[MD.gauge == g]
        b.scatter(k + rng.uniform(-.15, .15, (d.Y == 0).sum()), d.D_M[d.Y == 0], s=6, color=C["nols"])
        b.scatter(np.full((d.Y == 1).sum(), k), d.D_M[d.Y == 1], s=70, marker="*", color=C["ls"], edgecolor="k", lw=.4)
    b.axhline(MD.thr.iloc[0], color="orange", ls="--")
    b.set_xticks(range(len(GAUGES)), GAUGES, rotation=30, ha="right")
    b.set_ylabel("Mahalanobis distance $D_M$")
    b.set_title("(b) Multivariate anomaly", loc="left", fontweight="bold", fontsize=9)
    b.legend(handles=[Line2D([], [], marker="o", ls="", color=C["nols"], ms=3, label="non-triggering"),
                      Line2D([], [], marker="*", ls="", mfc=C["ls"], mec="k", ms=9, label="landslide"),
                      Line2D([], [], color="orange", ls="--", label="$χ^2_3$ 95% threshold")], loc="upper right", fontsize=7)
    fig.tight_layout()
    save(fig, "FigS4_windows_and_mahalanobis")


def figS5_indicator_construction():
    G, combo, ex = M.REF, ["E_mm", "NV_VWC0_15"], "L1"
    need = sorted({f for c in M.CFG["indicator"]["fixed"].values() for f in c} | set(M.CFG["indicator"]["select_rain"])
                  | set(M.CFG["indicator"]["select_water"]))
    D = EV[EV.gauge == G].dropna(subset=need).reset_index(drop=True)
    y = D.Y.to_numpy(int); X = D[combo].to_numpy(float); sg = np.ones(2); neg = X[y == 0]
    sc = ind._score(neg, X, sg); _, tau, _ = ind.build_rule(X, y, sg)
    e = int(np.flatnonzero(D.landslide.str.contains(ex))[0])
    fig, axs = plt.subplots(2, 2, figsize=(W, 5.0))
    labels = ["E (mm)", "VWC$_0$ NV 15 cm (m$^3$ m$^{-3}$)"]
    for j in range(2):
        a = axs[0, j]; v = np.sort(neg[:, j]); pct = lambda x: 100 * np.searchsorted(v, x, side="right") / len(v)
        a.step(v, 100 * np.arange(1, len(v) + 1) / len(v), where="post", color="#455a64", label="non-triggering events")
        a.plot(X[y == 1, j], [pct(x) for x in X[y == 1, j]], "*", color=C["ls"], ms=9, mec="k", mew=.4, label="landslide events")
        p = pct(X[e, j]); a.axhline(p, color=C["ls"], lw=.6, ls=":"); a.axvline(X[e, j], color=C["ls"], lw=.6, ls=":")
        a.annotate(f"L1: {X[e, j]:.3g} → {p:.0f}th pct.", (X[e, j], p), xytext=[(-20, -75), (-150, 8)][j], textcoords="offset points",
                   arrowprops=dict(arrowstyle="->", lw=.6), fontsize=7.5)
        a.set_xlabel(labels[j]); a.set_ylabel("percentile among\nnon-triggering events")
        a.set_title(f"({'ab'[j]}) Step 2: empirical percentile", loc="left", fontweight="bold", fontsize=9)
        a.legend(loc="lower right", fontsize=7)
    a = axs[1, 0]; o = np.argsort(sc)
    a.bar(range(len(sc)), sc[o], color=np.where(y[o] == 1, C["ls"], "#b0bec5"))
    a.axhline(tau, color="k", ls="--", label=f"threshold τ = {tau:.1f}")
    a.set_xticks([]); a.set_xlabel("events sorted by I"); a.set_ylabel("indicator I (0–100)"); a.set_ylim(0, 105)
    a.set_title("(c) Step 3: I = mean of percentiles", loc="left", fontweight="bold", fontsize=9)
    a.legend(handles=[Patch(color="#b0bec5", label="non-triggering"), Patch(color=C["ls"], label="landslide"),
                      Line2D([], [], color="k", ls="--", label=f"τ = {tau:.1f}")], loc="upper left", fontsize=7)
    a = axs[1, 1]; cand = np.unique(sc)
    tpr = np.array([(sc[y == 1] >= c).mean() for c in cand]); fpr = np.array([(sc[y == 0] >= c).mean() for c in cand])
    a.step(cand, tpr, where="post", color="#2e7d32", label="TPR"); a.step(cand, fpr, where="post", color="#e8834c", label="FPR")
    a.step(cand, tpr - fpr, where="post", color="#3f51b5", lw=1.8, label="J = TPR − FPR")
    a.axvline(tau, color="k", ls="--"); a.set_xlabel("threshold τ"); a.set_ylim(-.02, 1.05)
    a.set_title("(d) Step 4: Youden threshold", loc="left", fontweight="bold", fontsize=9)
    a.legend(loc="center left", fontsize=7)
    fig.tight_layout()
    save(fig, "FigS5_indicator_construction")


def figS6_triples():
    tri = pd.read_csv(M.P["tables"] / "T23_indicator_all_3var_pooled.csv")
    pooled = pd.read_csv(M.P["tables"] / "T20_indicator_performance_pooled.csv").set_index("strategy")
    nice = {"rain": "R", "VWC0": "W", "suction": "S"}
    tri["t"] = tri.type.apply(lambda s: " + ".join(nice[x] for x in s.split(" + ")))
    types = tri.groupby("t").TSS.median().sort_values().index.tolist()
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.6), gridspec_kw=dict(width_ratios=[1, 1.35]))
    a = axs[0]
    a.boxplot([tri.TSS[tri.t == t] for t in types], orientation="horizontal", widths=.55, showfliers=True,
              flierprops=dict(markersize=2))
    a.set_yticks(range(1, len(types) + 1), [f"{t} (n={int((tri.t == t).sum())})" for t in types], fontsize=7.5)
    for nm, col, ls in [("E", C["ls"], "--"), ("E + NV VWC0 15", "#2e6b4f", "-.")]:
        a.axvline(pooled.loc[nm, "TSS"], color=col, ls=ls, lw=1, label=f"{nm.replace('NV VWC0 15', 'VWC$_0$ NV 15')}: {pooled.loc[nm, 'TSS']:.2f}")
    a.set_xlabel("pooled TSS (cross-validated)")
    a.set_title("(a) 455 three-variable indicators", loc="left", fontweight="bold", fontsize=9)
    a.legend(loc="upper left", fontsize=7)
    b = axs[1]; top = tri.head(15).iloc[::-1]
    import re
    def lab1(f):
        t = re.sub(r" \((mm|h|mm/h)\)| cm", "", FEAT[f][0])
        t = re.sub(r"\b([PA])_(\w+)", r"$\1_{\2}$", t).replace("I_max", "$I_{max}$")
        return t.replace("VWC0", "VWC$_0$").replace(" s0 ", " $s_0$ ").replace("NV s0", "NV $s_0$")
    lab = lambda c: " + ".join(lab1(f) for f in c.split(" + "))
    b.barh(range(len(top)), top.TSS, color="#5c8f74", label="pooled TSS")
    b.scatter(top.TSS_min, range(len(top)), marker="|", s=80, color="k", label="worst gauge")
    b.set_yticks(range(len(top)), [lab(c) for c in top.combo], fontsize=6.8)
    b.set_xlim(0, 1); b.set_xlabel("TSS")
    b.set_title("(b) Top 15 (selected on the same data)", loc="left", fontweight="bold", fontsize=9)
    b.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    save(fig, "FigS6_all_three_variable_indicators")


if __name__ == "__main__":
    figS1_timeline(); figS2_ED_all(); figS3_roc(); figS4_windows_mahal(); figS5_indicator_construction(); figS6_triples()
