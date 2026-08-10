# Put the WDPA extracts here

This folder is empty on purpose. The World Database on Protected Areas is
licence-gated, so it is not committed with the rest of the analysis.

## What to download

For each of the 14 survey countries, open

    https://www.protectedplanet.net/country/<ISO3>

and use the download button (top right of the country page). ISO3 codes:

    BEN  Benin
    CAF  Central African Republic
    CIV  Cote d'Ivoire
    CMR  Cameroon
    COD  DR Congo
    COG  Republic of the Congo
    GAB  Gabon
    GHA  Ghana
    GIN  Guinea
    GNQ  Equatorial Guinea
    LBR  Liberia
    NGA  Nigeria
    SLE  Sierra Leone
    TGO  Togo

Choose **shapefile** or **file geodatabase** - either works. You will have to
accept the terms and conditions first; the data is free for non-commercial use,
and commercial use needs written permission from UNEP-WCMC.

## What to do with them

Unpack the zips anywhere under this folder, nested or flat, then run

    python3 pipeline/protected_areas.py

Every readable file under `wdpa/` is loaded and concatenated, so the 14
country folders can just sit side by side. Points and polygons ship as separate
shapefiles inside each zip; both can be left in place - the script uses the
polygons and reports how many point-only areas it had to skip.

## Citation

    UNEP-WCMC and IUCN (2026), Protected Planet: The World Database on Protected
    Areas (WDPA), <month/year of your download>, Cambridge, UK: UNEP-WCMC and
    IUCN. Available at www.protectedplanet.net

Record the release month you downloaded - the WDPA is revised monthly, and
figures are not comparable across releases.
