#!/usr/bin/env python3
"""A standalone GeoJSON of detection counts per administrative area.

Written for other tools rather than for this page: drop it into mapshaper,
geojson.io or QGIS, or point them at its URL.

Every administrative area in the survey is included, including the 2,621 with
no detections, so the file describes the whole surveyed footprint rather than
only the affected part. Filter on `detections > 0` if you want just the latter.

Styling travels with the file two ways:
  * simplestyle-spec fields (`fill`, `stroke`, `title`, ...) which geojson.io
    and Mapbox honour, so it renders colour-coded the moment it loads
  * a `bin` index and the raw numbers, so QGIS or mapshaper can drive their own
    categorised or graduated styling

Outputs (data/)
  detections_by_admin.geojson
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
# Works in either layout: `data/` in the published repo, `analysis/` in the
# working folder the analysis was first written in.
OUT = next((ROOT / d for d in ("data", "analysis")
            if (ROOT / d / "detections_by_admin.csv").exists()), ROOT / "data")
BOUNDARIES = ROOT / "GeoJSON boundaries - simplified.json"
EQUAL_AREA = "ESRI:102022"

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse import fix_mojibake, ISO3  # noqa: E402

SIMPLIFY = 0.002       # degrees, ~220 m: keeps shapes honest, keeps the file small
COORD_DP = 5           # ~1 m

# Same bins and ramp the map uses, so the file and the page agree.
BINS = [1, 2, 4, 8, 16, 40, 100]
RAMP = ["#fbdcd6", "#f7bcb2", "#f2968b", "#e96a60", "#d93b36", "#b21f22", "#7d1418"]
NO_DETECTIONS = "#dcdbd7"


def bin_of(v: float) -> int:
    i = -1
    for k, edge in enumerate(BINS):
        if v >= edge:
            i = k
    return i


def main() -> None:
    stats = pd.read_csv(OUT / "detections_by_admin.csv")

    print("loading boundaries ...")
    adm = gpd.read_file(BOUNDARIES)
    if adm.crs is None:
        adm = adm.set_crs("EPSG:4326")
    adm = adm[adm.geometry.notna() & ~adm.geometry.is_empty].copy()
    bad = ~adm.geometry.is_valid
    if bad.any():
        adm.loc[bad, "geometry"] = adm.loc[bad, "geometry"].buffer(0)
    adm["shapeName"] = adm["shapeName"].map(fix_mojibake)
    adm["country"] = adm["shapeGroup"].map(ISO3).fillna(adm["shapeGroup"])
    adm["area_km2"] = adm.to_crs(EQUAL_AREA).geometry.area / 1_000_000.0
    print(f"  {len(adm):,} administrative areas")

    merged = adm.merge(
        stats[["adm_id", "detections", "sites_hosted", "mined_area_ha",
               "largest_patch_ha", "pct_area_mined", "detections_per_1000km2",
               "region"]],
        left_on="shapeID", right_on="adm_id", how="left",
    )
    for c, fill in (("detections", 0), ("sites_hosted", 0), ("mined_area_ha", 0.0),
                    ("largest_patch_ha", 0.0), ("pct_area_mined", 0.0),
                    ("detections_per_1000km2", 0.0)):
        merged[c] = merged[c].fillna(fill)
    merged["region"] = merged["region"].fillna("no detections")
    hit = int((merged["detections"] > 0).sum())
    print(f"  {hit:,} with detections, {len(merged) - hit:,} without")

    merged["geometry"] = merged.geometry.simplify(SIMPLIFY, preserve_topology=True)

    features = []
    for r in merged.itertuples():
        d = int(r.detections)
        b = bin_of(d)
        colour = RAMP[b] if b >= 0 else NO_DETECTIONS
        geom = json.loads(gpd.GeoSeries([r.geometry], crs="EPSG:4326").to_json())
        geom = geom["features"][0]["geometry"]
        features.append({
            "type": "Feature",
            "properties": {
                # identity
                "shape_id": r.shapeID,
                "name": r.shapeName,
                "level": r.shapeType,
                "country": r.country,
                "iso3": r.shapeGroup,
                # the measures, same definitions as detections_by_admin.csv
                "detections": d,
                "sites_hosted": int(r.sites_hosted),
                "mined_area_ha": round(float(r.mined_area_ha), 1),
                "largest_patch_ha": round(float(r.largest_patch_ha), 1),
                "area_km2": round(float(r.area_km2), 1),
                "pct_area_mined": round(float(r.pct_area_mined), 3),
                "detections_per_1000km2": round(float(r.detections_per_1000km2), 2),
                "survey": r.region,
                # class index for your own styling: -1 = none, 0-6 = the map's bins
                "bin": b,
                # simplestyle-spec, honoured by geojson.io and Mapbox
                "title": f"{r.shapeName} ({r.country})",
                "description": f"{d:,} detections · "
                               f"{float(r.mined_area_ha):,.0f} ha mined · "
                               f"{float(r.pct_area_mined):.2f}% of area",
                "fill": colour,
                "fill-opacity": 0.85 if d else 0.35,
                "stroke": "#ffffff",
                "stroke-width": 0.5,
                "stroke-opacity": 0.8,
            },
            "geometry": geom,
        })

    fc = {
        "type": "FeatureCollection",
        "name": "africa_mining_watch_detections_by_admin",
        "crs": {"type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {
            "title": "Mining detections by administrative area",
            "source": "Africa Mining Watch / Code for Africa",
            "detections": "Earth Index (Earth Genome): Congo Basin 2026-06-17, "
                          "West Africa 2026-06-24",
            "boundaries": "geoBoundaries ADM2/ADM3, 14 countries",
            "areas_measured_on": EQUAL_AREA,
            "note": "detections counts footprints touching the area, so a footprint "
                    "straddling a boundary is counted in each area it reaches; "
                    "sites_hosted counts only those whose interior point falls inside, "
                    "and that column sums to the 12,874 distinct footprints",
            "colour_bins": {"edges": BINS, "ramp": RAMP, "no_detections": NO_DETECTIONS},
            "more": "https://codeforafrica.github.io/africa-mining-watch/",
        },
        "features": features,
    }

    path = OUT / "detections_by_admin.geojson"
    text = json.dumps(fc, ensure_ascii=False, separators=(",", ":"))
    # trim coordinate precision without touching the structure
    import re
    text = re.sub(r"-?\d+\.\d{%d,}" % (COORD_DP + 1),
                  lambda m: f"{float(m.group()):.{COORD_DP}f}".rstrip("0").rstrip("."),
                  text)
    path.write_text(text, encoding="utf-8")
    mb = path.stat().st_size / 1e6
    print(f"wrote {path.name}: {mb:.2f} MB, {len(features):,} features")


if __name__ == "__main__":
    main()
