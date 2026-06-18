"""The Series model.

One Series per data column. It holds the *raw* Time (x) and value (y) arrays and a
set of display parameters (gain, offsets, visibility, colour). The raw arrays are
never mutated — the plotted arrays are computed on the fly by ``plot_x`` / ``plot_y``,
so "reset to original" is just resetting the parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# A palette that reads well on the dark plot background. Cycled across series.
DEFAULT_PALETTE = [
    "#4f9dde",  # blue
    "#e8703a",  # orange
    "#5fbf6f",  # green
    "#d65f8a",  # pink
    "#c9a227",  # gold
    "#9b7fd1",  # purple
    "#46b3b3",  # teal
    "#d6564a",  # red
]


def palette_color(index: int) -> str:
    """Pick a colour for the *index*-th series, cycling the palette."""
    return DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)]


def fmt_num(value: float) -> str:
    """Compact, readable number formatting shared by the readouts."""
    return f"{value:.6g}"


@dataclass
class Series:
    name: str
    x: np.ndarray
    y: np.ndarray
    color: str
    visible: bool = True
    gain: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    def plot_x(self) -> np.ndarray:
        """X values as displayed (Time shifted by the X offset)."""
        return self.x + self.offset_x

    def plot_y(self) -> np.ndarray:
        """Y values as displayed (scaled by gain, then shifted by the Y offset)."""
        return self.y * self.gain + self.offset_y

    def sample_at(self, x: float) -> tuple[float, float] | None:
        """The (x, y) of the sample nearest to *x* in plotted coordinates, or
        None if *x* falls outside this series' range."""
        xs = self.plot_x()
        if xs.size == 0 or x < xs[0] or x > xs[-1]:
            return None
        idx = int(np.searchsorted(xs, x))
        if idx > 0 and (idx == xs.size or abs(xs[idx - 1] - x) <= abs(xs[idx] - x)):
            idx -= 1
        return float(xs[idx]), float(self.plot_y()[idx])
