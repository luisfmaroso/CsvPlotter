"""MainWindow — menus, layout, and wiring.

Phase 1: the window shell. A File menu (Open CSV… is a placeholder until Phase 2),
a View menu with Reset View, a Help/About box, the PlotView as the central widget,
and a status bar.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .data.csv_loader import CsvLoadError, load_csv
from .data.series import Series
from .ui.pin_panel import PinPanel
from .ui.plot_view import PlotView
from .ui.series_panel import SeriesPanel


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CsvPlotter")
        self.resize(1000, 650)

        # The currently loaded series, keyed by name (the source of truth the
        # panel and plot both reflect).
        self._series: dict[str, Series] = {}

        self.plot_view = PlotView(self)
        self.setCentralWidget(self.plot_view)

        self.series_panel = SeriesPanel(self)
        self.series_panel.visibility_changed.connect(self._on_series_visibility)
        self.series_panel.transform_changed.connect(self._on_series_transform)

        # Pinned-points readout lives at the bottom of the same left tab.
        self.pin_panel = PinPanel(self)
        self.pin_panel.clear_requested.connect(self.plot_view.clear_pins)
        self.plot_view.pins_changed.connect(self._refresh_pins)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.series_panel, stretch=1)
        left_layout.addWidget(self.pin_panel)

        self._series_dock = QDockWidget("Signals", self)
        self._series_dock.setWidget(left)
        self._series_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._series_dock)
        self.resizeDocks([self._series_dock], [320], Qt.Orientation.Horizontal)

        self._build_menus()
        self.statusBar().showMessage("Ready — open a CSV to begin.")

    def _build_menus(self) -> None:
        menu = self.menuBar()

        # --- File -------------------------------------------------------
        file_menu = menu.addMenu("&File")

        self.open_action = QAction("&Open CSV…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)  # Ctrl+O
        self.open_action.triggered.connect(self._on_open_csv)
        file_menu.addAction(self.open_action)

        file_menu.addSeparator()

        quit_action = QAction("E&xit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # --- View -------------------------------------------------------
        view_menu = menu.addMenu("&View")

        reset_action = QAction("&Reset View", self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self.plot_view.reset_view)
        view_menu.addAction(reset_action)

        step_action = QAction("&Step Lines (sample && hold)", self)
        step_action.setCheckable(True)
        step_action.setChecked(True)
        step_action.toggled.connect(self.plot_view.set_step_mode)
        view_menu.addAction(step_action)

        hover_action = QAction("&Hover Tooltip", self)
        hover_action.setCheckable(True)
        hover_action.setChecked(True)
        hover_action.setShortcut("Ctrl+H")
        hover_action.toggled.connect(self.plot_view.set_hover_enabled)
        view_menu.addAction(hover_action)

        view_menu.addSeparator()
        # Built-in show/hide action for the Series dock.
        view_menu.addAction(self._series_dock.toggleViewAction())

        # --- Help -------------------------------------------------------
        help_menu = menu.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # --- Slots ----------------------------------------------------------
    def _on_open_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV", "", "CSV files (*.csv);;All files (*)"
        )
        if not path:
            return

        try:
            loaded = load_csv(path)
        except CsvLoadError as exc:
            QMessageBox.critical(self, "Could not open CSV", str(exc))
            self.statusBar().showMessage("Failed to load CSV.")
            return

        self._series = {s.name: s for s in loaded.series}
        self.plot_view.set_series(loaded.series, x_label=loaded.time_name)
        self.series_panel.set_series(loaded.series)
        self.setWindowTitle(f"CsvPlotter — {Path(path).name}")
        self.statusBar().showMessage(
            f"{Path(path).name}: {len(loaded.series)} series, "
            f"Time = '{loaded.time_name}'."
        )

    def _on_series_visibility(self, name: str, visible: bool) -> None:
        series = self._series.get(name)
        if series is not None:
            series.visible = visible
        self.plot_view.set_series_visible(name, visible)

    def _on_series_transform(self, name: str) -> None:
        series = self._series.get(name)
        if series is not None:
            self.plot_view.refresh_curve(series)

    def _refresh_pins(self) -> None:
        self.pin_panel.update_readout(self.plot_view.pin_data())

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About CsvPlotter",
            f"<b>CsvPlotter</b> v{__version__}<br>"
            "A simple tool for plotting and analysing time-series CSVs.<br>"
            "Built with PySide6 + pyqtgraph.",
        )
