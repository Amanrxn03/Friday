"""Master Main Window for Project FRIDAY.

Brings together the sidebar navigation, top status bar, real-time audio waveform,
approval modal trigger, emergency stop controls, and compact HUD switcher.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QObject

from app.ui.theme import FRIDAY_STYLESHEET, COLOR_CYAN_ACCENT, COLOR_DANGER, COLOR_SUCCESS
from app.ui.widgets.waveform import WaveformVisualizer
from app.ui.widgets.approval_dialog import ApprovalDialog
from app.ui.conversation import ConversationView
from app.ui.dashboard import DashboardView
from app.ui.tasks_view import TasksView
from app.ui.memory_view import MemoryView
from app.ui.settings import SettingsView
from app.ui.compact_hud import CompactHUD
from app.core.event_bus import event_bus, Events
from app.core.permissions import permissions_engine, ApprovalRequest
from app.voice.audio_stream import audio_stream
from app.voice.voice_session import voice_session
from app.ai.provider_manager import provider_manager


class MainWindowBridge(QObject):
    approval_requested = Signal(object)
    status_changed = Signal(str)
    provider_changed = Signal(dict)


class MainWindow(QMainWindow):
    """Primary desktop interface for Project FRIDAY."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FRIDAY — Personal AI Desktop Companion")
        self.resize(1180, 780)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(FRIDAY_STYLESHEET)

        self.bridge = MainWindowBridge()
        self.bridge.approval_requested.connect(self._show_approval_dialog)
        self.bridge.status_changed.connect(self._update_status_badge)
        self.bridge.provider_changed.connect(self._update_provider_badge)

        self.compact_hud = CompactHUD(main_window=self)

        self._setup_ui()
        self._setup_event_subscriptions()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Header Bar
        header = self._create_header_bar()
        main_layout.addWidget(header)

        # 2. Main Content Body (Sidebar + Stacked Views)
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Sidebar
        sidebar = self._create_sidebar()
        body_layout.addWidget(sidebar)

        # Central Stacked Views
        self.stack = QStackedWidget()
        self.view_conversation = ConversationView()
        self.view_dashboard = DashboardView()
        self.view_tasks = TasksView()
        self.view_memory = MemoryView()
        self.view_settings = SettingsView()

        self.stack.addWidget(self.view_conversation)  # Index 0
        self.stack.addWidget(self.view_dashboard)     # Index 1
        self.stack.addWidget(self.view_tasks)         # Index 2
        self.stack.addWidget(self.view_memory)        # Index 3
        self.stack.addWidget(self.view_settings)      # Index 4

        body_layout.addWidget(self.stack)
        main_layout.addWidget(body)

    def _create_header_bar(self) -> QFrame:
        header = QFrame()
        header.setObjectName("HeaderBar")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(14)

        # Logo & Name
        logo = QLabel("FRIDAY")
        logo.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {COLOR_CYAN_ACCENT}; letter-spacing: 2px;")
        layout.addWidget(logo)

        # Status Badge
        self.lbl_status = QLabel("● Ready")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #10B981; background: #132E27; border-radius: 4px; padding: 2px 8px;")
        layout.addWidget(self.lbl_status)

        # Active Provider Badge
        self.lbl_provider = QLabel(f"AI: {provider_manager.get_active_provider_name().upper()}")
        self.lbl_provider.setStyleSheet("font-size: 11px; color: #94A3B8; background: #182234; border-radius: 4px; padding: 2px 8px;")
        layout.addWidget(self.lbl_provider)

        layout.addStretch()

        # Waveform Visualizer
        self.waveform = WaveformVisualizer(num_bars=24)
        self.waveform.setFixedWidth(140)
        layout.addWidget(self.waveform)

        # Mic Controls
        self.btn_ptt = QPushButton("🎙️ Push to Talk")
        self.btn_ptt.setProperty("class", "secondary-btn")
        self.btn_ptt.clicked.connect(lambda: voice_session.push_to_talk())
        layout.addWidget(self.btn_ptt)

        self.btn_mute = QPushButton("🎤 Mute")
        self.btn_mute.setProperty("class", "secondary-btn")
        self.btn_mute.clicked.connect(self._toggle_mute)
        layout.addWidget(self.btn_mute)

        # Compact Mode Switcher
        self.btn_compact = QPushButton("⛶ Compact HUD")
        self.btn_compact.setProperty("class", "secondary-btn")
        self.btn_compact.clicked.connect(self._switch_to_compact_mode)
        layout.addWidget(self.btn_compact)

        # Global Emergency Stop
        self.btn_emergency_stop = QPushButton("🛑 EMERGENCY STOP")
        self.btn_emergency_stop.setProperty("class", "danger-btn")
        self.btn_emergency_stop.clicked.connect(self._on_emergency_stop_clicked)
        layout.addWidget(self.btn_emergency_stop)

        return header

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        tabs = [
            ("💬  Conversation", 0),
            ("📊  Dashboard", 1),
            ("📋  Tasks & Workflows", 2),
            ("🧠  Memory Manager", 3),
            ("⚙️  Settings & Security", 4),
        ]

        for label, idx in tabs:
            btn = QPushButton(label)
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, i=idx: self.stack.setCurrentIndex(i))
            self.btn_group.addButton(btn)
            layout.addWidget(btn)

        layout.addStretch()
        return sidebar

    def _setup_event_subscriptions(self) -> None:
        event_bus.subscribe(Events.APPROVAL_REQUIRED, lambda req: self.bridge.approval_requested.emit(req))
        event_bus.subscribe(Events.STATE_CHANGED, lambda s: self.bridge.status_changed.emit(s))
        event_bus.subscribe(Events.PROVIDER_CHANGED, lambda d: self.bridge.provider_changed.emit(d))

    def _show_approval_dialog(self, request: ApprovalRequest) -> None:
        dialog = ApprovalDialog(request, self)
        dialog.exec()

    def _update_status_badge(self, state: str) -> None:
        color = "#10B981"
        bg = "#132E27"
        if state in ("Thinking", "Executing"):
            color = "#00E5FF"
            bg = "#0C2E38"
        elif state == "Waiting for Approval":
            color = "#F59E0B"
            bg = "#382A0C"
        elif state == "Error":
            color = "#EF4444"
            bg = "#381010"

        self.lbl_status.setText(f"● {state}")
        self.lbl_status.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {color}; background: {bg}; border-radius: 4px; padding: 2px 8px;")

    def _update_provider_badge(self, data: dict) -> None:
        prov = data.get("provider", "unknown")
        self.lbl_provider.setText(f"AI: {prov.upper()}")

    def _toggle_mute(self) -> None:
        new_state = audio_stream.toggle_mute()
        self.btn_mute.setText("🔇 Unmute" if new_state else "🎤 Mute")

    def _on_emergency_stop_clicked(self) -> None:
        if permissions_engine.is_emergency_stopped():
            permissions_engine.reset_emergency_stop()
            self.btn_emergency_stop.setText("🛑 EMERGENCY STOP")
            self.btn_emergency_stop.setProperty("class", "danger-btn")
        else:
            permissions_engine.trigger_emergency_stop("User clicked Emergency Stop button")
            self.btn_emergency_stop.setText("✅ RESUME SYSTEM")

    def _switch_to_compact_mode(self) -> None:
        self.hide()
        self.compact_hud.show()
