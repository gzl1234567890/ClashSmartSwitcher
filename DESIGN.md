---
name: "Clash Smart Switcher"
description: "Native Windows connection workspace with app-local frosted surfaces and truthful node status."
colors:
  background: "#edf2fb"
  surface: "#ffffff"
  text: "#202c42"
  muted: "#5e6e86"
  border: "#ced9eb"
  accent: "#1762d6"
  accent-hover: "#104fb5"
  accent-tint: "#e5edff"
  success: "#23764e"
  tint: "#e8f5ed"
  warning: "#8b5b12"
  warning-bg: "#fff5e3"
  error: "#b23f38"
  error-bg: "#fff0ed"
  glass-card: "rgba(255, 255, 255, 0.698039)"
  glass-navigation: "rgba(255, 255, 255, 0.490196)"
  glass-context: "rgba(255, 255, 255, 0.568627)"
  glass-save: "rgba(255, 255, 255, 0.823529)"
  control-surface: "rgba(255, 255, 255, 0.823529)"
  field-surface: "rgba(255, 255, 255, 0.843137)"
  glass-help-contents: "rgba(255, 255, 255, 0.509804)"
  glass-help-reading: "rgba(255, 255, 255, 0.745098)"
  code-text: "#365785"
  code-background: "#eaf0fc"
typography:
  heading:
    fontSize: "28px"
    fontWeight: 600
    fontFamily: "Clash Sans SC, Microsoft YaHei UI, Microsoft YaHei, Segoe UI, Noto Sans, Segoe UI Symbol, Segoe UI Emoji, Arial, sans-serif"
    letterSpacing: "0"
  section:
    fontSize: "17px"
    fontWeight: 600
  body:
    fontSize: "15px"
    fontWeight: 400
  button:
    fontSize: "14px"
    fontWeight: 500
  support:
    fontSize: "13px"
    fontWeight: 400
  metric:
    fontSize: "30px"
    fontWeight: 600
  table:
    fontSize: "14px"
    fontWeight: 400
  table-header:
    fontSize: "13px"
    fontWeight: 500
  help-title:
    fontSize: "22px"
    fontWeight: 600
  help-body:
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "25px"
  help-heading:
    fontSize: "17px"
    fontWeight: 600
    lineHeight: "28px"
  code:
    fontFamily: "Consolas, Clash Sans SC, Noto Sans"
    fontSize: "14px"
    fontWeight: 400
rounded:
  control: "10px"
  surface: "16px"
  navigation: "12px"
  badge: "12px"
  region-chip: "8px"
spacing:
  small: "8px"
  control: "12px"
  group: "16px"
  section: "16px"
  page: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "38px"
  button-secondary:
    backgroundColor: "{colors.control-surface}"
    textColor: "{colors.text}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "38px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.surface}"
  input:
    backgroundColor: "{colors.field-surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "0 10px"
    height: "38px"
  navigation:
    backgroundColor: "{colors.glass-navigation}"
    rounded: "{rounded.surface}"
    padding: "6px"
  navigation-segment:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.navigation}"
    padding: "0 12px"
    height: "48px"
  card:
    backgroundColor: "{colors.glass-card}"
    rounded: "{rounded.surface}"
    padding: "16px"
  badge-success:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.success}"
    typography: "{typography.support}"
    rounded: "{rounded.badge}"
    padding: "6px 12px"
  help-topic:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "0 10px"
    height: "42px"
  help-reading:
    backgroundColor: "{colors.glass-help-reading}"
    textColor: "{colors.text}"
    rounded: "{rounded.surface}"
    padding: "20px 28px"
  inline-code:
    backgroundColor: "{colors.code-background}"
    textColor: "{colors.code-text}"
    typography: "{typography.code}"
---

# Design System: Clash Smart Switcher

## Overview

**Creative North Star: "The Frosted Connection Workspace"**

A calm, connection-first Chinese desktop workspace: broad blue and lilac light sits behind translucent white cards, while crisp native text presents the current node, measured latency, and the next useful action. This is an independent third-party Windows utility, built with PySide6; the iOS-inspired material is a visual language for the native Windows window.

The global app bar and five-segment navigation give each task a complete page. Connection status and recovery stay visible across navigation. The shared controller owns ongoing work, so changing pages does not start, stop, or reset measurement or automation. Every status, node row, and chart point must represent the underlying state.

**Key Characteristics:**

