"""Export the tables of the Supplementary Material to paper/supplementary/supp_tables.json.
Run from the repository root:  python paper/export_supp_tables.py   (then: node paper/build_supp.js)"""
import json, re
import numpy as np, pandas as pd

T = 'outputs/tables/'
G = ['Albori', 'Cetara', 'Cetara S.C.', 'Dragonea', 'Salerno G.C.']
feat = json.load(open('data/processed/features.json'))


def f(v, n=3):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '–'
    return f"{v:.{n}f}" if isinstance(v, (float, np.floating)) else str(v)


def fx(s):
    """paper notation: subscripts via _{..} markup, ≥/≤ symbols"""
    if not isinstance(s, str):
        return s
    s = re.sub(r'\b([PA])_?(\d+[hd])\b', r'\1_{\2}', s)
    s = re.sub(r'\bI_?max\b', 'I_{max}', s); s = re.sub(r'\bI_?mean\b', 'I_{mean}', s)
    s = re.sub(r'\bVWC0\b', 'VWC_{0}', s); s = re.sub(r'\bs0\b', 's_{0}', s); s = re.sub(r'\bdVWC\b', 'ΔVWC', s)
    return s.replace('VWCpeak', 'VWC_{peak}').replace('>=', '≥').replace('<=', '≤')


out = {}
sg = pd.read_csv(T + 'T00_soil_gaps.csv'); sg = sg[sg.duration_h > 0.1]
out['soil_gaps'] = [[r.site, r.variable, r.start[:16], r.end[:16], f(r.duration_h, 1)] for r in sg.itertuples()]
rg = pd.read_csv(T + 'T00_rain_gaps.csv'); out['rain_gaps'] = rg.astype(str).values.tolist()
ls = pd.read_csv(T + 'T09_landslide_events_by_gauge.csv')
out['ls_match'] = [[r.gauge, r.landslide.replace(',', ' + '), r.event_id, r.t_start[:16], r.t_end[:16], f(r.D_h, 1),
                    f(r.E_mm, 1), f(r.Imax_mmh, 1)] for r in ls.itertuples()]
d = pd.read_csv(T + 'T11_discriminant_metrics_all.csv')
M = d.pivot(index='feature', columns='gauge', values='AUC_star')[G]; Pm = d.pivot(index='feature', columns='gauge', values='p')[G]
ref = d[d.gauge == 'Salerno G.C.'].set_index('feature')
out['auc_matrix'] = [[feat[k][0]] + [f(M.loc[k, g], 2) + ('*' if Pm.loc[k, g] < .05 else '') for g in G]
                     + [ref.loc[k, 'direction'], 'yes' if ref.loc[k, 'physics_consistent'] else 'no'] for k in feat]
out['ref_metrics'] = [[feat[k][0], f(x.mean_ls), f(x.mean_nols), f(x.AUC_star, 2), f(x.RB, 2), f(x.p), f(x.p_adj),
                       f(x.median_pct, 0), x.direction + ' ' + f(x.threshold), f(x.recall, 2), f(x.FPR, 2)]
                      for k, x in ref.loc[list(feat)].iterrows()]
m = pd.read_csv(T + 'T14_mahalanobis_summary.csv')
out['mahal'] = [[x.gauge, str(x.n), str(x.n_ls), f(x.median_DM_ls, 2), f(x.median_DM_nols, 2), f(x.AUC, 2),
                 f(x.MWU_p_one_sided), f"{x.ls_above_thr}/{x.n_ls}", f"{x.nols_above_thr}/{x.n - x.n_ls}"] for x in m.itertuples()]
w = pd.read_csv(T + 'T15_auc_by_accumulation_window.csv', index_col=0)
out['windows'] = [[feat[k][0]] + [f(w.loc[k, g], 2) for g in G] for k in w.index]
t19 = pd.read_csv(T + 'T19_indicator_performance_by_gauge.csv')
keep = ['E', 'E + A7d', 'E + NV VWC0 15', 'D + P6h + NV VWC0 30', 'E + P6h + A7d + NV VWC0 15',
        'D + A7d + V dVWC 60 (event)', 'SEL rain + VWC0 (2 var)']
out['ind_gauge'] = [[x.strategy, x.gauge, str(x.n), str(x.n_ls), str(x.TP), str(x.FN), str(x.FP), str(x.TN), f(x.TSS, 2),
                     f(x.AUC_cv, 2)] for s in keep for x in t19[t19.strategy == s].itertuples()]
t20 = pd.read_csv(T + 'T20_indicator_performance_pooled.csv')
out['ind_all'] = [[x.strategy, x.kind, str(x.TP), str(x.FN), str(x.FP), str(x.TN), f(x.POD, 2), f(x.POFD, 2), f(x.FAR, 2),
                   f(x.TSS, 2), f(x.TSS_min, 2)] for x in t20.itertuples()]
t23 = pd.read_csv(T + 'T23_indicator_all_3var_pooled.csv').head(20)
out['tri'] = [[' + '.join(feat[c][0] for c in x.combo.split(' + ')), x.type, str(x.TP), str(x.FN), str(x.FP), f(x.POD, 2),
               f(x.POFD, 2), f(x.TSS, 2), f(x.TSS_min, 2)] for x in t23.itertuples()]
t8 = pd.read_csv(T + 'T08_V_vs_NV_paired_by_event.csv')
out['paired'] = [[x.variable, f"{x.depth_V} / {x.depth_NV}", str(x.n_events), f(x.median_V), f(x.median_NV),
                  f(x.frac_events_V_lt_NV, 2), f(x.wilcoxon_p)] for x in t8.itertuples()]
t6 = pd.read_csv(T + 'T06_infiltration_velocity_summary.csv')
out['vel'] = [[x.site, x.pair, str(x.n), str(x.n_positive_lag), f(x.v_peak_median, 2), f(x.v_peak_q25, 2), f(x.v_peak_q75, 2),
               f(x.dt_peak_median_h, 1), str(x.n_onset), f(x.v_onset_median, 2)] for x in t6.itertuples()]
for k in out:
    if k not in ('soil_gaps', 'rain_gaps'):
        out[k] = [[fx(c) for c in row] for row in out[k]]
json.dump(out, open('paper/supplementary/supp_tables.json', 'w'), ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
