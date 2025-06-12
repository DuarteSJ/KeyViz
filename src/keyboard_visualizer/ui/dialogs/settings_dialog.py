from typing import Optional, Dict, Any, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)
from PyQt6.QtCore import QTimer
from pathlib import Path
import json
from keyboard_visualizer.utils.config import load_dialog_colors

if TYPE_CHECKING:
    from keyboard_visualizer.core.keyboard_manager import KeyboardManager

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
    """
    Dialog for collecting sudo password authentication.

    This modal dialog prompts the user to enter their sudo password for
    authenticating keyboard monitoring operations that require elevated
    privileges. The password field is masked for security.

    The dialog provides a clear explanation of why authentication is needed
    and includes standard OK/Cancel buttons for user interaction.

    Attributes:
        password_field (QLineEdit): Masked input field for the password.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the PasswordDialog.

        Sets up the dialog with an explanation label, password input field,
        and OK/Cancel buttons. The dialog is configured as modal and applies
        the standard dialog styling.

        Args:
            parent (Optional[QWidget]): Parent widget for the dialog, defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("Authentication Required")
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        layout: QVBoxLayout = QVBoxLayout()

        # Add explanation label
        label: QLabel = QLabel(
            "KeyViz needs elevated privileges to monitor keyboard input.\n"
            "Please enter your sudo password:"
        )
        layout.addWidget(label)

        # Add password field
        self.password_field: QLineEdit = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_field)

        # Add buttons
        button_layout: QHBoxLayout = QHBoxLayout()
        ok_button: QPushButton = QPushButton("OK")
        cancel_button: QPushButton = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Connect buttons
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        self.setLayout(layout)

    def get_password(self) -> str:
        """
        Get the entered password from the dialog.

        Returns:
            str: The password entered by the user. May be empty if no password
                was entered.
        """
        return self.password_field.text()


class KeyBindDialog(QDialog):
    """
    Dialog for capturing keyboard key presses for key binding.

    This modal dialog prompts the user to press a key that will be bound to
    a keyboard key widget. It automatically detects the key press and captures
    both the key name and scan code for use in keyboard monitoring.

    The dialog uses a timer to continuously check for key presses through
    the keyboard manager's wait_for_key method. Once a key is detected,
    the dialog automatically closes and provides the key information.

    Attributes:
        keyboard_manager (KeyboardManager): Manager for detecting key presses.
        layout (QVBoxLayout): Main layout for dialog components.
        label (QLabel): Instruction label for the user.
        key_info (Optional[Dict[str, Any]]): Information about the detected key.
        timer (QTimer): Timer for polling key detection.
    """

    def __init__(
        self, keyboard_manager: "KeyboardManager", parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize the KeyBindDialog.

        Sets up the dialog with an instruction label and starts the key detection
        timer. The dialog is configured as modal and applies standard styling.

        Args:
            keyboard_manager (KeyboardManager): The keyboard manager for key detection.
            parent (Optional[QWidget]): Parent widget for the dialog, defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("Press a Key")
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        self.keyboard_manager: "KeyboardManager" = keyboard_manager
        self.layout: QVBoxLayout = QVBoxLayout()
        self.label: QLabel = QLabel("Press the key you want to bind...")
        self.layout.addWidget(self.label)

        self.key_info: Optional[Dict[str, Any]] = None
        self.setLayout(self.layout)

        # Start key detection
        self.timer: QTimer = QTimer()
        self.timer.timeout.connect(self.check_key)
        self.timer.start(100)

    def check_key(self) -> None:
        """
        Check for key presses and handle key detection.

        This method is called periodically by the timer to check if a key
        has been pressed. When a key is detected, it stores the key information,
        stops the timer, and accepts the dialog.

        The key information includes both the key name and scan code needed
        for keyboard monitoring operations.
        """
        key_info: Optional[Dict[str, Any]] = self.keyboard_manager.wait_for_key()
        if key_info:
            self.key_info = key_info  # This now contains both name and scan_code
            self.timer.stop()
            self.accept()