- Cool mist-blue ground, diffuse blue and lilac light, and translucent white material.
- Blue commands, green success, and readable text for every semantic state.
- Rounded cards, compact controls, and a connection-first hierarchy.
- Bundled Chinese typography, native keyboard behavior, DPI scaling, and bounded motion.

## Colors

The frontmatter records the palette from `smart_switcher/theme.py` and white-alpha material from `smart_switcher/glass.py`; these source files remain authoritative. CSS alpha values translate Qt's 0-255 opacity without changing the material.

### Primary

- **Command Blue** (`accent`): commands, selected navigation, focus, and chart marks.
- **Deep Command Blue** (`accent-hover`): primary hover and focus feedback.
- **Pale Command Blue** (`accent-tint`): informational feedback and selected region chips.

### Neutral

- **Mist Blue** (`background`): the application ground beneath its diffuse backdrop.
- **Clear White** (`surface`): solid foreground and popup material.
- **Ink Blue** (`text`): labels, values, and table content.
- **Slate Blue** (`muted`): hints, captions, and supporting status.
- **Frost Edge** (`border`): visible field and control boundaries.
- **Frosted White** (`glass-card`, `glass-navigation`, `glass-context`, `glass-save`): distinct opacity layers over the same app-owned backdrop. Fields and ordinary buttons have dedicated surface tokens. Help uses separate contents and reading opacities; code text has a soft blue highlight.

Success pairs `success` with `tint`; warning pairs `warning` with `warning-bg`; error pairs `error` with `error-bg`. State text and icons carry meaning alongside color. Unknown, disconnected, unmeasured, and busy states stay explicit.

**The Two Signals Rule.** Blue communicates action and selection; green communicates confirmed success. A successful connection does not recolor the command system.

## Typography

Use bundled Clash Sans SC first, followed by Microsoft YaHei UI/YaHei, Segoe UI, Noto Sans, and symbol fallbacks in the frontmatter. Its static faces supply real regular (400), medium (500), and semibold (600) weights. The default size is measured in logical pixels, and Qt handles Windows DPI scaling. Smooth outline rendering uses `PreferAntialias | PreferOutline` with `PreferNoHinting` for the shared interface font.

### Hierarchy

- **Heading:** the page title; the active node shares its size and weight.
- **Section:** card and form-group titles.
- **Body:** normal Chinese content.
- **Button:** commands and compact task labels.
- **Support:** hints, secondary statuses, and log text.
- **Metric:** the current measured latency, with its unit visible.
- **Table / Table header:** node rows and quieter column labels.

Source-specific roles include the compact brand title (21px semibold), caption/version (12px), group/traffic labels (14px medium), and automation state (26px semibold). `theme.apply_interface_typography` applies the shared family and rendering settings to every widget after QSS polishing, preserving role sizes and weights, then enables OpenType tabular figures (`tnum`) on numeric widgets. The tray is created before this font pass so its native widgets share the setup.

Rich-text documents use design metrics for both layout and text options. Markdown emphasis is normalized to the supplied real semibold (600). Help uses its own reading rhythm: body paragraphs have a fixed 25px line height and 14px bottom gap; list blocks use an 8px bottom gap; in-document headings use a 28px line height, 10px bottom gap, and 18px top gap after the first block. The separate chapter title uses the help-title role. Code uses Consolas with Clash Sans SC/Noto Sans fallback and the code color tokens.

**The Full Value Rule.** Long node names, group names, controller details, and bounded status badges elide at the right edge instead of expanding their layout. Preserve the complete value in the tooltip and accessible name; `ElidedLabel` also retains the full selectable underlying text. Supporting instructions and notices wrap.

**The Task-First Copy Rule.** Lead help and recovery copy with the user's task and next action. Explain conditions where they affect a choice, keep operating instructions concrete, and tie each claim to the implemented behavior.

## Layout

The native window starts at 1440 x 900 logical pixels and supports a compact minimum of 850 x 630. Its vertical workspace contains the global app bar, full-width five-segment navigation, contextual heading/group controls, inline notice and real-task progress, active page, and compact connection footer. Help is an app-bar destination. The five primary pages are overview, measurement, automation, logs, and settings.

Root margins are 28px left/right, 20px top, and 16px bottom. Navigation has a 6px inset and 4px segment gap. The group surface has 14px horizontal and 10px vertical padding. Ordinary cards use the group inset; settings sections use 18px horizontal, 16px top, and 18px bottom padding. Form gaps are 24px horizontal and 12px vertical. Use the shared spacing tokens between related elements.

