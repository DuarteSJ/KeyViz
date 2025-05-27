"""
Main application window
"""
import sys
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QPushButton,
                            QVBoxLayout, QHBoxLayout, QMessageBox,
                            QFileDialog)
from PyQt6.QtCore import QTimer, Qt
from .canvas import KeyboardCanvas
from ..input.keyboard_manager import KeyboardManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard Visualizer")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E3440;
            }
            QPushButton {
                background-color: #3B4252;
                color: #ECEFF4;
                border: 1px solid #4C566A;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #434C5E;
            }
            QPushButton:pressed {
                background-color: #4C566A;
            }
            QPushButton:disabled {
                background-color: #2E3440;
                color: #4C566A;
            }
        """)
        
        # Initialize keyboard manager
        self.keyboard_manager = KeyboardManager()
        
        # Start the keyboard helper
        try:
            if not self.keyboard_manager.start():
                error_msg = (
                    "Failed to start keyboard helper. This could be due to permission issues.\n\n"
                    "To fix this, you need to either:\n"
                    "1. Add your user to the 'input' group:\n"
                    "   sudo usermod -a -G input $USER\n"
                    "   (requires logout/login to take effect)\n\n"
                    "2. Or run the application with sudo:\n"
                    "   sudo python main.py"
                )
                QMessageBox.critical(self, "Error", error_msg)
                sys.exit(1)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start keyboard helper: {str(e)}")
            sys.exit(1)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        # Create keyboard canvas
        self.canvas = KeyboardCanvas(self.keyboard_manager)
        
        # Add buttons
        self.save_btn = QPushButton("Save Layout")
        self.save_btn.clicked.connect(self.saveLayout)
        
        self.load_btn = QPushButton("Load Layout")
        self.load_btn.clicked.connect(self.loadLayout)
        
        self.toggle_mode_btn = QPushButton("Start Visualizer")
        self.toggle_mode_btn.clicked.connect(self.toggleMode)
        
        # Add buttons to toolbar
        toolbar.addWidget(self.save_btn)
        toolbar.addWidget(self.load_btn)
        toolbar.addWidget(self.toggle_mode_btn)
        
        # Add layouts to main layout
        layout.addLayout(toolbar)
        layout.addWidget(self.canvas)
        
        # Setup state check timer
        self.state_check_timer = QTimer(self)
        self.state_check_timer.timeout.connect(self.check_keyboard_state)
        self.state_check_timer.setInterval(16)  # ~60 FPS
            
    def toggleMode(self):
        self.canvas.editor_mode = not self.canvas.editor_mode
        editor_widgets = [self.save_btn, self.load_btn]
        
        if self.canvas.editor_mode:
            self.toggle_mode_btn.setText("Start Visualizer")
            for widget in editor_widgets:
                widget.setEnabled(True)
            # Stop monitoring
            with open(self.keyboard_manager.command_file, 'w') as f:
                json.dump({'type': 'stop_monitor'}, f)
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
            self.state_check_timer.stop()
        else:
            self.toggle_mode_btn.setText("Stop Visualizer")
            for widget in editor_widgets:
                widget.setEnabled(False)
            # Start monitoring with current key bindings
            key_binds = [key.key_bind for key in self.canvas.keys]
            if key_binds:  # Only start monitoring if we have keys to monitor
                with open(self.keyboard_manager.command_file, 'w') as f:
                    json.dump({'type': 'monitor', 'keys': key_binds}, f)
                self.state_check_timer.start()
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
            
    def saveLayout(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Layout", "", 
                                                "JSON Files (*.json)")
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.canvas.getConfiguration(), f)
                
    def loadLayout(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Layout", "", 
                                                "JSON Files (*.json)")
        if filename:
            with open(filename, 'r') as f:
                config = json.load(f)
                self.canvas.loadConfiguration(config)
                
    def check_keyboard_state(self):
        if not self.canvas.editor_mode:  # Only check states in visualizer mode
            key_states = self.keyboard_manager.get_key_states()
            # Create case-insensitive mapping
            key_map = {key.key_bind.lower(): key for key in self.canvas.keys}
            
            # Update all keys first to ensure proper state
            for key in self.canvas.keys:
                key_bind = key.key_bind.lower()
                if key_bind in key_states:
                    key.pressed = key_states[key_bind]
                else:
                    key.pressed = False
                key.update()
                    
    def closeEvent(self, event):
        self.state_check_timer.stop()
        self.keyboard_manager.stop()
        event.accept() 