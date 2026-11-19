"""Publication figures for the manuscript (paper/figures, 600 dpi, Times-metric serif font).

Usage:  python make_paper_figures.py   (after run_analysis.py and run_indicator.py)
"""
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import yaml
from scipy import stats

CFG = yaml.safe_load(open("config.yaml"))
P = {k: Path(v) for k, v in CFG["paths"].items()}
OUT = Path("paper/figures"); OUT.mkdir(parents=True, exist_ok=True)
# Liberation Serif is metric-compatible with Times New Roman
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8, "legend.title_fontsize": 8,
    "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    "axes.grid": True, "grid.alpha": .25, "grid.linewidth": .5, "axes.linewidth": .7,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": True,
    "legend.framealpha": .92, "legend.edgecolor": "#bbbbbb", "lines.linewidth": 1.0})
W = 6.5   # full text width (in)
C = {"V": "#2e7d32", "NV": "#b07a0a", "ls": "#c62828", "nols": "#8a8f93",
     "irrelevant": "#c9c9c9", "relevant": "#f2c14e", "extreme": "#d1495b"}
DC = {15: "#1f77b4", 30: "#ff7f0e", 35: "#ff7f0e", 60: "#6a3d9a"}
GAUGES = list(CFG["rain_gauges"].values())
GC = dict(zip(GAUGES, ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#1f78b4"]))
REF = CFG["hydro"]["reference_gauge"]
SITES = CFG["soil"]["sites"]

rain = pd.read_csv(P["processed"] / "rain_10min_UTC+1.csv.gz", index_col=0, parse_dates=True)
soil = {s: pd.read_csv(P["processed"] / f"soil_{s}_5min_UTC+1.csv.gz", index_col=0, parse_dates=True) for s in SITES}
EV = pd.read_pickle(P["processed"] / "events.pkl")
VEL = pd.read_pickle(P["processed"] / "velocity.pkl")
DT = pd.read_pickle(P["processed"] / "discriminant.pkl")
LS = pd.read_csv(P["landslides"]); LS["t"] = pd.to_datetime(LS.datetime_local)
IND = json.load(open("docs/indicator.json"))


def save(fig, name):
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)
    print("saved", name)


def panel(ax, letter, x=-0.09, y=1.04):
    ax.text(x, y, f"({letter})", transform=ax.transAxes, fontweight="bold", fontsize=10, va="bottom")


def ls_lines(ax, label=False):
    for r in LS.itertuples():
        ax.axvline(r.t, color=C["ls"], lw=.8, ls="--", zorder=1)
        if label:
            ha = {"L3": "right", "L4": "left"}.get(r.id, "center")
            ax.text(r.t, 1.01, r.id, transform=ax.get_xaxis_transform(), color=C["ls"], ha=ha,
                    va="bottom", fontsize=8)


# ------------------------------------------------------------------ Fig 2
def fig2():
    fig, ax = plt.subplots(5, 1, figsize=(W, 8.4), sharex=True, gridspec_kw=dict(height_ratios=[1.25, 1, 1, 1, 1]))
    d = rain.resample("D").sum()
    ax[0].bar(d.index, d[REF], width=1, color="#4a7fb5", label=f"daily rainfall, {REF}")
    ax[0].set_ylabel("daily rainfall (mm)")
    a2 = ax[0].twinx(); a2.grid(False)
    for g in GAUGES:
        a2.plot(rain[g].cumsum(), color=GC[g], lw=1.1, label=f"cumulative, {g}")
    a2.set_ylabel("cumulative (mm)")
    a2.spines["right"].set_visible(True)
    h1, l1 = ax[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    ax[0].set_ylim(0, 115); a2.set_ylim(-50, 3900)
    ax[0].legend(h1 + h2, l1 + l2, loc="upper left", ncol=3, fontsize=7)
    ls_lines(ax[0], label=True)
    rows = [("NV", "VWC", "VWC (m$^3$ m$^{-3}$)"), ("NV", "s", "suction (kPa)"),
            ("V", "VWC", "VWC (m$^3$ m$^{-3}$)"), ("V", "s", "suction (kPa)")]
    for k, (site, var, lab) in enumerate(rows):
        a = ax[k + 1]
        for dpt in SITES[site]["depths_cm"]:
            a.plot(soil[site][f"{var}_{dpt}"], color=DC[dpt], lw=.8, label=f"{dpt} cm")
        a.set_ylabel(f"{site}: {lab}")
        if var == "s":
            a.set_yscale("log"); a.set_ylim(.08, 4e4)
        a.text(.995, .96, f"{'non-vegetated (NV)' if site == 'NV' else 'vegetated (V)'} site", transform=a.transAxes,
               ha="right", va="top", fontsize=8, bbox=dict(fc="white", ec="#bbbbbb", lw=.5))
        if k in (0, 2):
            a.set_ylim(top=a.get_ylim()[1] * 1.3)
            a.legend(loc="upper left", ncol=3, fontsize=7.5)
        ls_lines(a)
    ax[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    for i, a in enumerate(ax):
        panel(a, "abcde"[i], x=-0.1)
    fig.align_ylabels(ax)
    fig.subplots_adjust(left=.1, right=.9, top=.96, bottom=.06, hspace=.28)
    save(fig, "Fig02_timeseries")


# ------------------------------------------------------------------ Fig 3
def fig3():
    fig = plt.figure(figsize=(W + 1.3, 7.6))
    gs = fig.add_gridspec(4, 1, height_ratios=[1.1, .7, 1, 1], hspace=.38)
    # (a) IETD example
    a = fig.add_subplot(gs[0])
    t0, t1 = pd.Timestamp("2025-10-18"), pd.Timestamp("2025-12-05")
    h = rain.loc[t0:t1, REF].resample("h").sum()
    ev = EV[(EV.gauge == REF) & (EV.t_end >= t0) & (EV.t_start <= t1)]
    a.bar(h.index, h, width=1 / 24, color="#4a7fb5", label="hourly rainfall")
    for k, e in enumerate(ev.sort_values("t_start").itertuples()):
        a.axvspan(e.t_start, e.t_end, color="#ffe9a8", zorder=0, lw=0)
        a.text(e.t_start + (e.t_end - e.t_start) / 2, h.max() * (1.04 + .2 * (k % 2)),
               f"{e.E_mm:.0f} mm / {e.D_h:.0f} h", ha="center", va="bottom", fontsize=6.5)
    ls_lines(a)
    a.set_xlim(t0, t1)
    a.set_ylim(0, h.max() * 1.75)
    a.set_ylabel("P (mm h$^{-1}$)")
    a.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    a.legend(handles=[Patch(color="#4a7fb5", label=f"hourly rainfall, {REF}"),
                      Patch(color="#ffe9a8", label="rainfall event (IETD = 24 h, E ≥ 10 mm)"),
                      Line2D([], [], color=C["ls"], ls="--", label="landslide")], loc="upper left",
             bbox_to_anchor=(1.01, 1), fontsize=7, title="labels: E / D")
    panel(a, "a")
    # (b-d) index extraction, event of L1, NV site
    e = EV[(EV.gauge == REF) & EV.landslide.str.contains("L1")].iloc[0]
    ext = pd.Timedelta(hours=CFG["hydro"]["response_extension_h"])
    w0, w1 = e.t_start - pd.Timedelta(hours=10), e.t_end + ext + pd.Timedelta(hours=4)
    ab = fig.add_subplot(gs[1]); ac = fig.add_subplot(gs[2], sharex=ab); ad = fig.add_subplot(gs[3], sharex=ab)
    hh = rain.loc[w0:w1, REF].resample("h").sum()
    ab.bar(hh.index, hh, width=1 / 24, color="#4a7fb5")
    ab.set_ylabel("P (mm h$^{-1}$)")
    ab.set_title(f"      Event of 25–28 Oct 2025 ({REF}): D = {e.D_h:.0f} h, E = {e.E_mm:.1f} mm, "
                 f"$I_{{max}}$ = {e.Imax_mmh:.1f} mm h$^{{-1}}$ — landslide L1", loc="left")
    for dpt in SITES["NV"]["depths_cm"]:
        s = soil["NV"].loc[w0:w1]
        ac.plot(s[f"VWC_{dpt}"], color=DC[dpt], label=f"{dpt} cm")
        ad.plot(s[f"s_{dpt}"], color=DC[dpt], label=f"{dpt} cm")
        v0, vp, tp = e[f"NV_VWC0_{dpt}"], e[f"NV_VWCpk_{dpt}"], e[f"NV_tpk_{dpt}"]
        ac.plot(e.t_start, v0, "o", color=DC[dpt], mec="k", mew=.5, ms=5)
        ac.plot(tp, vp, "^", color=DC[dpt], mec="k", mew=.5, ms=6)
        ac.annotate("", (tp, vp), (tp, v0), arrowprops=dict(arrowstyle="<->", color=DC[dpt], lw=.8))
        ac.text(tp + pd.Timedelta(hours=7), v0 + (vp - v0) * .45, f"ΔVWC = {vp - v0:.3f}", color=DC[dpt], fontsize=7)
        ad.plot(e.t_start, e[f"NV_s0_{dpt}"], "o", color=DC[dpt], mec="k", mew=.5, ms=5)
        ad.plot(e[f"NV_tsmin_{dpt}"], e[f"NV_smin_{dpt}"], "v", color=DC[dpt], mec="k", mew=.5, ms=6)
    ad.set_yscale("log")
    ac.set_ylabel("VWC (m$^3$ m$^{-3}$)"); ad.set_ylabel("suction (kPa)")
    mk = [Line2D([], [], marker="o", ls="", mfc="w", mec="k", label="antecedent value (VWC$_0$, $s_0$)"),
          Line2D([], [], marker="^", ls="", mfc="w", mec="k", label="VWC$_{peak}$"),
          Line2D([], [], marker="v", ls="", mfc="w", mec="k", label="$s_{min}$")]
    h_, l_ = ac.get_legend_handles_labels()
    ac.legend(h_ + mk[:2], l_ + [m.get_label() for m in mk[:2]], loc="upper left", bbox_to_anchor=(1.01, 1),
              fontsize=7, title="NV site")
    h_, l_ = ad.get_legend_handles_labels()
    ad.legend(h_ + [mk[0], mk[2]], l_ + [mk[0].get_label(), mk[2].get_label()], loc="upper left",
              bbox_to_anchor=(1.01, 1), fontsize=7, title="NV site")
    ab.legend(handles=[Patch(color="#ffe9a8", label="rainfall event"),
                       Patch(color="#ececec", label="+24 h response\nwindow"),
                       Line2D([], [], color=C["ls"], ls="--", label="landslide L1")], loc="upper left",
              bbox_to_anchor=(1.01, 1), fontsize=7)
    for a_ in (ab, ac, ad):
        a_.axvspan(e.t_start, e.t_end, color="#ffe9a8", zorder=0, lw=0)
        a_.axvspan(e.t_end, e.t_end + ext, color="#ececec", zorder=0, lw=0)
        a_.axvline(LS.set_index("id").t["L1"], color=C["ls"], ls="--", lw=.8)
    plt.setp(ab.get_xticklabels(), visible=False); plt.setp(ac.get_xticklabels(), visible=False)
    ad.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M"))
    for a_, l in zip((ab, ac, ad), "bcd"):
        panel(a_, l)
    save(fig, "Fig03_events_and_indices")


# ------------------------------------------------------------------ Fig 4
def fig4():
    R = EV[EV.gauge == REF]
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.1), sharey=True)
    for a, (site, d) in zip(axs, [("NV", 60), ("V", 60)]):
        cl = R[f"{site}_class_{d}"]
        for k in ["irrelevant", "relevant", "extreme"]:
            m = cl == k
            a.scatter(R.D_h[m], R.E_mm[m], s=28, c=C[k], edgecolor="k", lw=.4, label=f"{k} (n = {m.sum()})", zorder=3)
        m = R.Y == 1
        a.scatter(R.D_h[m], R.E_mm[m], marker="*", s=230, facecolor="none", edgecolor=C["ls"], lw=1.2,
                  label="landslide event", zorder=4)
        for r in R[m].itertuples():
            a.annotate(r.landslide.replace(",", "+"), (r.D_h, r.E_mm), xytext=(7, -3), textcoords="offset points",
                       color=C["ls"], fontsize=7.5)
        a.set_xscale("log"); a.set_yscale("log")
        a.set_xlabel("duration D (h)")
        a.set_title(f"{'Non-vegetated' if site == 'NV' else 'Vegetated'} site, {d} cm", loc="center")
        a.set_xlim(.2, 900)
        a.legend(loc="upper left", fontsize=7)
    axs[0].set_ylabel("cumulative rainfall E (mm)")
    panel(axs[0], "a", x=-.13); panel(axs[1], "b", x=-.06)
    fig.tight_layout()
    save(fig, "Fig04_ED_classes")


# ------------------------------------------------------------------ Fig 5
def fig5():
    V = VEL[VEL.gauge == REF]
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.3), gridspec_kw=dict(width_ratios=[1.45, 1]))
    a = axs[0]
    layers = [("0–15 cm", "0-15", "0-15"), ("15–30/35\ncm", "15-35", "15-30"),
              ("30/35–60\ncm", "35-60", "30-60"), ("15–60 cm", "15-60", "15-60")]
    T7 = pd.read_csv(P["tables"] / "T07_infiltration_V_vs_NV.csv")
    T7 = T7[T7.metric == "v_peak_cmh"].reset_index(drop=True)
    rng = np.random.default_rng(3)
    for i, (lab, pv, pn) in enumerate(layers):
        for site, pair, off in [("V", pv, -.18), ("NV", pn, .18)]:
            x = V[(V.site == site) & (V.pair == pair)].v_peak_cmh.dropna()
            bp = a.boxplot([x], positions=[i + off], widths=.3, patch_artist=True, showfliers=False,
                           medianprops=dict(color="k"))
            bp["boxes"][0].set(facecolor=C[site], alpha=.45)
            a.scatter(i + off + rng.uniform(-.07, .07, len(x)), x, s=8, color=C[site], edgecolor="k", lw=.3, zorder=3)
        p = T7.MWU_p[i]
        a.text(i, 420, f"p = {p:.3f}" if p >= .001 else "p < 0.001", ha="center", fontsize=7.5,
               fontweight="bold" if p < .05 else "normal")
    a.set_yscale("log"); a.set_ylim(.08, 900)
    a.set_xticks(range(len(layers)), [l for l, _, _ in layers])
    a.set_ylabel("infiltration velocity $v = Δz/Δt_{peak}$ (cm h$^{-1}$)")
    a.legend(handles=[Patch(color=C["V"], alpha=.6, label="vegetated (V)"),
                      Patch(color=C["NV"], alpha=.6, label="non-vegetated (NV)")], loc="lower right")
    panel(a, "a", x=-.14)
    b = axs[1]
    R = EV[EV.gauge == REF]
    for dv, dn, mkr in [(15, 15, "o"), (35, 30, "s"), (60, 60, "D")]:
        b.scatter(R[f"NV_dVWC_{dn}"], R[f"V_dVWC_{dv}"], s=18, marker=mkr, color=DC[dv], edgecolor="k", lw=.3,
                  label=f"V {dv} cm vs NV {dn} cm")
    lim = [-.005, .22]
    b.plot(lim, lim, "k--", lw=.8, label="1:1 line")
    b.set_xlim(lim); b.set_ylim(lim)
    b.set_xlabel("ΔVWC non-vegetated (m$^3$ m$^{-3}$)"); b.set_ylabel("ΔVWC vegetated (m$^3$ m$^{-3}$)")
    b.legend(loc="upper left", fontsize=7)
    panel(b, "b", x=-.2)
    fig.tight_layout()
    save(fig, "Fig05_infiltration")


