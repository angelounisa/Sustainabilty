"""Loading and quality control of rain-gauge and METER (TEROS 10/21) data.

Raw files are never modified; cleaned series are written to data/processed.
All timestamps are returned in UTC+1 (no DST).
"""
from pathlib import Path

import numpy as np
import pandas as pd


def load_rain(raw_dir: Path, stem: str, timestep_min: int) -> pd.Series:
    """Return a 10-min rainfall series (mm per interval) indexed by interval END time (UTC+1).

    In the CF files the 'Time UTC+1' column is an Excel formula (t_i = t_{i-1} + dt);
    pandas reads the cached values. We verify the grid is perfectly regular.
    """
    df = pd.read_excel(raw_dir / f"{stem}.xlsx", sheet_name=0)
    t_raw = pd.to_datetime(df["Time UTC+1"])
    # the Excel formula accumulates floating-point drift (< 1 s): round to the grid
    t = t_raw.dt.round(f"{timestep_min}min")
    assert ((t - t_raw).abs() < pd.Timedelta(seconds=5)).all(), "time drift larger than rounding tolerance"
    step = t.diff().dropna()
    assert (step == pd.Timedelta(minutes=timestep_min)).all(), f"{stem}: irregular time grid"
    rain = pd.Series(df["Rain (mm)"].to_numpy(dtype=float), index=t, name="rain_mm")
    assert rain.notna().all(), f"{stem}: NaN rainfall values"
    assert (rain >= 0).all(), f"{stem}: negative rainfall"
    return rain


def load_rain_gaps(raw_dir: Path, stem: str) -> pd.DataFrame | None:
    """Return the 'Buchi' (gap) sheet when the file provides one, else None."""
    xl = pd.ExcelFile(raw_dir / f"{stem}.xlsx")
    if "Buchi" not in xl.sheet_names:
        return None
    return pd.read_excel(xl, sheet_name="Buchi")


def load_soil(raw_dir: Path, file_stem: str, depths_cm: list[int], timestep_min: int,
              dst_switch_local: str, vwc_range: list[float], suction_range: list[float]) -> pd.DataFrame:
    """Return VWC (m3/m3) and suction (kPa) per depth, indexed by UTC+1 time.

    Columns: VWC_<d>, s_<d> for d in depths_cm.
    """
    df = pd.read_excel(raw_dir / f"{file_stem}.xlsx")
    t = pd.to_datetime(df["Time"])
    assert t.is_monotonic_increasing and not t.duplicated().any()
    # DST correction (see config): shift the post-switch part by -1 h
    switch = pd.Timestamp(dst_switch_local)
    jump = t[t >= switch].iloc[0] - t[t < switch].iloc[-1]
    assert jump == pd.Timedelta(minutes=60 + timestep_min), f"unexpected clock jump {jump}"
    t = t.where(t < switch, t - pd.Timedelta(hours=1))
    assert not t.duplicated().any()

    out = pd.DataFrame(index=pd.DatetimeIndex(t, name="time"))
    vwc_cols = [c for c in df.columns if c.startswith("VWC")]
    s_cols = [c for c in df.columns if c.startswith("s ")]
    assert [int(c.split()[1]) for c in vwc_cols] == depths_cm, vwc_cols
    assert [int(c.split()[1]) for c in s_cols] == depths_cm, s_cols
    for d, cv, cs in zip(depths_cm, vwc_cols, s_cols):
        out[f"VWC_{d}"] = df[cv].to_numpy(dtype=float)
        out[f"s_{d}"] = df[cs].to_numpy(dtype=float)
    v = out.filter(like="VWC").stack().dropna()
    s = out.filter(like="s_").stack().dropna()
    assert v.between(*vwc_range).all(), "VWC outside physical range"
    assert s.between(*suction_range).all(), "suction outside sensor range"
    # put on a regular 5-min grid: missing timestamps become explicit NaN
    grid = pd.date_range(out.index[0], out.index[-1], freq=f"{timestep_min}min")
    out = out.reindex(grid)
    out.index.name = "time"
    return out


def soil_gap_table(soil: pd.DataFrame, site: str, timestep_min: int) -> pd.DataFrame:
    """List contiguous NaN blocks per column (data gaps)."""
    rows = []
    for c in soil.columns:
        na = soil[c].isna()
        if not na.any():
            continue
        blk = (na != na.shift()).cumsum()
        for _, g in soil[c][na].groupby(blk[na]):
            rows.append(dict(site=site, variable=c, start=g.index[0], end=g.index[-1],
                             duration_h=(len(g) * timestep_min) / 60))
    return pd.DataFrame(rows)
