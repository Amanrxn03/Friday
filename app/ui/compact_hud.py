"""Compact Floating HUD Mode for Project FRIDAY.

A minimalist, always-on-top floating pill interface designed for unobtrusive desktop presence.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor

from app.ui.widgets.waveform import WaveformVisualizer
from app.voice.voice_session import voice_session
from app.core.event_bus import event_bus, Events
from app.ui.theme import COLOR_BG_DARK, COLOR_BORDER, COLOR_CYAN_ACCENT
from app.config import config


class CompactHUD(QWidget):
    """Floating compact pill widget staying on top of other windows."""

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self._drag_pos = QPoint()

        # Frameless and always on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(540, 64)

        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Inner container pill
        self.pill = QWidget(self)
        self.pill.setStyleSheet(f"""
            QWidget {{
                background-color: #121824;
                border: 1px solid #1E2D4A;
                border-radius: 22px;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.pill.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.pill)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(10)

        # Logo / Drag handle
        logo = QLabel(f"{config.app_name} · {config.assistant_nickname}")
        logo.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {COLOR_CYAN_ACCENT}; letter-spacing: 1px;")
        layout.addWidget(logo)

        # Waveform
        self.waveform = WaveformVisualizer(num_bars=16)
        self.waveform.setFixedSize(90, 32)
        layout.addWidget(self.waveform)

        # Quick Input
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Ask FRIDAY...")
        self.txt_input.setStyleSheet("background-color: #182234; border: 1px solid #1E2D4A; border-radius: 14px; padding: 4px 10px; font-size: 12px;")
        self.txt_input.returnPressed.connect(self._submit)
        layout.addWidget(self.txt_input)

        # Mic Button
        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setFixedSize(32, 32)
        self.btn_mic.setStyleSheet(f"background-color: #182234; border: 1px solid #1E2D4A; border-radius: 16px; font-size: 14px;")
        self.btn_mic.clicked.connect(lambda: voice_session.push_to_talk())
        layout.addWidget(self.btn_mic)

        # Expand Button
        self.btn_expand = QPushButton("⛶")
        self.btn_expand.setToolTip("Expand to Full Workspace")
        self.btn_expand.setFixedSize(32, 32)
        self.btn_expand.setStyleSheet(f"background-color: #182234; border: 1px solid #1E2D4A; border-radius: 16px; font-size: 13px;")
        self.btn_expand.clicked.connect(self._restore_main_window)
        layout.addWidget(self.btn_expand)

        outer_layout.addWidget(self.pill)

    def _submit(self) -> None:
        text = self.txt_input.text().strip()
        if text:
            self.txt_input.clear()
            event_bus.publish(Events.USER_MESSAGE, {"text": text, "source": "compact_hud"})

    def _restore_main_window(self) -> None:
        self.hide()
        if self.main_window:
            self.main_window.show()
            self.main_window.activateWindow()

    # Enable dragging anywhere on the pill
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
