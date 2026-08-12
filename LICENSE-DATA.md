# Data licence

The code in this repository is MIT — see [`LICENSE`](LICENSE). Software licences
are a poor fit for data, so the derived tables are licensed separately.

## What Code for Africa and Earth Genome license

Everything in `data/`:

- `detections_by_admin.csv`
- `detections_by_admin.geojson`
- `detections_affected_areas.geojson`
- `detections_by_country.csv`
- `detection_points.csv`
- `summary.json`

is released by Code for Africa and Earth Genome, as joint copyright holders, under
**Creative Commons Attribution 4.0 International (CC BY 4.0)**.

https://creativecommons.org/licenses/by/4.0/

You may share and adapt it, including commercially, provided you attribute it.
Suggested attribution:

> Mining detections by administrative area. Code for Africa and Earth Genome,
> Africa Mining Watch, 2026. https://codeforafrica.github.io/africa-mining-watch/
> Derived from Earth Index mining detections (Earth Genome) and geoBoundaries
> ADM2/ADM3. CC BY 4.0.

CC BY 4.0 was chosen rather than a more permissive dedication because the
boundaries these figures are attached to come from geoBoundaries under CC BY 4.0,
which requires attribution downstream. Keeping the same licence keeps that
obligation intact instead of quietly dropping it.

## What it does not cover

This repository cannot and does not relicense other people's work.

| Material | Holder | Terms |
|---|---|---|
| Earth Index mining detections (the source surveys, **not committed here**) | Earth Genome | Earth Genome's own terms — confirm with them before redistributing the raw surveys |
| Administrative boundaries, `GeoJSON boundaries - simplified.json` (**not committed here**) | geoBoundaries | CC BY 4.0 — https://www.geoboundaries.org/ |
| `data/africa_outline.geojson` | Natural Earth | public domain |
| `pipeline/fonts/geist-*.woff2` | Vercel | SIL Open Font License 1.1 — see [`pipeline/fonts/OFL.txt`](pipeline/fonts/OFL.txt) |
| Satellite imagery shown in the map | Esri / Maxar, or Mapbox / Maxar | the provider's terms; attribution is displayed in the map |
| Protected areas, if a WDPA extract is added under `wdpa/` | UNEP-WCMC and IUCN | **not redistributable** without written permission — see [`wdpa/README.md`](wdpa/README.md) |

The derived figures in `data/` are the project's own measurements over those
inputs, which is what makes them ours to license. The inputs themselves are not:
Earth Genome is a joint copyright holder here as a partner in this analysis, which
is separate from the terms on the raw Earth Index surveys listed above.

## A note on the detections

The detection surveys are Earth Genome's work and are deliberately not committed
to this repository. If you want them, get them from Earth Genome. If you are
publishing figures derived from them, credit Earth Index — and see the
["Read this before quoting the numbers"](docs/SUMMARY.md) caveats first, in
particular that a single dissolved polygon accounts for a fifth of all detected
area, and that a detected footprint is not proof of active mining.
