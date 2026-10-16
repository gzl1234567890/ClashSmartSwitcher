---
name: Clash Smart Switcher
description: Native Windows control panel for real node status and scoped automation.
colors:
  background: "#f4f7fa"
  surface: "#ffffff"
  text: "#203040"
  muted: "#586b7c"
  border: "#dce5ec"
  accent: "#087f69"
  accent-hover: "#066953"
  tint: "#eaf5ef"
  warning: "#936010"
  warning-bg: "#fff6e5"
  error: "#b23f38"
  error-bg: "#fff0ed"
typography:
  heading:
    fontFamily: "Microsoft YaHei UI, Microsoft YaHei, Clash Sans SC, Segoe UI, Noto Sans, Segoe UI Symbol, Segoe UI Emoji, Arial, sans-serif"
    fontSize: "26px"
    fontWeight: 600
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
    fontSize: "28px"
    fontWeight: 600
  table:
    fontSize: "14px"
    fontWeight: 400
  table-header:
    fontSize: "14px"
    fontWeight: 500
rounded:
  control: "6px"
  surface: "8px"
spacing:
  related: "8px"
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
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.surface}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "0 10px"
    height: "36px"
  metric:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
    padding: "16px"
---

# Design System: Clash Smart Switcher

## Overview

A modern, restrained Chinese Windows control panel, implemented with native
PySide6 widgets. The product is an independent third-party utility. Clear status,
stable controls, readable Chinese, and recovery from connection failures take
priority over decoration.

The approved redesign uses a persistent sidebar and independent overview,
measurement, automation, logs, and settings pages, with help as a secondary
destination. All pages share the same controller state; navigation does not
start, reset, or stop work.

**Key Characteristics:**

- Neutral blue-grey canvas, white work surfaces, and a restrained teal accent.
- Compact, consistent controls and a clear hierarchy of real status information.
- Native keyboard behavior, DPI scaling, and Chinese font coverage.
- Inline operational feedback and recoverable error states.

## Colors

The neutral canvas and dark blue-grey text support repeated scanning; teal marks
the primary command, selected navigation, successful state, and measured data.
Use the frontmatter tokens as the normative shared palette from
`smart_switcher/theme.py`.

Warning and error colors are semantic pairs with their pale backgrounds. Pair
color with readable state text and an appropriate icon. Unknown, disconnected,
and unmeasured values must remain explicit text states.

## Typography

Use native Microsoft YaHei UI/YaHei on Windows, followed by bundled Clash Sans SC
(static Noto Sans SC derivatives at 400/500/600), Segoe UI, Noto Sans, and symbol
fallbacks. QFont and QSS share the chain in `theme.font_families`. Never register
the development variable source. Generated static faces remove the empty STAT
table and use Windows-compatible legacy names so Qt selects the actual weight.
All sizes are logical pixels; the application default is also 15px, not points.
`theme.apply_interface_typography` applies font families and OpenType tabular
figures (`tnum`) after QSS polishing so styled widgets retain the feature.

Use heading for page titles, section for work-group headings, body for normal
content, support for secondary status and hints, button for commands, and metric
for the current measured latency. Table headers use table-header; table rows
use table. The brand uses a compact 20px semibold title, while the automation
state uses 24px semibold text. Letter spacing remains zero.

Long node names elide within the available width and retain their complete value
in the tooltip, accessible name, and underlying selectable text. Supporting
messages wrap. Text and units must fit at each supported DPI.

## Layout

The sidebar is 206 logical pixels wide. The main area has page-token horizontal
and top margins, with a 12px bottom margin. Place the page title and connection
status first, then the contextual proxy-group toolbar, then inline feedback and
the active page. The group toolbar is shown on overview, measurement, and
automation; its measurement command is hidden on automation.

Use the section-token gap between work groups and the related-token gap between
adjacent controls. Repeated metric surfaces and framed tools have 16px padding.
Settings use full-width sections with dividers and a persistent save/feedback
bar. Avoid nested framed surfaces.

The overview's six metrics use six columns when the main available width is at
least 1100px and three columns below it. Paired overview regions stack below
780px available width. Hide the last-check timestamp below 740px available
width. Automation commands stack when their minimum widths do not fit.
Scrollable pages and wrapping form rows preserve usable controls in compact
windows. These are Qt layout thresholds, not browser breakpoints.

