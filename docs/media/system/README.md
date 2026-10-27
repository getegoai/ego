# Ego system concept figure

**Figure scale:** 65 physical parts, a static SVG. The scene is an ordinary personal data workspace: an exposed observation board, a personal computer, and evidence cards in a shallow desk tray. The screen's small lime authorization control is the only colored mechanism. No physical connection or flowing signal claims that integration already works.

The image is a product-direction concept. EgoLink is an engineering prototype; Data Core is a software prototype. The complete Link → Base loop has not been validated. The board is illustrative, not a PCB layout or a finished product enclosure, and the computer does not imply a dedicated EgoBase hardware product. Screen contents are a conceptual interface, not a screenshot.

Suggested external Chinese caption:

> 产品方向概念图：EgoLink 提供物理观察，用户掌控的 PC / EgoBase 保存证据与上下文，支持经用户授权的行动。EgoLink 仍为工程原型，Data Core 为软件原型，Link → Base 完整闭环尚未完成；图中电路板与界面为概念表达，不是成品或实测连接。

Rebuild with Node.js 20.10 or newer from this directory:

```sh
node build.mjs
```

`model.mjs` records the truthful boundaries and grouped parts before geometry. `build.mjs` regenerates `ego-system.svg` and its `parts.json` inventory with no network dependency. Add `--preview` to generate an optional local HTML preview. `ego-system.png` is the static rendered fallback. The committed `vendor/iso-kit.mjs` is the only Anatomy dependency; its original MIT license is retained in `vendor/LICENSE`. No local skill installation is required to rebuild the SVG.

The original SVG/PNG illustration and prose are **CC BY 4.0**. The original `build.mjs` and `model.mjs` code are **Apache-2.0**. The vendored Anatomy kit is **MIT**, Copyright (c) 2026 Ryan; its full license is retained in `vendor/LICENSE`. The illustration uses the EgoLabs ink/paper family and a restrained `#b4ff5a` accent.

Visual checks: desktop and 390 px viewport, a 4× subject close-up, no horizontal overflow or console errors, and zero floating line ends (61 line paths checked). This is a static, slab-based figure with no pipes, cables, motion, or WebGL; no mechanical simulation is claimed.
