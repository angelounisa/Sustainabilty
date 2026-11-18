"""Rainfall event identification (IETD) and pluviometric / hydrological indices.

Chapter 3.1 of the manuscript.
"""
import numpy as np
import pandas as pd


def identify_events(rain: pd.Series, ietd_h: float, min_cum_mm: float, timestep_min: int) -> pd.DataFrame:
    """Inter-Event Time Definition: a new event starts when the dry gap between
    two wet intervals exceeds ietd_h. Events with E < min_cum_mm are discarded.

    rain is indexed by interval END time. t_start = beginning of the first wet
    interval (end-time minus one step); t_end = end of the last wet interval.
    """
    dt = pd.Timedelta(minutes=timestep_min)
    wet = rain[rain > 0]
    gap = wet.index.to_series().diff()
    # gap measured between the end of the previous wet interval and the start of
    # the current one = diff - dt
    new = (gap - dt) > pd.Timedelta(hours=ietd_h)
    new.iloc[0] = True
    eid = new.cumsum()
    rows = []
    for k, g in wet.groupby(eid.values):
        t0 = g.index[0] - dt
        t1 = g.index[-1]
        rows.append(dict(t_start=t0, t_end=t1, E_mm=g.sum()))
    ev = pd.DataFrame(rows)
    n_all = len(ev)
    ev = ev[ev.E_mm >= min_cum_mm].reset_index(drop=True)
    ev.attrs["n_before_filter"] = n_all
    return ev


def rainfall_indices(ev: pd.DataFrame, rain: pd.Series, timestep_min: int, imax_window_min: int,
                     max_windows_h: list[int], antecedent_days: list[int]) -> pd.DataFrame:
    """Add D (h), E (mm), I_mean (mm/h), I_max (mm/h, max moving 60-min sum),
    max moving totals P_<w>h within the event and antecedent rainfall A_<d>d."""
    ev = ev.copy()
    n_imax = imax_window_min // timestep_min
    roll_imax = rain.rolling(n_imax, min_periods=1).sum() * (60 / imax_window_min)  # mm/h
    rolls = {w: rain.rolling(int(w * 60 / timestep_min), min_periods=1).sum() for w in max_windows_h}
    cum = rain.cumsum()
    D, Imax, Pw, A = [], [], {w: [] for w in max_windows_h}, {d: [] for d in antecedent_days}
    for r in ev.itertuples():
        sel = slice(r.t_start + pd.Timedelta(minutes=timestep_min), r.t_end)
        D.append((r.t_end - r.t_start) / pd.Timedelta(hours=1))
        Imax.append(roll_imax[sel].max())
        for w in max_windows_h:
            Pw[w].append(rolls[w][sel].max())
        c0 = cum.asof(r.t_start)
        for d in antecedent_days:
            tA = r.t_start - pd.Timedelta(days=d)
            if tA < rain.index[0]:
                A[d].append(np.nan)      # antecedent window not covered by the record
            else:
                A[d].append(c0 - cum.asof(tA))
    ev["D_h"] = D
    ev["Imax_mmh"] = Imax
    ev["Imean_mmh"] = ev.E_mm / ev.D_h
    for w in max_windows_h:
        ev[f"P{w}h_mm"] = Pw[w]
    for d in antecedent_days:
        ev[f"A{d}d_mm"] = A[d]
    assert (ev.D_h > 0).all()
    # conservation check: the event total equals the sum inside the window
    for r in ev.itertuples():
        s = rain[r.t_start + pd.Timedelta(minutes=timestep_min): r.t_end].sum()
        assert np.isclose(s, r.E_mm), "event total mismatch"
    return ev


def hydro_indices(ev: pd.DataFrame, soil: pd.DataFrame, site: str, depths_cm: list[int],
                  antecedent_window_min: int, response_extension_h: float) -> pd.DataFrame:
    """Event-based indices from VWC (m3/m3) and suction s (kPa, positive):

    VWC0   mean VWC in the antecedent window before t_start
    VWCpk  max VWC in [t_start, t_end + ext]
    dVWC   VWCpk - VWC0
    tpk    time of VWCpk
    s0     mean suction in the antecedent window
    smin   min suction in the response window (max wetting)
    ds     smin - s0 (negative = suction drop)
    An index is NaN when any sample needed is missing (no gap filling).
    """
    out = pd.DataFrame(index=ev.index)
    aw = pd.Timedelta(minutes=antecedent_window_min)
    ext = pd.Timedelta(hours=response_extension_h)
    for d in depths_cm:
        cols = {k: [] for k in ["VWC0", "VWCpk", "dVWC", "tpk", "s0", "smin", "ds", "tsmin"]}
        for r in ev.itertuples():
            pre = soil.loc[r.t_start - aw: r.t_start]
            win = soil.loc[r.t_start: r.t_end + ext]
            expected_win = int(((r.t_end + ext) - r.t_start) / pd.Timedelta(minutes=5))
            ok = (len(pre) > 0 and len(win) >= 0.99 * expected_win)
            v_pre, v_win = pre[f"VWC_{d}"], win[f"VWC_{d}"]
            s_pre, s_win = pre[f"s_{d}"], win[f"s_{d}"]
            if ok and v_pre.notna().all() and v_win.notna().all() and len(v_pre):
                v0, vpk = v_pre.mean(), v_win.max()
                cols["VWC0"].append(v0); cols["VWCpk"].append(vpk); cols["dVWC"].append(vpk - v0)
                cols["tpk"].append(v_win.idxmax())
            else:
                for k in ["VWC0", "VWCpk", "dVWC"]:
                    cols[k].append(np.nan)
                cols["tpk"].append(pd.NaT)
            if ok and s_pre.notna().all() and s_win.notna().all() and len(s_pre):
                s0, smin = s_pre.mean(), s_win.min()
                cols["s0"].append(s0); cols["smin"].append(smin); cols["ds"].append(smin - s0)
                cols["tsmin"].append(s_win.idxmin())
            else:
                for k in ["s0", "smin", "ds"]:
                    cols[k].append(np.nan)
                cols["tsmin"].append(pd.NaT)
        for k, v in cols.items():
            out[f"{site}_{k}_{d}"] = v
    return out


def onset_time(soil: pd.DataFrame, col: str, t_start, t_end, vwc0: float, dvwc: float, frac: float):
    """First time VWC >= VWC0 + frac*dVWC within [t_start, t_end] (wetting-front arrival)."""
    w = soil.loc[t_start:t_end, col]
    hit = w[w >= vwc0 + frac * dvwc]
    return hit.index[0] if len(hit) else pd.NaT