## Elevation & Depth

The interface is flat. Separate work areas using white surfaces, the neutral
canvas, fine borders, and settings dividers. Do not add decorative drop shadows,
glows, gradients, or floating page containers. Native popup behavior remains
appropriate for menus and the region selector.

## Shapes

Use the control radius for buttons, fields, and status badges; use the surface
radius for repeated metric surfaces and genuinely framed tools. Buttons and
fields have a 36px minimum and 40px maximum QSS height. Table rows are 42px.
Keep icons consistently sized and preserve Qt's working spin-box subcontrols.
The region selector retains its existing compact chip and popup corner values.

## Components

- **Sidebar:** persistent icon-and-label navigation, with an explicit selected
  state and visible keyboard focus. Help, connection context, and version sit
  below the five primary destinations.
- **Commands and fields:** primary, ordinary, and quiet buttons share stable
  dimensions. Local Lucide SVG assets provide icons; icon-only controls require
  tooltips and accessible names. Text fields, combos, and numeric steppers expose
  focus, hover, and disabled states.
- **Overview:** six current-state metrics, real latency history, connection
  detail, the first five genuine direct-node rows in the selected group's order,
  and the latest five log entries. The trend accepts only genuine measurements
  from the latest five history entries; it must not interpolate fabricated data.
- **Measurement:** searchable, read-only node results and an actionable empty
  state. Search filters displayed rows without altering the measurement or
  automation scope. Keep prior results visible while measuring and identify
  their age. Preserve row selection and scroll during result updates.
- **Automation:** explicit current state, start/pause/stop commands, current
  rules, and switch history. Derive availability from the shared controller.
- **Feedback:** use the inline `NoticePanel` for connection and operation
  failures, with recovery actions and file-log recording. Automatic operations
  must not open notifications or modal dialogs. Preserve the confirmation for
  a user-requested exit while automation is running.
- **Logs:** read-only native text view with follow-latest control. Scrolling
  into history suspends following. Clearing the displayed log preserves files.
- **Settings:** four groups for connection, rules, candidates/performance, and
  application/security. Keep save feedback and the save command available while
  scrolling. Secret fields remain masked.

Source ownership: `smart_switcher/theme.py` owns shared tokens, QSS, and fonts;
`smart_switcher/ui_layout.py` owns native composition and page controls;
`smart_switcher/ui_components.py` owns local icon rendering, long labels,
semantic notices, and the latency chart; `smart_switcher/ui.py` binds controller
state and user actions.

## Motion

`smart_switcher/motion.py` owns all interaction timings and lifecycle management.
Use OutCubic easing: hover and focus 120ms, press 80ms, sidebar indicator 160ms,
page surface veil 140ms, and semantic background transitions 180ms. The page
veil is mouse-transparent and never scales or rasterizes text. Keep metric
surfaces still; do not animate digits, reorder results, or delay commands.

Busy icon rotation and the indeterminate progress track run only while a real
task is busy and the window is visible. Windows client-area animation settings
control decorative motion; disabled motion uses immediate feedback and a static
busy track. Stop callbacks before child destruction and bind delayed popup
positioning to the popup owner's QObject lifetime.

## Do's and Don'ts

- Do render real controller and node state, with explicit empty and unknown states.
- Do keep page navigation independent of work already running.
- Do retain focus visibility, accessible names, selectable values, and IME-safe input.
- Do verify all pages at standard and compact window sizes and 100%, 125%, and
  150% DPI, including long Chinese text, empty/error/busy/results states, and
  settings scrolling. Inspect captures for clipping, overlaps, and numeric alignment.
- Do exercise keyboard navigation, IME composition, region selection, row updates,
  log following, automation transitions, exit confirmation, and packaged font/icon
  loading before release. These are verification requirements, not a record of
  completed checks.
- Don't invent percentages, node results, history, or operational success.
- Don't change proxy/TUN state or routing mode through visual controls.
- Don't show secrets in ordinary logs or generate automatic notification dialogs.
- Don't introduce nested cards, decorative imagery, or oversized typography into
  this operational desktop interface.
