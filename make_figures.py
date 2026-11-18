"""All manuscript figures. Run after run_analysis.py.

Usage:  python make_figures.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy import stats

from src import stats_ls

CFG = yaml.safe_load(open("config.yaml"))
P = {k: Path(v) for k, v in CFG["paths"].items()}
F = P["figures"]
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "figure.dpi": 110,
                     "savefig.dpi": 300, "savefig.bbox": "tight", "axes.grid": True, "grid.alpha": .3,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False})
C = {"V": "#2e7d32", "NV": "#b8860b", "ls": "#c62828", "nols": "#7f8c8d",
     "irrelevant": "#bdbdbd", "relevant": "#f2c14e", "extreme": "#d1495b"}
DEPTH_C = {15: "#4c9be8", 30: "#e8834c", 35: "#e8834c", 60: "#5b3fa0"}
GAUGES = list(CFG["rain_gauges"].values())
REF = CFG["hydro"]["reference_gauge"]
SITES = CFG["soil"]["sites"]

rain = pd.read_csv(P["processed"] / "rain_10min_UTC+1.csv.gz", index_col=0, parse_dates=True)
soil = {s: pd.read_csv(P["processed"] / f"soil_{s}_5min_UTC+1.csv.gz", index_col=0, parse_dates=True)
        for s in SITES}
EV = pd.read_pickle(P["processed"] / "events.pkl")
VEL = pd.read_pickle(P["processed"] / "velocity.pkl")
DT = pd.read_pickle(P["processed"] / "discriminant.pkl")
MD = pd.read_pickle(P["processed"] / "mahalanobis.pkl")
FEAT = json.load(open(P["processed"] / "features.json"))
LS = pd.read_csv(P["landslides"])
LS["t"] = pd.to_datetime(LS.datetime_local)


def savefig(fig, name):
    fig.savefig(F / f"{name}.png")
    plt.close(fig)
    print("saved", name)


def gtag(g):
    return g.replace(" ", "_").replace(".", "")


# ---------------------------------------------------------------- Fig.2 (Ch.2) time series
def fig_timeseries():
    fig, ax = plt.subplots(5, 1, figsize=(12, 11), sharex=True,
                           gridspec_kw=dict(height_ratios=[1.2, 1, 1, 1, 1]))
    daily = rain.resample("D").sum()
    ax[0].bar(daily.index, daily[REF], width=1, color="#1f77b4", label=f"{REF} (daily)")
    a2 = ax[0].twinx()
    for g in GAUGES:
        a2.plot(rain[g].cumsum(), lw=1, label=g)
    a2.set_ylabel("cumulative (mm)")
    a2.legend(ncol=5, fontsize=7, loc="upper left")
    a2.grid(False)
    ax[0].set_ylabel("daily rain (mm)")
    for k, site in enumerate(SITES):
        for d in SITES[site]["depths_cm"]:
            ax[1 + 2 * k].plot(soil[site][f"VWC_{d}"], lw=.8, color=DEPTH_C[d], label=f"{d} cm")
            ax[2 + 2 * k].plot(soil[site][f"s_{d}"], lw=.8, color=DEPTH_C[d], label=f"{d} cm")
        ax[1 + 2 * k].set_ylabel(f"VWC (m³/m³)\n{site}")
        ax[2 + 2 * k].set_ylabel(f"suction (kPa)\n{site}")
        ax[2 + 2 * k].set_yscale("log")
        ax[1 + 2 * k].legend(ncol=3, loc="upper left")
    for a in ax:
        for t in LS.t:
            a.axvline(t, color=C["ls"], lw=.8, ls="--")
    for r in LS.itertuples():
        ax[0].annotate(r.id, (r.t, ax[0].get_ylim()[1]), color=C["ls"], fontsize=8, ha="center", va="bottom")
    ax[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.suptitle("Rainfall, volumetric water content and matric suction at the vegetated (V) and "
                 "non-vegetated (NV) verticals — dashed red lines: landslides", y=.995)
    fig.tight_layout()
    savefig(fig, "Fig02_timeseries_rain_VWC_suction")


# ---------------------------------------------------------------- Fig.2b IETD example
def fig_ietd_example():
    g = REF
    t0, t1 = pd.Timestamp("2025-10-20"), pd.Timestamp("2025-12-05")
    r = rain.loc[t0:t1, g]
    ev = EV[(EV.gauge == g) & (EV.t_end >= t0) & (EV.t_start <= t1)]
    fig, ax = plt.subplots(2, 1, figsize=(11, 5), sharex=True)
    h = r.resample("h").sum()
    ax[0].bar(h.index, h, width=1 / 24, color="#1f77b4")
    ax[0].set_ylabel("P (mm/h)")
    cum = pd.Series(0.0, index=r.index)
    for e in ev.itertuples():
        for a in ax:
            a.axvspan(e.t_start, e.t_end, color="#fff2cc", zorder=0)
        seg = r.loc[e.t_start:e.t_end].cumsum()
        ax[1].plot(seg, color="b")
        ax[1].annotate(f"{e.event_id}\nD={e.D_h:.0f} h\nE={e.E_mm:.0f} mm", (e.t_end, e.E_mm),
                       fontsize=7, ha="left", va="center")
        if e.landslide:
            ax[0].annotate(e.landslide, (e.t_start, h.max()), color=C["ls"], fontsize=8)
    ax[1].axhline(CFG["events"]["min_cumulative_mm"], color="r", ls="--", lw=1, label="E = 10 mm")
    ax[1].set_ylabel("E (mm)")
    ax[1].legend()
    ax[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.suptitle(f"IETD event identification (T_s = {CFG['events']['ietd_h']} h, E ≥ 10 mm) — {g}, "
                 "Oct–Dec 2025 (shaded: retained events)")
    fig.tight_layout()
    savefig(fig, "Fig02b_IETD_event_identification_example")


# ---------------------------------------------------------------- Fig.3 index extraction
def fig_index_extraction():
    e = EV[(EV.gauge == REF) & (EV.landslide.str.contains("L1"))].iloc[0]
    ext = pd.Timedelta(hours=CFG["hydro"]["response_extension_h"])
    a0, a1 = e.t_start - pd.Timedelta(hours=12), e.t_end + ext + pd.Timedelta(hours=12)
    fig, ax = plt.subplots(5, 1, figsize=(10, 11), sharex=True)
    h = rain.loc[a0:a1, REF].resample("h").sum()
    ax[0].bar(h.index, h, width=1 / 24, color="#1f77b4")
    ax[0].set_ylabel(f"P (mm/h)\n{REF}")
    ax[0].set_title(f"Event {e.event_id}: D = {e.D_h:.1f} h, E = {e.E_mm:.1f} mm, "
                    f"I_max = {e.Imax_mmh:.1f} mm/h (landslide {e.landslide})")
    for k, site in enumerate(SITES):
        av, asx = ax[1 + 2 * k], ax[2 + 2 * k]
        for d in SITES[site]["depths_cm"]:
            av.plot(soil[site].loc[a0:a1, f"VWC_{d}"], color=DEPTH_C[d], label=f"{d} cm")
            asx.plot(soil[site].loc[a0:a1, f"s_{d}"], color=DEPTH_C[d], label=f"{d} cm")
            v0, vp, tp = e[f"{site}_VWC0_{d}"], e[f"{site}_VWCpk_{d}"], e[f"{site}_tpk_{d}"]
            if pd.notna(v0):
                av.plot(e.t_start, v0, "o", color=DEPTH_C[d], mec="k")
                av.plot(tp, vp, "^", color=DEPTH_C[d], mec="k")
                av.annotate("", (tp, vp), (tp, v0), arrowprops=dict(arrowstyle="<->", color=DEPTH_C[d]))
                av.text(tp, (v0 + vp) / 2, f" ΔVWC={vp - v0:.3f}", color=DEPTH_C[d], fontsize=7)
                asx.plot(e.t_start, e[f"{site}_s0_{d}"], "o", color=DEPTH_C[d], mec="k")
                asx.plot(e[f"{site}_tsmin_{d}"], e[f"{site}_smin_{d}"], "v", color=DEPTH_C[d], mec="k")
        av.set_ylabel(f"VWC (m³/m³)\n{site}")
        asx.set_ylabel(f"suction (kPa)\n{site}")
        asx.set_yscale("log")
        av.legend(ncol=3, fontsize=7, loc="upper left")
    for a in ax:
        a.axvspan(e.t_start, e.t_end, color="#fff2cc", zorder=0)
        a.axvspan(e.t_end, e.t_end + ext, color="#eeeeee", zorder=0)
        a.axvline(LS.set_index("id").t["L1"], color=C["ls"], ls="--")
    ax[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    fig.text(.01, .005, "● antecedent value (mean of 60 min before t_start)   ▲ VWC peak   ▼ min suction   "
             "yellow: rainfall event   grey: +24 h response window", fontsize=8)
    fig.tight_layout()
    savefig(fig, "Fig03_hydrological_index_extraction")


# ---------------------------------------------------------------- Fig.4 E–D classes
def fig_ED_classes():
    R = EV[EV.gauge == REF]
    fig, axs = plt.subplots(2, 3, figsize=(13, 8), sharex=True, sharey=True)
    for i, site in enumerate(SITES):
        for j, d in enumerate(SITES[site]["depths_cm"]):
            a = axs[i, j]
            cl = R[f"{site}_class_{d}"].fillna("no soil data")
            for k, col in [("no soil data", "white"), ("irrelevant", C["irrelevant"]),
                           ("relevant", C["relevant"]), ("extreme", C["extreme"])]:
                m = cl == k
                a.scatter(R.D_h[m], R.E_mm[m], c=col, edgecolor="k", lw=.5, s=40, label=f"{k} ({m.sum()})")
            m = R.Y == 1
            a.scatter(R.D_h[m], R.E_mm[m], marker="*", s=260, facecolor="none", edgecolor=C["ls"], lw=1.5,
                      label="landslide")
            for r in R[m].itertuples():
                a.annotate(r.landslide, (r.D_h, r.E_mm), xytext=(6, 4), textcoords="offset points",
                           color=C["ls"], fontsize=7)
            a.set_xscale("log"); a.set_yscale("log")
            a.set_title(f"{site} — {d} cm")
            a.legend(fontsize=7, loc="upper left")
    for a in axs[-1]:
        a.set_xlabel("D (h)")
    for a in axs[:, 0]:
        a.set_ylabel("E (mm)")
    fig.suptitle(f"Rainfall events in E–D space classified by soil-moisture response (ΔVWC) — {REF}")
    fig.tight_layout()
    savefig(fig, "Fig04_ED_space_event_classes")


# ---------------------------------------------------------------- Fig.5 infiltration
def fig_infiltration():
    V = VEL[VEL.gauge == REF]
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.6))
    groups = [("V", "15-35"), ("NV", "15-30"), ("V", "35-60"), ("NV", "30-60"), ("V", "15-60"), ("NV", "15-60")]
    for k, metric in enumerate(["v_peak_cmh", "v_onset_cmh"]):
        data = [V[(V.site == s) & (V.pair == p)][metric].dropna() for s, p in groups]
        bp = ax[k].boxplot(data, patch_artist=True, widths=.6, showfliers=False)
        for patch, (s, _) in zip(bp["boxes"], groups):
            patch.set_facecolor(C[s]); patch.set_alpha(.5)
        rng = np.random.default_rng(0)
        for i, (dd, (s, p)) in enumerate(zip(data, groups)):
            cls = V[(V.site == s) & (V.pair == p)].dropna(subset=[metric]).class_lower
            ax[k].scatter(i + 1 + rng.uniform(-.15, .15, len(dd)), dd, s=14,
                          c=[C[c] for c in cls], edgecolor="k", lw=.4, zorder=3)
        ax[k].set_xticks(range(1, 7), [f"{s}\n{p} cm" for s, p in groups])
        ax[k].set_yscale("log")
        ax[k].set_ylabel("v (cm/h)")
        ax[k].set_title("peak-lag velocity Δz/Δt_peak" if k == 0 else "wetting-front (onset) velocity")
    # dVWC V vs NV paired
    R = EV[EV.gauge == REF]
    for dv, dn in [(15, 15), (35, 30), (60, 60)]:
        ax[2].scatter(R[f"NV_dVWC_{dn}"], R[f"V_dVWC_{dv}"], s=22, color=DEPTH_C[dv], edgecolor="k", lw=.4,
                      label=f"V {dv} / NV {dn} cm")
        m = R.Y == 1
        ax[2].scatter(R[f"NV_dVWC_{dn}"][m], R[f"V_dVWC_{dv}"][m], marker="*", s=150, facecolor="none",
                      edgecolor=C["ls"])
    lim = [0, .22]
    ax[2].plot(lim, lim, "k--", lw=.8, label="1:1")
    ax[2].fill_between(lim, 0, lim, color=C["V"], alpha=.07, label="V < NV (buffering)")
    ax[2].set_xlim(lim); ax[2].set_ylim(lim)
    ax[2].set_xlabel("ΔVWC NV (m³/m³)"); ax[2].set_ylabel("ΔVWC V (m³/m³)")
    ax[2].set_title("event ΔVWC: vegetated vs non-vegetated (★ landslide)")
    ax[2].legend(fontsize=7)
    fig.suptitle(f"Infiltration dynamics, vegetated (V) vs non-vegetated (NV) — events of {REF} "
                 "(points coloured by class of the deeper sensor)")
    fig.tight_layout()
    savefig(fig, "Fig05_infiltration_velocity_V_vs_NV")


# ---------------------------------------------------------------- Fig.6 landslide timeline
def fig_timeline():
    daily = rain.resample("D").sum()
    fig, ax = plt.subplots(len(GAUGES), 1, figsize=(12, 9), sharex=True, sharey=True)
    for a, g in zip(ax, GAUGES):
        a.bar(daily.index, daily[g], width=1, color="#1f77b4")
        for e in EV[EV.gauge == g].itertuples():
            col = C["ls"] if e.Y else "#cfd8dc"
            a.axvspan(e.t_start, e.t_end, color=col, alpha=.35 if e.Y else .25, lw=0)
            if e.Y:
                a.annotate(f"{e.landslide}\nE={e.E_mm:.0f}", (e.t_end, 80), fontsize=7, color=C["ls"])
        for t in LS.t:
            a.axvline(t, color=C["ls"], lw=.8, ls="--")
        a.set_ylabel(f"{g}\nmm/day")
    ax[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.suptitle("Daily rainfall at the five gauges, rainfall events (grey) and landslide-triggering events (red)")
    fig.tight_layout()
    savefig(fig, "Fig06_landslide_timeline")


def fig_patton_hourly():
    """Hourly rainfall 3 days before / 1 day after each landslide (cf. Patton et al. 2023, Fig. 2)."""
    fig, ax = plt.subplots(1, len(LS), figsize=(15, 3.8), sharey=True)
    for a, r in zip(ax, LS.itertuples()):
        a0, a1 = r.t - pd.Timedelta(days=3), r.t + pd.Timedelta(days=1)
        for g in GAUGES:
            h = rain.loc[a0:a1, g].resample("h").sum()
            a.step((h.index - r.t) / pd.Timedelta(hours=1), h.cumsum(), where="post", label=g)
        a.axvline(0, color=C["ls"], ls="--")
        a.axvspan(-r.uncertainty_h, r.uncertainty_h, color=C["ls"], alpha=.1)
        a.set_title(f"{r.id} — {r.t:%d %b %Y %H:%M}")
        a.set_xlabel("hours from landslide")
    ax[0].set_ylabel("cumulative rainfall (mm)")
    ax[0].legend(fontsize=7)
    fig.suptitle("Cumulative rainfall around each landslide (shaded: timing uncertainty)")
    fig.tight_layout()
    savefig(fig, "Fig06b_rainfall_around_landslides")


# ---------------------------------------------------------------- Fig.7 boxplots
BOX = [("D_h", "D (h)"), ("E_mm", "E (mm)"), ("Imax_mmh", "I_max (mm/h)"), ("NV_VWC0_60", "NV VWC0 60 cm"),
       ("V_VWC0_60", "V VWC0 60 cm"), ("NV_s0_15", "NV s0 15 cm (kPa)"), ("V_s0_15", "V s0 15 cm (kPa)"),
       ("NV_dVWC_60", "NV ΔVWC 60 cm"), ("V_dVWC_60", "V ΔVWC 60 cm")]


def fig_boxplots(g):
    D = EV[EV.gauge == g]
    T = DT[DT.gauge == g].set_index("feature")
    fig, axs = plt.subplots(1, len(BOX), figsize=(17, 3.8))
    rng = np.random.default_rng(1)
    for a, (c, lab) in zip(axs, BOX):
        x0, x1 = D[c][D.Y == 0].dropna(), D[c][D.Y == 1].dropna()
        bp = a.boxplot([x0, x1], patch_artist=True, widths=.55, showfliers=False)
        for p_, col in zip(bp["boxes"], [C["nols"], C["ls"]]):
            p_.set_facecolor(col); p_.set_alpha(.45)
        a.scatter(1 + rng.uniform(-.12, .12, len(x0)), x0, s=10, color=C["nols"], zorder=3)
        a.scatter(2 + rng.uniform(-.12, .12, len(x1)), x1, s=60, marker="*", color=C["ls"], zorder=3)
        a.set_xticks([1, 2], ["no LS", "LS"])
        if c.endswith(("s0_15",)):
            a.set_yscale("log")
        p = T.loc[c, "p"]
        star = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "n.s."
        a.set_title(f"{lab}\nAUC*={T.loc[c, 'AUC_star']:.2f}  p={p:.3f} {star}", fontsize=8)
    fig.suptitle(f"{g}: distribution of predictive features, landslide-triggering vs non-triggering events "
                 f"(n_LS={int(D.Y.sum())}, n_noLS={int((D.Y == 0).sum())}; p: Mann–Whitney, unadjusted)")
    fig.tight_layout()
    savefig(fig, f"Fig07_boxplots_{gtag(g)}")


# ---------------------------------------------------------------- Fig.8 ROC
def fig_roc():
    feats = ["E_mm", "D_h", "Imax_mmh", "P6h_mm", "NV_VWC0_60", "NV_s0_15", "V_dVWC_60", "NV_dVWC_60"]
    cols = plt.cm.tab10(np.arange(len(feats)))
    fig, axs = plt.subplots(1, len(GAUGES), figsize=(18, 4), sharey=True)
    for a, g in zip(axs, GAUGES):
        D = EV[EV.gauge == g]
        T = DT[DT.gauge == g].set_index("feature")
        for c, col in zip(feats, cols):
            lower = T.loc[c, "direction"] == "<="
            fpr, tpr = stats_ls.roc_curve(D[c], D.Y, lower)
            a.plot(fpr, tpr, color=col, lw=1.4, drawstyle="steps-post",
                   label=f"{FEAT[c][0]} ({T.loc[c, 'AUC_star']:.2f})")
        a.plot([0, 1], [0, 1], "k:", lw=.8)
        a.set_title(g); a.set_xlabel("FPR"); a.set_aspect("equal")
        a.legend(fontsize=6, loc="lower right")
    axs[0].set_ylabel("TPR (recall)")
    fig.suptitle("ROC curves of single predictors (AUC* in brackets)")
    fig.tight_layout()
    savefig(fig, "Fig08_ROC_curves")


# ---------------------------------------------------------------- Fig.9 E–VWC0 KDE
def fig_kde():
    xcol = "NV_VWC0_60"
    fig, axs = plt.subplots(1, len(GAUGES), figsize=(18, 4), sharex=True)
    for a, g in zip(axs, GAUGES):
        D = EV[EV.gauge == g].dropna(subset=[xcol])
        n = D[D.Y == 0]
        kde = stats.gaussian_kde(np.vstack([n[xcol], n.E_mm]), bw_method=CFG["stats"]["kde_bw"])
        xx, yy = np.meshgrid(np.linspace(.08, .36, 120), np.linspace(0, D.E_mm.max() * 1.15, 120))
        zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
        a.contourf(xx, yy, zz, levels=8, cmap="Blues", alpha=.7)
        a.scatter(n[xcol], n.E_mm, s=12, color="#555", label="no landslide")
        l = D[D.Y == 1]
        a.scatter(l[xcol], l.E_mm, marker="*", s=220, color=C["ls"], edgecolor="k", label="landslide")
        for r in l.itertuples():
            a.annotate(r.landslide, (getattr(r, xcol), r.E_mm), xytext=(5, 5), textcoords="offset points",
                       fontsize=7)
        a.set_title(g); a.set_xlabel("antecedent VWC 60 cm, NV (m³/m³)")
    axs[0].set_ylabel("E (mm)"); axs[0].legend(fontsize=7, loc="upper left")
    fig.suptitle("Landslide events in the E – antecedent VWC(60 cm) space; contours: KDE of non-triggering events")
    fig.tight_layout()
    savefig(fig, "Fig09_E_vs_VWC0_60_KDE")


# ---------------------------------------------------------------- Fig.10 profiles
def fig_profiles():
    g = REF
    D = EV[EV.gauge == g]
    fig, axs = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
    for a, site in zip(axs, SITES):
        dd = SITES[site]["depths_cm"]
        n = D[D.Y == 0]
        med = [n[f"{site}_VWC0_{d}"].median() for d in dd]
        q1 = [n[f"{site}_VWC0_{d}"].quantile(.25) for d in dd]
        q3 = [n[f"{site}_VWC0_{d}"].quantile(.75) for d in dd]
        a.fill_betweenx(dd, q1, q3, color="b", alpha=.12, label="IQR no-landslide")
        a.plot(med, dd, "b--o", label="median no-landslide")
        for r in D[D.Y == 1].itertuples():
            a.plot([getattr(r, f"{site}_VWC0_{d}") for d in dd], dd, "-*", color=C["ls"], ms=10)
            a.annotate(r.landslide, (getattr(r, f"{site}_VWC0_{dd[-1]}"), dd[-1]), xytext=(4, -10),
                       textcoords="offset points", fontsize=7, color=C["ls"])
        a.plot([], [], "-*", color=C["ls"], label="landslide events")
        a.set_title(f"{site}: pre-event VWC profile"); a.set_xlabel("VWC0 (m³/m³)")
        a.legend(fontsize=7)
    axs[0].invert_yaxis(); axs[0].set_ylabel("depth (cm)")
    fig.suptitle(f"Antecedent VWC by depth — landslide events vs non-triggering events ({g})")
    fig.tight_layout()
    savefig(fig, "Fig10_antecedent_VWC_profiles")


# ---------------------------------------------------------------- Fig.11 synthesis
def fig_synthesis():
    keep = [k for k in FEAT if not k.startswith(("V_VWCpk", "NV_VWCpk"))]
    M = DT[DT.feature.isin(keep)].pivot(index="feature", columns="gauge", values="AUC_star")[GAUGES]
    order = M.mean(axis=1).sort_values().index
    M = M.loc[order]
    Pm = DT.pivot(index="feature", columns="gauge", values="p").loc[order, GAUGES]
    RB = DT.pivot(index="feature", columns="gauge", values="RB").loc[order, GAUGES]
    fig, ax = plt.subplots(1, 2, figsize=(14, 11), gridspec_kw=dict(width_ratios=[1.2, 1]))
    im = ax[0].imshow(M.to_numpy(), cmap="RdYlGn", vmin=.5, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v, p = M.iat[i, j], Pm.iat[i, j]
            if pd.notna(v):
                ax[0].text(j, i, f"{v:.2f}{'*' if p < .05 else ''}", ha="center", va="center", fontsize=7)
    ax[0].set_yticks(range(len(order)), [FEAT[k][0] for k in order])
    ax[0].set_xticks(range(len(GAUGES)), GAUGES, rotation=30)
    ax[0].grid(False)
    plt.colorbar(im, ax=ax[0], label="AUC*", shrink=.6)
    ax[0].set_title("AUC* per feature and gauge (* p<0.05 unadjusted)")
    y = np.arange(len(order))
    for k, g in enumerate(GAUGES):
        ax[1].scatter(RB[g].abs(), y + (k - 2) * .12, s=18, label=g)
    ax[1].scatter(RB.abs().mean(axis=1), y, marker="|", s=200, color="k", label="mean")
    ax[1].axvline(.5, color="orange", ls=":"); ax[1].axvline(.7, color="r", ls=":")
    ax[1].set_yticks(y, [])
    ax[1].set_ylim(len(order) - .5, -.5)   # same row order as the heatmap
    ax[1].set_xlabel("|rank-biserial r|  (0.5 medium, 0.7 large)")
    ax[1].legend(fontsize=7, loc="lower right")
    ax[1].set_title("effect size")
    fig.suptitle("Discriminant power synthesis (features sorted by mean AUC* across gauges)")
    fig.tight_layout()
    savefig(fig, "Fig11_discriminant_synthesis")


def fig_mahalanobis_windows():
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.3))
    for k, g in enumerate(GAUGES):
        d = MD[MD.gauge == g]
        rng = np.random.default_rng(k)
        ax[0].scatter(k - .15 + rng.uniform(-.07, .07, (d.Y == 0).sum()), d.D_M[d.Y == 0], s=10, color=C["nols"])
        ax[0].scatter(k + .15 + np.zeros((d.Y == 1).sum()), d.D_M[d.Y == 1], s=110, marker="*", color=C["ls"],
                      edgecolor="k")
        for r in d[d.Y == 1].itertuples():
            ax[0].annotate(r.landslide, (k + .2, r.D_M), fontsize=6)
    ax[0].axhline(MD.thr.iloc[0], color="orange", ls="--", label=f"χ²₃ 95% threshold ({MD.thr.iloc[0]:.2f})")
    ax[0].set_xticks(range(len(GAUGES)), GAUGES)
    ax[0].set_ylabel("Mahalanobis distance D_M")
    ax[0].set_title("Multivariate anomaly (E, I_max, NV VWC0 60 cm)")
    ax[0].legend(fontsize=7)
    win = ["P1h_mm", "P3h_mm", "P6h_mm", "P12h_mm", "P24h_mm", "E_mm", "A3d_mm", "A7d_mm", "A14d_mm", "A30d_mm"]
    lab = ["1 h", "3 h", "6 h", "12 h", "24 h", "event E", "3 d ant.", "7 d ant.", "14 d ant.", "30 d ant."]
    for g in GAUGES:
        t = DT[DT.gauge == g].set_index("feature").loc[win, "AUC_star"]
        ln, = ax[1].plot(lab[:6], t.to_numpy()[:6], "-o", ms=4, label=g)
        ax[1].plot(lab[6:], t.to_numpy()[6:], "-o", ms=4, color=ln.get_color())
    ax[1].axvline(5.5, color="k", lw=.6)
    ax[1].set_ylabel("AUC*"); ax[1].set_ylim(.5, 1.02)
    ax[1].set_title("Discrimination vs rainfall accumulation window (cf. Patton et al., 2023)")
    ax[1].legend(fontsize=7)
    plt.setp(ax[1].get_xticklabels(), rotation=30)
    fig.tight_layout()
    savefig(fig, "Fig12_mahalanobis_and_accumulation_windows")


if __name__ == "__main__":
    fig_timeseries()
    fig_ietd_example()
    fig_index_extraction()
    fig_ED_classes()
    fig_infiltration()
    fig_timeline()
    fig_patton_hourly()
    for g in GAUGES:
        fig_boxplots(g)
    fig_roc()
    fig_kde()
    fig_profiles()
    fig_synthesis()
    fig_mahalanobis_windows()
