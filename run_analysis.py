"""Full analysis pipeline: data QC -> events -> hydrological indices -> clustering
-> infiltration velocity -> landslide statistics. Writes tables to outputs/tables
and intermediate objects to data/processed. Figures: make_figures.py.

Usage:  python run_analysis.py
"""
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import yaml
from scipy import stats

from src import io_data, events, stats_ls

CFG = yaml.safe_load(open("config.yaml"))
P = {k: Path(v) for k, v in CFG["paths"].items()}
for k in ["processed", "tables", "figures"]:
    P[k].mkdir(parents=True, exist_ok=True)
T = P["tables"]


def save(df, name, index=False):
    df.to_csv(T / f"{name}.csv", index=index, float_format="%.4g")


# --------------------------------------------------------------------- 1. data
rain, gaps = {}, []
for stem, name in CFG["rain_gauges"].items():
    rain[name] = io_data.load_rain(P["raw"], stem, CFG["rain"]["timestep_min"])
    g = io_data.load_rain_gaps(P["raw"], stem)
    if g is not None:
        g.insert(0, "gauge", name)
        gaps.append(g)
rain_df = pd.DataFrame(rain)
rain_df.to_csv(P["processed"] / "rain_10min_UTC+1.csv.gz")
if gaps:
    save(pd.concat(gaps), "T00_rain_gaps")

soil, soil_gaps = {}, []
sc = CFG["soil"]
for site, s in sc["sites"].items():
    soil[site] = io_data.load_soil(P["raw"], s["file"], s["depths_cm"], sc["timestep_min"],
                                   sc["dst_switch_local"], sc["vwc_valid_range"], sc["suction_valid_range"])
    soil[site].to_csv(P["processed"] / f"soil_{site}_5min_UTC+1.csv.gz")
    soil_gaps.append(io_data.soil_gap_table(soil[site], site, sc["timestep_min"]))
save(pd.concat(soil_gaps), "T00_soil_gaps")

rows = []
for g, r in rain.items():
    rows.append(dict(series=g, variable="rain (mm)", start=r.index[0], end=r.index[-1],
                     total_mm=r.sum(), total_2025_mm=r.loc["2025"].sum(),
                     total_jan_sep_2026_mm=r.loc["2026"].sum(), max_10min_mm=r.max()))
for site, d in soil.items():
    for c in d.columns:
        rows.append(dict(series=site, variable=c, start=d[c].first_valid_index(), end=d[c].last_valid_index(),
                         completeness_pct=100 * d[c].notna().mean(), min=d[c].min(),
                         median=d[c].median(), max=d[c].max()))
save(pd.DataFrame(rows), "T01_data_summary")

# ---------------------------------------------------------------- 2. events
ec, hc = CFG["events"], CFG["hydro"]
ls = pd.read_csv(P["landslides"])
ls["t"] = pd.to_datetime(ls.datetime_local)   # Italian local time; all dates fall in CET = UTC+1

all_ev = []
for g, r in rain.items():
    ev = events.identify_events(r, ec["ietd_h"], ec["min_cumulative_mm"], CFG["rain"]["timestep_min"])
    n_before = ev.attrs["n_before_filter"]
    ev = events.rainfall_indices(ev, r, CFG["rain"]["timestep_min"], ec["imax_window_min"],
                                 ec["max_windows_h"], ec["antecedent_days"])
    for site, s in sc["sites"].items():
        ev = ev.join(events.hydro_indices(ev, soil[site], site, s["depths_cm"],
                                          hc["antecedent_window_min"], hc["response_extension_h"]))
    ev["landslide"] = stats_ls.match_landslides(ev, ls, CFG["stats"]["landslide_match_extension_h"])
    ev["Y"] = (ev.landslide != "").astype(int)
    ev.insert(0, "gauge", g)
    ev.insert(1, "event_id", [f"{g[:3].upper()}{'S' if 'S.C' in g else ''}-{i + 1:03d}" for i in range(len(ev))])
    ev["n_spells_before_filter"] = n_before
    print(f"{g}: {n_before} rain spells (IETD) -> {len(ev)} events with E>=10 mm; "
          f"landslide events: {ev.loc[ev.Y == 1, 'landslide'].tolist()}")
    all_ev.append(ev)
EV = pd.concat(all_ev, ignore_index=True)

