#!/usr/bin/env python3
"""Build the compact geometry + metric payload the cluster map renders from.

Three layers, kept small enough to inline in a single self-contained page:
  countries  14 dissolved outlines, for context
  units      the admin units with >=1 detection, choropleth + cluster anchor
  points     every detection footprint as a single lon/lat, for the dot layer
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"
BOUNDARIES = ROOT / "GeoJSON boundaries - simplified.json"
EQUAL_AREA = "ESRI:102022"

COORD_DP = 3            # ~110 m, ample for a continental map
UNIT_TOLERANCE = 0.004  # degrees, ~440 m
COUNTRY_TOLERANCE = 0.01
CONTINENT_TOLERANCE = 0.02   # backdrop only, no need for coastline detail

# The 14 countries the two surveys cover, as ISO3.
SURVEYED_ISO3 = {"BEN", "CAF", "CIV", "CMR", "COD", "COG", "GAB",
                 "GHA", "GIN", "GNQ", "LBR", "NGA", "SLE", "TGO"}

AFRICA_CACHE = OUT / "africa_outline.geojson"


def africa_outline() -> gpd.GeoDataFrame:
    """Every African country, for the continental backdrop.

    Sourced once from the Natural Earth copy bundled with geopandas, then
    cached to disk so the build does not depend on `gpd.datasets`, which is
    deprecated and due for removal.
    """
    if AFRICA_CACHE.exists():
        return gpd.read_file(AFRICA_CACHE)

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    af = world[world["continent"] == "Africa"][["name", "iso_a3", "geometry"]].copy()
    af = af.to_crs("EPSG:4326")
    af.to_file(AFRICA_CACHE, driver="GeoJSON")
    print(f"  cached {AFRICA_CACHE.name} ({len(af)} countries)")
    return af

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse import fix_mojibake, ISO3  # noqa: E402


def rings(geom, dp=COORD_DP):
    """Flatten a (Multi)Polygon to a list of exterior rings as [x,y,x,y,...]."""
    if geom.is_empty:
        return []
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for p in polys:
        if not isinstance(p, Polygon) or p.is_empty:
            continue
        coords = []
        last = None
        for x, y in p.exterior.coords:
            xy = (round(x, dp), round(y, dp))
            if xy != last:            # drop points collapsed by rounding
                coords.extend(xy)
                last = xy
        if len(coords) >= 8:          # need >=4 distinct points for a shape
            out.append(coords)
    return out


def main() -> None:
    by_adm = pd.read_csv(OUT / "detections_by_admin.csv")
    summary = json.loads((OUT / "summary.json").read_text())

    adm = gpd.read_file(BOUNDARIES)
    if adm.crs is None:
        adm = adm.set_crs("EPSG:4326")
    adm = adm[adm.geometry.notna() & ~adm.geometry.is_empty].copy()
    bad = ~adm.geometry.is_valid
    if bad.any():
        adm.loc[bad, "geometry"] = adm.loc[bad, "geometry"].buffer(0)
    adm["shapeName"] = adm["shapeName"].map(fix_mojibake)
    adm["country"] = adm["shapeGroup"].map(ISO3).fillna(adm["shapeGroup"])

    countries = sorted(adm["country"].unique())
    cidx = {c: i for i, c in enumerate(countries)}

    # ---- layer 0: the whole continent, as context ------------------------
    print("building Africa backdrop ...")
    africa = africa_outline()
    africa["geometry"] = africa.geometry.simplify(CONTINENT_TOLERANCE,
                                                  preserve_topology=True)
    continent_layer = [
        {"n": r["name"],
         "s": 1 if r["iso_a3"] in SURVEYED_ISO3 else 0,
         "r": rings(r.geometry, 2)}
        for _, r in africa.iterrows()
    ]
    africa_bounds = [round(v, 3) for v in africa.total_bounds]

    # ---- layer 1: country outlines ---------------------------------------
    print("dissolving country outlines ...")
    diss = adm.dissolve(by="country").reset_index()
    diss["geometry"] = diss.geometry.simplify(COUNTRY_TOLERANCE, preserve_topology=True)
    country_layer = [
        {"n": r["country"], "r": rings(r.geometry, 2)}
        for _, r in diss.iterrows()
    ]

    # ---- layer 2: affected admin units -----------------------------------
    print("simplifying affected admin units ...")
    hit = adm.merge(by_adm, left_on="shapeID", right_on="adm_id", how="inner",
                    suffixes=("", "_agg"))
    hit["geometry"] = hit.geometry.simplify(UNIT_TOLERANCE, preserve_topology=True)
    # label/cluster anchor guaranteed to sit inside the unit
    anchor = hit.geometry.representative_point()
    hit["ax"] = anchor.x.round(3)
    hit["ay"] = anchor.y.round(3)

    unit_layer = []
    for _, r in hit.iterrows():
        rr = rings(r.geometry)
        if not rr:
            continue
        # 0 = West Africa survey only, 1 = Congo Basin only, 2 = both
        reg = r["region"]
        gcode = 2 if "+" in reg else (1 if reg == "Congo Basin" else 0)
        unit_layer.append({
            "n": r["shapeName"],
            "c": cidx[r["country"]],
            "t": r["shapeType"],
            "g": gcode,
            "d": int(r["detections"]),
            "h": int(r["sites_hosted"]),
            "a": round(float(r["mined_area_ha"]), 1),
            "k": round(float(r["adm_area_km2"]), 1),
            "dn": round(float(r["detections_per_1000km2"]), 2),
            "p": round(float(r["pct_area_mined"]), 2),
            "x": float(r["ax"]),
            "y": float(r["ay"]),
            "r": rr,
        })
    unit_layer.sort(key=lambda u: -u["d"])

    # ---- layer 3: raw detection points -----------------------------------
    pts = pd.read_csv(OUT / "detection_points.csv")
    point_layer = {
        "cb": [[round(r.lon, 3), round(r.lat, 3)]
               for r in pts[pts.region == "Congo Basin"].itertuples()],
        "wa": [[round(r.lon, 3), round(r.lat, 3)]
               for r in pts[pts.region == "West Africa"].itertuples()],
    }

    # ---- optional: protected areas, if protected_areas.py has been run -----
    pa_path = OUT / "protected_areas_map.json"
    protected = []
    if pa_path.exists():
        protected = json.loads(pa_path.read_text())["areas"]
        print(f"  including {len(protected):,} protected-area outlines")
    else:
        print("  no protected-area layer yet (run protected_areas.py to add it)")

    # ---- derived tables offered for download, for transparency -------------
    # Our own computed statistics only. The WDPA itself is not redistributable,
    # so the page links out to Protected Planet for the source geometry.
    downloads = []
    for fname, label in (
        ("detections_by_admin.csv", "Detections by administrative area"),
        ("detections_by_country.csv", "Detections by country"),
        ("detections_by_protected_area.csv", "Detections by protected area"),
    ):
        f = OUT / fname
        if f.exists():
            downloads.append({"f": fname, "l": label, "t": f.read_text()})
    print(f"  embedding {len(downloads)} downloadable tables")

    bounds = adm.total_bounds
    payload = {
        "meta": {
            "bounds": [round(v, 3) for v in bounds],
            "africaBounds": africa_bounds,
            "countries": countries,
            "summary": summary,
        },
        "continent": continent_layer,
        "protected": protected,
        "downloads": downloads,
        "countries": country_layer,
        "units": unit_layer,
        "points": point_layer,
    }

    path = OUT / "map_data.json"
    # ensure_ascii keeps every district name as a \uXXXX escape, so the page
    # renders correctly even when the host serves it without a charset header.
    path.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=True))
    mb = path.stat().st_size / 1e6
    print(f"wrote {path.name}: {mb:.2f} MB "
          f"({len(continent_layer)} African countries, {len(country_layer)} surveyed, "
          f"{len(unit_layer)} units, "
          f"{len(point_layer['cb']) + len(point_layer['wa']):,} points)")
    if mb > 12:
        print("WARNING: payload is large for a single page")


if __name__ == "__main__":
    main()
