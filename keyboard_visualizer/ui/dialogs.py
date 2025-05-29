from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from PyQt6.QtCore import QTimer
from pathlib import Path
import json
from ..utils.config import load_dialog_colors

DIALOG_COLORS = load_dialog_colors()

# Common dialog stylesheet
DIALOG_STYLE = f"""
    QDialog {{
        background-color: {DIALOG_COLORS['dialog_background']};
        color: {DIALOG_COLORS['text_color']};
    }}
    QLabel {{
        color: {DIALOG_COLORS['text_color']};
        padding: 5px;
    }}
    QLineEdit {{
        background-color: {DIALOG_COLORS['input_background']};
        color: {DIALOG_COLORS['text_color']};
        border: 1px solid {DIALOG_COLORS['input_border']};
        border-radius: 4px;
        padding: 6px;
    }}
    QPushButton {{
        background-color: {DIALOG_COLORS['button_normal']};
        color: {DIALOG_COLORS['button_text']};
        border: 1px solid {DIALOG_COLORS['button_border']};
        border-radius: 4px;
        padding: 6px 12px;
        min-width: 80px;
    }}
    QPushButton:hover {{
        background-color: {DIALOG_COLORS['button_hover']};
    }}
    QPushButton:pressed {{
        background-color: {DIALOG_COLORS['button_pressed']};
    }}
"""

class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Authentication Required")
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)
        
        layout = QVBoxLayout()
        
        # Add explanation label
        label = QLabel(
            "KeyViz needs elevated privileges to monitor keyboard input.\n"
            "Please enter your sudo password:"
        )
        layout.addWidget(label)
        
        # Add password field
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_field)
        
        # Add buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Connect buttons
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        self.setLayout(layout)
    
    def get_password(self):
        return self.password_field.text()


class KeyBindDialog(QDialog):
    def __init__(self, keyboard_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Press a Key")
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)
        
        self.keyboard_manager = keyboard_manager
        self.layout = QVBoxLayout()
        
        self.label = QLabel("Press the key you want to bind...")
        self.layout.addWidget(self.label)
        
        self.key_info = None
        self.setLayout(self.layout)
        
        # Start key detection
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_key)
        self.timer.start(100)
    
    def check_key(self):
        key_info = self.keyboard_manager.wait_for_key()
        if key_info:
            self.key_info = key_info  # This now contains both name and scan_code
            self.timer.stop()
            self.accept()
