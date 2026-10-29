# Interface icons

The application mark is an image-generated opalescent flow ribbon on a cobalt
rounded tile. Its high-resolution RGBA source is `resources/app-master.png`;
the complete prompt and origin are recorded in `resources/app-icon-prompt.md`.
`scripts/make_icon.py` preserves the master and exports the clean 1024px
`app-icon.png`, the 256px `app.png`, and an ICO with ten native sizes from
16–256px. The user-approved standard rounded-square alpha mask cleans the
outside silhouette. PNG metadata records the source, prompt and mask geometry.
No image generation or network access takes place during a normal build.

The local `check.svg` is a white checkbox variant of Lucide's check path.

The application uses a small, locally bundled subset of **Lucide 0.468.0**.

- Files: `resources/icons/lucide/*.svg`
- Upstream: https://github.com/lucide-icons/lucide/tree/0.468.0
- License: `lucide/LICENSE` (upstream ISC license with the included Feather notice)
- Reproduce downloads: `python scripts/download_icons.py`

The requested MotionSites icon page (https://motionsites.org/zh/icons) was consulted
and lists Lucide among its free libraries. The selected Lucide SVGs are downloaded
directly from Lucide's official repository at the pinned version above, rather than
scraping a dynamic page. The release includes the original SVGs and license. There
are no runtime downloads.
