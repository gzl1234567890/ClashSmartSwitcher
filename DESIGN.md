# Clash 智能节点管家：桌面界面规范

## Direction
Preserve the established light / low-saturation green identity. This is a Windows
Operate surface: trustworthy status, readable Chinese, and predictable controls.
The product remains an independent third-party tool. No network behavior changes.

## Composition
White application header and one integrated node / measurement / automation
summary. A pale neutral workspace holds the three existing tabs. The control
panel prioritizes group selection, operations, real feedback, and the node table;
a resizable log region is secondary. Settings are grouped into four sections
with a persistent save/feedback bar. No decorative charts or fabricated metrics.

## Tokens and components
`smart_switcher/theme.py` owns colors, logical-pixel type sizes and spacing.
Body 15, supporting text 13, section 16, title 21, measurement 26. Microsoft YaHei
UI / Microsoft YaHei / Segoe UI with Qt font fallback. Accent #087f69; canvas
#f4f7f6; surfaces white; text #20342f. Border radii 7–10 for controls/surfaces.
`ui_components.py` owns local SVG rendering, semantic feedback and long labels.
Lucide icons use a consistent stroke; source and license live with the assets.

## Behavior
The existing controller is the authority for active/busy state. No percentage
without a backend measurement. Retain previous results while measuring and label
them as such. Refresh rows without clearing the viewport; preserve selection and
scroll. Log following yields to the user reading history. Enter is local to the
focused widget; composition input must not trigger region selection. Animations
are limited to the optional Qt busy indicator and respect Windows animation
preferences. All network/configuration safety boundaries remain in force.

## Verification
Inspect empty, connected, results, settings, region popup and compact windows in
one batched capture pass; fix its defects together, then perform one confirmation
pass. Exercise keyboard, IME events, row updates, logs and existing business tests.
Build and smoke-test the PyInstaller distribution with isolated data directories.
