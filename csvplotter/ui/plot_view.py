"""PlotView — a thin wrapper around pyqtgraph's PlotWidget.

Sets up a themed plot (grid, axis labels) and three interactions:

* **Mouse:** left-drag draws a rubber-band box and zooms to it; middle-drag pans;
  the wheel zooms; the right button does nothing (menu disabled).
* **Hover tooltip:** when the cursor is near a signal, a marker snaps to the nearest
  sample and a small box shows its X and Y.
* **Pinned points:** left-clicking near a signal pins a point there (at most two, FIFO).
  The window reads them to fill the left-panel ΔX / ΔY readout.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ..data.series import Series, fmt_num

# Dark plot theme (matches the docs' code-block palette).
PLOT_BACKGROUND = "#1e2228"
PLOT_FOREGROUND = "#c8d0d8"  # axes, ticks, labels
pg.setConfigOption("background", PLOT_BACKGROUND)
pg.setConfigOption("foreground", PLOT_FOREGROUND)
pg.setConfigOptions(antialias=True)

# How close (in pixels) the cursor must be to a signal to hover/pin.
HOVER_THRESHOLD_PX = 20.0

MAX_PINS = 2


class PlotViewBox(pg.ViewBox):
    """ViewBox with our mouse policy: left-drag = box-zoom, middle-drag = pan,
    wheel = zoom, and the right button is inert (no context menu, no right-drag
    scaling)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setMouseMode(self.RectMode)  # left-drag draws a zoom box
        self.setMenuEnabled(False)        # no right-click context menu

    def mouseDragEvent(self, ev, axis=None) -> None:
        # Right button: disabled.
        if ev.button() == Qt.MouseButton.RightButton:
            ev.ignore()
            return
        # Middle button: pan. In RectMode the base ViewBox would draw a box for
        # the middle button too, so flip to PanMode just for this drag.
        if ev.button() == Qt.MouseButton.MiddleButton:
            self.setMouseMode(self.PanMode)
            try:
                super().mouseDragEvent(ev, axis=axis)
            finally:
                self.setMouseMode(self.RectMode)
            return
        # Left button: box-zoom (RectMode).
        super().mouseDragEvent(ev, axis=axis)

    def mouseClickEvent(self, ev) -> None:
        # Swallow right-clicks (no menu); left clicks flow to the scene for pinning.
        if ev.button() == Qt.MouseButton.RightButton:
            ev.accept()
            return
        super().mouseClickEvent(ev)


@dataclass
class _Pin:
    name: str
    color: str
    x: float
    y: float
    marker: pg.ScatterPlotItem
    label: pg.TextItem


def _coord_html(x: float, y: float) -> str:
    return (
        "<div style='font-family:monospace; color:#e6edf3'>"
        f"x = {fmt_num(x)}<br>y = {fmt_num(y)}</div>"
    )


