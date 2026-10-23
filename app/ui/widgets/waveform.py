"""Animated Voice Waveform Widget for Project FRIDAY.

Renders an active audio waveform visualizer driven by real-time microphone RMS energy
and speech states.
"""

from collections import deque
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from app.core.event_bus import event_bus, Events
from app.ui.theme import COLOR_CYAN_ACCENT, COLOR_CYAN_DIM, COLOR_BORDER


class WaveformVisualizer(QWidget):
    """Futuristic animated audio visualizer bar widget."""

    def __init__(self, parent=None, num_bars: int = 24):
        super().__init__(parent)
        self.num_bars = num_bars
        self.bar_values = deque([0.05] * num_bars, maxlen=num_bars)
        self.target_level = 0.05
        self.setMinimumHeight(40)
        self.setMaximumHeight(60)

        # Animation update timer (~30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_tick)
        self.timer.start(33)

        # Connect to event bus
        event_bus.subscribe(Events.AUDIO_LEVEL, self._on_audio_level)
        event_bus.subscribe(Events.VOICE_STATE, self._on_voice_state)

    def _on_audio_level(self, level: float) -> None:
        self.target_level = max(0.05, min(1.0, float(level)))

    def _on_voice_state(self, state: str) -> None:
        if state == "SPEAKING":
            # Oscillate during speech playback
            self.target_level = 0.6
        elif state == "IDLE":
            self.target_level = 0.05

    def _animate_tick(self) -> None:
        import random
        # Smooth interpolation towards target with subtle natural jitter
        current = self.bar_values[-1]
        step = (self.target_level - current) * 0.35
        jitter = (random.random() - 0.5) * 0.1 * self.target_level
        new_val = max(0.05, min(1.0, current + step + jitter))
        self.bar_values.append(new_val)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        bar_width = max(2.0, (width / self.num_bars) - 3.0)
        center_y = height / 2.0

        for i, val in enumerate(self.bar_values):
            x = i * (bar_width + 3.0)
            bar_height = max(4.0, val * (height * 0.85))
            y = center_y - (bar_height / 2.0)

            # Intensity color based on amplitude
            alpha = int(100 + val * 155)
            color = QColor(COLOR_CYAN_ACCENT)
            color.setAlpha(alpha)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_height, 2, 2)

        painter.end()
