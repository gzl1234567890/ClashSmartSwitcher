# App icon source

Generated with the built-in imagegen tool on 2026-10-28. The selected master is `app-master.png` (1254 × 1254, RGBA, transparent exterior). It supplies the application/window/tray/EXE icon; Lucide remains the interface control icon set.

## Selected generation prompt

Use case: logo-brand. Asset type: final high-resolution desktop application icon, square 2048 x 2048 composition. Create one premium iOS-inspired app icon for a smart network connection switcher. Center a single bold sculptural continuous ribbon loop: two broad rounded flowing transitions fold smoothly into each other to suggest intelligent automatic route switching. The mark has a memorable simple S-like flow silhouette, thick enough to remain clear at 24 pixels, with generous negative space and no tiny details. Use icy opalescent white glass for the flowing mark, subtle azure edge refraction, and a rich cobalt-to-azure rounded-square blue tile. Front-facing orthographic composition, restrained polished dimensionality, soft internal studio light, crisp clean contours. The rounded-square tile occupies about 90 percent of the canvas, with a genuinely transparent exterior and no outer drop shadow. The central mark occupies about 60 percent of the tile. Output one finished icon asset, not an icon mockup or a sheet of options. No letters, numbers, typography, watermark, node diagram, network branches, shield, globe, lightning bolt, pedestal, tilt, perspective scene, or fine decorative sparkles. Preserve actual transparent alpha outside the rounded tile.

## Build assets

`scripts/make_icon.py` exports the retained master into the clean 1024px
`app-icon.png`, the 256px `app.png`, and ten native Windows icon sizes. The PNG
files embed their source, generation prompt and standard export-mask geometry.
The original `app-master.png` is retained unchanged during export.

The user authorized a standard rounded-square alpha mask on 2026-10-28 to clean
the outside silhouette. On the 1254px source coordinate system the mask bounds
are `(96, 96, 1158, 1158)` with a 250px corner radius. Color uses LANCZOS
resampling; the mask uses 4x supersampling and BOX antialiasing. This preserves
the interior image while removing outside fragments and retaining transparent
corners. No image generation or network access runs during a normal build.
