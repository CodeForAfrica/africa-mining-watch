# Fonts

`geist-latin.woff2` and `geist-mono-latin.woff2` are the Latin subsets of **Geist**
and **Geist Mono**, the typefaces used by africaminingwatch.org. They are vendored
here because the published page runs under a Content Security Policy that blocks
font CDNs, so `build_page.py` inlines them into `index.html` as base64.

- Typefaces: Geist, Geist Mono
- Copyright: © Vercel, Inc.
- Licence: **SIL Open Font License 1.1**
- Source: https://github.com/vercel/geist-font

## Outstanding obligation

The OFL permits bundling and redistribution, **but requires that the licence text
accompany the font**. The full `OFL.txt` is not included here because it should be
copied verbatim from the upstream repository rather than retyped:

```bash
curl -o pipeline/fonts/OFL.txt \
  https://raw.githubusercontent.com/vercel/geist-font/main/LICENSE.TXT
```

Do that before this repository is made public. Because `index.html` embeds the
fonts, the obligation applies to the published page as well as to these files.