# ------------------------------------------------------------------ Fig 6
def fig6():
    fig, axs = plt.subplots(1, 4, figsize=(W, 2.6), sharey=True)
    for a, r, l in zip(axs, LS.itertuples(), "abcd"):
        a0, a1 = r.t - pd.Timedelta(days=3), r.t + pd.Timedelta(days=1)
        for g in GAUGES:
            h = rain.loc[a0:a1, g].resample("h").sum()
            a.step((h.index - r.t) / pd.Timedelta(hours=1), h.cumsum(), where="post", color=GC[g], lw=1.1, label=g)
        a.axvline(0, color=C["ls"], ls="--", lw=.8)
        a.axvspan(-r.uncertainty_h, r.uncertainty_h, color=C["ls"], alpha=.12, lw=0)
        a.set_title(f"({l}) {r.id}: {r.t:%d %b %Y}", loc="left", fontweight="bold", fontsize=9)
        a.set_xlabel("hours from landslide")
        a.set_xticks([-72, -48, -24, 0, 24])
    axs[0].set_ylabel("cumulative rainfall (mm)")
    h, l = axs[0].get_legend_handles_labels()
    h += [Patch(color=C["ls"], alpha=.25, label="timing uncertainty")]
    fig.tight_layout(rect=(0, .1, 1, 1))
    fig.legend(h, l + ["timing uncertainty"], loc="lower center", ncol=6, bbox_to_anchor=(.5, 0), fontsize=7.5)
    save(fig, "Fig06_rainfall_around_landslides")


