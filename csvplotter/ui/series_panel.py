"""SeriesPanel — a compact table of columns with per-series controls.

One thin row per series: a colour-swatch + visibility checkbox (the name), then
three spin-boxes — Gain (multiplies Y), X off (shifts along Time), Y off (shifts the
value) — and a small reset button. The Gain/X/Y headers are shown once at the top.
Editing a control mutates that Series and emits a signal so the window can redraw
just that curve.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..data.series import Series

_BIG = 1e12  # spin-box range cap; large enough for any real data

# Grid columns.
_COL_NAME = 0
_COL_GAIN = 1
_COL_X = 2
_COL_Y = 3
_COL_RESET = 4

_SPACER_ROW = 100_000  # grid row used only to pin content to the top


def _spin(value: float, decimals: int, step: float) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(-_BIG, _BIG)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    box.setMinimumWidth(48)
    box.setMaximumWidth(62)
    box.setKeyboardTracking(False)  # emit only when editing finishes / steps
    return box


def _swatch(color: str, size: int = 12) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor(color))
    return QIcon(pix)


@dataclass
class _Row:
    series: Series
    checkbox: QCheckBox
    gain: QDoubleSpinBox
    offset_x: QDoubleSpinBox
    offset_y: QDoubleSpinBox
    reset: QPushButton

    def widgets(self) -> list[QWidget]:
        return [self.checkbox, self.gain, self.offset_x, self.offset_y, self.reset]


class SeriesPanel(QWidget):
    """Compact grid: one row per series, shared Gain/X/Y headers on top."""

    visibility_changed = Signal(str, bool)
    transform_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self._grid.setHorizontalSpacing(6)
        self._grid.setVerticalSpacing(4)
        self._grid.setColumnStretch(_COL_NAME, 1)
        # Spacer row far below any real row, so rows stay packed at the top
        # instead of spreading across the panel height.
        self._grid.setRowStretch(_SPACER_ROW, 1)

        self._add_header()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._grid_host)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

        self._rows: list[_Row] = []

    def _add_header(self) -> None:
        for col, text in (
            (_COL_NAME, "Series"),
            (_COL_GAIN, "Gain"),
            (_COL_X, "X off"),
            (_COL_Y, "Y off"),
        ):
            label = QLabel(text)
            label.setStyleSheet("font-weight: 600;")
            align = Qt.AlignmentFlag.AlignLeft if col == _COL_NAME else Qt.AlignmentFlag.AlignHCenter
            self._grid.addWidget(label, 0, col, alignment=align)

    def set_series(self, series: list[Series]) -> None:
        """Rebuild the rows from a fresh set of series (header stays)."""
        for row in self._rows:
            for w in row.widgets():
                w.setParent(None)
                w.deleteLater()
        self._rows.clear()

        for i, s in enumerate(series, start=1):  # row 0 is the header
            checkbox = QCheckBox(s.name)
            checkbox.setIcon(_swatch(s.color))
            checkbox.setChecked(s.visible)

            gain = _spin(s.gain, decimals=3, step=0.1)
            offset_x = _spin(s.offset_x, decimals=3, step=0.1)
            offset_y = _spin(s.offset_y, decimals=3, step=0.1)

            reset = QPushButton("↺")  # ↺
            reset.setToolTip("Reset gain to 1 and offsets to 0")
            reset.setFixedWidth(28)

            row = _Row(s, checkbox, gain, offset_x, offset_y, reset)
            self._wire(row)

            self._grid.addWidget(checkbox, i, _COL_NAME)
            self._grid.addWidget(gain, i, _COL_GAIN)
            self._grid.addWidget(offset_x, i, _COL_X)
            self._grid.addWidget(offset_y, i, _COL_Y)
            self._grid.addWidget(reset, i, _COL_RESET)
            self._rows.append(row)

    def _wire(self, row: _Row) -> None:
        s = row.series
        row.checkbox.toggled.connect(lambda checked: self._on_visibility(s, checked))
        row.gain.valueChanged.connect(lambda v: self._on_transform(s, "gain", v))
        row.offset_x.valueChanged.connect(lambda v: self._on_transform(s, "offset_x", v))
        row.offset_y.valueChanged.connect(lambda v: self._on_transform(s, "offset_y", v))
        row.reset.clicked.connect(lambda: self._on_reset(row))

    # --- slots ---------------------------------------------------------
    def _on_visibility(self, series: Series, checked: bool) -> None:
        series.visible = checked
        self.visibility_changed.emit(series.name, checked)

    def _on_transform(self, series: Series, field: str, value: float) -> None:
        setattr(series, field, value)
        self.transform_changed.emit(series.name)

    def _on_reset(self, row: _Row) -> None:
        # Set all three without firing three redraws, then emit one.
        for box, value in ((row.gain, 1.0), (row.offset_x, 0.0), (row.offset_y, 0.0)):
            box.blockSignals(True)
            box.setValue(value)
            box.blockSignals(False)
        row.series.gain = 1.0
        row.series.offset_x = 0.0
        row.series.offset_y = 0.0
        self.transform_changed.emit(row.series.name)
