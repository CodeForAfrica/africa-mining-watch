# Fonts

`geist-latin.woff2` and `geist-mono-latin.woff2` are the Latin subsets of **Geist**
and **Geist Mono**, the typefaces used by africaminingwatch.org. They are vendored
here because the published page runs under a Content Security Policy that blocks
font CDNs, so `build_page.py` inlines them into `index.html` as base64.

- Typefaces: Geist, Geist Mono
- Copyright: © Vercel, Inc.
- Licence: **SIL Open Font License 1.1**
- Source: https://github.com/vercel/geist-font

## Licence text

The OFL requires that the licence accompany the font, so the full text is in
[`OFL.txt`](OFL.txt), copied verbatim from the upstream repository. Because
`index.html` embeds the fonts as base64, this obligation covers the published
page as well as these files.