# ------------------------------------------------------------------ Fig 7
def fig7():
    g = REF
    D = EV[EV.gauge == g]
    T = DT[DT.gauge == g].set_index("feature")
    feats = [("D_h", "D (h)"), ("E_mm", "E (mm)"), ("Imax_mmh", "$I_{max}$ (mm h$^{-1}$)"),
             ("A7d_mm", "$A_{7d}$ (mm)"), ("NV_VWC0_15", "VWC$_0$ NV 15 cm"),
             ("NV_VWC0_60", "VWC$_0$ NV 60 cm"), ("NV_s0_15", "$s_0$ NV 15 cm (kPa)"),
             ("V_dVWC_60", "ΔVWC V 60 cm")]
    fig, axs = plt.subplots(2, 4, figsize=(W, 4.6))
    rng = np.random.default_rng(1)
    for a, (c, lab) in zip(axs.ravel(), feats):
        x0, x1 = D[c][D.Y == 0].dropna(), D[c][D.Y == 1].dropna()
        bp = a.boxplot([x0, x1], patch_artist=True, widths=.5, showfliers=False, medianprops=dict(color="k"))
        for b_, col in zip(bp["boxes"], [C["nols"], C["ls"]]):
            b_.set(facecolor=col, alpha=.4)
        a.scatter(1 + rng.uniform(-.1, .1, len(x0)), x0, s=7, color=C["nols"], edgecolor="k", lw=.2, zorder=3)
        a.scatter(np.full(len(x1), 2), x1, s=70, marker="*", color=C["ls"], edgecolor="k", lw=.4, zorder=4)
        a.set_xticks([1, 2], ["no landslide", "landslide"], fontsize=7.5)
        if "s0" in c:
            a.set_yscale("log")
        p = T.loc[c, "p"]
        a.set_title(f"{lab}\nAUC* = {T.loc[c, 'AUC_star']:.2f}, p = {p:.3f}", fontsize=8.5)
    fig.tight_layout(h_pad=1.0)
    save(fig, "Fig07_boxplots_reference_gauge")


