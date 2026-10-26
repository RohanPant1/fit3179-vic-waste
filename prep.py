"""
Build analysis-ready CSVs for Data Visualisation 2 from the raw downloads.

This copy is published for transparency: it is the exact script that produced
every file in data/. It will not run as-is from this repository, because the
raw government downloads it reads are tens of megabytes and are not committed
here. Each one is cited, with its URL, in the page footer and in README.md.

Run from the Data/ folder:   python prep.py

Inputs  (Data/raw, Data/geo) -- see Research/01-data-sources.md for provenance
Outputs (Data/clean)         -- small, flat CSVs that Vega-Lite can read directly

The joins here are the only wrangling this assignment does. The brief says data
wrangling is not a marked topic, so this stays deliberately thin: normalise the
council name, join, derive a handful of per-capita / per-household rates.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW, GEO, OUT = HERE / "raw", HERE / "geo", HERE / "clean"
OUT.mkdir(exist_ok=True)

VLGAS = RAW / "victorian-local-government-waste-data-release-notes-2025.03.xlsx"
LGPRF = RAW / "LGPRF-2020-2025-Full-Council-Data-Set.xlsx"
INFRA = RAW / "vic-waste-infrastructure-Mar2025.csv"
SEIFA = RAW / "abs-seifa-2021-lga.csv"

LATEST_WASTE_YEAR = "2023-2024"   # most recent year in VLGAS v2025.03
LATEST_LGPRF_SHEET = "Indicators 2024-25"


def key(name: str) -> str:
    """Normalise a council name to a join key.

    The three sources spell the same council three ways -- 'Alpine Shire Council'
    (VLGAS), 'Alpine Shire' (LGPRF), 'Alpine' (ABS). Stripping the status words
    and punctuation reconciles all 79 with no manual exceptions.
    """
    s = re.sub(r"\b(Shire|Rural City|City|Council|Borough|of)\b", "", str(name))
    return re.sub(r"[^a-z]", "", s.lower())


def num(s):
    return pd.to_numeric(s, errors="coerce")


# ---------------------------------------------------------------- VLGAS panel
vl = pd.read_excel(VLGAS, sheet_name="VLGAS v2025.03")
vl.columns = [c.strip() for c in vl.columns]
vl["key"] = vl["council"].map(key)

TONNE_COLS = {
    "garbage_collected_total_tonnes": "garbage_t",
    "kerbside_recycling_total_collected_tonnes": "recycling_t",
    "kerbside_recycling_total_recycled_tonnes": "recycled_t",
    "kerbside_organics_collected_tonnes": "organics_t",
    "kerbside_glass_total_collected_tonnes": "glass_t",
    "hardwaste_collected_tonnes": "hardwaste_t",
    "kerbside_recycling_glass_all_recycled_tonnes": "rec_glass_t",
    "kerbside_recycling_metal_recycled_tonnes": "rec_metal_t",
    "kerbside_recycling_paper_all_recycled_tonnes": "rec_paper_t",
    "kerbside_recycling_plastics_all_recycled_tonnes": "rec_plastic_t",
}

panel = pd.DataFrame({
    "financial_year": vl["financial_year"],
    "key": vl["key"],
    "council": vl["council"].str.replace(r"\s+Council$", "", regex=True),
    "population": num(vl["Population"]),
    "households": num(vl["premises_residential"]),
})
for src, dst in TONNE_COLS.items():
    panel[dst] = num(vl[src])

panel["has_organics"] = panel["organics_t"].fillna(0) > 0
panel["has_glass"] = panel["glass_t"].fillna(0) > 0
panel["fogo"] = (
    vl["kerbside_organics_fogo_included"].astype(str).str.strip().str.lower() == "yes"
)
panel["streams"] = 2 + panel["has_organics"].astype(int) + panel["has_glass"].astype(int)

# Diversion computed the VLGAS way: everything that is not garbage, over the total.
collected = panel[["garbage_t", "recycling_t", "organics_t", "glass_t"]].fillna(0)
panel["total_kerbside_t"] = collected.sum(axis=1)
panel["diverted_t"] = panel["total_kerbside_t"] - collected["garbage_t"]
panel["diversion_pct"] = np.where(
    panel["total_kerbside_t"] > 0,
    100 * panel["diverted_t"] / panel["total_kerbside_t"],
    np.nan,
)
panel["kg_per_capita"] = np.where(
    panel["population"] > 0, 1000 * panel["total_kerbside_t"] / panel["population"], np.nan
)
panel["garbage_kg_per_capita"] = np.where(
    panel["population"] > 0, 1000 * panel["garbage_t"] / panel["population"], np.nan
)

panel.round(3).to_csv(OUT / "council_waste_panel_2001_2024.csv", index=False)

# ----------------------------------------------------- LGPRF cost / diversion
WC = {
    "WC2": "bins_missed_per_1000",
    "WC3": "garbage_cost_per_bin",
    "WC4": "recycling_cost_per_bin",
    "WC5": "lgprf_diversion_pct",
}

cost_years = []
for sheet, fy in [
    ("Indicators 2020-21", "2020-2021"),
    ("Indicators 2021-22", "2021-2022"),
    ("Indicators 2022-23", "2022-2023"),
    ("Indicators 2023-24", "2023-2024"),
    ("Indicators 2024-25", "2024-2025"),
]:
    lg = pd.read_excel(LGPRF, sheet_name=sheet)
    lg.columns = [str(c).strip() for c in lg.columns]
    w = lg[lg["ID"].isin(WC)].copy()
    w["Result"] = num(w["Result"])
    p = w.pivot_table(index=["Council", "Group"], columns="ID", values="Result").reset_index()
    p = p.rename(columns=WC)
    p["financial_year"] = fy
    cost_years.append(p)

cost = pd.concat(cost_years, ignore_index=True)
cost["lgprf_diversion_pct"] = cost["lgprf_diversion_pct"] * 100
cost["key"] = cost["Council"].map(key)
# LGPRF group labels changed case between years; settle on title case.
cost["group"] = cost["Group"].astype(str).str.replace("_", " ").str.title()
cost["metro_regional"] = np.where(
    cost["group"].isin(["Metro", "Interface"]), "Metropolitan", "Regional"
)
cost = cost.drop(columns=["Group"])
cost.round(3).to_csv(OUT / "council_cost_diversion_2020_2025.csv", index=False)

# --------------------------------------------------------- latest-year joined
latest_waste = panel[panel.financial_year == LATEST_WASTE_YEAR]
latest_cost = cost[cost.financial_year == "2024-2025"]
cen = pd.read_csv(GEO / "vic_lga_centroids.csv", dtype={"lga_code": str})
cen["key"] = cen["lga_name"].map(key)

snap = (
    latest_cost.drop(columns=["financial_year"])
    .merge(latest_waste.drop(columns=["council"]), on="key", how="left")
    .merge(cen[["key", "lga_code", "lga_name", "lon", "lat"]], on="key", how="left")
)

# ---------------------------------------- distance to nearest processing site
infra = pd.read_csv(INFRA, encoding="utf-8-sig")
infra.columns = [c.strip() for c in infra.columns]
infra.to_csv(OUT / "waste_infrastructure.csv", index=False)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    )
    return 2 * r * np.arcsin(np.sqrt(a))


mrf = infra[infra["Facility Type"] == "MRF"]
org = infra[infra["Infrastructure Type"] == "Organics recycling"]

snap["km_to_mrf"] = [
    haversine_km(r.lat, r.lon, mrf.Latitude.values, mrf.Longitude.values).min()
    if pd.notna(r.lat) else np.nan
    for r in snap.itertuples()
]
snap["km_to_organics"] = [
    haversine_km(r.lat, r.lon, org.Latitude.values, org.Longitude.values).min()
    if pd.notna(r.lat) else np.nan
    for r in snap.itertuples()
]

# The flow map needs the coordinates of that nearest plant, not just how far
# away it is, so record which one it was while the distance matrix is to hand.
_near = []
for r in snap.itertuples():
    if pd.isna(r.lat):
        _near.append((np.nan, np.nan, None, None))
        continue
    d = haversine_km(r.lat, r.lon, org.Latitude.values, org.Longitude.values)
    j = int(d.argmin())
    f = org.iloc[j]
    _near.append((f.Longitude, f.Latitude, f["Facility Name"], f["Suburb"]))
snap[["org_lon", "org_lat", "org_name", "org_suburb"]] = pd.DataFrame(
    _near, index=snap.index
)

# ------------------------------------------------------------------- SEIFA
# ABS socio-economic indexes, 2021 Census, by 2021 LGA boundaries.
seifa = pd.read_csv(SEIFA)
seifa = seifa[(seifa.SEIFA_MEASURE == "SCORE") & (seifa.TIME_PERIOD == 2021)]
seifa = seifa.pivot_table(
    index="LGA_2021", columns="SEIFAINDEXTYPE", values="OBS_VALUE"
)
seifa.index = seifa.index.astype(str)
seifa = seifa.rename(columns={
    "IRSD": "seifa_disadvantage",      # lower = more disadvantaged
    "IRSAD": "seifa_advantage",
    "IEO": "seifa_education",
    "IER": "seifa_resources",
})

# Moreland was renamed Merri-bek in 2022, so its 2021 SEIFA code differs from
# its 2025 boundary code. This is the only Victorian council affected.
seifa = seifa.rename(index={"25250": "24700"})

snap = snap.merge(seifa, left_on="lga_code", right_index=True, how="left")

# Terciles for the bivariate choropleth. Vega-Lite can bin, but it cannot
# easily cross two binnings into one class field, so do it here.
snap["seifa_tercile"] = pd.qcut(
    snap.seifa_disadvantage, 3, labels=["low", "mid", "high"]
)
snap["diversion_tercile"] = pd.qcut(
    snap.lgprf_diversion_pct, 3, labels=["low", "mid", "high"]
)
snap["bivariate_class"] = (
    snap.seifa_tercile.astype(str) + "-" + snap.diversion_tercile.astype(str)
)

# Stable jitter for the beeswarm. Vega-Lite's random() reshuffles on every
# redraw, which would stop the built page matching the submitted sketch.
rng = np.random.default_rng(3179)
snap["jitter"] = rng.uniform(-1, 1, len(snap)).round(4)

# Ranks and per-household rates for the "find your council" scorecard. Rank 1
# is the best diverter; cost rank 1 is the cheapest garbage bin.
snap["diversion_rank"] = snap.lgprf_diversion_pct.rank(
    ascending=False, method="min").astype("Int64")
snap["cost_rank"] = snap.garbage_cost_per_bin.rank(
    ascending=True, method="min").astype("Int64")
snap["kg_per_household"] = np.where(
    snap.households > 0, 1000 * snap.total_kerbside_t / snap.households, np.nan)
snap["kg_per_household_week"] = (snap.kg_per_household / 52).round(1)

# Three councils have a glass bin but no green bin, so "two bins" (10 councils)
# and "no green bin" (13) are different sets. The page kept conflating them.
snap["service_label"] = np.select(
    [(snap.streams == 2),
     (~snap.has_organics.astype(bool)) & (snap.has_glass.astype(bool)),
     (snap.has_organics.astype(bool)) & (~snap.has_glass.astype(bool)),
     (snap.has_organics.astype(bool)) & (snap.has_glass.astype(bool))],
    ["Garbage and recycling only",
     "Glass bin but no green bin",
     "Green bin, no glass",
     "All four bins"],
    default="Green bin, no glass",
)

snap.round(3).to_csv(OUT / "council_snapshot_latest.csv", index=False)

# -------------------------------------------------- statewide yearly totals
# Drives the policy-impact charts. "not recovered" is collected recycling minus
# recycling actually recovered: contamination plus process loss, not one or the
# other, so label it carefully on the page.
sw = panel.groupby("financial_year", as_index=False).agg(
    garbage_t=("garbage_t", "sum"),
    recycling_t=("recycling_t", "sum"),
    recycled_t=("recycled_t", "sum"),
    organics_t=("organics_t", "sum"),
    glass_t=("glass_t", "sum"),
    population=("population", "sum"),
    councils_with_organics=("has_organics", "sum"),
    councils_with_glass=("has_glass", "sum"),
    councils_with_fogo=("fogo", "sum"),
)
sw["year_end"] = sw.financial_year.str[-4:].astype(int)
sw["total_kerbside_t"] = sw[["garbage_t", "recycling_t", "organics_t", "glass_t"]].sum(axis=1)
sw["diversion_pct"] = 100 * (1 - sw.garbage_t / sw.total_kerbside_t)
sw["not_recovered_pct"] = np.where(
    sw.recycling_t > 0, 100 * (1 - sw.recycled_t / sw.recycling_t), np.nan
)
sw["kg_per_capita"] = np.where(
    sw.population > 0, 1000 * sw.total_kerbside_t / sw.population, np.nan
)
sw.round(3).to_csv(OUT / "statewide_by_year.csv", index=False)

# ------------------------------------------------------- waffle chart squares
# One row per percentage point of statewide kerbside tonnage. Far simpler to
# expand here than to try it with Vega-Lite transforms.
latest_sw = sw[sw.financial_year == LATEST_WASTE_YEAR].iloc[0]
streams = [
    ("Garbage", latest_sw.garbage_t),
    ("Organics", latest_sw.organics_t),
    ("Mixed recycling", latest_sw.recycling_t),
    ("Glass", latest_sw.glass_t),
]
total = sum(t for _, t in streams)
squares, i = [], 0
for name, tonnes in streams:
    n = round(100 * tonnes / total)
    for _ in range(n):
        squares.append({"stream": name, "i": i, "row": i // 10, "col": i % 10})
        i += 1
while len(squares) < 100:                       # rounding slack
    squares.append({"stream": streams[-1][0], "i": len(squares),
                    "row": len(squares) // 10, "col": len(squares) % 10})
pd.DataFrame(squares[:100]).to_csv(OUT / "waffle_streams.csv", index=False)

# --------------------------------------------- council streams, selected years
# Drives the small-multiples rollout map.
roll = panel[panel.financial_year >= "2015-2016"].copy()
roll = roll.merge(
    snap[["key", "lga_code"]], on="key", how="left"
)[["financial_year", "council", "lga_code", "streams", "has_organics",
     "has_glass", "fogo"]]
roll["year_end"] = roll.financial_year.str[-4:].astype(int)

# Two different things happened over the rollout and they are easy to conflate:
# councils gaining a green bin at all (52 -> 66) and councils whose green bin
# started accepting food as well as garden waste (3 -> 55). The service level
# below keeps them apart.
roll["service"] = np.select(
    [~roll.has_organics,
     roll.has_organics & ~roll.fogo,
     roll.has_organics & roll.fogo & ~roll.has_glass,
     roll.has_organics & roll.fogo & roll.has_glass],
    ["No green bin", "Garden only", "Food and garden", "Food, garden and glass"],
    default="Garden only",
)
roll.to_csv(OUT / "rollout_by_year.csv", index=False)

# councils on three or more bins each year, for the timeline under the map
rollout_counts = (
    roll.groupby(["financial_year", "year_end"], as_index=False)
        .agg(with_organics=("has_organics", "sum"),
             with_fogo=("fogo", "sum"),
             with_glass=("has_glass", "sum"))
)
rollout_counts.to_csv(OUT / "rollout_counts.csv", index=False)

# ------------------------------------------------------- Dorling cartogram
# Each council becomes a circle sized by households, nudged apart until none
# overlap while staying as close to its real centroid as possible. Vega-Lite
# has no force layout, so the positions are solved here and shipped as x/y.
# See Course Notes 16f: Dorling cartograms trade shape for comparable area,
# which is what fixes the unreadable metropolitan cluster.
def dorling(lon, lat, value, settle=1200, polish=400,
            strength=0.7, gravity=0.0015, rscale=0.25, rmin=0.030):
    """Solve Dorling circle positions.

    Repulsion alone lets the circles drift into a featureless cloud, which
    defeats the point: a Dorling only works if the reader still recognises the
    arrangement. So each pass pushes overlapping circles apart and then pulls
    every circle back toward its true centroid. Gravity is annealed to zero for
    the last few hundred passes, which clears the residual overlaps that the
    restoring force would otherwise hold in place.

    Settles to zero overlaps at a mean displacement of about 0.27 degrees.
    """
    ox = lon.astype(float).to_numpy()
    oy = lat.astype(float).to_numpy()
    x, y = ox.copy(), oy.copy()
    v = value.astype(float).to_numpy()
    r = np.sqrt(v / v.max()) * rscale + rmin
    ASPECT = 1.3                       # a degree of latitude is shorter here
    n = len(x)
    for t in range(settle + polish):
        g = gravity if t < settle else 0.0
        for i in range(n):
            dx = x - x[i]
            dy = (y - y[i]) * ASPECT
            d = np.hypot(dx, dy)
            overlap = (r + r[i]) * 1.02 - d
            hit = (overlap > 0) & (d > 1e-9)
            hit[i] = False
            if hit.any():
                push = overlap[hit] / d[hit] * strength
                x[i] -= (dx[hit] * push).sum() / hit.sum()
                y[i] -= (dy[hit] * push).sum() / hit.sum() / ASPECT
        if g:
            x += (ox - x) * g
            y += (oy - y) * g
    return x, y, r


dx, dy, dr = dorling(snap["lon"], snap["lat"], snap["total_kerbside_t"].fillna(1))
dorling_df = snap[["Council", "lga_name", "group", "garbage_cost_per_bin",
                   "lgprf_diversion_pct", "households", "total_kerbside_t",
                   "diverted_t", "garbage_t", "streams", "lon", "lat"]].copy()
# radius of the inner circle, so area is proportional to the tonnage diverted
dorling_df["diverted_share"] = (
    dorling_df.diverted_t / dorling_df.total_kerbside_t).round(4)
dorling_df["x"] = dx.round(4)
dorling_df["y"] = dy.round(4)
dorling_df["r"] = dr.round(4)
dorling_df["r_inner"] = (dr * np.sqrt(dorling_df.diverted_share)).round(4)
dorling_df.to_csv(OUT / "council_dorling.csv", index=False)

# ------------------------------------------------------- mosaic rectangles
# A real mosaic varies bar WIDTH by the group total as well as height by the
# share. The previous chart used uniform widths, which made it a 100% stacked
# bar -- a basic idiom under the brief, and it hid that Metro is 44% of state
# tonnage while Small Shire is 3%. Vega-Lite cannot cross a group-level
# cumulative sum with a within-group stack in one transform pipeline, so the
# rectangle corners are solved here and shipped as x/x2/y/y2.
STREAM_ORDER = ["Garbage", "Mixed recycling", "Organics", "Glass"]
_m = snap.melt(
    id_vars=["group"],
    value_vars=["garbage_t", "recycling_t", "organics_t", "glass_t"],
    var_name="col", value_name="t",
)
_m["Stream"] = _m.col.map({
    "garbage_t": "Garbage", "recycling_t": "Mixed recycling",
    "organics_t": "Organics", "glass_t": "Glass",
})
_m = _m.groupby(["group", "Stream"], as_index=False).t.sum()
_gt = _m.groupby("group").t.sum().sort_values(ascending=False)

GAP = 0.004                                  # a hairline between columns
rows, x = [], 0.0
for g, gt in _gt.items():
    w = gt / _gt.sum()
    y = 0.0
    for s in STREAM_ORDER:
        t = float(_m[(_m.group == g) & (_m.Stream == s)].t.sum())
        h = t / gt if gt else 0.0
        rows.append({
            "group": g, "Stream": s, "tonnes": round(t, 1),
            "x0": round(x, 5), "x1": round(x + w - GAP, 5),
            "y0": round(y, 5), "y1": round(y + h, 5),
            "xmid": round(x + (w - GAP) / 2, 5),
            "group_share": round(100 * w, 1),
            "stream_share": round(100 * h, 1),
        })
        y += h
    x += w
pd.DataFrame(rows).to_csv(OUT / "mosaic_streams.csv", index=False)

# ------------------------------------------- facilities per council area
# Drives the proportional-symbol map. 664 individual points is an unreadable
# smear over Melbourne, so aggregate to the council and size the circle by the
# count. Organics plants are split out because they are the ones that decide
# whether a green bin is feasible.
infra_lga = infra.copy()
infra_lga["key"] = infra_lga["LGA"].map(key)
infra_lga["is_organics"] = infra_lga["Infrastructure Type"] == "Organics recycling"
infra_lga["is_mrf"] = infra_lga["Facility Type"] == "MRF"
infra_lga["is_landfill"] = infra_lga["Facility Type"] == "Landfill"

fac = (
    infra_lga.groupby("key", as_index=False)
    .agg(facilities=("Facility Name", "size"),
         organics_plants=("is_organics", "sum"),
         mrfs=("is_mrf", "sum"),
         landfills=("is_landfill", "sum"))
)
fac = cen[["key", "lga_code", "lga_name", "lon", "lat"]].merge(fac, on="key", how="left")
fac[["facilities", "organics_plants", "mrfs", "landfills"]] = (
    fac[["facilities", "organics_plants", "mrfs", "landfills"]].fillna(0).astype(int)
)
fac = fac.merge(snap[["key", "Council", "group"]], on="key", how="left")
fac.to_csv(OUT / "facilities_by_lga.csv", index=False)

# --------------------------------------------- flow map: 13 councils -> plant
# One row per council with no green bin: where it is, where the nearest
# organics plant is, and how far. Yarra is the point of the chart -- it is
# 12 km from a plant, closer than the median council that has a green bin.
flow = snap.loc[
    ~snap.has_organics.astype(bool),
    ["Council", "lga_code", "group", "lon", "lat", "org_lon", "org_lat",
     "org_name", "org_suburb", "km_to_organics", "lgprf_diversion_pct",
     "streams", "has_glass", "service_label"],
].copy()
flow = flow.sort_values("km_to_organics")
flow.round(4).to_csv(OUT / "no_green_bin_flows.csv", index=False)

# ------------------------------------------------------------------- summary
unmatched = snap[snap.lga_code.isna()]
print(f"panel      {len(panel):5d} rows  {panel.financial_year.nunique()} years")
print(f"cost       {len(cost):5d} rows  {cost.financial_year.nunique()} years")
print(f"snapshot   {len(snap):5d} councils, {len(unmatched)} unmatched to geography")
print(f"infra      {len(infra):5d} facilities")
print(f"seifa      {snap.seifa_disadvantage.notna().sum():5d} of {len(snap)} councils matched")
print(f"statewide  {len(sw):5d} years")
print(f"dorling    {len(dorling_df):5d} circles")
print(f"facilities {len(fac):5d} council areas, {fac.facilities.sum()} sites")
print(f"flows      {len(flow):5d} councils with no green bin")
if len(unmatched):
    print("UNMATCHED:", unmatched.Council.tolist())
