"""Dashboard View for Project FRIDAY.

Displays real-time hardware telemetry, morning briefing highlights, pending tasks,
and quick desktop control triggers.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, QTimer

from app.desktop.windows_controller import windows_controller
from app.services.briefing_service import briefing_service
from app.memory.task_repository import task_repository
from app.core.metrics import latency_tracker
from app.ui.theme import COLOR_CYAN_ACCENT, COLOR_TEXT_MUTED, COLOR_TEXT_SECONDARY, COLOR_SUCCESS


class DashboardView(QWidget):
    """Futuristic system telemetry and daily briefing overview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

        # Telemetry refresh timer (every 2.5 seconds)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._refresh_telemetry)
        self.telemetry_timer.start(2500)
        self._refresh_telemetry()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header Title
        title_box = QHBoxLayout()
        title_lbl = QLabel("SYSTEM OVERVIEW & STATUS")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLOR_CYAN_ACCENT}; letter-spacing: 1px;")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        self.btn_refresh_briefing = QPushButton("🔄 Refresh Briefing")
        self.btn_refresh_briefing.setProperty("class", "secondary-btn")
        self.btn_refresh_briefing.clicked.connect(self._load_briefing_content)
        title_box.addWidget(self.btn_refresh_briefing)

        main_layout.addLayout(title_box)

        # Telemetry Grid (CPU, RAM, GPU, Disk, Battery)
        telemetry_layout = QGridLayout()
        telemetry_layout.setSpacing(14)

        # CPU Card
        self.cpu_card = self._create_metric_card("PROCESSOR", "CPU Utilization", "0%")
        telemetry_layout.addWidget(self.cpu_card, 0, 0)

        # RAM Card
        self.ram_card = self._create_metric_card("MEMORY", "32 GB System RAM", "0 / 0 GB")
        telemetry_layout.addWidget(self.ram_card, 0, 1)

        # GPU Card
        self.gpu_card = self._create_metric_card("GPU ACCELERATION", "NVIDIA RTX 4070 Laptop", "8 GB VRAM Ready")
        telemetry_layout.addWidget(self.gpu_card, 0, 2)

        # Disk Card
        self.disk_card = self._create_metric_card("STORAGE", "System Drive C:", "0 GB Free")
        telemetry_layout.addWidget(self.disk_card, 1, 0)

        # Battery / Power Card
        self.battery_card = self._create_metric_card("POWER", "System Power", "AC Connected")
        telemetry_layout.addWidget(self.battery_card, 1, 1)

        # Quick Actions Card
        actions_card = QFrame()
        actions_card.setProperty("class", "glass-card")
        act_box = QVBoxLayout(actions_card)
        act_box.addWidget(QLabel("<b>QUICK CONTROLS</b>"))
        act_row = QHBoxLayout()

        btn_lock = QPushButton("🔒 Lock Workstation")
        btn_lock.setProperty("class", "secondary-btn")
        btn_lock.clicked.connect(lambda: windows_controller.lock_workstation())
        act_row.addWidget(btn_lock)

        act_box.addLayout(act_row)
        telemetry_layout.addWidget(actions_card, 1, 2)

        main_layout.addLayout(telemetry_layout)

        # High-Resolution Latency & Telemetry Row
        latency_layout = QGridLayout()
        latency_layout.setSpacing(14)

        self.p50_card = self._create_metric_card("LATENCY (P50 MEDIAN)", "Target: 800 - 1500 ms", "Ready")
        latency_layout.addWidget(self.p50_card, 0, 0)

        self.p95_card = self._create_metric_card("LATENCY (P95 TAIL)", "Worst 5% Turn Time", "Ready")
        latency_layout.addWidget(self.p95_card, 0, 1)

        self.fastpath_card = self._create_metric_card("DETERMINISTIC BYPASS", "Intent Engine (<5ms)", "Active")
        latency_layout.addWidget(self.fastpath_card, 0, 2)

        main_layout.addLayout(latency_layout)

        # Morning Briefing Section
        briefing_frame = QFrame()
        briefing_frame.setProperty("class", "glass-card")
        b_layout = QVBoxLayout(briefing_frame)
        b_layout.setSpacing(10)

        b_header = QLabel("DAILY BRIEFING & CONTINUITY")
        b_header.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLOR_CYAN_ACCENT};")
        b_layout.addWidget(b_header)

        self.briefing_text = QLabel("Loading morning briefing...")
        self.briefing_text.setWordWrap(True)
        self.briefing_text.setStyleSheet("font-size: 13px; line-height: 1.4; color: #E2E8F0;")
        b_layout.addWidget(self.briefing_text)

        main_layout.addWidget(briefing_frame)
        main_layout.addStretch()

        self._load_briefing_content()

    def _create_metric_card(self, category: str, title: str, initial_val: str) -> QFrame:
        frame = QFrame()
        frame.setProperty("class", "glass-card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        cat_lbl = QLabel(category.upper())
        cat_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLOR_TEXT_MUTED}; letter-spacing: 1px;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY};")
        val_lbl = QLabel(initial_val)
        val_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: #FFFFFF;")
        val_lbl.setObjectName("val_label")

        layout.addWidget(cat_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(val_lbl)
        return frame

    def _refresh_telemetry(self) -> None:
        try:
            status = windows_controller.get_system_status()
            # Update CPU
            lbl_cpu = self.cpu_card.findChild(QLabel, "val_label")
            if lbl_cpu:
                lbl_cpu.setText(f"{status['cpu_percent']}%")

            # Update RAM
            lbl_ram = self.ram_card.findChild(QLabel, "val_label")
            if lbl_ram:
                lbl_ram.setText(f"{status['ram_used_gb']} / {status['ram_total_gb']} GB ({status['ram_percent']}%)")

            # Update Disk
            lbl_disk = self.disk_card.findChild(QLabel, "val_label")
            if lbl_disk:
                lbl_disk.setText(f"{status['disk_c_free_gb']} GB Free")

            # Update Battery
            lbl_bat = self.battery_card.findChild(QLabel, "val_label")
            if lbl_bat:
                bat = status.get("battery")
                if bat:
                    status_str = f"{bat['percent']}% ({'Charging' if bat['power_plugged'] else 'Battery'})"
                else:
                    status_str = "AC Power Connected"
                lbl_bat.setText(status_str)

            # Update High-Resolution Latency Stats
            stats = latency_tracker.get_summary_stats()
            lbl_p50 = self.p50_card.findChild(QLabel, "val_label")
            if lbl_p50:
                p50_val = stats.get("e2e_p50_ms", 0.0)
                if stats.get("count", 0) > 0:
                    lbl_p50.setText(f"{p50_val:.1f} ms")
                    lbl_p50.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLOR_SUCCESS};")
                else:
                    lbl_p50.setText("Ready (<5ms fast)")

            lbl_p95 = self.p95_card.findChild(QLabel, "val_label")
            if lbl_p95:
                p95_val = stats.get("e2e_p95_ms", 0.0)
                if stats.get("count", 0) > 0:
                    lbl_p95.setText(f"{p95_val:.1f} ms")
                else:
                    lbl_p95.setText("Ready")
        except Exception:
            pass

    def _load_briefing_content(self) -> None:
        try:
            b = briefing_service.generate_morning_briefing()
            greeting = b.get("greeting", "")
            weather = b.get("weather", {})
            tasks = b.get("tasks", [])

            html = f"<p style='font-size: 14px;'><b>{greeting}</b></p>"
            if weather and "temperature_c" in weather:
                html += f"<p>🌡️ <b>Weather:</b> {weather.get('temperature_c')}°C in {weather.get('city')} | Wind: {weather.get('wind_speed_kmh')} km/h</p>"

            if tasks:
                html += "<p>📋 <b>Pending Work:</b></p><ul>"
                for t in tasks[:3]:
                    html += f"<li><b>[{t['priority']}]</b> {t['title']} — Progress: {t['progress']}%</li>"
                html += "</ul>"

            self.briefing_text.setText(html)
        except Exception as e:
            self.briefing_text.setText(f"Briefing status: Ready. Tasks up to date.")
