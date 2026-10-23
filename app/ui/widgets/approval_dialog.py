"""Approval Confirmation Dialog for High-Impact Actions.

Presents explicit risk disclosures, affected resources, and reversibility status
before consequential actions can execute.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit
)
from PySide6.QtCore import Qt

from app.core.permissions import ApprovalRequest, permissions_engine
from app.ui.theme import COLOR_DANGER, COLOR_WARNING, COLOR_CYAN_ACCENT


class ApprovalDialog(QDialog):
    """Modal prompt requiring user confirmation for high-impact actions."""

    def __init__(self, request: ApprovalRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.setWindowTitle(f"Security Authorization Required — {request.tool_name}")
        self.setFixedSize(520, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header with Alert Icon & Title
        header_layout = QHBoxLayout()
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(icon_label)

        title_vbox = QVBoxLayout()
        title_label = QLabel("Consequential Action Authorization")
        title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        subtitle = QLabel("FRIDAY requires your explicit permission before executing this step.")
        subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Card container for details
        card = QFrame()
        card.setProperty("class", "glass-card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        # Tool & Risk Level
        risk_color = COLOR_DANGER if self.request.risk_level == "HIGH" else COLOR_WARNING
        tool_lbl = QLabel(f"<b>Requested Tool:</b> <code style='color: {COLOR_CYAN_ACCENT};'>{self.request.tool_name}</code> "
                          f"&nbsp;&nbsp;<span style='color: {risk_color}; font-weight: bold;'>[{self.request.risk_level} RISK]</span>")
        card_layout.addWidget(tool_lbl)

        # Reversibility
        rev_text = "Yes (Automated backup available)" if self.request.is_reversible else "No (Irreversible modification)"
        card_layout.addWidget(QLabel(f"<b>Reversible:</b> {rev_text}"))

        # Affected Resource
        card_layout.addWidget(QLabel(f"<b>Target Resource:</b> {self.request.affected_resource}"))

        # Description / Explanation
        card_layout.addWidget(QLabel(f"<b>Operation:</b> {self.request.description}"))
        layout.addWidget(card)

        # Button Bar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_reject = QPushButton("Reject & Cancel")
        self.btn_reject.setProperty("class", "secondary-btn")
        self.btn_reject.clicked.connect(self._on_reject)
        btn_layout.addWidget(self.btn_reject)

        self.btn_approve = QPushButton("Authorize Action")
        self.btn_approve.setProperty("class", "primary-btn")
        self.btn_approve.setStyleSheet("background-color: #00E5FF; color: #0B0E14; font-weight: bold;")
        self.btn_approve.clicked.connect(self._on_approve)
        btn_layout.addWidget(self.btn_approve)

        layout.addLayout(btn_layout)

    def _on_approve(self) -> None:
        permissions_engine.resolve_approval(self.request.id, approved=True)
        self.accept()

    def _on_reject(self) -> None:
        permissions_engine.resolve_approval(self.request.id, approved=False)
        self.reject()