# ------------------------------------------------------------------ Fig 8
def fig8():
    feats = [("E_mm", "E"), ("P6h_mm", "$P_{6h}$"), ("D_h", "D"), ("A7d_mm", "$A_{7d}$"), ("Imax_mmh", "$I_{max}$"),
             ("V_dVWC_60", "ΔVWC V 60"), ("NV_dVWC_60", "ΔVWC NV 60"), ("NV_s0_15", "$s_0$ NV 15"),
             ("V_s0_15", "$s_0$ V 15"), ("NV_VWC0_15", "VWC$_0$ NV 15"), ("NV_VWC0_30", "VWC$_0$ NV 30"),
             ("NV_VWC0_60", "VWC$_0$ NV 60"), ("V_VWC0_60", "VWC$_0$ V 60")]
    M = DT.pivot(index="feature", columns="gauge", values="AUC_star").loc[[f for f, _ in feats], GAUGES]
    Pm = DT.pivot(index="feature", columns="gauge", values="p").loc[M.index, GAUGES]
    RB = DT.pivot(index="feature", columns="gauge", values="RB").loc[M.index, GAUGES]
    fig, axs = plt.subplots(1, 2, figsize=(W, 4.0), gridspec_kw=dict(width_ratios=[1.35, 1]))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("ryg", ["#c62828", "#fdd835", "#1b7f3b"])
    im = axs[0].imshow(M.to_numpy(), cmap=cmap, vmin=.5, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            axs[0].text(j, i, f"{M.iat[i, j]:.2f}{'*' if Pm.iat[i, j] < .05 else ''}", ha="center", va="center",
                        fontsize=7.5)
    axs[0].set_yticks(range(len(feats)), [l for _, l in feats])
    axs[0].set_xticks(range(len(GAUGES)), GAUGES, rotation=30, ha="right")
    axs[0].grid(False)
    cb = fig.colorbar(im, ax=axs[0], shrink=.85, pad=.02); cb.set_label("AUC*")
    y = np.arange(len(feats))
    for k, g in enumerate(GAUGES):
        axs[1].scatter(RB[g], y + (k - 2) * .11, s=14, color=GC[g], label=g, zorder=3)
    axs[1].axvline(0, color="k", lw=.6)
    for v in (-.5, .5):
        axs[1].axvline(v, color="#999", ls=":", lw=.8)
    axs[1].set_yticks(y, [l for _, l in feats]); axs[1].set_ylim(len(feats) - .5, -.5)
    axs[1].set_xlim(-1.05, 1.05)
    axs[1].set_xlabel("rank-biserial correlation RB")
    axs[1].legend(loc="lower left", fontsize=7)
    panel(axs[0], "a", x=-.3); panel(axs[1], "b", x=-.32)
    fig.tight_layout()
    save(fig, "Fig08_discriminant_synthesis")


# ------------------------------------------------------------------ Fig 9
def fig9():
    xcol = "NV_VWC0_15"
    fig, axs = plt.subplots(2, 3, figsize=(W, 4.9), sharex=True, sharey=True)
    for a, g in zip(axs.ravel(), GAUGES):
        D = EV[EV.gauge == g].dropna(subset=[xcol])
        n, l = D[D.Y == 0], D[D.Y == 1]
        kde = stats.gaussian_kde(np.vstack([n[xcol], n.E_mm]), bw_method=CFG["stats"]["kde_bw"])
        xx, yy = np.meshgrid(np.linspace(.02, .14, 150), np.linspace(0, 260, 150))
        zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
        a.contourf(xx, yy, zz, levels=np.linspace(zz.max() * .08, zz.max(), 7), cmap="Blues", alpha=.75)
        a.scatter(n[xcol], n.E_mm, s=9, color="#444", label="no landslide")
        a.scatter(l[xcol], l.E_mm, marker="*", s=120, color=C["ls"], edgecolor="k", lw=.4, label="landslide")
        for r in l.itertuples():
            a.annotate(r.landslide.replace(",", "+"), (getattr(r, xcol), r.E_mm), xytext=(4, 3),
                       textcoords="offset points", fontsize=7)
        auc = DT.query("gauge == @g and feature == 'E_mm'").AUC_star.iloc[0]
        a.set_title(g, loc="left")
    fig.supxlabel("antecedent VWC$_0$, non-vegetated site, 15 cm (m$^3$ m$^{-3}$)", fontsize=9, y=.02)
    for a in axs[:, 0]:
        a.set_ylabel("cumulative rainfall E (mm)")
    leg = axs[1, 2]; leg.axis("off")
    leg.legend(handles=[Line2D([], [], marker="o", ls="", color="#444", ms=4, label="non-triggering event"),
                        Line2D([], [], marker="*", ls="", mfc=C["ls"], mec="k", ms=11, label="landslide event"),
                        Patch(color="#6baed6", label="KDE of non-triggering\nevents (density)")],
               loc="center", fontsize=8)
    axs[1, 2].tick_params(labelbottom=False)
    fig.tight_layout()
    save(fig, "Fig09_E_vs_VWC0_NV15")


# ------------------------------------------------------------------ Fig 10
def fig10():
    D = EV[EV.gauge == REF]
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.5), sharey=True)
    mk = {"L1": "o", "L2": "s", "L3,L4": "D", "L3": "D", "L4": "^"}
    for a, site in zip(axs, ["NV", "V"]):
        dd = SITES[site]["depths_cm"]
        n = D[D.Y == 0]
        med = [n[f"{site}_VWC0_{d}"].median() for d in dd]
        q1 = [n[f"{site}_VWC0_{d}"].quantile(.25) for d in dd]; q3 = [n[f"{site}_VWC0_{d}"].quantile(.75) for d in dd]
        a.fill_betweenx(dd, q1, q3, color="#4a7fb5", alpha=.18, label="IQR, non-triggering events")
        a.plot(med, dd, "--", color="#4a7fb5", marker="o", ms=4, label="median, non-triggering events")
        for r in D[D.Y == 1].itertuples():
            a.plot([getattr(r, f"{site}_VWC0_{d}") for d in dd], dd, "-", color=C["ls"], marker=mk[r.landslide],
                   ms=5, mfc="w", label=f"landslide {r.landslide.replace(',', '+')}")
        a.set_title(f"({'a' if site == 'NV' else 'b'}) {'Non-vegetated' if site == 'NV' else 'Vegetated'} site",
                    loc="left", fontweight="bold", fontsize=9)
        a.set_xlabel("antecedent VWC$_0$ (m$^3$ m$^{-3}$)")
        a.set_yticks(dd)
    axs[0].set_yticks([15, 30, 35, 60]); axs[0].set_yticklabels(["15", "30", "35", "60"])
    axs[0].invert_yaxis(); axs[0].set_ylabel("depth (cm)")
    h, l = axs[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, .13, 1, 1))
    fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(.5, 0), fontsize=7.5)
    save(fig, "Fig10_VWC0_profiles")


