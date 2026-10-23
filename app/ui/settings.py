"""Settings and Security View for Project FRIDAY.

Configures AI provider credentials via Windows Credential Manager, local Ollama runtime,
Windows startup integration, voice parameters, and autonomy permission modes.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QSlider, QCheckBox, QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt

from app.security.secret_store import secret_store
from app.ai.provider_manager import provider_manager
from app.voice.text_to_speech import tts_manager
from app.services.startup_service import startup_service
from app.core.permissions import permissions_engine
from app.config import config, AutonomyMode
from app.ui.theme import COLOR_CYAN_ACCENT, COLOR_SUCCESS, COLOR_DANGER


class SettingsView(QWidget):
    """Settings and system configuration panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Title
        title_lbl = QLabel("SETTINGS & SECURITY PREFERENCES")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLOR_CYAN_ACCENT};")
        layout.addWidget(title_lbl)

        # Section 1: AI Provider Configuration
        prov_card = QFrame()
        prov_card.setProperty("class", "glass-card")
        p_layout = QVBoxLayout(prov_card)
        p_layout.setSpacing(12)

        p_layout.addWidget(QLabel("<b>AI PROVIDER & REASONING ENGINE</b>"))

        # Active Provider Selector
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Active Provider:"))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["ollama", "openai", "gemini", "anthropic"])
        self.combo_provider.setCurrentText(provider_manager.get_active_provider_name())
        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)
        row1.addWidget(self.combo_provider)

        self.btn_test_conn = QPushButton("⚡ Test Connection")
        self.btn_test_conn.setProperty("class", "secondary-btn")
        self.btn_test_conn.clicked.connect(self._test_connection)
        row1.addWidget(self.btn_test_conn)
        row1.addStretch()
        p_layout.addLayout(row1)

        # OpenAI API Key Input
        row_oai = QHBoxLayout()
        row_oai.addWidget(QLabel("OpenAI API Key:"))
        self.txt_openai_key = QLineEdit()
        self.txt_openai_key.setEchoMode(QLineEdit.Password)
        self.txt_openai_key.setPlaceholderText("sk-... (Stored securely in Windows Credential Manager)")
        if secret_store.has_credential("openai"):
            self.txt_openai_key.setText("••••••••••••••••••••••••")
        row_oai.addWidget(self.txt_openai_key)

        btn_save_oai = QPushButton("Save")
        btn_save_oai.setProperty("class", "secondary-btn")
        btn_save_oai.clicked.connect(lambda: self._save_key("openai", self.txt_openai_key.text()))
        row_oai.addWidget(btn_save_oai)
        p_layout.addLayout(row_oai)

        # Gemini API Key Input
        row_gem = QHBoxLayout()
        row_gem.addWidget(QLabel("Gemini API Key:"))
        self.txt_gemini_key = QLineEdit()
        self.txt_gemini_key.setEchoMode(QLineEdit.Password)
        self.txt_gemini_key.setPlaceholderText("AIza... (Google AI Studio Key)")
        if secret_store.has_credential("gemini"):
            self.txt_gemini_key.setText("••••••••••••••••••••••••")
        row_gem.addWidget(self.txt_gemini_key)

        btn_save_gem = QPushButton("Save")
        btn_save_gem.setProperty("class", "secondary-btn")
        btn_save_gem.clicked.connect(lambda: self._save_key("gemini", self.txt_gemini_key.text()))
        row_gem.addWidget(btn_save_gem)
        p_layout.addLayout(row_gem)

        # Anthropic API Key Input
        row_ant = QHBoxLayout()
        row_ant.addWidget(QLabel("Anthropic Key:"))
        self.txt_anthropic_key = QLineEdit()
        self.txt_anthropic_key.setEchoMode(QLineEdit.Password)
        self.txt_anthropic_key.setPlaceholderText("sk-ant-... (Claude Key)")
        if secret_store.has_credential("anthropic"):
            self.txt_anthropic_key.setText("••••••••••••••••••••••••")
        row_ant.addWidget(self.txt_anthropic_key)

        btn_save_ant = QPushButton("Save")
        btn_save_ant.setProperty("class", "secondary-btn")
        btn_save_ant.clicked.connect(lambda: self._save_key("anthropic", self.txt_anthropic_key.text()))
        row_ant.addWidget(btn_save_ant)
        p_layout.addLayout(row_ant)

        layout.addWidget(prov_card)

        # Section 2: Autonomy & Permissions Mode
        perm_card = QFrame()
        perm_card.setProperty("class", "glass-card")
        perm_layout = QVBoxLayout(perm_card)
        perm_layout.addWidget(QLabel("<b>SAFE AUTONOMY & PERMISSION LEVEL</b>"))

        row_perm = QHBoxLayout()
        row_perm.addWidget(QLabel("Execution Mode:"))
        self.combo_autonomy = QComboBox()
        self.combo_autonomy.addItems([
            "APPROVED_AUTONOMY (Mode 2: Low-risk auto, high-impact confirms)",
            "CONFIRM_HIGH_IMPACT (Mode 3: Always confirm high impact)",
            "SUGGEST (Mode 1: Suggest only, wait for approval)",
        ])
        if permissions_engine.mode == AutonomyMode.SUGGEST:
            self.combo_autonomy.setCurrentIndex(2)
        elif permissions_engine.mode == AutonomyMode.CONFIRM_HIGH_IMPACT:
            self.combo_autonomy.setCurrentIndex(1)
        else:
            self.combo_autonomy.setCurrentIndex(0)

        self.combo_autonomy.currentIndexChanged.connect(self._on_autonomy_mode_changed)
        row_perm.addWidget(self.combo_autonomy)
        row_perm.addStretch()
        perm_layout.addLayout(row_perm)
        layout.addWidget(perm_card)

        # Section 3: Windows Startup Registration
        start_card = QFrame()
        start_card.setProperty("class", "glass-card")
        start_layout = QVBoxLayout(start_card)
        start_layout.addWidget(QLabel("<b>WINDOWS STARTUP INTEGRATION</b>"))

        row_start = QHBoxLayout()
        self.chk_startup = QCheckBox("Launch FRIDAY automatically when signing in to Windows")
        self.chk_startup.setChecked(startup_service.is_startup_enabled())
        self.chk_startup.toggled.connect(self._on_startup_toggled)
        row_start.addWidget(self.chk_startup)
        row_start.addStretch()
        start_layout.addLayout(row_start)
        layout.addWidget(start_card)

        # Section 4: Multilingual Voice & Speech Synthesis
        voice_card = QFrame()
        voice_card.setProperty("class", "glass-card")
        v_layout = QVBoxLayout(voice_card)
        v_layout.addWidget(QLabel("<b>MULTILINGUAL VOICE & SPEECH CONFIGURATION</b>"))

        # Language Mode
        row_lang = QHBoxLayout()
        row_lang.addWidget(QLabel("Spoken Language Mode:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems([
            "Auto-Detect (English, Hindi, Hinglish)",
            "English (English Only)",
            "Hindi (हिंदी)",
            "Hinglish (Natural Code-Switching)",
        ])
        row_lang.addWidget(self.combo_lang)
        row_lang.addStretch()
        v_layout.addLayout(row_lang)

        # Automatic Adaptation Checkbox
        row_auto_switch = QHBoxLayout()
        self.chk_auto_switch = QCheckBox("Enable automatic language switching in mid-conversation")
        self.chk_auto_switch.setChecked(True)
        row_auto_switch.addWidget(self.chk_auto_switch)
        row_auto_switch.addStretch()
        v_layout.addLayout(row_auto_switch)

        # Accent & Hinglish Style
        row_style = QHBoxLayout()
        row_style.addWidget(QLabel("English Accent:"))
        self.combo_accent = QComboBox()
        self.combo_accent.addItems(["Indian English (Natural)", "Standard English"])
        row_style.addWidget(self.combo_accent)

        row_style.addWidget(QLabel("Hinglish Style:"))
        self.combo_hinglish = QComboBox()
        self.combo_hinglish.addItems(["Conversational & Natural", "Technical & Concise", "Formal"])
        row_style.addWidget(self.combo_hinglish)
        row_style.addStretch()
        v_layout.addLayout(row_style)

        # Speech Rate
        row_rate = QHBoxLayout()
        row_rate.addWidget(QLabel("Speech Rate (WPM):"))
        self.slider_rate = QSlider(Qt.Horizontal)
        self.slider_rate.setRange(120, 240)
        self.slider_rate.setValue(tts_manager.speech_rate)
        self.slider_rate.valueChanged.connect(lambda v: tts_manager.update_settings(rate=v))
        row_rate.addWidget(self.slider_rate)
        v_layout.addLayout(row_rate)

        # Speech Volume
        row_vol = QHBoxLayout()
        row_vol.addWidget(QLabel("Speech Volume:"))
        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(int(tts_manager.volume * 100))
        self.slider_vol.valueChanged.connect(lambda v: tts_manager.update_settings(volume=v / 100.0))
        row_vol.addWidget(self.slider_vol)
        v_layout.addLayout(row_vol)

        layout.addWidget(voice_card)
        layout.addStretch()

        scroll.setWidget(container)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _save_key(self, provider: str, key_val: str) -> None:
        if not key_val or "••••" in key_val:
            return
        success = secret_store.set_credential(provider, key_val)
        if success:
            QMessageBox.information(self, "Saved", f"Securely stored {provider.title()} API key in Windows Credential Manager.")

    def _test_connection(self) -> None:
        provider = self.combo_provider.currentText()
        res = provider_manager.test_connectivity(provider)
        if res.get("success"):
            QMessageBox.information(
                self, "Connected", f"Successfully reached {provider.title()} ({res.get('model')})!\nResponse: {res.get('content')}"
            )
        else:
            QMessageBox.warning(
                self, "Connection Failed", f"Could not connect to {provider.title()}:\n{res.get('error')}"
            )

    def _on_provider_changed(self, new_prov: str) -> None:
        provider_manager.set_active_provider(new_prov)

    def _on_autonomy_mode_changed(self, idx: int) -> None:
        if idx == 0:
            permissions_engine.set_autonomy_mode(AutonomyMode.APPROVED_AUTONOMY)
        elif idx == 1:
            permissions_engine.set_autonomy_mode(AutonomyMode.CONFIRM_HIGH_IMPACT)
        else:
            permissions_engine.set_autonomy_mode(AutonomyMode.SUGGEST)

    def _on_startup_toggled(self, checked: bool) -> None:
        if checked:
            startup_service.enable_startup()
        else:
            startup_service.disable_startup()
