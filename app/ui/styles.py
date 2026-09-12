"""Futuristic Glassmorphism Dark QSS Stylesheet Definitions."""

DARK_FUTURISTIC_STYLE = """
/* Global Window & Widget Dark Background */
QMainWindow, QDialog {
    background-color: #0B0F17;
    color: #F8FAFC;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QWidget {
    color: #E2E8F0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

/* Glassmorphism Dimensional Card Panels */
QFrame.glass-card, QWidget.glass-card {
    background-color: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
}

QFrame.glass-card-header {
    background-color: rgba(15, 23, 42, 0.85);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
}

/* Futuristic Neon Typography */
QLabel.title-primary {
    font-size: 28px;
    font-weight: 800;
    color: #00F0FF;
    letter-spacing: 1.5px;
}

QLabel.title-sub {
    font-size: 14px;
    font-weight: 500;
    color: #94A3B8;
    letter-spacing: 0.5px;
}

QLabel.header-badge {
    background-color: rgba(0, 240, 255, 0.12);
    border: 1px solid rgba(0, 240, 255, 0.3);
    color: #00F0FF;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
}

QLabel.status-active {
    color: #10B981;
    font-weight: 600;
    font-size: 12px;
}

QLabel.status-inactive {
    color: #EF4444;
    font-weight: 600;
    font-size: 12px;
}

/* Futuristic Buttons */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E293B, stop:1 #0F172A);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    color: #F1F5F9;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #334155, stop:1 #1E293B);
    border: 1px solid #00F0FF;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #0F172A;
    border: 1px solid #A855F7;
}

QPushButton:disabled {
    background-color: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.04);
    color: #475569;
}

/* Primary Hero Action Button */
QPushButton.btn-primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #3B82F6);
    border: none;
    border-radius: 12px;
    color: #0B0F17;
    font-size: 15px;
    font-weight: 700;
    padding: 12px 24px;
}

QPushButton.btn-primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #60A5FA);
    border: 1px solid #FFFFFF;
}

/* Tool Buttons */
QPushButton.btn-tool {
    min-width: 36px;
    min-height: 36px;
    max-width: 36px;
    max-height: 36px;
    border-radius: 18px;
    padding: 0px;
}

QPushButton.btn-tool-active {
    border: 2px solid #00F0FF;
}

/* Modern Input LineEdit & TextEdit */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: #F8FAFC;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #00F0FF;
    selection-color: #0B0F17;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #00F0FF;
}

/* Sliders */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #1E293B;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #A855F7);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #00F0FF;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #00F0FF;
}

/* ComboBox */
QComboBox {
    background-color: #1E293B;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 6px 12px;
    color: #F8FAFC;
    font-size: 13px;
}

QComboBox:hover {
    border: 1px solid #00F0FF;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #0F172A;
    border: 1px solid rgba(255, 255, 255, 0.15);
    selection-background-color: #00F0FF;
    selection-color: #0B0F17;
    font-size: 13px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    color: #E2E8F0;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background-color: #1E293B;
}

QCheckBox::indicator:checked {
    background-color: #00F0FF;
    border: 1px solid #00F0FF;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0F172A;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #00F0FF;
}
"""
