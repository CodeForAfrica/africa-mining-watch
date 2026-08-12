#!/usr/bin/env python3
"""Inline map_data.json into template.html and write the finished page.

The output is deliberately pure ASCII: the page is published inside a wrapper
whose <head> we do not control, so we never rely on a charset declaration.
"""
from __future__ import annotations   # this runs on 3.9, where `str | None` would fail

import base64
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"

# The Africa Mining Watch faces, Latin subset, as the brand site serves them.
# Variable weight 100-900 in one file each. Geist is SIL OFL 1.1, so embedding
# is permitted; the CSP on the published page blocks any font CDN, hence base64.
FONTS = {
    "__FONT_SANS__": HERE / "fonts" / "geist-latin.woff2",
    "__FONT_MONO__": HERE / "fonts" / "geist-mono-latin.woff2",
}

# ---- satellite tiles ------------------------------------------------------
# The committed page uses Esri: no key, so nothing secret ever reaches the repo.
ESRI = {
    "url": "https://services.arcgisonline.com/ArcGIS/rest/services/"
           "World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "attr": "Imagery: Esri, Maxar, Earthstar Geographics and the GIS User Community",
}

# A Mapbox token is read from $MAPBOX_TOKEN or pipeline/mapbox_token.txt, both
# of which stay out of git. When one is present the build writes a SEPARATE,
# git-ignored page, so a token can never end up in the file that gets pushed.
TOKEN_FILE = HERE / "mapbox_token.txt"
LOCAL_OUTPUT = "index.local.html"


def mapbox_token() -> str | None:
    tok = (os.environ.get("MAPBOX_TOKEN") or "").strip()
    if not tok and TOKEN_FILE.exists():
        tok = TOKEN_FILE.read_text().strip()
    if not tok:
        return None
    if not re.fullmatch(r"(pk|sk)\.[A-Za-z0-9._-]+", tok):
        raise SystemExit(f"MAPBOX_TOKEN does not look like a Mapbox token: {tok[:6]}...")
    if tok.startswith("sk."):
        raise SystemExit(
            "That is a Mapbox SECRET token (sk.). Secret tokens must never be put in\n"
            "a web page - anyone loading it could use your whole account. Create a\n"
            "public token (pk.) at https://account.mapbox.com/access-tokens/ instead."
        )
    return tok


def tile_config():
    """(url, attribution, output filename, is_local)."""
    tok = mapbox_token()
    if not tok:
        return ESRI["url"], ESRI["attr"], "index.html", False
    url = ("https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.jpg90"
           "?access_token=" + tok)
    attr = "Imagery: Mapbox, Maxar; map data (c) OpenStreetMap contributors"
    return url, attr, LOCAL_OUTPUT, True


def main() -> None:
    template = (HERE / "template.html").read_text()
    data = (DATA / "map_data.json").read_text()

    assert "__DATA__" in template, "template lost its data placeholder"
    # "</script>" inside the JSON would close the block early.
    data = data.replace("<", "\\u003c")

    out = template.replace("__DATA__", data)

    for token, path in FONTS.items():
        assert token in out, f"template lost {token}"
        raw = path.read_bytes()
        assert raw[:4] == b"wOF2", f"{path.name} is not a woff2 file"
        out = out.replace(token, base64.b64encode(raw).decode("ascii"))
        print(f"  inlined {path.name}: {len(raw) / 1024:.0f} KB")

    tile_url, tile_attr, out_name, is_local = tile_config()
    for token, value in (("__TILE_URL__", tile_url), ("__TILE_ATTR__", tile_attr)):
        assert token in out, f"template lost {token}"
        out = out.replace(token, value)

    non_ascii = sorted({c for c in out if ord(c) > 127})
    assert not non_ascii, f"non-ascii leaked into the page: {non_ascii}"

    path = ROOT / out_name
    # Belt and braces: whatever happens above, the committed page must not
    # carry a credential.
    if not is_local:
        leaked = re.findall(r"\b(?:pk|sk)\.[A-Za-z0-9._-]{20,}", out)
        assert not leaked, "a Mapbox token reached the committed page - refusing to write"
        assert "access_token" not in out, "access_token reached the committed page"

    path.write_text(out, encoding="ascii")
    print(f"wrote {path.name}: {path.stat().st_size / 1e6:.2f} MB")
    if is_local:
        print(f"  tiles: Mapbox Satellite (token from "
              f"{'$MAPBOX_TOKEN' if os.environ.get('MAPBOX_TOKEN') else TOKEN_FILE.name})")
        print(f"  NOTE: {path.name} contains your token. It is git-ignored - do not")
        print(f"        commit it or serve it publicly. The committed page still uses Esri.")
    else:
        print("  tiles: Esri World Imagery (no key)")


if __name__ == "__main__":
    main()
