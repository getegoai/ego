# Ego visual assets

The visual identity follows the existing EgoLabs website: near-black `#080a08`,
off-white `#f0f3ea`, lime `#b4ff5a`, and the cut-corner mark. The diagram uses a
light surface for detail. Website source and deployment are unchanged.

| Asset | Type and source |
|---|---|
| `ego-cover.svg`, `.png` | New original brand artwork, 1600 × 640, generated 2026-10-27 |
| `ego-social.svg`, `.png` | 1600 × 840 vector master / 1200 × 630 PNG for sharing |
| [system/](system/README.md) | Conceptual product-relationship drawing and its editable source; no production hardware or completed integration claim |
| `screenshots/data-core-workspace.png` | Actual Dashboard, 1280 × 520, captured 2026-10-27 |
| `screenshots/data-core-evidence.png` | Actual search view, 1280 × 900, query `brief`, captured 2026-10-27 |

The screenshots use the unchanged application from source commit
`beac7680ed203dff96fa6ce514f86ee81fc39747` and the five synthetic files in
`projects/egobase/data-core/demo/sample_workspace/`. A fresh isolated local
database was populated by the existing demo runner. No private database, private
document, remote service, substituted UI or image retouching was used.
The source name visible in the UI is **Ego Demo Workspace**. The local capture
server was stopped when the screenshots were complete.

Screenshot SHA-256:

```text
2a8692f839831987e3e1b5173872c2a662938e70b30b7c1b10ea80d968e54fc9  data-core-workspace.png
0c4dd080d15925e5cbf830ef0956e17fa6223db6f9217430c69408fe72686a54  data-core-evidence.png
```

Original cover artwork, explanatory figure and captions are CC BY 4.0.
Generation scripts are Apache-2.0 except identified MIT helper code under the
figure's `vendor` directory. Screenshots depict the project's Apache-2.0 Data Core
and bundled demo; preserve its attribution when reusing them. The existing
EgoLabs trademark boundary continues to apply.

Regenerate the SVG covers with Node.js:

```sh
node docs/media/build-covers.mjs ego
```

To regenerate PNGs too, make `sharp` available to Node and add `--png`.
No font files are distributed. The SVG uses Arial/Helvetica/system sans-serif.
The system figure has [its own source and regeneration instructions](system/README.md).

For a new software capture, run the existing Data Core demo in a fresh scratch
data directory, launch its local UI, and use the Dashboard or Search view.
Keep the synthetic-data caption with screenshots used outside this repository.