The overview leads with current connection and automation (3:2), then node preview and latency trend (3:2), followed by secondary recent activity. Automation separates live controls/history from rules (3:2). Settings pair connection/rules with candidates/application preferences in equal columns and keep the save/feedback bar outside the scroll area. Measurement keeps search and result context above the table.

Available width is **window width minus 56 logical pixels**:

| Available width | Native arrangement |
| --- | --- |
| At least 1000px | Heading/group actions sit side by side; settings have two columns; last-check timestamp is visible. |
| Below 1000px | Context header and settings stack; timestamp hides; measurement spacing tightens from 12px to 8px. |
| At least 900px | Overview pairs and automation columns stay side by side. |
| Below 900px | Overview pairs and automation columns stack. |

Automation commands stack independently when their measured minimum widths plus gaps cannot fit. Scrollable pages and wrapping form rows preserve usable controls. These are native logical-width thresholds, not browser breakpoints or an iOS deployment target.

Help has an independent reading layout measured against `HelpCenter.width()`: at 1000px or wider, a 180px chapter rail sits beside the reading card with a 20px gap; below 1000px, a chapter picker replaces the rail. The reading card has 28px horizontal/20px vertical insets on desktop and 20px insets in compact mode. Its native text browser is capped at 960px wide. Six H2 sections in `docs/HELP.md` supply the topics, and only the selected section is loaded. Each chapter retains its own scroll position.

## Elevation & Depth

Depth comes from tonal layering and a luminous one-pixel rim. `GlassCanvas` paints a broad linear gradient and three diffuse radial lights, cached by size and device-pixel ratio. `GlassSurface` samples that same app-owned backdrop at its position, adds its white-opacity layer, and draws a rim fading from white alpha 245 at the top to 110 at the bottom. Text and controls remain native and crisp. The shared material adds no drop shadows.

Card opacity is Qt alpha 178; navigation uses 125, group controls 145, and the save bar 210. Help contents use 130 and the reading card uses 190. The lighter rail recedes behind the working surfaces. Sidecar extensions record backdrop colors, native opacity integers, rim, and motion beyond the frontmatter schema.

**The Local Glass Rule.** Sample only the app's cached diffuse backdrop. Do not capture the desktop, blur each frame, rasterize text, or apply a blur effect to native child widgets.

Motion uses Qt OutCubic: hover/focus (120ms), press (80ms), navigation indicator (160ms), page surface veil (140ms), and semantic background (180ms). The selected mark is blue (24 x 3px) and follows resize geometry. The mouse-transparent page veil fades from 13% opacity. The refresh icon rotates once per 1200ms only during real work, paired with a 3px indeterminate track. Windows client-area animation preferences disable decorative transitions and use a static busy track. Hidden/minimized windows stop animation; callbacks stop before widget teardown. Do not animate text, digits, card geometry, or result order.

## Shapes

Buttons and fields use the control radius; cards use the surface radius. Navigation segments, badges, notices, and result surfaces use the intermediate radius. Region chips use the smaller chip radius. Preserve the hierarchy instead of making everything a pill.

Commands and fields have a 38px outer height from a fixed 36px QSS content height and one-pixel borders; icon-only commands are square. Navigation segments have a 48px outer height and help-topic commands use 42px. Geometry is restored after QSS font metrics resolve. Command icons are 18px. The brand displays the application ICO at 42px. Fields and ordinary commands have fine borders; glass cards use their luminous rim.

## Components

### Commands and fields

Primary buttons use blue and white text; ordinary buttons use translucent white and a visible border; quiet buttons use transparent material and muted text until interaction. Hover, press, focus, and disabled states preserve dimensions. Bounded feedback overlays native painting. `SE_PushButtonContents` controls icon/text placement so QSS padding stays correct.

Line edits, combos, and numeric steppers share geometry and state treatment. Preserve working native subcontrols. Steppers accept direct keyboard entry and ignore wheel events so settings scrolling cannot silently edit rules. Secret fields remain masked. Region selection retains searchable chips and its popup.

### Navigation and status

Five equal icon-and-label segments share a lighter glass rail. Selection has white material, blue text, and a blue indicator; keyboard focus stays visible. Navigation preserves ongoing controller work. Icon-only actions need tooltips and accessible names.

