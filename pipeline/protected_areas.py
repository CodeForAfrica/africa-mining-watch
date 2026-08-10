#!/usr/bin/env python3
"""Mining detections inside protected areas.

This answers the two protected-area questions the administrative analysis cannot:
how many protected areas carry detected mining, and which ones carry the most.

It needs a WDPA extract, which is licence-gated and so is not in this repo.
Drop the downloaded country files anywhere under `wdpa/` and run:

    python3 pipeline/protected_areas.py

Any mix of .shp / .gpkg / .geojson / .gdb is fine, nested or flat - every file
found is read and concatenated, so the 14 per-country zips can just be unpacked
side by side.

Outputs (data/)
  detections_by_protected_area.csv   one row per protected area with >=1 detection
  protected_areas_summary.json       headline figures, machine-readable
"""
import json
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from analyse import EQUAL_AREA, ISO3, load_detections  # noqa: E402

WDPA_DIR = ROOT / "wdpa"
OUT = ROOT / "data"
READABLE = ("*.shp", "*.gpkg", "*.geojson", "*.json", "*.gdb")

# UNEP-WCMC's own guidance for calculating protected-area coverage. Each of
# these is a real methodological choice, so each is logged when it fires.
DROP_STATUS = {"Proposed"}                        # not yet protected
DROP_MARINE = {"2"}                               # purely marine, no land to mine
DROP_DESIG = {"UNESCO-MAB Biosphere Reserve"}      # transition zones aren't protected

WANTED_ISO3 = set(ISO3)


def find_inputs() -> list[Path]:
    if not WDPA_DIR.exists():
        return []
    hits: list[Path] = []
    for pat in READABLE:
        hits.extend(sorted(WDPA_DIR.rglob(pat)))
    # a .gdb is a directory; rglob on *.gdb catches it, but drop files inside one
    gdbs = {h for h in hits if h.suffix == ".gdb"}
    hits = [h for h in hits if not any(g in h.parents for g in gdbs)]
    return hits


def load_wdpa() -> gpd.GeoDataFrame:
    paths = find_inputs()
    if not paths:
        sys.exit(
            f"No WDPA files found under {WDPA_DIR}\n\n"
            "Download the protected areas for the 14 survey countries from\n"
            "  https://www.protectedplanet.net/country/<ISO3>\n"
            "(BEN CAF CIV CMR COD COG GAB GHA GIN GNQ LBR NGA SLE TGO)\n"
            "accept the terms, unpack the zips under wdpa/, and re-run."
        )

    frames = []
    for p in paths:
        try:
            gdf = gpd.read_file(p)
        except Exception as exc:                       # noqa: BLE001
            print(f"  skipped {p.name}: {exc}")
            continue
        if gdf.empty:
            continue
        gdf.columns = [c.upper() if c != gdf.geometry.name else c for c in gdf.columns]
        gdf["_SRC"] = p.name
        frames.append(gdf)
        print(f"  read {p.relative_to(WDPA_DIR)}: {len(gdf):,} features")

    if not frames:
        sys.exit("Found WDPA files but none could be read.")

    pa = pd.concat(frames, ignore_index=True)
    pa = gpd.GeoDataFrame(pa, geometry=frames[0].geometry.name,
                          crs=frames[0].crs or "EPSG:4326")
    if pa.crs is None:
        pa = pa.set_crs("EPSG:4326")
    return pa.to_crs("EPSG:4326")


def col(pa: gpd.GeoDataFrame, name: str, default=""):
    """WDPA field, or a constant if this extract lacks it."""
    return pa[name].astype(str) if name in pa.columns else pd.Series(default, index=pa.index)


