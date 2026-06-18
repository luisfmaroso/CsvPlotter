"""PinPanel — the pinned-points readout at the bottom of the left tab.

Shows where the (up to two) pinned tooltips are — the signal name and X/Y of each —
and the X/Y difference between them, with a button to clear both.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..data.series import fmt_num

_HINT = "Click a signal to pin a point (up to two)."


def _dot(color: str) -> str:
    return f"<span style='color:{color}'>&#9632;</span>"  # ■


class PinPanel(QWidget):
    """Readout for the pinned points; emits clear_requested for the Clear button."""

    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)

        title = QLabel("<b>Pinned points</b>")

        self.pin1_label = QLabel(_HINT)
        self.pin2_label = QLabel("")
        self.diff_label = QLabel("")
        for lbl in (self.pin1_label, self.pin2_label, self.diff_label):
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)

        self.clear_button = QPushButton("Clear points")
        self.clear_button.clicked.connect(self.clear_requested)
        self.clear_button.setEnabled(False)
        clear_row = QHBoxLayout()
        clear_row.addStretch(1)
        clear_row.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(3)
        layout.addWidget(divider)
        layout.addWidget(title)
        layout.addWidget(self.pin1_label)
        layout.addWidget(self.pin2_label)
        layout.addWidget(self.diff_label)
        layout.addLayout(clear_row)

    def update_readout(self, pins: list[tuple[str, str, float, float]]) -> None:
        """pins: (name, colour, x, y) for each pinned point, in order placed."""
        self.clear_button.setEnabled(bool(pins))

        if not pins:
            self.pin1_label.setText(_HINT)
            self.pin2_label.setText("")
            self.diff_label.setText("")
            return

        self.pin1_label.setText(self._pin_text(1, pins[0]))

        if len(pins) < 2:
            self.pin2_label.setText("Click again to pin a second point.")
            self.diff_label.setText("")
            return

        self.pin2_label.setText(self._pin_text(2, pins[1]))
        dx = pins[1][2] - pins[0][2]
        dy = pins[1][3] - pins[0][3]
        self.diff_label.setText(
            "<span style='font-family:monospace'>"
            f"<b>Δx = {fmt_num(dx)} &nbsp; Δy = {fmt_num(dy)}</b></span>"
        )

    @staticmethod
    def _pin_text(index: int, pin: tuple[str, str, float, float]) -> str:
        name, color, x, y = pin
        return (
            "<span style='font-family:monospace'>"
            f"{_dot(color)} <b>{index}.</b> {name} &nbsp; "
            f"x={fmt_num(x)} y={fmt_num(y)}</span>"
        )