Status badges have an 80px minimum size hint and 360px maximum width, with full-text access under the Full Value Rule. `NoticePanel` has a wrapped selectable message, semantic icon, and optional recovery action. Successful recovery hides it. Automatic work does not open notification dialogs.

### Connection and operational cards

The leading card combines node, latency, group, controller detail, and read-only system-proxy/TUN state. Automation derives command availability from the controller. The trend displays genuine measurements from the latest five history entries, with an explicit empty state; do not manufacture continuity.

### Node tables and logs

Read-only single-row selection tables use 44px rows and a 44px header. The preview reserves 264px for one header plus five genuine direct-node rows. Latency/status columns are 94px/100px; names and detail stretch, with 64px minimum sections. Latency numbers align right; unavailable placeholders and status text align centrally. Cells elide and retain native tooltips. Preserve selection and scroll on refresh. Search filters presentation only, preserving measurement/automation scope.

Logs are read-only native text. Following the latest entry is explicit; scrolling into history suspends it. Clearing the display preserves files. Settings keep save feedback visible while scrolling. Preserve confirmation for a user-requested exit during automation.

### Help center

The guide presents one task chapter at a time: 快速开始, 连接设置, 自动切换, 测速与候选, 常见问题, and 日常使用. The chapter rail uses quiet, left-aligned topic commands; the selected topic is white with blue text, and keyboard focus retains a blue boundary. The compact picker selects the same source section. The reading card combines a native chapter heading with a transparent text browser, comfortable paragraph rhythm, selectable text, working links, and blue-highlighted code. Topic changes restore the saved reading position.

### Native interaction and assets

Retain Tab/Shift+Tab traversal, visible focus, native button activation, editable-field shortcuts, IME composition, combo/stepper keyboard operation, table selection, and popup dismissal. These are acceptance expectations, not claims of unperformed checks. Full native tooltips appear immediately, centered with padding, without Windows roll/fade clipping.

`theme.py` owns tokens/QSS/fonts; `glass.py` owns material; `motion.py` owns feedback; `ui_layout.py` owns composition; `ui_components.py` owns action icons/elision/notices/trend; `help_page.py` owns chapter navigation and reading rhythm; `ui.py` binds controller state. Sidecar HTML/CSS snippets are portable visual previews, not runtime frontend code.

The application mark is an image-generated opalescent flow ribbon on a cobalt-to-azure rounded tile. The retained RGBA master is `resources/app-master.png` (1254 x 1254); `resources/app-icon-prompt.md` records its complete prompt and provenance. `scripts/make_icon.py` preserves that master and applies the approved rounded-square alpha mask when exporting `app-icon.png` (1024px), `app.png` (256px), and ten Windows ICO sizes (16, 20, 24, 32, 40, 48, 64, 96, 128, 256px). Color resampling uses LANCZOS; the alpha mask uses 4x supersampling and BOX antialiasing. The PNG exports embed source, generation prompt, and mask geometry. The app bar, window, tray, and EXE share this identity.

Local Lucide SVGs remain the action-icon system; `resources/icons/README.md` records both artwork origins and the Lucide license. Normal builds export the retained artwork locally. UI screenshots originate in `scripts/capture_ui.py`, embed synthetic-QA `Source` metadata, and display a QA state tag.

## Do's and Don'ts

### Do:

- Do render genuine controller state, node results, and history with explicit unknown and empty states.
- Do keep blue commands distinct from green confirmed success.
- Do preserve crisp text with the bundled family, real font weights, and shared outline-rendering settings over the cached glass backdrop.
- Do retain full tooltips, accessible names, selectable values, visible focus, and IME-safe input.
- Do preserve work, selection, and scroll across navigation, help chapters, and result updates.
- Do keep help organized around tasks and export application icons from the retained master with recorded provenance.
- Do verify standard/compact layouts at 100%, 125%, and 150% DPI, including long text, empty/error/busy/results states, and settings scrolling.

### Don't:

- Don't invent percentages, node results, trend points, or operational success.
- Don't capture the desktop or introduce per-frame blur, text rasterization, or decorative card motion.
- Don't expose controls that change system proxy, TUN, or routing mode.
- Don't expose secrets in ordinary logs or open notification dialogs for automatic operations.
- Don't revive the obsolete sidebar, six equal metric tiles, flat teal palette, or single-column settings at spacious widths.
- Don't treat iOS-inspired material as an iOS platform dependency or replace native Windows keyboard behavior.