for g in rain:
    got = ",".join(EV.loc[(EV.gauge == g) & (EV.Y == 1), "landslide"]).split(",")
    missing = set(ls.id) - set(got)
    if missing:
        print(f"WARNING {g}: landslides {missing} not matched to any event with E>=10 mm")

# ------------------------------------------------------- 3. clustering (Ch.3.2)
cc = CFG["clustering"]
for site, s in sc["sites"].items():
    for d in s["depths_cm"]:
        v0, dv = EV[f"{site}_VWC0_{d}"], EV[f"{site}_dVWC_{d}"]
        cls = pd.Series(np.where(v0.isna() | dv.isna(), None, "irrelevant"), index=EV.index, dtype=object)
        rel = dv >= cc["relevance_ratio"] * v0
        z = pd.Series(np.nan, index=EV.index)
        for g in rain:   # z-score per gauge (each gauge defines its own event set)
            m = rel & (EV.gauge == g)
            z[m] = (dv[m] - dv[m].mean()) / dv[m].std(ddof=1)
        cls[rel & (z < cc["z_extreme"])] = "relevant"
        cls[rel & (z >= cc["z_extreme"])] = "extreme"
        EV[f"{site}_z_{d}"] = z
        EV[f"{site}_class_{d}"] = cls

# --------------------------------------------- 4. infiltration velocity (Ch.3.2)
ic = CFG["infiltration"]
vel_rows = []
for site, s in sc["sites"].items():
    dd = s["depths_cm"]
    for i, r in EV.iterrows():
        for a, b in [(dd[0], dd[1]), (dd[1], dd[2]), (dd[0], dd[2])]:
            ca, cb = r[f"{site}_class_{a}"], r[f"{site}_class_{b}"]
            if ca in (None, "irrelevant") or cb in (None, "irrelevant"):
                continue
            dt_pk = (r[f"{site}_tpk_{b}"] - r[f"{site}_tpk_{a}"]) / pd.Timedelta(hours=1)
            tend = r.t_end + pd.Timedelta(hours=hc["response_extension_h"])
            ta = events.onset_time(soil[site], f"VWC_{a}", r.t_start, tend, r[f"{site}_VWC0_{a}"],
                                   r[f"{site}_dVWC_{a}"], ic["onset_fraction"])
            tb = events.onset_time(soil[site], f"VWC_{b}", r.t_start, tend, r[f"{site}_VWC0_{b}"],
                                   r[f"{site}_dVWC_{b}"], ic["onset_fraction"])
            dt_on = (tb - ta) / pd.Timedelta(hours=1)
            vel_rows.append(dict(gauge=r.gauge, event_id=r.event_id, t_start=r.t_start, E_mm=r.E_mm,
                                 Imax_mmh=r.Imax_mmh, site=site, pair=f"{a}-{b}", dz_cm=b - a,
                                 class_upper=ca, class_lower=cb, dt_peak_h=dt_pk, dt_onset_h=dt_on,
                                 v_peak_cmh=(b - a) / dt_pk if dt_pk > 0 else np.nan,
                                 v_onset_cmh=(b - a) / dt_on if dt_on > 0 else np.nan,
                                 landslide=r.landslide))
VEL = pd.DataFrame(vel_rows)
EV.to_pickle(P["processed"] / "events.pkl")
VEL.to_pickle(P["processed"] / "velocity.pkl")

# ------------------------------------------------------------------ TABLES Ch.3
cols_rain = ["event_id", "t_start", "t_end", "D_h", "E_mm", "Imax_mmh", "Imean_mmh", "P1h_mm", "P3h_mm",
             "P6h_mm", "P12h_mm", "P24h_mm", "A3d_mm", "A7d_mm", "A14d_mm", "A30d_mm", "landslide"]
for g in rain:
    save(EV.loc[EV.gauge == g, cols_rain], f"T02_events_{g.replace(' ', '_').replace('.', '')}")
hyd = [c for c in EV.columns if c.startswith(("V_", "NV_")) and c.split("_")[1] not in ("tpk", "tsmin")]
save(EV[["gauge", "event_id", "t_start", "E_mm", "landslide"] + hyd], "T03_events_hydro_indices_all_gauges")

summ = EV.groupby("gauge").agg(n_rain_spells_IETD=("n_spells_before_filter", "first"),
                               n_events=("E_mm", "size"), D_median_h=("D_h", "median"),
                               E_median_mm=("E_mm", "median"), E_max_mm=("E_mm", "max"),
                               Imax_median_mmh=("Imax_mmh", "median"), Imax_max_mmh=("Imax_mmh", "max"),
                               n_with_soil_data=("NV_VWC0_60", "count"), n_landslide_events=("Y", "sum"))
