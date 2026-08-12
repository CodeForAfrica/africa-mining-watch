# Africa Mining Watch — mining detections by administrative area

Where satellite-detected mining sits on the administrative map of West Africa and
the Congo Basin, and how unevenly it is spread.

**Live map:** https://codeforafrica.github.io/africa-mining-watch/

Published by GitHub Actions on every push to `main` - see
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml). The Mapbox token
comes from the `MAPBOX_TOKEN` repository secret and is never committed.

Two Earth Index surveys mapped the ground scars left by mining across fourteen
countries. This repository holds the interactive map built from them, the tables
every figure on it comes from, and the pipeline that produced both.

## Headline figures

| | |
|---|---|
| Total detections | **12,874** distinct mining footprints |
| Ground disturbed | **868,110 ha** (8,681 km²) |
| Administrative areas affected | **994 of 3,615** (27.5%) |
| Countries affected | **14 of 14** |

Read [`docs/SUMMARY.md`](docs/SUMMARY.md) before quoting any of these. It records
the method, the rankings, and four caveats that matter — in particular that a
single dissolved polygon accounts for 20% of all detected area, and that
"detected" is not the same as "mining".

## What is here

```
index.html              the map; self-contained apart from the optional satellite layer
data/                   the derived tables - every figure on the page
  detections_by_admin.csv       994 rows, one per affected administrative area
  detections_by_admin.geojson   all 3,615 areas with counts, colour-coded
  detections_by_country.csv     14 rows
  detection_points.csv          12,874 rows, one interior point per footprint
  summary.json                  headline figures, machine-readable
pipeline/               the analysis, re-runnable
docs/                   method, caveats, and the design tokens
```

## Sources