class PlotView(QWidget):
    """The central plotting area."""

    # Emitted whenever the set of pinned points changes.
    pins_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.plot_widget = pg.PlotWidget(viewBox=PlotViewBox())
        self._plot_item = self.plot_widget.getPlotItem()
        self._plot_item.setMenuEnabled(False)

        # Dark, analysis-friendly defaults. No legend — the side panel already
        # shows which colour is which.
        self.plot_widget.setBackground(PLOT_BACKGROUND)
        self._plot_item.showGrid(x=True, y=True, alpha=0.3)
        self._plot_item.setLabel("bottom", "Time")
        self._plot_item.setLabel("left", "Value")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

        self._series: list[Series] = []
        # name -> the pyqtgraph curve, so we can redraw a single series later.
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._pins: list[_Pin] = []
        # Sample-and-hold (stair) lines by default — right for embedded logs.
        self._step_mode = True

        self._build_hover()
        self.plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    # --- hover tooltip -------------------------------------------------
    def _build_hover(self) -> None:
        self._marker = pg.ScatterPlotItem(size=11, pen=pg.mkPen("#ffffff", width=1.5))
        self._readout = pg.TextItem(anchor=(0, 1), fill=pg.mkBrush(30, 34, 40, 220))
        self._readout.setZValue(100)
        self._hover_enabled = True
        self._plot_item.addItem(self._marker, ignoreBounds=True)
        self._plot_item.addItem(self._readout, ignoreBounds=True)
        self._set_hover_visible(False)

        # Rate-limited mouse tracking over the plot scene.
        self._proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )

    def _set_hover_visible(self, visible: bool) -> None:
        self._marker.setVisible(visible)
        self._readout.setVisible(visible)

    def set_hover_enabled(self, enabled: bool) -> None:
        self._hover_enabled = enabled
        if not enabled:
            self._set_hover_visible(False)

    # --- pinned points -------------------------------------------------
    def place_pin(self, series: Series, x: float, y: float) -> None:
        """Pin a point on *series* at (x, y). Keeps at most MAX_PINS, FIFO."""
        if len(self._pins) >= MAX_PINS:
            self._remove_pin(self._pins.pop(0))

        marker = pg.ScatterPlotItem(
            [x], [y], symbol="s", size=12,
            pen=pg.mkPen("#ffffff", width=1.5), brush=pg.mkBrush(series.color),
        )
        marker.setZValue(90)
        label = pg.TextItem(anchor=(0, 1), fill=pg.mkBrush(30, 34, 40, 220))
        label.setHtml(_coord_html(x, y))
        label.setPos(x, y)
        label.setZValue(100)
        self._plot_item.addItem(marker, ignoreBounds=True)
        self._plot_item.addItem(label, ignoreBounds=True)

        self._pins.append(_Pin(series.name, series.color, x, y, marker, label))
        self.pins_changed.emit()

    def clear_pins(self) -> None:
        for pin in self._pins:
            self._remove_pin(pin)
        self._pins.clear()
        self.pins_changed.emit()

    def _remove_pin(self, pin: _Pin) -> None:
        self._plot_item.removeItem(pin.marker)
        self._plot_item.removeItem(pin.label)

    def pin_data(self) -> list[tuple[str, str, float, float]]:
        """(name, colour, x, y) for each pinned point, in order placed."""
        return [(p.name, p.color, p.x, p.y) for p in self._pins]

    # --- series --------------------------------------------------------
    def set_series(self, series: list[Series], x_label: str = "Time") -> None:
        """Replace everything on the plot with a new set of series."""
        self._plot_item.clear()  # also removes overlay + pin items
        self._curves.clear()
        self._pins.clear()       # items already removed by clear()
        self._series = series

        self._plot_item.setLabel("bottom", x_label)
        for s in series:
            self._add_curve(s)

        self._readd_overlays()   # re-add hover items after clear
        self.reset_view()
        self.pins_changed.emit()

    def _readd_overlays(self) -> None:
        self._plot_item.addItem(self._marker, ignoreBounds=True)
        self._plot_item.addItem(self._readout, ignoreBounds=True)
        self._set_hover_visible(False)

    def _add_curve(self, s: Series) -> None:
        curve = self._plot_item.plot(
            s.plot_x(),
            s.plot_y(),
            pen=pg.mkPen(s.color, width=1.5),
            name=s.name,
            stepMode=self._step_value(),
        )
        curve.setVisible(s.visible)
        self._curves[s.name] = curve

    def _step_value(self) -> str | None:
        # "right" = each sample's value holds until the next sample's time.
        return "right" if self._step_mode else None

    def set_step_mode(self, enabled: bool) -> None:
        """Switch all curves between sample-and-hold (stair) and linear lines."""
        self._step_mode = enabled
        for s in self._series:
            curve = self._curves.get(s.name)
            if curve is not None:
                curve.setData(s.plot_x(), s.plot_y(), stepMode=self._step_value())

    def set_series_visible(self, name: str, visible: bool) -> None:
        """Show or hide a single curve by series name."""
        curve = self._curves.get(name)
        if curve is not None:
            curve.setVisible(visible)

    def refresh_curve(self, series: Series) -> None:
        """Redraw one curve after its gain/offset changed."""
        curve = self._curves.get(series.name)
        if curve is not None:
            curve.setData(
                series.plot_x(), series.plot_y(), stepMode=self._step_value()
            )

    # --- mouse handling ------------------------------------------------
    def _on_mouse_moved(self, event) -> None:
        pos = event[0]  # SignalProxy wraps args in a tuple
        if not self._hover_enabled or not self._series:
            return
        if not self._plot_item.sceneBoundingRect().contains(pos):
            self._set_hover_visible(False)
            return

        cursor_x = self._plot_item.vb.mapSceneToView(pos).x()
        hit = self._nearest_point(pos, cursor_x)
        if hit is None:
            self._set_hover_visible(False)
            return

        series, px, py = hit
        self._marker.setData([px], [py], brush=pg.mkBrush(series.color))
        self._readout.setHtml(_coord_html(px, py))
        self._readout.setPos(px, py)
        self._set_hover_visible(True)

    def _on_mouse_clicked(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._series:
            return
        pos = event.scenePos()
        if not self._plot_item.sceneBoundingRect().contains(pos):
            return
        cursor_x = self._plot_item.vb.mapSceneToView(pos).x()
        hit = self._nearest_point(pos, cursor_x)
        if hit is None:
            return  # clicked far from any signal — leave it for box-zoom drags
        series, px, py = hit
        self.place_pin(series, px, py)
        event.accept()

    def _nearest_point(
        self, scene_pos: QPointF, cursor_x: float
    ) -> tuple[Series, float, float] | None:
        """The (series, x, y) of the sample closest to the cursor in *pixels*,
        across all visible series, or None if nothing is within the threshold."""
        vb = self._plot_item.vb
        best: tuple[Series, float, float] | None = None
        best_dist = HOVER_THRESHOLD_PX

        for s in self._series:
            if not s.visible:
                continue
            sample = s.sample_at(cursor_x)
            if sample is None:
                continue
            px, py = sample
            scene_pt = vb.mapViewToScene(QPointF(px, py))
            dist = np.hypot(scene_pt.x() - scene_pos.x(), scene_pt.y() - scene_pos.y())
            if dist < best_dist:
                best_dist = dist
                best = (s, px, py)

        return best

    def reset_view(self) -> None:
        """Auto-fit the view to all visible data."""
        self.plot_widget.autoRange()