save(summ, "T04_event_summary_by_gauge", index=True)

ref = hc["reference_gauge"]
R = EV[EV.gauge == ref]
rows = []
for site, s in sc["sites"].items():
    for d in s["depths_cm"]:
        c = R[f"{site}_class_{d}"]
        for k in ["irrelevant", "relevant", "extreme"]:
            m = c == k
            rows.append(dict(site=site, depth_cm=d, cls=k, n=int(m.sum()),
                             E_median_mm=R.E_mm[m].median(), Imax_median_mmh=R.Imax_mmh[m].median(),
                             VWC0_median=R[f"{site}_VWC0_{d}"][m].median(),
                             dVWC_median=R[f"{site}_dVWC_{d}"][m].median(),
                             dVWC_max=R[f"{site}_dVWC_{d}"][m].max(),
                             s0_median_kPa=R[f"{site}_s0_{d}"][m].median(),
                             ds_median_kPa=R[f"{site}_ds_{d}"][m].median()))
        rows.append(dict(site=site, depth_cm=d, cls="no soil data", n=int(c.isna().sum())))
save(pd.DataFrame(rows), "T05_event_classes_reference_gauge")

V = VEL[VEL.gauge == ref]
vs = V.groupby(["site", "pair"]).agg(n=("dt_peak_h", "count"),
                                     n_positive_lag=("v_peak_cmh", "count"),
                                     v_peak_median=("v_peak_cmh", "median"),
                                     v_peak_q25=("v_peak_cmh", lambda x: x.quantile(.25)),
                                     v_peak_q75=("v_peak_cmh", lambda x: x.quantile(.75)),
                                     dt_peak_median_h=("dt_peak_h", "median"),
                                     n_onset=("v_onset_cmh", "count"), v_onset_median=("v_onset_cmh", "median"),
                                     dt_onset_median_h=("dt_onset_h", "median"))
save(vs, "T06_infiltration_velocity_summary", index=True)

rows = []
for lab, pv, pn in [("upper (15-35 V / 15-30 NV)", "15-35", "15-30"),
                    ("lower (35-60 V / 30-60 NV)", "35-60", "30-60"), ("15-60", "15-60", "15-60")]:
    for metric in ["v_peak_cmh", "v_onset_cmh"]:
        a = V[(V.site == "V") & (V.pair == pv)][metric].dropna()
        b = V[(V.site == "NV") & (V.pair == pn)][metric].dropna()
        if len(a) >= 3 and len(b) >= 3:
            U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            rb = 2 * U / (len(a) * len(b)) - 1
        else:
            p = rb = np.nan
        rows.append(dict(pair=lab, metric=metric, n_V=len(a), n_NV=len(b), median_V=a.median(),
                         median_NV=b.median(), RB_V_vs_NV=rb, MWU_p=p))
save(pd.DataFrame(rows), "T07_infiltration_V_vs_NV")

rows = []
for dv_, dn_ in [(15, 15), (35, 30), (60, 60)]:
    for var in ["dVWC", "VWC0", "s0", "ds"]:
        m = R[[f"V_{var}_{dv_}", f"NV_{var}_{dn_}"]].dropna()
        w = stats.wilcoxon(m.iloc[:, 0], m.iloc[:, 1])
        rows.append(dict(variable=var, depth_V=dv_, depth_NV=dn_, n_events=len(m),
                         median_V=m.iloc[:, 0].median(), median_NV=m.iloc[:, 1].median(),
                         frac_events_V_lt_NV=(m.iloc[:, 0] < m.iloc[:, 1]).mean(), wilcoxon_p=w.pvalue))
save(pd.DataFrame(rows), "T08_V_vs_NV_paired_by_event")

# ------------------------------------------------------------------ Ch.4 stats
FEAT = {"D_h": ("D (h)", False), "E_mm": ("E (mm)", False), "Imax_mmh": ("I_max (mm/h)", False),
        "Imean_mmh": ("I_mean (mm/h)", False)}
for w in ec["max_windows_h"]:
    FEAT[f"P{w}h_mm"] = (f"P_{w}h (mm)", False)
for d in ec["antecedent_days"]:
    FEAT[f"A{d}d_mm"] = (f"A_{d}d (mm)", False)
