# Where Victoria's Rubbish Goes

Kerbside waste and recycling across all 79 Victorian councils — volumes, diversion rates,
service costs, and how they have changed since 2001.

**Live page:** https://rohanpant1.github.io/fit3179-vic-waste/

Created for **FIT3179 Data Visualisation**, Monash University, Semester 2 2026.
Author: Rohan Pant. Built with [Vega-Lite](https://vega.github.io/vega-lite/).

## Repository layout

| path | contents |
|---|---|
| `index.html` | the visualisation — a single scrollable page |
| `specs/` | one Vega-Lite JSON specification per chart, plus the shared `config.json` |
| `data/` | the datasets the page loads (~540 KB total) |
| `css/`, `js/`, `fonts/` | styling, embed script, self-hosted webfonts |
| `sketch/` | the hand-drawn design sketch |

## Data sources

All four sources are Australian government open data under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

- Recycling Victoria, *Victorian Local Government Annual Waste Services Survey*,
  release 2025.03 — kerbside tonnages, 2001–02 to 2023–24.
  [data.vic.gov.au](https://discover.data.vic.gov.au/dataset/victorian-local-government-waste-data-dashboard)
- Local Government Victoria, *Local Government Performance Reporting Framework full
  council dataset*, Nov 2025 release — service costs and diversion, 2020–21 to 2024–25.
  [data.vic.gov.au](https://discover.data.vic.gov.au/dataset/local-government-performance-reporting)
- Recycling Victoria, *Victoria's waste and resource recovery infrastructure map data*,
  March 2025 — 664 facility locations.
  [data.vic.gov.au](https://discover.data.vic.gov.au/dataset/victoria-s-waste-and-resource-recovery-infrastructure-map-data)
- Australian Bureau of Statistics, *Local Government Areas 2025*, ASGS Edition 3,
  GDA2020 — council boundaries, simplified to 81 KB with mapshaper.
  [abs.gov.au](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files)

## Use of generative AI

Generative AI (Claude) was used to research data sources, debug Vega-Lite specifications,
and copy-edit narrative text. All data analysis was computed directly from the source
datasets listed above.

## Licence

Code and visualisations: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Underlying data remains under its original licence as cited above.

# Local preview

Double-click `serve.cmd`, or run:

```bash
python -m http.server 8777
```

then open <http://localhost:8777>.

**Opening `index.html` directly from the file system will not work** — the browser blocks
the page from fetching the spec and data files over `file://`, so every chart comes up
empty. Always go through a local server.
