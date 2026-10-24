"""Settings and Security View for Project FRIDAY.

Configures AI provider credentials via Windows Credential Manager, local Ollama runtime,
Windows startup integration, voice parameters, and autonomy permission modes.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QSlider, QCheckBox, QFrame, QScrollArea, QMessageBox, QFileDialog
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
        v_layout.addWidget(QLabel("<b>VOICE PERSONA & CUSTOM VOICE CLONING (KRITI'S VOICE)</b>"))

        # Voice Profile Selector
        row_voice = QHBoxLayout()
        row_voice.addWidget(QLabel("Active Voice Persona:"))
        self.combo_voice = QComboBox()
        self._voice_items = [
            ("kriti", "🌟 Kriti's Voice (Custom Clone - WhatsApp Sample)"),
            ("heera", "Microsoft Heera (Indian English - Natural Female)"),
            ("zira", "Microsoft Zira (US English Female)"),
            ("david", "Microsoft David (US English Male)"),
        ]
        for vid, vlabel in self._voice_items:
            self.combo_voice.addItem(vlabel, vid)

        # Select current profile
        cur_prof = tts_manager.voice_profile
        for i, (vid, _) in enumerate(self._voice_items):
            if vid == cur_prof:
                self.combo_voice.setCurrentIndex(i)
                break
        self.combo_voice.currentIndexChanged.connect(self._on_voice_profile_changed)
        row_voice.addWidget(self.combo_voice)

        # Sample & Test buttons
        self.btn_listen_sample = QPushButton("▶ Listen to Sample")
        self.btn_listen_sample.setProperty("class", "secondary-btn")
        self.btn_listen_sample.clicked.connect(lambda: tts_manager.play_custom_sample())
        row_voice.addWidget(self.btn_listen_sample)

        self.btn_test_voice = QPushButton("🔊 Test Voice")
        self.btn_test_voice.setProperty("class", "primary-btn")
        self.btn_test_voice.clicked.connect(self._test_voice_speech)
        row_voice.addWidget(self.btn_test_voice)
        row_voice.addStretch()
        v_layout.addLayout(row_voice)

        # Custom Sample Reference Path
        row_sample_file = QHBoxLayout()
        row_sample_file.addWidget(QLabel("Voice Sample Source:"))
        self.txt_voice_path = QLineEdit(tts_manager.custom_voice_path)
        self.txt_voice_path.setReadOnly(True)
        row_sample_file.addWidget(self.txt_voice_path)

        btn_browse_voice = QPushButton("Browse...")
        btn_browse_voice.setProperty("class", "secondary-btn")
        btn_browse_voice.clicked.connect(self._browse_voice_sample)
        row_sample_file.addWidget(btn_browse_voice)
        v_layout.addLayout(row_sample_file)

        # ElevenLabs Instant Voice Cloning API Key (Optional)
        row_el = QHBoxLayout()
        row_el.addWidget(QLabel("ElevenLabs Key (For Neural Cloning):"))
        self.txt_elevenlabs_key = QLineEdit()
        self.txt_elevenlabs_key.setEchoMode(QLineEdit.Password)
        self.txt_elevenlabs_key.setPlaceholderText("xi-api-key (Enables zero-shot dynamic speech in Kriti's voice)")
        if secret_store.has_credential("elevenlabs"):
            self.txt_elevenlabs_key.setText("••••••••••••••••••••••••")
        row_el.addWidget(self.txt_elevenlabs_key)

        btn_save_el = QPushButton("Save & Clone")
        btn_save_el.setProperty("class", "secondary-btn")
        btn_save_el.clicked.connect(self._save_and_clone_elevenlabs)
        row_el.addWidget(btn_save_el)
        v_layout.addLayout(row_el)

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

    def _on_voice_profile_changed(self, idx: int) -> None:
        if idx >= 0 and idx < len(self._voice_items):
            vid, label = self._voice_items[idx]
            tts_manager.set_voice_profile(vid)

    def _test_voice_speech(self) -> None:
        tts_manager.speak("Hello! I am Friday, speaking with your chosen voice. What else can I do for you?")

    def _browse_voice_sample(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Voice Audio Sample",
            tts_manager.custom_voice_path,
            "Audio Files (*.wav *.ogg *.mp3 *.m4a);;All Files (*.*)",
        )
        if file_path:
            tts_manager.custom_voice_path = file_path
            config.voice.custom_voice_path = file_path
            self.txt_voice_path.setText(file_path)
            QMessageBox.information(self, "Voice Sample Updated", f"Loaded custom voice sample from:\n{file_path}")

    def _save_and_clone_elevenlabs(self) -> None:
        key_val = self.txt_elevenlabs_key.text().strip()
        if key_val and "••••" not in key_val:
            secret_store.set_credential("elevenlabs", key_val)

        res = tts_manager.clone_voice_elevenlabs()
        if res.get("success"):
            QMessageBox.information(
                self, "Voice Cloned Successfully",
                f"Kriti's voice was successfully cloned in ElevenLabs!\nVoice ID: {res.get('voice_id')}\nFRIDAY will now speak in her cloned voice."
            )
        else:
            QMessageBox.warning(
                self, "Cloning Status",
                f"Stored API key. Note: {res.get('error', 'Ready for synthesis.')}"
            )

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