for site, s in sc["sites"].items():
    for d in s["depths_cm"]:
        FEAT[f"{site}_VWC0_{d}"] = (f"{site} VWC0 {d} cm", False)
        FEAT[f"{site}_dVWC_{d}"] = (f"{site} ΔVWC {d} cm", False)
        FEAT[f"{site}_VWCpk_{d}"] = (f"{site} VWCpeak {d} cm", False)
        FEAT[f"{site}_s0_{d}"] = (f"{site} s0 {d} cm", True)      # low suction = less stable
        FEAT[f"{site}_ds_{d}"] = (f"{site} Δs {d} cm", True)      # larger drop (more negative)
json.dump({k: list(v) for k, v in FEAT.items()}, open(P["processed"] / "features.json", "w"), indent=1)

LS = EV[EV.Y == 1][["gauge", "event_id", "landslide", "t_start", "t_end", "D_h", "E_mm", "Imax_mmh",
                    "P3h_mm", "P24h_mm", "A30d_mm", "NV_VWC0_15", "NV_VWC0_30", "NV_VWC0_60", "V_VWC0_60",
                    "NV_s0_15", "V_s0_15", "NV_dVWC_60", "V_dVWC_60", "NV_class_15", "NV_class_60",
                    "V_class_60"]]
save(LS, "T09_landslide_events_by_gauge")
mean_tab = EV.groupby(["gauge", "Y"])[list(FEAT)].mean().T
mean_tab.columns = [f"{g} | {'LS' if y else 'no-LS'}" for g, y in mean_tab.columns]
save(mean_tab, "T10_mean_features_ls_vs_nols", index=True)

DT = []
for g in rain:
    t = stats_ls.feature_table(EV[EV.gauge == g], FEAT, "Y", CFG["stats"]["multiple_testing"])
    t.insert(0, "gauge", g)
    DT.append(t)
DT = pd.concat(DT, ignore_index=True)
DT.to_pickle(P["processed"] / "discriminant.pkl")
save(DT, "T11_discriminant_metrics_all")
core = ["D_h", "E_mm", "Imax_mmh", "NV_VWC0_60", "V_VWC0_60", "NV_s0_15", "V_s0_15", "NV_dVWC_60", "V_dVWC_60"]
syn = DT[DT.feature.isin(core)][["gauge", "label", "n_ls", "n_nols", "AUC_star", "RB", "direction", "physics_consistent", "p", "p_adj",
                                 "median_pct", "threshold", "recall", "FPR"]]
save(syn, "T12_discriminant_synthesis_core_features")
sev = EV[EV.Y == 1][["gauge", "event_id", "landslide"] + [c for c in EV.columns if "_class_" in c]]
save(sev, "T13_severity_class_of_landslide_events")

MD, mrows = [], []
for g in rain:
    d, thr = stats_ls.mahalanobis(EV[EV.gauge == g], CFG["stats"]["mahalanobis_features"], "Y",
                                  CFG["stats"]["mahalanobis_quantile"])
    d["thr"] = thr
    MD.append(d[["gauge", "event_id", "Y", "landslide", "D_M", "thr"]])
    x1, x0 = d.D_M[d.Y == 1], d.D_M[d.Y == 0]
    U, p = stats.mannwhitneyu(x1, x0, alternative="greater")
    mrows.append(dict(gauge=g, n=len(d), n_ls=len(x1), threshold=thr, median_DM_ls=x1.median(),
                      median_DM_nols=x0.median(), AUC=U / (len(x1) * len(x0)),
                      ls_above_thr=int((x1 > thr).sum()), nols_above_thr=int((x0 > thr).sum()),
                      MWU_p_one_sided=p))
pd.concat(MD).to_pickle(P["processed"] / "mahalanobis.pkl")
save(pd.DataFrame(mrows), "T14_mahalanobis_summary")

# Patton et al. (2023)-inspired comparison of rainfall accumulation windows:
# which duration (1 h ... event total, antecedent days) best separates triggering events
win = ["P1h_mm", "P3h_mm", "P6h_mm", "P12h_mm", "P24h_mm", "E_mm", "A3d_mm", "A7d_mm", "A14d_mm", "A30d_mm"]
save(DT[DT.feature.isin(win)].pivot(index="feature", columns="gauge", values="AUC_star").loc[win],
     "T15_auc_by_accumulation_window", index=True)

json.dump(dict(python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__,
               scipy=scipy.__version__, config=CFG),
          open(T / "run_provenance.json", "w"), indent=1, default=str)
print("done")
