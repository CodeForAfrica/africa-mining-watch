# Africa Mining Watch — mining detections by administrative area

Where satellite-detected mining sits on the administrative map of West Africa and
the Congo Basin, and how unevenly it is spread.

**Live map:** https://codeforafrica.github.io/africa-mining-watch/

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
index.html              the map, self-contained, no network dependencies
data/                   the derived tables - every figure on the page
  detections_by_admin.csv      994 rows, one per affected administrative area
  detections_by_country.csv    14 rows
  detection_points.csv         12,874 rows, one interior point per footprint
  summary.json                 headline figures, machine-readable
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

- [ ] Add a `LICENSE` for the code and data in this repo (not chosen here — CfA's call).
- [x] Geist font licence — `pipeline/fonts/OFL.txt` is in place; the fonts are
      embedded in `index.html` under the SIL Open Font License 1.1. See
      [`pipeline/fonts/NOTICE.md`](pipeline/fonts/NOTICE.md).
- [ ] Confirm with Earth Genome how they want the detection surveys credited.

## Credits

Analysis and map by Code for Africa. Detections by
[Earth Genome](https://www.earthgenome.org/) via Earth Index. Part of
[Africa Mining Watch](https://africaminingwatch.org).