# ------------------------------------------------------------------ Fig 11
def fig11():
    pooled = pd.DataFrame(IND["pooled"]).set_index("strategy")
    bg = pd.DataFrame(IND["by_gauge"])
    sel = [("E", "E"), ("E + A7d", "E + $A_{7d}$"), ("E + NV VWC0 15", "E + VWC$_0$ NV 15"),
           ("E + NV s0 15", "E + $s_0$ NV 15"), ("D + P6h + NV VWC0 30", "D + $P_{6h}$ + VWC$_0$ NV 30"),
           ("E + P6h + A7d + NV VWC0 15", "E + $P_{6h}$ + $A_{7d}$ + VWC$_0$ NV 15"),
           ("All rain (8 var)", "all 8 rainfall variables"),
           ("All rain + all VWC0 + NV s0 (15 var)", "all 15 variables"),
           ("D + A7d + V dVWC 60 (event)", "D + $A_{7d}$ + ΔVWC V 60 (during event)"),
           ("SEL rain + VWC0 (2 var)", "selected in each fold: rain + VWC$_0$")]
    tri = pd.DataFrame(IND["triples"])
    best3 = tri.iloc[0]
    fig, axs = plt.subplots(1, 2, figsize=(W, 4.4), sharey=True, gridspec_kw=dict(width_ratios=[1.25, 1]))
    y = np.arange(len(sel))[::-1]
    a = axs[0]
    for off, met, col in [(.22, "POD", "#2e7d32"), (0, "POFD", "#e8834c"), (-.22, "TSS", "#3f51b5")]:
        v = [pooled.loc[s, met] for s, _ in sel]
        a.barh(y + off, v, height=.21, color=col, label={"POD": "POD (landslides detected)",
                                                         "POFD": "POFD (false alarms / non-triggering)",
                                                         "TSS": "TSS = POD − POFD"}[met])
    a.set_yticks(y, [l for _, l in sel], fontsize=7.5)
    a.set_xlim(0, 1); a.set_xlabel("score (5 gauges pooled)")
    b = axs[1]
    for k, g in enumerate(GAUGES):
        v = [bg[(bg.strategy == s) & (bg.gauge == g)].TSS.iloc[0] for s, _ in sel]
        b.scatter(v, y + (k - 2) * .1, s=14, color=GC[g], label=g, zorder=3)
    b.scatter([pooled.loc[s, "TSS"] for s, _ in sel], y, marker="|", s=160, color="k", label="pooled", zorder=4)
    b.set_xlim(-.2, 1.02); b.set_xlabel("TSS per rain gauge")
    panel(a, "a", x=-.62); panel(b, "b", x=-.05)
    fig.tight_layout(rect=(0, .14, 1, 1))
    ha, la = a.get_legend_handles_labels(); hb, lb = b.get_legend_handles_labels()
    fig.legend(ha, la, loc="lower left", bbox_to_anchor=(.0, 0), ncol=1, fontsize=7)
    fig.legend(hb, lb, loc="lower right", bbox_to_anchor=(1, 0), ncol=3, fontsize=7)
    save(fig, "Fig11_indicator_performance")


if __name__ == "__main__":
    shutil.copy("/home/claude/docs/img/Chapter_2.docx/word/media/image1.png", OUT / "Fig01_study_area.png")
    fig2(); fig3(); fig4(); fig5(); fig6(); fig7(); fig8(); fig9(); fig10(); fig11()
