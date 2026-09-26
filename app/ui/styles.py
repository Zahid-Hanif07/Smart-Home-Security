"""Modern Dark Security Dashboard QSS Stylesheet."""

DARK_SECURITY_THEME = """
QMainWindow {
    background-color: #11111b;
    color: #cdd6f4;
}

QWidget {
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
    color: #cdd6f4;
}

/* Header Banner */
#headerCard {
    background-color: #1e1e2e;
    border-bottom: 2px solid #313244;
    padding: 12px 20px;
}

#headerTitle {
    font-size: 22px;
    font-weight: bold;
    color: #89b4fa;
}

#headerSubtitle {
    font-size: 13px;
    color: #a6adc8;
}

#systemStatusBadge {
    background-color: #181825;
    border: 1px solid #a6e3a1;
    border-radius: 12px;
    color: #a6e3a1;
    font-weight: bold;
    font-size: 12px;
    padding: 6px 14px;
}

/* Common Card Panel */
.QGroupBox, #cardPanel {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 15px;
    margin-top: 5px;
}

.QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #89b4fa;
    font-weight: bold;
    font-size: 14px;
}

/* Camera Preview Label */
#cameraDisplayLabel {
    background-color: #181825;
    border: 2px dashed #313244;
    border-radius: 8px;
    color: #6c7086;
    font-size: 16px;
    font-weight: 500;
}

/* Status Indicator Pill Badges */
#statusBadge {
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: bold;
    font-size: 13px;
    background-color: #313244;
    color: #cdd6f4;
}

#statusBadge[status="online"] {
    background-color: rgba(166, 227, 161, 0.2);
    border: 1px solid #a6e3a1;
    color: #a6e3a1;
}

#statusBadge[status="offline"] {
    background-color: rgba(243, 139, 168, 0.2);
    border: 1px solid #f38ba8;
    color: #f38ba8;
}

#statusBadge[status="no_motion"] {
    background-color: rgba(166, 227, 161, 0.2);
    border: 1px solid #a6e3a1;
    color: #a6e3a1;
}

#statusBadge[status="motion_detected"] {
    background-color: rgba(243, 139, 168, 0.2);
    border: 1px solid #f38ba8;
    color: #f38ba8;
}

#statusBadge[status="no_face"] {
    background-color: rgba(147, 153, 178, 0.2);
    border: 1px solid #9399b2;
    color: #a6adc8;
}

#statusBadge[status="face_detected"] {
    background-color: rgba(137, 220, 235, 0.2);
    border: 1px solid #89dceb;
    color: #89dceb;
}

#statusBadge[status="authorized"] {
    background-color: rgba(166, 227, 161, 0.2);
    border: 1px solid #a6e3a1;
    color: #a6e3a1;
}

#statusBadge[status="unauthorized"] {
    background-color: rgba(243, 139, 168, 0.2);
    border: 1px solid #f38ba8;
    color: #f38ba8;
}

#statusBadge[status="identity_known"] {
    background-color: rgba(137, 220, 235, 0.2);
    border: 1px solid #89dceb;
    color: #89dceb;
}

#statusBadge[status="identity_unknown"] {
    background-color: rgba(243, 139, 168, 0.2);
    border: 1px solid #f38ba8;
    color: #f38ba8;
}

#statusBadge[status="backend_online"] {
    background-color: rgba(166, 227, 161, 0.2);
    border: 1px solid #a6e3a1;
    color: #a6e3a1;
}

#statusBadge[status="backend_offline"] {
    background-color: rgba(243, 139, 168, 0.2);
    border: 1px solid #f38ba8;
    color: #f38ba8;
}

#statusBadge[status="backend_unconfigured"] {
    background-color: rgba(249, 226, 175, 0.2);
    border: 1px solid #f9e2af;
    color: #f9e2af;
}

#statusBadge[status="locked"] {
    background-color: rgba(249, 226, 175, 0.2);
    border: 1px solid #f9e2af;
    color: #f9e2af;
}

/* Action Control Buttons */
QPushButton#btnStart {
    background-color: #a6e3a1;
    color: #11111b;
    font-weight: bold;
    font-size: 13px;
    border-radius: 8px;
    padding: 10px 16px;
    border: none;
}

QPushButton#btnStart:hover {
    background-color: #94e297;
}

QPushButton#btnStart:disabled {
    background-color: #45475a;
    color: #7f849c;
}

QPushButton#btnStop {
    background-color: #f38ba8;
    color: #11111b;
    font-weight: bold;
    font-size: 13px;
    border-radius: 8px;
    padding: 10px 16px;
    border: none;
}

QPushButton#btnStop:hover {
    background-color: #f27b9b;
}

QPushButton#btnStop:disabled {
    background-color: #45475a;
    color: #7f849c;
}

QPushButton#btnRegister {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: bold;
    font-size: 13px;
    border-radius: 8px;
    padding: 10px 16px;
    border: none;
}

QPushButton#btnRegister:hover {
    background-color: #b4befe;
}

QPushButton#btnRegister:disabled {
    background-color: #45475a;
    color: #7f849c;
}


/* Security Log Box */
QTextEdit#logTextEdit {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    color: #a6adc8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}

QScrollBar:vertical {
    background: #181825;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}
"""
