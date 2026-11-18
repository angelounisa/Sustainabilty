"""Export analysis results to docs/ for the GitHub Pages dashboard.

Usage:  python make_dashboard.py   (after run_analysis.py and make_figures.py)
"""
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CFG = yaml.safe_load(open("config.yaml"))
P = {k: Path(v) for k, v in CFG["paths"].items()}
D = Path("docs")
(D / "figures").mkdir(parents=True, exist_ok=True)


def clean(x):
    """JSON-safe: NaN -> None, timestamps -> ISO strings, numpy -> python."""
    if isinstance(x, (float, np.floating)):
        return None if np.isnan(x) else round(float(x), 5)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (pd.Timestamp,)):
        return x.strftime("%Y-%m-%d %H:%M")
    if x is pd.NaT or x is None:
        return None
    return x


def records(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


rain = pd.read_csv(P["processed"] / "rain_10min_UTC+1.csv.gz", index_col=0, parse_dates=True)
soil = {s: pd.read_csv(P["processed"] / f"soil_{s}_5min_UTC+1.csv.gz", index_col=0, parse_dates=True)
        for s in CFG["soil"]["sites"]}
rh = rain.resample("h").sum()                       # hourly rainfall (mm/h)
sh = {s: d.resample("h").mean() for s, d in soil.items()}
idx = rh.index.union(sh["V"].index)
ts = {"t": [t.strftime("%Y-%m-%d %H:%M") for t in idx]}
for g in rh.columns:
    ts[f"rain|{g}"] = [clean(v) for v in rh[g].reindex(idx).to_numpy()]
for s, d in sh.items():
    for c in d.columns:
        ts[f"{s}|{c}"] = [clean(v) for v in d[c].reindex(idx).to_numpy()]

EV = pd.read_pickle(P["processed"] / "events.pkl")
keep = [c for c in EV.columns if not c.split("_")[1:2] or c.split("_")[1] not in ("tpk", "tsmin")]
EVo = EV[keep].copy()
VEL = pd.read_pickle(P["processed"] / "velocity.pkl")
DT = pd.read_pickle(P["processed"] / "discriminant.pkl")
MD = pd.read_pickle(P["processed"] / "mahalanobis.pkl")
LS = pd.read_csv(P["landslides"])
tabs = {n: pd.read_csv(P["tables"] / f"{n}.csv") for n in
        ["T04_event_summary_by_gauge", "T06_infiltration_velocity_summary", "T07_infiltration_V_vs_NV",
         "T08_V_vs_NV_paired_by_event", "T14_mahalanobis_summary", "T05_event_classes_reference_gauge"]}

MV = pd.read_pickle(P["processed"] / "multivar.pkl")
from src import multivar as _mv
NEXP = EV.groupby("gauge").Y.sum().to_dict()

out = dict(
    gauges=list(CFG["rain_gauges"].values()), reference_gauge=CFG["hydro"]["reference_gauge"],
    sites={k: v["depths_cm"] for k, v in CFG["soil"]["sites"].items()},
    features=json.load(open(P["processed"] / "features.json")),
    timeseries=ts, events=records(EVo), velocity=records(VEL), discriminant=records(DT.drop(columns=["U"])),
    mahalanobis=records(MD), landslides=records(LS), tables={k: records(v) for k, v in tabs.items()},
    multivar=dict(rain_vars=CFG["multivariate"]["rain_vars"], water_vars=CFG["multivariate"]["water_vars"],
                  summary={k: records(_mv.summarise(v, NEXP)) for k, v in MV.items()},
                  by_gauge={k: records(v[["gauge", "combo", "n_ls", "n_nols", "AUC_DM", "AUC_PS", "LS_above_thr",
                                          "FP_above_thr", "recall_at_FPR10"]]) for k, v in MV.items()}),
    params=dict(ietd_h=CFG["events"]["ietd_h"], min_E=CFG["events"]["min_cumulative_mm"],
                ext_h=CFG["hydro"]["response_extension_h"]),
)
json.dump(out, open(D / "data.json", "w"), separators=(",", ":"), allow_nan=False)
print("data.json", round((D / "data.json").stat().st_size / 1e6, 2), "MB")

CAPTIONS = {
    "Fig02_timeseries_rain_VWC_suction": ("s-over", "Serie storiche: pioggia, VWC e suzione nei siti V e NV, con le frane"),
    "Fig03_hydrological_index_extraction": ("s-over", "Estrazione degli indici idrologici sull'evento di L1"),
    "Fig02b_IETD_event_identification_example": ("s-ev", "Identificazione degli eventi (IETD 24 h, E ≥ 10 mm)"),
    "Fig04_ED_space_event_classes": ("s-ev", "Eventi nello spazio E–D per classe di risposta, sito e profondità"),
    "Fig05_infiltration_velocity_V_vs_NV": ("s-inf", "Velocità di infiltrazione (0–15, 15–30/35, 30/35–60, 15–60 cm) e ΔVWC V vs NV"),
    "Fig06_landslide_timeline": ("s-ls", "Timeline delle frane e degli eventi per pluviometro"),
    "Fig06b_rainfall_around_landslides": ("s-ls", "Pioggia cumulata intorno a ciascuna frana"),
    "Fig07_boxplots_Salerno_GC": ("s-ls", "Boxplot frana vs non frana — Salerno G.C."),
    "Fig07_boxplots_Albori": ("s-ls", "Boxplot frana vs non frana — Albori"),
    "Fig07_boxplots_Cetara": ("s-ls", "Boxplot frana vs non frana — Cetara"),
    "Fig07_boxplots_Cetara_SC": ("s-ls", "Boxplot frana vs non frana — Cetara S.C."),
    "Fig07_boxplots_Dragonea": ("s-ls", "Boxplot frana vs non frana — Dragonea"),
    "Fig08_ROC_curves": ("s-ls", "Curve ROC dei singoli predittori"),
    "Fig09_E_vs_VWC0_60_KDE": ("s-ls", "Spazio E – VWC0 60 cm con densità degli eventi senza frana"),
    "Fig10_antecedent_VWC_profiles": ("s-ls", "Profili di VWC antecedente: frane vs eventi normali"),
    "Fig11_discriminant_synthesis": ("s-ls", "Sintesi del potere discriminante (AUC*, rank-biserial)"),
    "Fig12_mahalanobis_and_accumulation_windows": ("s-ls", "Mahalanobis e AUC per finestra di accumulo"),
    "Fig13_multivar_2var_heatmaps": ("s-mv", "Tutte le coppie pioggia × contenuto d'acqua"),
    "Fig14_multivar_best_by_family": ("s-mv", "Migliore combinazione per famiglia (1, 2, 3 variabili)"),
    "Fig15_multivar_scatter_examples": ("s-mv", "Esempi E vs VWC0 con ellisse di Mahalanobis"),
    "Fig18_indicator_construction": ("s-ind", "Come è costruito l'indicatore (esempio numerico)"),
    "Fig16_indicator_performance": ("s-ind", "Performance in validazione di tutti gli indicatori, per pluviometro"),
    "Fig19_indicator_TSS_vs_nvars": ("s-ind", "TSS in funzione del numero di variabili"),
    "Fig20_indicator_all_3var": ("s-ind", "Tutti gli indicatori a 3 variabili"),
    "Fig17_indicator_timeline_best": ("s-ind", "Valore dell'indicatore migliore evento per evento"),
}
present = {f.stem for f in P["figures"].glob("*.png")}
missing = set(CAPTIONS) - present
assert not missing, f"figures listed but not generated: {missing}"
json.dump([dict(file=f"{k}.png", tab=v[0], caption=v[1]) for k, v in CAPTIONS.items()] +
          [dict(file=f"{k}.png", tab=None, caption=k) for k in sorted(present - set(CAPTIONS))],
          open(D / "figures.json", "w"), ensure_ascii=False, indent=0)

for f in sorted(P["figures"].glob("*.png")):
    shutil.copy(f, D / "figures" / f.name)
print("figures copied:", len(list((D / "figures").glob("*.png"))))
