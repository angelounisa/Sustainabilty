"""Explanatory figure: how the landslide indicator is built (worked example).

Usage: python make_indicator_figure.py   (after run_analysis.py / run_indicator.py)
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
import yaml

from src import indicator as ind

CFG = yaml.safe_load(open("config.yaml"))
P = {k: Path(v) for k, v in CFG["paths"].items()}
G, COMBO, EX = "Salerno G.C.", ["E_mm", "NV_VWC0_15"], "L1"     # gauge, combination, example event
LAB = {"E_mm": "E (mm)", "NV_VWC0_15": "VWC0 NV 15 cm (m³/m³)"}
EV = pd.read_pickle(P["processed"] / "events.pkl")
need = sorted({f for c in CFG["indicator"]["fixed"].values() for f in c} | set(CFG["indicator"]["select_rain"])
              | set(CFG["indicator"]["select_water"]))
D = EV[EV.gauge == G].dropna(subset=need).reset_index(drop=True)   # same sample as run_indicator.py
y = D.Y.to_numpy(int)
X = D[COMBO].to_numpy(float)
sg = np.ones(len(COMBO))
neg = X[y == 0]
score = ind._score(neg, X, sg)
ex = int(np.flatnonzero(D.landslide.str.contains(EX))[0])
SCV = pd.read_pickle(P["processed"] / "indicator_scores.pkl")
SCV = SCV[(SCV.gauge == G) & (SCV.strategy == "E + NV VWC0 15")].reset_index(drop=True)
assert (SCV.event_id.to_numpy() == D.event_id.to_numpy()).all()

plt.rcParams.update({"font.size": 9, "savefig.dpi": 300, "savefig.bbox": "tight",
                     "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(15, 10.5))
gs = fig.add_gridspec(3, 4, height_ratios=[.42, 1, 1], hspace=.6, wspace=.35)

# ---- row 0: workflow
ax0 = fig.add_subplot(gs[0, :]); ax0.axis("off"); ax0.set_xlim(0, 100); ax0.set_ylim(0, 10)
steps = ["1  Variabili dell'evento\n(es. E, VWC0 NV 15 cm)",
         "2  Percentile di ogni variabile\nrispetto agli eventi SENZA frana\n(verso critico; suzione invertita)",
         "3  Indicatore I = media\ndei percentili (0–100)",
         "4  Soglia τ = max indice di Youden\n(TPR − FPR) sugli eventi di training",
         "5  Allarme se I ≥ τ\nValidazione leave-one-event-out:\npassi 2–4 rifatti senza l'evento testato"]
for k, t in enumerate(steps):
    x0 = 1 + k * 20
    ax0.add_patch(FancyBboxPatch((x0, 1), 17, 8, boxstyle="round,pad=0.3,rounding_size=1.2",
                                 fc=["#e3f2fd", "#e8f5e9", "#fff8e1", "#fce4ec", "#ede7f6"][k], ec="#555"))
    ax0.text(x0 + 8.5, 5, t, ha="center", va="center", fontsize=8)
    if k < 4:
        ax0.annotate("", (x0 + 19.3, 5), (x0 + 17.6, 5), arrowprops=dict(arrowstyle="-|>", color="#333"))
ax0.set_title(f"Costruzione dell'indicatore frana / no frana — esempio: {G}, combinazione E + VWC0 NV 15 cm, "
              f"evento con frana {EX}", fontsize=11, loc="left")

# ---- row 1: ECDF of each variable among non-landslide events
for j, f in enumerate(COMBO):
    a = fig.add_subplot(gs[1, 2 * j:2 * j + 2])
    v = np.sort(neg[:, j]); e = np.arange(1, len(v) + 1) / len(v) * 100
    a.step(v, e, where="post", color="#455a64", label=f"eventi senza frana (n={len(v)})")
    a.plot(X[y == 1, j], [100 * np.searchsorted(v, x, side="right") / len(v) for x in X[y == 1, j]],
           "*", color="#c62828", ms=12, label="eventi con frana")
    xv = X[ex, j]; pv = 100 * np.searchsorted(v, xv, side="right") / len(v)
    a.annotate(f"{EX}: {LAB[f].split(' (')[0]} = {xv:.3g}\n→ percentile {pv:.0f}", (xv, pv), xytext=(15, -45),
               textcoords="offset points", arrowprops=dict(arrowstyle="->"), fontsize=8.5,
               bbox=dict(fc="white", ec="#c62828"))
    a.axhline(pv, color="#c62828", lw=.6, ls=":"); a.axvline(xv, color="#c62828", lw=.6, ls=":")
    a.set_xlabel(LAB[f]); a.set_ylabel("percentile tra gli eventi senza frana")
    a.set_title(f"Passo 2 — curva cumulata di {LAB[f].split(' (')[0]}", loc="left")
    a.legend(fontsize=7.5, loc="lower right"); a.grid(alpha=.3)

# ---- row 2 left: indicator of all events vs threshold
a = fig.add_subplot(gs[2, :2])
order = np.argsort(score)
a.bar(range(len(score)), score[order], color=np.where(y[order] == 1, "#c62828", "#b0bec5"))
_, tau, _ = ind.build_rule(X, y, sg)
a.axhline(tau, color="k", ls="--", label=f"soglia τ = {tau:.1f} (tutti gli eventi)")
k = int(np.flatnonzero(order == ex)[0])
a.annotate(f"{EX}: I = ({'+'.join(f'{100*np.searchsorted(np.sort(neg[:, j]), X[ex, j], side='right')/len(neg):.0f}' for j in range(2))})/2"
           f" = {score[ex]:.0f}", (k, score[ex]), xytext=(-170, 10), textcoords="offset points",
           arrowprops=dict(arrowstyle="->"), fontsize=8.5, bbox=dict(fc="white", ec="#c62828"))
a.set_xticks([]); a.set_xlabel("eventi ordinati per I"); a.set_ylabel("I (0–100)")
a.set_title("Passo 3 — indicatore di tutti gli eventi (rosso = frana)", loc="left")
a.legend(fontsize=8, loc="upper left"); a.set_ylim(0, 105)

# ---- row 2 right: Youden threshold selection
a = fig.add_subplot(gs[2, 2:])
cand = np.unique(score)
tpr = np.array([(score[y == 1] >= c).mean() for c in cand]); fpr = np.array([(score[y == 0] >= c).mean() for c in cand])
a.step(cand, tpr, where="post", color="#2e7d32", label="TPR = frane rilevate")
a.step(cand, fpr, where="post", color="#e8834c", label="FPR = falsi allarmi / eventi senza frana")
a.step(cand, tpr - fpr, where="post", color="#3f51b5", lw=2, label="J = TPR − FPR (Youden)")
a.axvline(tau, color="k", ls="--")
a.set_xlabel("soglia τ su I"); a.set_ylim(-.02, 1.05)
a.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(.5, -.16), ncol=3, frameon=False); a.grid(alpha=.3)
m = ind.metrics(y, SCV.alarm.to_numpy(), SCV.score.to_numpy())
a.set_title(f"Passo 4 — scelta della soglia (max J)\nvalidazione leave-one-event-out {G}: TP {m['TP']} · FN {m['FN']} · "
            f"FP {m['FP']} · TN {m['TN']} → POD {m['POD']:.2f}, POFD {m['POFD']:.2f}, TSS {m['TSS']:.2f}", loc="left")
fig.savefig(P["figures"] / "Fig18_indicator_construction.png")
(Path("docs/figures") / "Fig18_indicator_construction.png").write_bytes((P["figures"] / "Fig18_indicator_construction.png").read_bytes())
print("saved Fig18", "tau", tau, "I_ex", score[ex])
