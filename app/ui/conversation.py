"""Conversation Thread View for Project FRIDAY.

Renders modern chat bubbles, tool execution cards, streaming replies, and input controls.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QScrollArea, QFrame, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject

from app.core.event_bus import event_bus, Events
from app.voice.voice_session import voice_session
from app.voice.text_to_speech import tts_manager
from app.ui.theme import (
    COLOR_BG_CARD, COLOR_CYAN_ACCENT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_BORDER
)


class ConversationBridge(QObject):
    """Qt signal bridge for thread-safe UI updates from the event bus."""
    user_message_received = Signal(dict)
    assistant_message_received = Signal(dict)
    state_changed = Signal(str)


class ConversationView(QWidget):
    """Full-featured conversation view with rich message bubbles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bridge = ConversationBridge()
        self.bridge.user_message_received.connect(self._add_user_message)
        self.bridge.assistant_message_received.connect(self._add_assistant_message)
        self._setup_ui()

        # Connect to event bus
        event_bus.subscribe(Events.USER_MESSAGE, lambda d: self.bridge.user_message_received.emit(d))
        event_bus.subscribe(Events.ASSISTANT_MESSAGE, lambda d: self.bridge.assistant_message_received.emit(d))

        # Initial assistant greeting
        self._add_assistant_message({
            "text": "Hello! FRIDAY is online and standing by. What would you like to work on today?",
            "tool_results": None,
        })

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Message Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(8, 8, 8, 8)
        self.messages_layout.setSpacing(14)
        self.messages_layout.addStretch()

        self.scroll.setWidget(self.messages_container)
        layout.addWidget(self.scroll)

        # Input Row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Ask FRIDAY or issue a desktop command... (Press Enter to send)")
        self.txt_input.returnPressed.connect(self._send_text_message)
        input_row.addWidget(self.txt_input)

        self.btn_send = QPushButton("Send")
        self.btn_send.setProperty("class", "primary-btn")
        self.btn_send.clicked.connect(self._send_text_message)
        input_row.addWidget(self.btn_send)

        self.btn_mic = QPushButton("🎙️ Speak")
        self.btn_mic.setProperty("class", "secondary-btn")
        self.btn_mic.clicked.connect(self._on_mic_clicked)
        input_row.addWidget(self.btn_mic)

        self.btn_stop_speech = QPushButton("⏹️ Stop Voice")
        self.btn_stop_speech.setProperty("class", "secondary-btn")
        self.btn_stop_speech.clicked.connect(lambda: tts_manager.stop_speaking())
        input_row.addWidget(self.btn_stop_speech)

        layout.addLayout(input_row)

    def _send_text_message(self) -> None:
        text = self.txt_input.text().strip()
        if not text:
            return
        self.txt_input.clear()
        event_bus.publish(Events.USER_MESSAGE, {"text": text, "source": "text"})

    def _on_mic_clicked(self) -> None:
        voice_session.push_to_talk()

    def _add_user_message(self, data: dict) -> None:
        text = data.get("text", "")
        time_str = datetime.now().strftime("%H:%M")

        bubble = QFrame()
        bubble.setStyleSheet(f"""
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 10px;
        """)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        vbox = QVBoxLayout(bubble)
        vbox.setContentsMargins(12, 10, 12, 10)
        vbox.setSpacing(4)

        header = QLabel(f"<span style='color: #94A3B8; font-weight: bold;'>You</span> &nbsp;<span style='color: #64748B; font-size: 11px;'>{time_str}</span>")
        content = QLabel(text)
        content.setWordWrap(True)
        content.setStyleSheet("font-size: 13px; color: #FFFFFF;")

        vbox.addWidget(header)
        vbox.addWidget(content)

        # Right align bubble
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(bubble)

        # Insert before stretch
        count = self.messages_layout.count()
        self.messages_layout.insertLayout(count - 1, row)
        self._scroll_to_bottom()

    def _add_assistant_message(self, data: dict) -> None:
        text = data.get("text", "")
        tool_results = data.get("tool_results")
        time_str = datetime.now().strftime("%H:%M")

        bubble = QFrame()
        bubble.setProperty("class", "glass-card")
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        vbox = QVBoxLayout(bubble)
        vbox.setContentsMargins(14, 12, 14, 12)
        vbox.setSpacing(6)

        header = QLabel(f"<span style='color: {COLOR_CYAN_ACCENT}; font-weight: bold;'>FRIDAY</span> &nbsp;<span style='color: #64748B; font-size: 11px;'>{time_str}</span>")
        vbox.addWidget(header)

        # Tool execution summary if present
        if tool_results:
            tools_box = QFrame()
            tools_box.setStyleSheet("background-color: #0F172A; border-radius: 6px; padding: 6px;")
            t_layout = QVBoxLayout(tools_box)
            t_layout.setContentsMargins(8, 6, 8, 6)
            for tr in tool_results:
                status_icon = "✅" if tr["outcome"].get("success") else "⚠️"
                t_lbl = QLabel(f"{status_icon} <code>{tr['name']}</code>: {tr['outcome'].get('message') or 'Executed'}")
                t_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
                t_layout.addWidget(t_lbl)
            vbox.addWidget(tools_box)

        content = QLabel(text)
        content.setWordWrap(True)
        content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content.setStyleSheet("font-size: 13px; color: #E2E8F0; line-height: 1.4;")
        vbox.addWidget(content)

        # Left align bubble
        row = QHBoxLayout()
        row.addWidget(bubble)
        row.addStretch()

        count = self.messages_layout.count()
        self.messages_layout.insertLayout(count - 1, row)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
