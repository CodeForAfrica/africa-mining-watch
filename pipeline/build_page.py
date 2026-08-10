#!/usr/bin/env python3
"""Inline map_data.json into template.html and write the finished page.

The output is deliberately pure ASCII: the page is published inside a wrapper
whose <head> we do not control, so we never rely on a charset declaration.
"""
import base64
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

    non_ascii = sorted({c for c in out if ord(c) > 127})
    assert not non_ascii, f"non-ascii leaked into the page: {non_ascii}"

    path = ROOT / "index.html"
    path.write_text(out, encoding="ascii")
    print(f"wrote {path.name}: {path.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
