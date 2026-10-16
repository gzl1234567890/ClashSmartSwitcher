# UI Font Assets

Clash Sans SC is a static derivative of Noto Sans SC. The original variable
source is `NotoSansSC-VF.ttf`; it is retained only for reproducible development
and is never registered or included in the runtime distribution.

Run `python scripts/make_static_fonts.py` with the pinned development
dependencies to regenerate the Regular (400), Medium (500), and SemiBold (600)
faces. The family is renamed to avoid matching an installed variable face.
Original copyright notices remain embedded in the fonts.

Windows uses Microsoft YaHei UI / Microsoft YaHei first; these static faces are
the shipped CJK fallback. QSS and native text use the same chain. Generated
instances remove the empty STAT table and use Windows legacy Regular/Bold
grouping plus typographic style names, so Qt selects real 400/500/600 data rather
than synthesizing bold from the Medium face. Tests inspect OS/2 weight data and
rendered ink coverage, not just the requested QFont weight.

- Noto Sans SC: copyright 2014-2021 Adobe, Reserved Font Name "Source".
  Upstream: https://github.com/notofonts/noto-cjk. License: `OFL.txt`.
- Noto Sans: copyright 2022 The Noto Project Authors.
  Upstream: https://github.com/notofonts/latin-greek-cyrillic.
  License: `OFL-Latin.txt`.

Font generation uses fontTools only at development time. Both projects use
the SIL Open Font License 1.1; retain both license files when redistributing.
