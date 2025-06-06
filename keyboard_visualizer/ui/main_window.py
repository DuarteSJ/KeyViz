import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import QTimer, Qt

from .keyboard_canvas import KeyboardCanvas
from ..core.keyboard_manager import KeyboardManager
from ..utils.config import load_main_window_settings


MAIN_WINDOW_SETTINGS = load_main_window_settings()
# print all keys int the loaded json
print(f"Loaded main window settings: {MAIN_WINDOW_SETTINGS}\n")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.interface_minimized = False
        self.hideable_buttons = []
        self.setWindowTitle("KeyViz")
        self.setMinimumSize(4, 3)
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {MAIN_WINDOW_SETTINGS['main_background']};
            }}
            QPushButton {{
                background-color: {MAIN_WINDOW_SETTINGS['button_normal']};
                color: {MAIN_WINDOW_SETTINGS['button_text']};
                border: 1px solid {MAIN_WINDOW_SETTINGS['button_border']};
                border-radius: 6px;
                padding: 2px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {MAIN_WINDOW_SETTINGS['button_hover']};
                border: 2px solid {MAIN_WINDOW_SETTINGS['button_border']};
            }}
            QPushButton:pressed {{
                background-color: {MAIN_WINDOW_SETTINGS['button_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {MAIN_WINDOW_SETTINGS['button_disabled_bg']};
                color: {MAIN_WINDOW_SETTINGS['button_disabled_text']};
                border: 1px solid {MAIN_WINDOW_SETTINGS['button_disabled_text']};
            }}
            """
            )

        # Initialize keyboard manager
        self.keyboard_manager = KeyboardManager()

        # Get authentication
        if not self.keyboard_manager.authenticate():
            QMessageBox.critical(
                self, "Error", "Authentication required to monitor keyboard input."
            )
            sys.exit(1)

        # Start the keyboard helper
        if not self.keyboard_manager.start():
            QMessageBox.critical(self, "Error", "Failed to start keyboard helper.")
            sys.exit(1)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create toolbar
        toolbar = QHBoxLayout()

        # Create keyboard canvas
        self.canvas = KeyboardCanvas(self.keyboard_manager)

        # Add icon buttons
        self.save_btn = QPushButton(" ")
        self.save_btn.setToolTip("Save Layout")
        self.save_btn.clicked.connect(self.saveLayout)
        self.save_btn.setFixedSize(30, 30)
        self.hideable_buttons.append(self.save_btn)

        self.load_btn = QPushButton(" ")
        self.load_btn.setToolTip("Load Layout")
        self.load_btn.clicked.connect(self.loadLayout)
        self.load_btn.setFixedSize(30, 30)
        self.hideable_buttons.append(self.load_btn)

        self.toggle_mode_btn = QPushButton(" ")
        self.toggle_mode_btn.setToolTip("Start Visualizer")
        self.toggle_mode_btn.clicked.connect(self.toggleMode)
        self.toggle_mode_btn.setFixedSize(30, 30)
        self.hideable_buttons.append(self.toggle_mode_btn)

        self.toggle_visibility_btn = QPushButton("  ")
        self.toggle_visibility_btn.setToolTip("Hide Toolbar")
        self.toggle_visibility_btn.clicked.connect(self.toggleVisibility)
        self.toggle_visibility_btn.setFixedSize(30, 30)

        # Add buttons to toolbar
        toolbar.addWidget(self.save_btn)
        toolbar.addWidget(self.load_btn)
        toolbar.addWidget(self.toggle_mode_btn)
        toolbar.addStretch()  # Push buttons to the left
        toolbar.addWidget(self.toggle_visibility_btn)

        # Add layouts to main layout
        layout.addLayout(toolbar)
        layout.addWidget(self.canvas)

        # Setup state check timer
        self.state_check_timer = QTimer(self)
        self.state_check_timer.timeout.connect(self.check_keyboard_state)
        self.state_check_timer.setInterval(16)  # ~60 FPS

    def toggleMode(self):
        self.canvas.toggleEditorMode(not self.canvas.editor_mode)
        editor_widgets = [self.save_btn, self.load_btn]

        if self.canvas.editor_mode:
            self.toggle_mode_btn.setText(" ")
            self.toggle_mode_btn.setToolTip("Start Visualizer")
            for widget in editor_widgets:
                widget.setEnabled(True)
            self.keyboard_manager.stop_monitoring()
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
            self.state_check_timer.stop()
        else:
            self.toggle_mode_btn.setText("")
            self.toggle_mode_btn.setToolTip("Stop Visualizer")
            for widget in editor_widgets:
                widget.setEnabled(False)
            # Start monitoring with current key scan codes
            scan_codes = [
                key.scan_code for key in self.canvas.keys if key.scan_code is not None
            ]
            if scan_codes:  # Only start monitoring if we have keys to monitor
                self.keyboard_manager.start_monitoring(scan_codes)
                self.state_check_timer.start()
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

    def saveLayout(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Layout", "", "JSON Files (*.json)"
        )
        if filename:
            with open(filename, "w") as f:
                json.dump(self.canvas.getConfiguration(), f)

    def loadLayout(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Layout", "", "JSON Files (*.json)"
        )
        if filename:
            with open(filename, "r") as f:
                config = json.load(f)
                self.canvas.loadConfiguration(config)

    def toggleVisibility(self):
        if self.interface_minimized:
            # Show all buttons
            for btn in self.hideable_buttons:
                btn.show()
            self.toggle_visibility_btn.setText("  ")
            self.toggle_visibility_btn.setToolTip("Hide Toolbar")
            self.toggle_visibility_btn.setFixedSize(30, 30)
            self.interface_minimized = False
        else:
            # Hide all except minimize button
            for btn in self.hideable_buttons:
                btn.hide()
            self.toggle_visibility_btn.setText("  ")
            self.toggle_visibility_btn.setToolTip("Show Toolbar")
            self.toggle_visibility_btn.setFixedSize(22, 22)
            self.interface_minimized = True

    def check_keyboard_state(self):
        if not self.canvas.editor_mode:  # Only check states in visualizer mode
            try:
                key_states = self.keyboard_manager.get_key_states()
                key_map = {
                    key.scan_code: key
                    for key in self.canvas.keys
                    if key.scan_code is not None
                }

                for scan_code, is_pressed in key_states.items():
                    try:
                        # Try to convert scan_code to int if it's a string
                        if isinstance(scan_code, str):
                            scan_code = int(scan_code)
                        if scan_code in key_map:
                            if key_map[scan_code].pressed == False and is_pressed:
                                key_map[scan_code].playSound()
                            key_map[scan_code].pressed = is_pressed
                            key_map[scan_code].update()
                    except (ValueError, TypeError):
                        # Skip invalid scan codes
                        continue

            except Exception as e:
                print(f"Error checking keyboard state: {e}")

    def closeEvent(self, event):
        self.state_check_timer.stop()
        self.keyboard_manager.stop()
        event.accept()
