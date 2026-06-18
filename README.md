# CsvPlotter

A simple, focused desktop tool for **plotting and analysing time-series CSV data** — a
file with one **Time** column and any number of data columns. You open the CSV, pick the
columns you care about, and explore them interactively: **zoom, pan, a crosshair tooltip,
per-series scale (gain) and X/Y offset**, and a pair of **measurement cursors** for reading
the time/value difference between two points.

Built with **Python + Qt Widgets (PySide6)** and **pyqtgraph**, it's the Python/Qt member
of the same family as **AutoLabel** and **InferenceVisualizer** — kept deliberately small:
an everyday "open a log and look at it" tool, not a full analysis suite.

> **Status: planning.** The design below is agreed but not yet built. See
> [`docs/index.html`](docs/index.html) for the architecture and the phased roadmap.

---

## Features (planned MVP)

- **Open a CSV** — a `Time` column plus N numeric data columns (pandas-backed loader).
- **Column selection** — a side panel lists every column with a checkbox; tick to plot.
- **Zoom / box-zoom / pan / auto-fit** — the mouse wheel zooms, **left-drag draws a box** the
  view zooms into, **middle-drag pans**, and a reset button re-frames all visible data. The
  right button is inert; the left button no longer pans (it's used to pin points).
- **Step lines (sample & hold)** — values hold until the next sample (stair shape), the way
  embedded/digital logs behave. Toggle to linear via **View → Step Lines**.
- **Hover tooltip** — when the cursor nears a signal, a marker snaps to the nearest sample
  and shows that point's X and Y.
- **Scale (gain)** — multiply a series' Y values by a factor.
- **Offset X and Y** — shift a series along time or value.
- **Pinned points** — left-click near a signal to pin a point (max two, FIFO); the left tab
  shows each pin and the **Δx / Δy** between them, with a Clear button.

The raw data is never mutated — gain and offset are display parameters, so "reset to
original" is trivial.

---

## Tech stack

| Area | Choice |
|---|---|
| Language | Python 3.10+ |
| GUI | Qt 6 Widgets via **PySide6** (official LGPL binding, hand-coded — no `.ui` files) |
| Plotting | **pyqtgraph** — Qt-native interactive plotting (zoom/pan/crosshair built in) |
| Data | **pandas** (CSV parsing) + **numpy** (gain/offset maths) |
| Platform | Windows first; pure-Python, so Linux/macOS follow |

**Why pyqtgraph over Matplotlib?** It's built for *interactive* exploration — wheel zoom,
drag pan, and crosshairs come with its `ViewBox`, and it stays fast on large arrays.
Matplotlib is better for static publication figures, the wrong trade here.

---

## Getting started

```powershell
# 1. Virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

`requirements.txt`: `PySide6`, `pyqtgraph`, `pandas`, `numpy`.

---

## Project structure

```
CsvPlotter/
├── main.py                  # entry point: QApplication + MainWindow
├── requirements.txt
├── csvplotter/
│   ├── main_window.py       # MainWindow: menus, layout, wiring
│   ├── data/
│   │   ├── csv_loader.py    # pandas read_csv -> detect Time col -> build Series
│   │   └── series.py        # Series: raw x/y + gain, offset_x, offset_y, visible, color
│   └── ui/
│       ├── plot_view.py     # pyqtgraph wrapper: curves, hover tooltip, pins, mouse policy
│       ├── series_panel.py  # checkable column list + gain/offset controls
│       └── pin_panel.py     # pinned-points readout (Δx/Δy) + Clear button
└── docs/                    # index.html + style.css (shared with the sibling projects)
```

---

## Documentation

[`docs/index.html`](docs/index.html) is the living project document: overview, tech stack,
architecture, the feature design, build instructions, and the phased roadmap with a
changelog. Open it in a browser (it shares `docs/style.css` with AutoLabel and
InferenceVisualizer).

---

## Roadmap

The agreed MVP is complete:

| Phase | Scope | State |
|---|---|---|
| 1 | Skeleton: window, menu, empty pyqtgraph plot that launches | done |
| 2 | Load & plot: pandas loader, detect Time column, plot all, auto-fit | done |
| 3 | Series panel: checkable show/hide, per-series colour | done |
| 4 | Transforms: per-series gain, offset X, offset Y with live redraw | done |
| 5 | Hover tooltip: marker snaps to nearest signal, shows X/Y | done |
| 6 | Pinned points: click-to-pin (max two), Δx/Δy readout + Clear | done |

### Possible future implementations

Not currently planned, but candidates: polish (`QSettings` window/dock state, more error
dialogs, extra shortcuts), PNG export, automatic downsampling for large files, session
save/load (selection + gains/offsets), visible-range statistics, multi-file overlay, and a
Time-column override dropdown.