| Layer | Source | Licence |
|---|---|---|
| Mining detections | [Earth Index](https://www.earthgenome.org/earth-index), Earth Genome — Congo Basin survey 2026-06-17, West Africa survey 2026-06-24 | see Earth Genome |
| Administrative boundaries | [geoBoundaries](https://www.geoboundaries.org/) ADM2/ADM3, 3,615 units | CC BY 4.0 |
| Africa outline | [Natural Earth](https://www.naturalearthdata.com/) countries | public domain |
| Protected areas *(optional)* | [WDPA](https://www.protectedplanet.net/), UNEP-WCMC & IUCN | not redistributable — see below |

**Licence:** the code is MIT, the derived tables in `data/` are CC BY 4.0, and
neither covers the third-party inputs above. See [`LICENSE`](LICENSE) and
[`LICENSE-DATA.md`](LICENSE-DATA.md).

Areas are measured on ESRI:102022 (Africa Albers Equal Area Conic), checked
against geodesic areas to within 0.000%.

The raw detection files and the full boundary file are **not committed here** —
they belong to Earth Genome and geoBoundaries respectively, and the boundary file
alone is 29 MB. Get them from the sources above and drop them where
`pipeline/analyse.py` expects them.

### A note on "administrative area"

The boundary file mixes levels: ADM2 for eight countries, ADM3 for six. What the
unit is called locally therefore varies — districts in Ghana and Liberia,
territories in DR Congo, chiefdoms in Sierra Leone, local government areas in
Nigeria, sub-prefectures in Guinea and Côte d'Ivoire, prefectures in Togo,
departments in Gabon. The map and tables use the neutral "administrative area",
and every row carries `shapeType` of `ADM2` or `ADM3` so the level is explicit.

## Rebuilding

Requires Python 3 with `geopandas` and `pandas`.

```bash
python3 pipeline/analyse.py          # spatial join, clipping, aggregation
python3 pipeline/export_map_data.py  # compact geometry payload for the map
python3 pipeline/build_page.py       # inline payload + fonts into index.html
```

`data/map_data.json` is committed, so `build_page.py` alone will regenerate
`index.html` without needing the raw source data.

## Satellite view

The map has a **Satellite imagery** toggle. With no Mapbox token supplied at
build time it uses **Esri World Imagery**, which needs no key; build with a token
and it uses **Mapbox Satellite** instead. Attribution for whichever service is in
use is shown on the map whenever the layer is on, as both require.

Zoom reaches tile level 16, which is close enough to make individual workings
visible. The boundaries are simplified to about 440 m so they go blocky well
before that - acceptable, because at that range the imagery is what you are
reading.

This is why the map is drawn in **Web Mercator** rather than plate carree: tile
services publish in Mercator, and imagery would not line up under the vectors
otherwise. Areas are still measured on Africa Albers - only the display
projection changed.

### Building with Mapbox

**No Mapbox token is committed to this repository.** GitHub push protection
blocks Mapbox tokens, and it is right to - a token in git outlives its usefulness
and is trivially scraped. The token is injected at build time:

```bash
export MAPBOX_TOKEN=pk.your_token_here      # or:
echo 'pk.your_token_here' > pipeline/mapbox_token.txt
python3 pipeline/build_page.py
```

That writes **`index.mapbox.html`**, which carries the token. `index.html` - the
one committed and served on GitHub Pages - stays keyless. Both
`pipeline/mapbox_token.txt` and `*.mapbox.html` are git-ignored, and
`build_page.py` refuses to write the committed page if any Mapbox token is found
in it. `sk.` secret tokens are rejected outright: they grant account-wide access
and must never sit in a page.

If a token does not work on the origin the page is served from, the tiles 403,
and the toggle disables itself rather than sitting there dead.

**Deployment.** `.github/workflows/deploy.yml` builds on every push to `main` and
publishes the Pages artifact directly, injecting `MAPBOX_TOKEN` from repository
secrets. Nothing carrying a token is ever committed - which is required, not just
tidy: GitHub push protection blocks Mapbox tokens on any branch. Pages is set to
deploy from GitHub Actions, so the `gh-pages` branch is no longer used.

The live site uses a `cfa-eric` token restricted to the `codeforafrica.github.io`
origin, so it is inert if lifted from the page. The main site build will use the
`earthrise` token, restricted to `africaminingwatch.org`, via the same mechanism.

**On the shared token.** The Africa Mining Watch token on the `earthrise`
account is restricted to the `africaminingwatch.org` origin - verified: imagery
with that referer, `403 Forbidden` from GitHub Pages, localhost and no referer.
It is the right token for the build that ships to the main site, but it cannot
be used for local testing unless those origins are added to it in the Mapbox
dashboard. Use a separate unrestricted token for that.

## The GeoJSON layers

Two files, both served next to the map so **mapshaper**, **geojson.io** and
**QGIS** can open them straight from a URL:

| File | Features | Size | For |
|---|---|---|---|
| `detections_affected_areas.geojson` | 994 | 2.5 MB | the areas that have detections - start here |
| `detections_by_admin.geojson` | 3,615 | 7.1 MB | every surveyed area, including `detections: 0` |

    https://codeforafrica.github.io/africa-mining-watch/detections_affected_areas.geojson
    https://codeforafrica.github.io/africa-mining-watch/detections_by_admin.geojson

Styling travels with them two ways. simplestyle-spec fields (`fill`, `stroke`,
`title`, `description`) mean the file renders colour-coded on open, using the
same bins and ramp as the map. A `bin` index (`-1` for none, `0`-`6` for the
ramp steps) plus the raw numbers let QGIS and mapshaper drive their own
categorised or graduated styling instead.

Properties per feature: `shape_id`, `name`, `level`, `country`, `iso3`,
`detections`, `sites_hosted`, `mined_area_ha`, `largest_patch_ha`, `area_km2`,
`pct_area_mined`, `detections_per_1000km2`, `survey`, `bin`.

**Tool notes.** mapshaper renders either file colour-coded straight from the
URL. geojson.io ingests them and zooms to their extent, but its map preview did
not paint the polygons in testing, at either size - the data is there in its
JSON and Table panels, so it still works for inspection and export. QGIS handles
both without complaint; use the larger one there.

`sites_hosted` sums to exactly 12,874, the distinct footprint count.
`detections` sums higher, because a footprint straddling a boundary is counted
in each area it reaches.

Regenerate with `python3 pipeline/export_geojson.py`.

## Protected areas

The two protected-area questions — how many are touched, and which are worst hit —
need a WDPA extract, which is licence-gated and so is not in this repository.
[`wdpa/README.md`](wdpa/README.md) has the download steps.
Once the extracts are in place:

```bash
python3 pipeline/protected_areas.py
```

That writes the per-protected-area table and adds a **Show protected areas**
overlay to the map.

**The WDPA is not redistributable.** UNEP-WCMC does not permit passing the
database on without written permission, so this repository and the published page
carry only our derived statistics, and link out to Protected Planet for the
source boundaries. Keep it that way.

## Before publishing — checklist for maintainers

- [x] Licensing — code MIT, data CC BY 4.0. See [`LICENSE`](LICENSE) and
      [`LICENSE-DATA.md`](LICENSE-DATA.md). Swap the code licence to GPL-3.0 if
      you would rather match the org's plurality; it is a one-file change.
- [x] Geist font licence — `pipeline/fonts/OFL.txt` is in place; the fonts are
      embedded in `index.html` under the SIL Open Font License 1.1. See
      [`pipeline/fonts/NOTICE.md`](pipeline/fonts/NOTICE.md).
- [ ] Confirm with Earth Genome how they want the detection surveys credited.

## Credits

A collaboration between [Code for Africa](https://codeforafrica.org) and
[Earth Genome](https://www.earthgenome.org/), joint copyright holders. Detections
from Earth Index. Part of [Africa Mining Watch](https://africaminingwatch.org).
