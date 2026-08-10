# Africa Mining Watch — design tokens

Extracted from the live site on 2026-08-10:
`https://africaminingwatch-ui-git-am-map-updates-earth-genome.vercel.app/`

## Colour

Taken from the site's CSS custom properties, its computed styles, and the logo SVG
(`/_next/static/media/africaminingwatch.*.svg`).

| Role | Hex | Where it comes from |
|---|---|---|
| Page ground | `#EFEEEC` | `--color-background` |
| Ink | `#0E2129` | logo fill, body text |
| Brand blue | `#2054C5` | logo fill |
| Brand red | `#F71723` | logo fill |
| Link navy | `#284586` | anchor colour |
| Rule / grid | `#C6C8C9` | `--grid-line-color` |
| Muted grey | `#9CA3AF` | secondary text |

The site is **light-only**, and so is our page — deliberately. There is no dark token
set: `color-scheme: light` is pinned on `:root`, `[data-theme="dark"]` and
`[data-theme="light"]` alike, so the page stays on the brand ground whatever the
viewer's OS preference or theme toggle says. If a dark variant is ever wanted, build
it from the brand ink `#0E2129` as the card surface rather than inverting the light one.

## Type

Both faces are variable (weight 100–900), served by the site as Latin subsets and
vendored here under `fonts/`. Geist is SIL OFL 1.1, so embedding is permitted.

| Role | Family | File |
|---|---|---|
| Sans — headings, body | Geist | `fonts/geist-latin.woff2` (29 KB) |
| Mono — labels, tables, numbers | Geist Mono | `fonts/geist-mono-latin.woff2` (23 KB) |

`build_page.py` inlines both as base64 `@font-face` sources, because the published
page runs under a CSP that blocks font CDNs. Every accented character in the district
names (è é ï ô) falls inside U+0–FF, so the Latin subset alone is sufficient — verify
this again if the boundary set ever gains Latin Extended names.

Headline setting matches the site: weight 700, `-0.02em` tracking.

## Data-visualisation palette

The brand gives no chart palette, so these were derived from it and checked with the
`dataviz` validator (adjacent CVD ΔE, normal-vision floor, lightness band, contrast).

**Sequential ramp** — one hue, stepped off the brand red, for detection magnitude.
Red carries "intensity of harm" and is the brand's own alert colour, which leaves
blue free for the region layer.

In use (on `#EFEEEC`), with the dark steps kept only for a possible future variant:

| Step | In use | (unused dark step) |
|---|---|---|
| 1 | `#FBDCD6` | `#3D1416` |
| 2 | `#F7BCB2` | `#5C1A1D` |
| 3 | `#F2968B` | `#812226` |
| 4 | `#E96A60` | `#A82F30` |
| 5 | `#D93B36` | `#CC4A44` |
| 6 | `#B21F22` | `#E8766C` |
| 7 | `#7D1418` | `#F7A79C` |

Both ramps are monotonic in OKLab lightness with even steps (Δ ≈ 0.07–0.11).

**Categorical pair** — the two surveys, used only on the individual-footprint layer.

| Survey | In use | (unused dark step) |
|---|---|---|
| West Africa | `#2054C5` (brand blue, unchanged) | `#4F88E5` |
| Congo Basin | `#12977F` | `#14A884` |

Both pairs clear every validator gate in both modes (worst CVD ΔE 22.5 light /
17.6 dark, against a floor of 8). The two surveys are also geographically separate
and separately labelled, so identity never rests on hue alone.

**Protected-area overlay** — `#1F8551`, stroke only.

Green beside red is the classic colour-vision trap, so this one was checked
against the ramp specifically: `#1F8551` vs the ramp mid `#D93B36` measures CVD
ΔE 8.4 (deutan), just clear of the floor of 8, and ΔE 28.8 against the darkest
step. That is thin enough that hue is not allowed to carry the layer on its own,
so the overlay uses three further channels: it is a **stroke, not a fill**
(different mark type from the choropleth), protected areas **with** detections
draw solid at 2px while those **without** draw dashed at 1.4px, and the legend
names the layer whenever it is switched on.