def filter_wdpa(pa: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    n0 = len(pa)

    # Points are protected areas with no mapped boundary. They cannot be
    # overlaid, and dropping them silently would overstate coverage.
    is_poly = pa.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    n_points = int((~is_poly).sum())
    pa = pa[is_poly].copy()

    status = col(pa, "STATUS")
    marine = col(pa, "MARINE")
    desig = col(pa, "DESIG_ENG")
    iso = col(pa, "ISO3")

    keep = ~status.isin(DROP_STATUS) & ~marine.isin(DROP_MARINE) & ~desig.isin(DROP_DESIG)
    # transboundary sites carry codes like "COD;RWA"
    in_scope = iso.apply(lambda s: bool(WANTED_ISO3 & {t.strip() for t in s.replace(",", ";").split(";")}))
    if in_scope.any():
        keep &= in_scope
    else:
        print("  note: no ISO3 field matched the 14 countries; keeping all rows")

    print(f"  dropped {n_points:,} point-only protected areas (no boundary to overlay)")
    print(f"  dropped {int(status.isin(DROP_STATUS).sum()):,} with STATUS in {sorted(DROP_STATUS)}")
    print(f"  dropped {int(marine.isin(DROP_MARINE).sum()):,} purely marine (MARINE=2)")
    print(f"  dropped {int(desig.isin(DROP_DESIG).sum()):,} UNESCO-MAB biosphere reserves")

    pa = pa[keep].copy()

    bad = ~pa.geometry.is_valid
    if bad.any():
        pa.loc[bad, "geometry"] = pa.loc[bad, "geometry"].buffer(0)
        print(f"  repaired {int(bad.sum()):,} invalid protected-area polygons")
    pa = pa[pa.geometry.notna() & ~pa.geometry.is_empty]

    # stable identity and label regardless of which fields the extract carries
    pa["pa_id"] = col(pa, "WDPA_PID", "")
    blank = pa["pa_id"].isin(["", "nan", "None"])
    if blank.any():
        pa.loc[blank, "pa_id"] = col(pa, "WDPAID", "")[blank]
    still_blank = pa["pa_id"].isin(["", "nan", "None"])
    pa.loc[still_blank, "pa_id"] = ["auto-" + str(i) for i in pa.index[still_blank]]

    pa["pa_name"] = col(pa, "NAME", "(unnamed)")
    pa["designation"] = col(pa, "DESIG_ENG", "")
    pa["iucn_cat"] = col(pa, "IUCN_CAT", "")
    pa["status_yr"] = col(pa, "STATUS_YR", "")
    pa["iso3"] = col(pa, "ISO3", "")
    pa["country"] = pa["iso3"].apply(
        lambda s: " / ".join(ISO3.get(t.strip(), t.strip())
                             for t in s.replace(",", ";").split(";") if t.strip())
    )

    pa = pa.drop_duplicates(subset="pa_id", keep="first")
    print(f"  {len(pa):,} usable protected-area polygons (from {n0:,} features read)")
    return pa[["pa_id", "pa_name", "designation", "iucn_cat", "status_yr",
               "iso3", "country", "geometry"]]


def export_map_layer(pa: gpd.GeoDataFrame, by_pa: pd.DataFrame) -> None:
    """Simplified protected-area outlines for the map's overlay layer.

    Only boundaries and a name go out - no WDPA attribute table. The licence
    forbids redistributing the database, and the page only needs to draw the
    outlines and credit the source.
    """
    from export_map_data import rings                      # same ring encoder

    hit = set(by_pa["pa_id"])
    geo = pa.copy()
    geo["geometry"] = geo.geometry.simplify(0.004, preserve_topology=True)
    layer = []
    for _, r in geo.iterrows():
        rr = rings(r.geometry, 3)
        if rr:
            layer.append({"n": r["pa_name"], "d": r["designation"],
                          "h": 1 if r["pa_id"] in hit else 0, "r": rr})
    path = OUT / "protected_areas_map.json"
    path.write_text(json.dumps({"areas": layer}, separators=(",", ":"), ensure_ascii=True))
    print(f"wrote {path.name}: {len(layer):,} outlines, "
          f"{path.stat().st_size / 1e6:.2f} MB "
          f"({sum(a['h'] for a in layer):,} with detections)")


def main() -> None:
    print("loading protected areas ...")
    pa = filter_wdpa(load_wdpa())

    print("loading detections ...")
    det = load_detections()
    print(f"  {len(det):,} detection polygons")

    det_ea = det.to_crs(EQUAL_AREA)
    det["area_ha"] = det_ea.geometry.area / 10_000.0
    pa_ea = pa.to_crs(EQUAL_AREA)
    pa_ea["pa_area_km2"] = pa_ea.geometry.area / 1_000_000.0

    print("overlaying detections on protected areas ...")
    det_g = det[["det_id", "region", "geometry"]].to_crs(EQUAL_AREA)
    pairs = gpd.sjoin(det_g, pa_ea, how="inner", predicate="intersects")
    if pairs.empty:
        print("\nNo detection intersects any protected area in this extract.")
        return
    print(f"  {len(pairs):,} (footprint, protected area) pairs")

    pa_geom = pa_ea.set_index("pa_id").geometry
    left = det_g.set_index("det_id").geometry.loc[pairs["det_id"].values]
    right = pa_geom.loc[pairs["pa_id"].values]
    clipped = (
        gpd.GeoSeries(left.values, crs=EQUAL_AREA)
        .intersection(gpd.GeoSeries(right.values, crs=EQUAL_AREA), align=False)
        .area.values / 10_000.0
    )
    pairs = pairs.assign(clipped_ha=clipped)
    pairs = pairs[pairs["clipped_ha"] > 0.01]
    print(f"  {len(pairs):,} pairs after dropping <0.01 ha slivers")

    by_pa = (
        pairs.groupby(["pa_id", "pa_name", "designation", "iucn_cat",
                       "status_yr", "country", "pa_area_km2"], as_index=False)
        .agg(detections=("det_id", "nunique"),
             mined_area_ha=("clipped_ha", "sum"),
             largest_patch_ha=("clipped_ha", "max"))
    )
    by_pa["pct_pa_mined"] = by_pa["mined_area_ha"] / 100.0 / by_pa["pa_area_km2"] * 100.0
    by_pa["detections_per_1000km2"] = by_pa["detections"] / by_pa["pa_area_km2"] * 1000.0
    regions = pairs.groupby("pa_id")["region"].agg(lambda s: " + ".join(sorted(set(s))))
    by_pa["region"] = by_pa["pa_id"].map(regions)
    by_pa = by_pa.sort_values("detections", ascending=False).reset_index(drop=True)
    by_pa.insert(0, "rank", range(1, len(by_pa) + 1))

    # Protected areas overlap (a Ramsar site can sit inside a national park), so
    # the honest "total area mined inside protection" needs a dissolved union.
    print("dissolving protected areas for an unduplicated total ...")
    union = pa_ea.geometry.union_all() if hasattr(pa_ea.geometry, "union_all") \
        else pa_ea.geometry.unary_union
    inside = det_ea.geometry.intersection(union)
    mined_inside_ha = float(inside.area.sum() / 10_000.0)

    touched = int(len(by_pa))
    det_inside = int(pairs["det_id"].nunique())
    summary = {
        "protected_areas_in_extract": int(len(pa)),
        "protected_areas_with_detections": touched,
        "pct_protected_areas_with_detections": float(touched / len(pa) * 100) if len(pa) else 0.0,
        "detections_touching_a_protected_area": det_inside,
        "pct_of_all_detections_in_protected_areas": float(det_inside / len(det) * 100),
        "mined_area_inside_protected_areas_ha": mined_inside_ha,
        "mined_area_inside_protected_areas_pct_of_total": float(
            mined_inside_ha / det["area_ha"].sum() * 100),
        "total_detections": int(len(det)),
        "total_mined_area_ha": float(det["area_ha"].sum()),
        "most_impacted_by_detections": by_pa.head(10).drop(columns=["pa_id"]).to_dict("records"),
        "most_impacted_by_mined_area": by_pa.nlargest(10, "mined_area_ha")
            .drop(columns=["pa_id"]).to_dict("records"),
        "most_impacted_by_share_of_own_area": by_pa[by_pa.detections >= 5]
            .nlargest(10, "pct_pa_mined").drop(columns=["pa_id"]).to_dict("records"),
        "filters_applied": {
            "dropped_status": sorted(DROP_STATUS),
            "dropped_marine": sorted(DROP_MARINE),
            "dropped_designations": sorted(DROP_DESIG),
            "note": "points excluded (no boundary); overlapping areas dissolved for "
                    "the unduplicated total but kept separate for per-area ranking",
        },
    }

    by_pa.to_csv(OUT / "detections_by_protected_area.csv", index=False)
    (OUT / "protected_areas_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    export_map_layer(pa, by_pa)

    print("\n=== PROTECTED AREAS ===")
    print(f"protected areas in extract        {len(pa):,}")
    print(f"protected areas with detections   {touched:,} "
          f"({summary['pct_protected_areas_with_detections']:.1f}%)")
    print(f"detections inside a protected area{det_inside:>8,} "
          f"({summary['pct_of_all_detections_in_protected_areas']:.1f}% of {len(det):,})")
    print(f"mined area inside protection      {mined_inside_ha:,.0f} ha "
          f"({summary['mined_area_inside_protected_areas_pct_of_total']:.1f}% of all detected)")
    print("\n=== MOST IMPACTED, BY DETECTION COUNT ===")
    cols = ["rank", "pa_name", "country", "designation", "detections",
            "mined_area_ha", "pct_pa_mined"]
    print(by_pa[cols].head(15).to_string(
        index=False,
        formatters={"mined_area_ha": "{:,.0f}".format, "pct_pa_mined": "{:.2f}".format}))
    print("\nwrote detections_by_protected_area.csv and protected_areas_summary.json")


if __name__ == "__main__":
    main()
