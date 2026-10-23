"""Futuristic Dark Charcoal & Cyan Theme for Project FRIDAY.

Provides the comprehensive Qt Style Sheet (QSS), refined color tokens, and palette definitions.
"""

# Color Palette Tokens
COLOR_BG_DARKEST = "#0B0E14"
COLOR_BG_DARK = "#121824"
COLOR_BG_CARD = "#182234"
COLOR_BG_CARD_HOVER = "#202D45"
COLOR_BORDER = "#1E2D4A"
COLOR_BORDER_ACCENT = "#00B4D8"
COLOR_CYAN_ACCENT = "#00E5FF"
COLOR_CYAN_DIM = "#0088A3"
COLOR_TEXT_PRIMARY = "#F0F4F8"
COLOR_TEXT_SECONDARY = "#94A3B8"
COLOR_TEXT_MUTED = "#64748B"
COLOR_DANGER = "#EF4444"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"

FRIDAY_STYLESHEET = f"""
/* Master Window & Panels */
QMainWindow, QDialog, QWidget {{
    background-color: {COLOR_BG_DARKEST};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
    font-size: 13px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {COLOR_BG_DARK};
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_CYAN_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Sidebar & Navigation */
#Sidebar {{
    background-color: {COLOR_BG_DARK};
    border-right: 1px solid {COLOR_BORDER};
}}

#Sidebar QPushButton {{
    background-color: transparent;
    color: {COLOR_TEXT_SECONDARY};
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-left: 3px solid transparent;
    font-weight: 500;
    font-size: 13px;
}}
#Sidebar QPushButton:hover {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_CYAN_ACCENT};
}}
#Sidebar QPushButton:checked {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_CYAN_ACCENT};
    border-left: 3px solid {COLOR_CYAN_ACCENT};
    font-weight: 600;
}}

/* Top Header Bar */
#HeaderBar {{
    background-color: {COLOR_BG_DARK};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 8px 16px;
}}

/* Cards & Glass Panels */
QFrame.glass-card {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 16px;
}}
QFrame.glass-card:hover {{
    border: 1px solid {COLOR_BORDER_ACCENT};
}}

/* Buttons */
QPushButton.primary-btn {{
    background-color: {COLOR_CYAN_DIM};
    color: #FFFFFF;
    border: 1px solid {COLOR_CYAN_ACCENT};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton.primary-btn:hover {{
    background-color: {COLOR_CYAN_ACCENT};
    color: {COLOR_BG_DARKEST};
}}
QPushButton.danger-btn {{
    background-color: rgba(239, 68, 68, 0.2);
    color: {COLOR_DANGER};
    border: 1px solid {COLOR_DANGER};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton.danger-btn:hover {{
    background-color: {COLOR_DANGER};
    color: #FFFFFF;
}}
QPushButton.secondary-btn {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px 16px;
}}
QPushButton.secondary-btn:hover {{
    border-color: {COLOR_CYAN_ACCENT};
    color: {COLOR_CYAN_ACCENT};
}}

/* Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px 12px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {COLOR_CYAN_ACCENT};
}}

/* Combo Boxes */
QComboBox {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
}}
QComboBox:hover {{
    border-color: {COLOR_CYAN_ACCENT};
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_CYAN_DIM};
    color: {COLOR_TEXT_PRIMARY};
}}

/* Tables & Lists */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    gridline-color: {COLOR_BORDER};
    color: {COLOR_TEXT_PRIMARY};
}}
QHeaderView::section {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_SECONDARY};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    font-weight: 600;
}}
"""
