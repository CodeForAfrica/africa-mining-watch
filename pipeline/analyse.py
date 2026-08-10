#!/usr/bin/env python3
"""
Africa Mining Watch — summary statistics for the dissolved mining-detection layers,
aggregated onto geoBoundaries administrative units.

Inputs
  results/CongoBasin_EI_2026-06-17-dissolved.geojson
  results/WestAfrica_EI_2026-06-24-dissolved.geojson
  GeoJSON boundaries - simplified.json     (geoBoundaries ADM2/ADM3, 14 countries)

Outputs (data/)
  detections_by_admin.csv     one row per admin unit that contains >=1 detection
  detections_by_country.csv   country rollup
  summary.json                headline numbers
  clusters.json               compact payload for the map
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"

DETECTIONS = {
    "Congo Basin": ROOT / "results" / "CongoBasin_EI_2026-06-17-dissolved.geojson",
    "West Africa": ROOT / "results" / "WestAfrica_EI_2026-06-24-dissolved.geojson",
}
BOUNDARIES = ROOT / "GeoJSON boundaries - simplified.json"

# Africa Albers Equal Area Conic — areas in m^2 are trustworthy continent-wide.
EQUAL_AREA = "ESRI:102022"

ISO3 = {
    "BEN": "Benin", "CAF": "Central African Republic", "CIV": "Côte d'Ivoire",
    "CMR": "Cameroon", "COD": "DR Congo", "COG": "Republic of the Congo",
    "GAB": "Gabon", "GHA": "Ghana", "GIN": "Guinea", "GNQ": "Equatorial Guinea",
    "LBR": "Liberia", "NGA": "Nigeria", "SLE": "Sierra Leone", "TGO": "Togo",
}

# Detections further than this from any admin unit are genuinely outside the
# survey footprint rather than victims of boundary simplification.
SNAP_TOLERANCE_KM = 5.0


def fix_mojibake(value):
    """The boundaries file stores names as double-encoded UTF-8.

    "Bétaré" was written as UTF-8 (C3 A9), read back as latin-1 ("Ã©"), then
    re-encoded as UTF-8 (C3 83 C2 A9). Reverse that round-trip, repeatedly, as
    long as it keeps producing decodable text.
    """
    if not isinstance(value, str):
        return value
    for _ in range(3):
        try:
            repaired = value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if repaired == value:
            break
        value = repaired
    return value


def load_detections() -> gpd.GeoDataFrame:
    parts = []
    for region, path in DETECTIONS.items():
        gdf = gpd.read_file(path)
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        gdf["region"] = region
        gdf["source_file"] = path.name
        parts.append(gdf[["region", "source_file", "geometry"]])
    det = pd.concat(parts, ignore_index=True)
    det = gpd.GeoDataFrame(det, geometry="geometry", crs="EPSG:4326")
    det["det_id"] = range(1, len(det) + 1)
    return det


def load_boundaries() -> gpd.GeoDataFrame:
    adm = gpd.read_file(BOUNDARIES)
    if adm.crs is None:
        adm = adm.set_crs("EPSG:4326")
    adm = adm[adm.geometry.notna() & ~adm.geometry.is_empty].copy()
    # geoBoundaries polygons contain self-intersections; make them valid so the
    # spatial join does not silently drop units.
    invalid = ~adm.geometry.is_valid
    if invalid.any():
        adm.loc[invalid, "geometry"] = adm.loc[invalid, "geometry"].buffer(0)
        print(f"  repaired {int(invalid.sum())} invalid admin polygons")
    adm["shapeName"] = adm["shapeName"].map(fix_mojibake)
    adm["country"] = adm["shapeGroup"].map(ISO3).fillna(adm["shapeGroup"])
    adm["adm_id"] = adm["shapeID"]
    return adm


def main() -> None:
    print("loading detections ...")
    det = load_detections()
    print(f"  {len(det):,} detection polygons")

    print("loading admin boundaries ...")
    adm = load_boundaries()
    print(f"  {len(adm):,} admin units, {adm['country'].nunique()} countries")

    # ---- areas in an equal-area projection -------------------------------
    det_ea = det.to_crs(EQUAL_AREA)
    det["area_ha"] = det_ea.geometry.area / 10_000.0
    adm_ea = adm.to_crs(EQUAL_AREA)
    adm["adm_area_km2"] = adm_ea.geometry.area / 1_000_000.0

    # Representative point is guaranteed to fall inside the polygon (centroids
    # of crescent-shaped dissolved footprints are not).
    pts = det.copy()
    pts["geometry"] = det.geometry.representative_point()
    pts["lon"] = pts.geometry.x
    pts["lat"] = pts.geometry.y
    det["lon"] = pts["lon"].values
    det["lat"] = pts["lat"].values

    print("spatial join (detection point -> admin unit) ...")
    joined = gpd.sjoin(
        pts[["det_id", "region", "area_ha", "lon", "lat", "geometry"]],
        adm[["adm_id", "shapeName", "shapeType", "country", "shapeGroup",
             "adm_area_km2", "geometry"]],
        how="left",
        predicate="within",
    )
    # A point on a shared border can match two units; keep the first match so
    # every detection is counted exactly once.
    joined = joined.drop_duplicates(subset="det_id", keep="first")
    assert len(joined) == len(det), (len(joined), len(det))

    direct_hits = int(joined["adm_id"].notna().sum())
    print(f"  inside a unit: {direct_hits:,} / {len(joined):,}")

    # Points that land in a gap left by boundary simplification (coastlines,
    # river borders) are snapped to the nearest unit if it is close enough.
    gap = joined["adm_id"].isna()
    snapped_count = 0
    if gap.any():
        near = gpd.sjoin_nearest(
            pts.loc[pts["det_id"].isin(joined.loc[gap, "det_id"]),
                    ["det_id", "geometry"]].to_crs(EQUAL_AREA),
            adm[["adm_id", "shapeName", "shapeType", "country", "shapeGroup",
                 "adm_area_km2", "geometry"]].to_crs(EQUAL_AREA),
            how="left",
            distance_col="dist_m",
        ).drop_duplicates(subset="det_id", keep="first")

        within_tol = near[near["dist_m"] <= SNAP_TOLERANCE_KM * 1000.0]
        fill = within_tol.set_index("det_id")
        idx = joined.index[gap & joined["det_id"].isin(fill.index)]
        for col in ["adm_id", "shapeName", "shapeType", "country",
                    "shapeGroup", "adm_area_km2"]:
            joined.loc[idx, col] = joined.loc[idx, "det_id"].map(fill[col])
        snapped_count = len(idx)
        far = near[near["dist_m"] > SNAP_TOLERANCE_KM * 1000.0]
        print(f"  snapped to nearest unit (<= {SNAP_TOLERANCE_KM:g} km): "
              f"{snapped_count:,}"
              + (f" (max {within_tol['dist_m'].max()/1000:.2f} km)"
                 if snapped_count else ""))
        print(f"  left unassigned (> {SNAP_TOLERANCE_KM:g} km from any unit): "
              f"{len(far):,}")

    unmatched = joined["adm_id"].isna()
    print(f"  total assigned {int((~unmatched).sum()):,} / {len(joined):,}")

    matched = joined[~unmatched].copy()

    # ---- true intersection overlay ---------------------------------------
    # A dissolved footprint can straddle several units (the largest spans
    # ~128 km), so counting and area-attribution by centroid alone would put
    # the whole footprint in one district. Clip every footprint to every unit
    # it touches and attribute the clipped area.
    print("overlaying detection polygons on admin units ...")
    det_ea_g = det[["det_id", "region", "geometry"]].to_crs(EQUAL_AREA)
    adm_ea_g = adm[["adm_id", "shapeName", "shapeType", "country", "shapeGroup",
                    "adm_area_km2", "geometry"]].to_crs(EQUAL_AREA)
    pairs = gpd.sjoin(det_ea_g, adm_ea_g, how="inner", predicate="intersects")
    print(f"  {len(pairs):,} (footprint, unit) pairs")

    adm_geom = adm_ea_g.set_index("adm_id").geometry
    left = det_ea_g.set_index("det_id").geometry.loc[pairs["det_id"].values]
    right = adm_geom.loc[pairs["adm_id"].values]
    clipped_ha = (
        gpd.GeoSeries(left.values, crs=EQUAL_AREA)
        .intersection(gpd.GeoSeries(right.values, crs=EQUAL_AREA), align=False)
        .area.values / 10_000.0
    )
    pairs = pairs.assign(clipped_ha=clipped_ha)
    # Drop slivers from boundary imprecision, but never drop a real touch.
    pairs = pairs[pairs["clipped_ha"] > 0.01]

    # A footprint sitting entirely in a boundary-simplification gap produces no
    # usable intersection. Fall back to the snapped point assignment so no
    # footprint vanishes between the two aggregations.
    orphan_ids = set(det["det_id"]) - set(pairs["det_id"])
    if orphan_ids:
        fb = matched[matched["det_id"].isin(orphan_ids)].copy()
        fb["clipped_ha"] = fb["area_ha"]
        keep = ["det_id", "region", "adm_id", "shapeName", "shapeType",
                "country", "shapeGroup", "adm_area_km2", "clipped_ha"]
        pairs = pd.concat([pairs[keep], fb[keep]], ignore_index=True)
        print(f"  {len(orphan_ids)} footprints had no intersection; "
              f"assigned via their snapped district")
    assert set(det["det_id"]) == set(pairs["det_id"]), "a footprint went missing"

    print(f"  {len(pairs):,} pairs after dropping <0.01 ha slivers; "
          f"clipped area total {pairs['clipped_ha'].sum():,.0f} ha "
          f"vs raw {det['area_ha'].sum():,.0f} ha")

    # ---- per admin unit --------------------------------------------------
    # detections  = footprints touching the unit (a straddling footprint is
    #               counted in each unit it reaches, so this column sums to
    #               more than the 12,874 distinct footprints)
    # sites_hosted= footprints whose representative point sits in the unit;
    #               this column does sum to the distinct footprint total
    by_adm = (
        pairs.groupby(
            ["adm_id", "shapeName", "shapeType", "country", "shapeGroup",
             "adm_area_km2"],
            as_index=False,
        )
        .agg(detections=("det_id", "nunique"),
             mined_area_ha=("clipped_ha", "sum"),
             median_patch_ha=("clipped_ha", "median"),
             largest_patch_ha=("clipped_ha", "max"))
    )
    hosted = matched.groupby("adm_id")["det_id"].count()
    by_adm["sites_hosted"] = by_adm["adm_id"].map(hosted).fillna(0).astype(int)
    by_adm["detections_per_1000km2"] = (
        by_adm["detections"] / by_adm["adm_area_km2"] * 1000.0
    )
    by_adm["pct_area_mined"] = (
        by_adm["mined_area_ha"] / 100.0 / by_adm["adm_area_km2"] * 100.0
    )
    regions = (pairs.groupby("adm_id")["region"]
               .agg(lambda s: " + ".join(sorted(set(s)))))
    by_adm["region"] = by_adm["adm_id"].map(regions)
    by_adm = by_adm.sort_values("detections", ascending=False).reset_index(drop=True)
    by_adm.insert(0, "rank", range(1, len(by_adm) + 1))

    # ---- per country -----------------------------------------------------
    by_country = (
        pairs.groupby(["country", "shapeGroup"], as_index=False)
        .agg(detections=("det_id", "nunique"), mined_area_ha=("clipped_ha", "sum"))
    )
    units_hit = by_adm.groupby("country")["adm_id"].nunique()
    units_total = adm.groupby("country")["adm_id"].nunique()
    by_country["admin_units_with_detections"] = by_country["country"].map(units_hit)
    by_country["admin_units_total"] = by_country["country"].map(units_total)
    by_country["pct_admin_units_affected"] = (
        by_country["admin_units_with_detections"] / by_country["admin_units_total"] * 100.0
    )
    by_country = by_country.sort_values("detections", ascending=False).reset_index(drop=True)

    # ---- per region ------------------------------------------------------
    by_region = (
        det.groupby("region", as_index=False)
        .agg(detections=("det_id", "count"), mined_area_ha=("area_ha", "sum"))
    )

    # ---- data-quality flags ----------------------------------------------
    spans = pairs.groupby("det_id")["adm_id"].nunique()
    country_spans = pairs.groupby("det_id")["country"].nunique()
    biggest = det.loc[det["area_ha"].idxmax()]
    bx = biggest.geometry.bounds
    quality = {
        "footprint_admin_pairs": int(len(pairs)),
        "footprints_spanning_multiple_units": int((spans > 1).sum()),
        "max_units_spanned_by_one_footprint": int(spans.max()),
        "footprints_crossing_country_borders": int((country_spans > 1).sum()),
        "sum_of_country_detection_counts": int(by_country["detections"].sum()),
        "clipped_area_total_ha": float(pairs["clipped_ha"].sum()),
        "footprints_over_1000_ha": int((det["area_ha"] > 1000).sum()),
        "largest_footprint": {
            "area_ha": float(biggest["area_ha"]),
            "share_of_total_area_pct": float(biggest["area_ha"] / det["area_ha"].sum() * 100),
            "region": biggest["region"],
            "bbox": [round(v, 4) for v in bx],
            "bbox_span_km": [round((bx[2] - bx[0]) * 111.32 * 0.995, 1),
                             round((bx[3] - bx[1]) * 110.57, 1)],
            "admin_units_spanned": int(spans.get(biggest["det_id"], 0)),
            "note": "One dissolved feature merging many adjacent sites across "
                    "the Ghanaian gold belt; counts it as a single detection.",
        },
        "total_area_excl_largest_ha": float(det["area_ha"].sum() - biggest["area_ha"]),
    }

    # ---- headline numbers ------------------------------------------------
    summary = {
        "total_detections": int(len(det)),
        "total_mined_area_ha": float(det["area_ha"].sum()),
        "total_mined_area_km2": float(det["area_ha"].sum() / 100.0),
        "detections_matched_to_admin": int((~unmatched).sum()),
        "detections_inside_admin_directly": direct_hits,
        "detections_snapped_to_nearest_admin": int(snapped_count),
        "detections_outside_admin": int(unmatched.sum()),
        "admin_units_total": int(len(adm)),
        "admin_units_with_detections": int(len(by_adm)),
        "pct_admin_units_with_detections": float(len(by_adm) / len(adm) * 100.0),
        "countries_total": int(adm["country"].nunique()),
        "countries_with_detections": int(by_country["country"].nunique()),
        "survey_area_km2": float(adm["adm_area_km2"].sum()),
        "patch_area_ha": {
            "min": float(det["area_ha"].min()),
            "p25": float(det["area_ha"].quantile(0.25)),
            "median": float(det["area_ha"].median()),
            "mean": float(det["area_ha"].mean()),
            "p75": float(det["area_ha"].quantile(0.75)),
            "p95": float(det["area_ha"].quantile(0.95)),
            "max": float(det["area_ha"].max()),
        },
        "data_quality": quality,
        "by_region": by_region.to_dict("records"),
        "by_country": by_country.to_dict("records"),
        "top_admin_units": by_adm.head(20).drop(columns=["adm_id"]).to_dict("records"),
        "sources": {
            "congo_basin": DETECTIONS["Congo Basin"].name,
            "west_africa": DETECTIONS["West Africa"].name,
            "boundaries": BOUNDARIES.name,
            "equal_area_crs": EQUAL_AREA,
        },
    }

    OUT.mkdir(exist_ok=True)
    by_adm.to_csv(OUT / "detections_by_admin.csv", index=False)
    by_country.to_csv(OUT / "detections_by_country.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))

    # detection points, for the map's raw layer
    det[["det_id", "region", "lon", "lat", "area_ha"]].to_csv(
        OUT / "detection_points.csv", index=False
    )

    print("\n=== HEADLINE ===")
    print(f"total detections          {summary['total_detections']:,}")
    print(f"total mined area          {summary['total_mined_area_ha']:,.0f} ha "
          f"({summary['total_mined_area_km2']:,.0f} km2)")
    print(f"admin units affected      {summary['admin_units_with_detections']:,}"
          f" / {summary['admin_units_total']:,}"
          f" ({summary['pct_admin_units_with_detections']:.1f}%)")
    print(f"countries affected        {summary['countries_with_detections']}"
          f" / {summary['countries_total']}")
    print(f"outside all admin units   {summary['detections_outside_admin']:,}")
    print(f"footprints straddling >1 unit  {quality['footprints_spanning_multiple_units']:,}"
          f" (max {quality['max_units_spanned_by_one_footprint']} units)")
    lf = quality["largest_footprint"]
    print(f"largest single footprint  {lf['area_ha']:,.0f} ha "
          f"= {lf['share_of_total_area_pct']:.1f}% of all mined area, "
          f"spans {lf['bbox_span_km'][0]}x{lf['bbox_span_km'][1]} km "
          f"and {lf['admin_units_spanned']} admin units")
    print("\n=== TOP 15 ADMIN UNITS ===")
    cols = ["rank", "shapeName", "shapeType", "country", "detections",
            "sites_hosted", "mined_area_ha", "detections_per_1000km2"]
    print(by_adm[cols].head(15).to_string(index=False,
          formatters={"mined_area_ha": "{:,.0f}".format,
                      "detections_per_1000km2": "{:.2f}".format}))
    print("\n=== BY COUNTRY ===")
    print(by_country.to_string(index=False,
          formatters={"mined_area_ha": "{:,.0f}".format,
                      "pct_admin_units_affected": "{:.1f}".format}))


if __name__ == "__main__":
    main()
