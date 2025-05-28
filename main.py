#!/usr/bin/env python3
import sys
import json
import subprocess
import os
import time
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton,
                            QVBoxLayout, QHBoxLayout, QLabel, QInputDialog,
                            QFileDialog, QMessageBox, QDialog, QLineEdit)
from PyQt6.QtCore import Qt, QPoint, QRect, QProcess, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor, QPainterPath, QRadialGradient
from sudo_helper import SudoHelper

class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Authentication Required")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Add explanation label
        label = QLabel(
            "Keyboard Visualizer needs elevated privileges to monitor keyboard input.\n"
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

class KeyboardManager:
    def __init__(self):
        self.helper_process = None
        self.tmp_dir = Path('/tmp/keyboard_visualizer')
        self.command_file = self.tmp_dir / 'command'
        self.response_file = self.tmp_dir / 'response'
        self.running_file = self.tmp_dir / 'running'
        self.sudo = SudoHelper()
        
        # Create tmp directory if it doesn't exist
        self.tmp_dir.mkdir(exist_ok=True)
        
    def authenticate(self):
        """Get sudo authentication from user."""
        dialog = PasswordDialog()
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False
                
            password = dialog.get_password()
            if self.sudo.authenticate(password):
                return True
                
            QMessageBox.critical(dialog, "Error", "Incorrect password. Please try again.")
        
    def start(self):
        """Start the keyboard helper process with elevated privileges."""
        if self.helper_process is not None:
            return True
            
        # Create helper script path
        helper_script = Path(__file__).parent / 'keyboard_helper.py'
        
        try:
            # Start the helper process with sudo
            self.helper_process = self.sudo.run_python_script(helper_script)
        except (subprocess.CalledProcessError, RuntimeError):
            return False
                
        # Wait for the helper to start
        for _ in range(20):  # Wait up to 2 seconds
            if self.running_file.exists():
                return True
            time.sleep(0.1)
            
        # If we get here, the helper didn't start properly
        if self.helper_process:
            try:
                self.helper_process.terminate()
            except:
                pass
        return False
        
    def stop(self):
        """Stop the keyboard helper process."""
        if self.running_file.exists():
            try:
                self.sudo.run_sudo(['rm', str(self.running_file)])
            except:
                pass
                
        if self.helper_process:
            try:
                self.helper_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    self.helper_process.terminate()
                except:
                    pass
            self.helper_process = None
            
    def send_command(self, command):
        """Send a command to the helper process."""
        try:
            with open(self.command_file, 'w') as f:
                json.dump(command, f)
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
            
    def wait_for_key(self):
        """Wait for a single keypress and return its name."""
        if not self.send_command({'type': 'wait_key'}):
            return None
            
        # Wait for response
        for _ in range(50):  # Wait up to 5 seconds
            try:
                if self.response_file.exists():
                    with open(self.response_file, 'r') as f:
                        response = json.load(f)
                    try:
                        os.remove(self.response_file)
                    except:
                        pass
                    return response.get('key')
            except:
                pass
            time.sleep(0.1)
        return None
        
    def start_monitoring(self, keys):
        """Start monitoring the specified keys."""
        return self.send_command({'type': 'monitor', 'keys': keys})
            
    def stop_monitoring(self):
        """Stop monitoring keys."""
        return self.send_command({'type': 'stop_monitor'})
            
    def get_key_states(self):
        """Get the current state of monitored keys."""
        try:
            with open(self.response_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

class KeyBindDialog(QDialog):
    def __init__(self, keyboard_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Press a Key")
        self.setModal(True)
        self.keyboard_manager = keyboard_manager
        
        self.layout = QVBoxLayout()
        self.label = QLabel("Press the key you want to bind...")
        self.layout.addWidget(self.label)
        
        self.key_name = None
        self.setLayout(self.layout)
        
        # Start key detection
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_key)
        self.timer.start(100)
        
    def check_key(self):
        key = self.keyboard_manager.wait_for_key()
        if key:
            self.key_name = key
            self.timer.stop()
            self.accept()

class KeyboardKey(QWidget):
    def __init__(self, label="", key_bind="", keyboard_manager=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.key_bind = key_bind
        self.keyboard_manager = keyboard_manager
        self.pressed = False
        self.selected = False
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QWidget {
                background-color: #2E3440;
                border-radius: 5px;
            }
        """)
        
        # For drag functionality
        self.dragging = False
        self.resizing = False
        self.resize_handle = None
        self.offset = QPoint()
        self.min_size = 30
        
        self.setMouseTracking(True)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create base shape with rounded corners
        path = QPainterPath()
        path.addRoundedRect(1, 1, self.width()-2, self.height()-2, 5, 5)
        
        # Define colors for different states and parts
        if self.pressed:
            # Brighter, more noticeable color when pressed
            top_color = QColor("#88C0D0")  # Bright blue when pressed
            side_color = QColor("#5E81AC")  # Darker blue for sides
            bottom_color = QColor("#4C566A")
            
            # Add a glow effect when pressed
            glow = QRadialGradient(self.width()/2, self.height()/2, self.width()/2)
            glow.setColorAt(0, QColor("#88C0D0"))
            glow.setColorAt(1, QColor("#88C0D000"))
            painter.fillRect(0, 0, self.width(), self.height(), glow)
        else:
            top_color = QColor("#4C566A") if self.selected else QColor("#434C5E")
            side_color = QColor("#3B4252")
            bottom_color = QColor("#2E3440")
        
        # Draw the key sides (3D effect)
        if not self.pressed:
            # Right side
            side_path = QPainterPath()
            side_path.moveTo(self.width() - 2, 2)
            side_path.lineTo(self.width() - 2, self.height() - 2)
            side_path.lineTo(self.width() - 4, self.height() - 4)
            side_path.lineTo(self.width() - 4, 4)
            side_path.closeSubpath()
            painter.fillPath(side_path, side_color)
            
            # Bottom side
            bottom_path = QPainterPath()
            bottom_path.moveTo(2, self.height() - 2)
            bottom_path.lineTo(self.width() - 2, self.height() - 2)
            bottom_path.lineTo(self.width() - 4, self.height() - 4)
            bottom_path.lineTo(4, self.height() - 4)
            bottom_path.closeSubpath()
            painter.fillPath(bottom_path, bottom_color)
        
        # Draw main key face
        main_face = QPainterPath()
        if self.pressed:
            # Move the face down and right slightly when pressed
            main_face.addRoundedRect(3, 3, self.width()-4, self.height()-4, 5, 5)
        else:
            main_face.addRoundedRect(1, 1, self.width()-2, self.height()-2, 5, 5)
        painter.fillPath(main_face, top_color)
        
        # Add highlight for top edge (only when not pressed)
        if not self.pressed:
            highlight_path = QPainterPath()
            highlight_path.moveTo(2, 2)
            highlight_path.lineTo(self.width() - 2, 2)
            pen = QPen(QColor("#5E81AC" if self.selected else "#5E6B81"))
            pen.setWidth(1)
            painter.strokePath(highlight_path, pen)
        
        # Draw text
        painter.setPen(QPen(QColor("#ECEFF4" if not self.pressed else "#2E3440")))  # Dark text on bright background when pressed
        font = painter.font()
        font.setPointSize(9)
        font.setFamily("Arial")
        font.setBold(True)
        painter.setFont(font)
        
        # Calculate text position for vertical centering
        text_rect = painter.fontMetrics().boundingRect(self.label)
        x = (self.width() - text_rect.width()) / 2
        y = (self.height() + text_rect.height()) / 2
        
        # Adjust text position when pressed
        if self.pressed:
            x += 2  # Move text right when pressed
            y += 2  # Move text down when pressed
        
        # Draw text with a subtle shadow (only when not pressed)
        if not self.pressed:
            painter.setPen(QPen(QColor("#2E3440")))
            painter.drawText(int(x + 1), int(y + 1), self.label)
            painter.setPen(QPen(QColor("#ECEFF4")))
        painter.drawText(int(x), int(y), self.label)
        
        # Draw resize handles when selected
        if self.selected and self.parent().editor_mode:
            handle_size = 6
            handle_color = QColor("#88C0D0")
            painter.fillRect(0, 0, handle_size, handle_size, handle_color)
            painter.fillRect(self.width() - handle_size, 0, handle_size, handle_size, handle_color)
            painter.fillRect(0, self.height() - handle_size, handle_size, handle_size, handle_color)
            painter.fillRect(self.width() - handle_size, self.height() - handle_size, 
                           handle_size, handle_size, handle_color)

    def getResizeHandle(self, pos):
        """Return which resize handle the position is over, if any."""
        handle_size = 6
        
        # Check each corner
        if QRect(0, 0, handle_size, handle_size).contains(pos):
            return "top-left"
        elif QRect(self.width() - handle_size, 0, handle_size, handle_size).contains(pos):
            return "top-right"
        elif QRect(0, self.height() - handle_size, handle_size, handle_size).contains(pos):
            return "bottom-left"
        elif QRect(self.width() - handle_size, self.height() - handle_size, 
                  handle_size, handle_size).contains(pos):
            return "bottom-right"
        return None
        
    def mousePressEvent(self, event):
        if self.parent().editor_mode:
            if event.button() == Qt.MouseButton.LeftButton:
                handle = self.getResizeHandle(event.pos())
                if handle and self.selected:
                    # Start resizing
                    self.resizing = True
                    self.resize_handle = handle
                    self.offset = event.pos()
                else:
                    modifiers = event.modifiers()
                    if modifiers & Qt.KeyboardModifier.ControlModifier:
                        # Toggle selection with Ctrl+Click
                        self.selected = not self.selected
                        self.update()
                    else:
                        # If not Ctrl+Click, start dragging and handle selection
                        if not self.selected:
                            self.parent().clearSelection()
                            self.selected = True
                            self.update()
                        self.dragging = True
                        self.offset = event.pos()
                        self.parent().startDrag(event.pos())
            elif event.button() == Qt.MouseButton.RightButton:
                self.parent().removeKey(self)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            self.resize_handle = None
            self.parent().endDrag()
            
    def mouseMoveEvent(self, event):
        if self.parent().editor_mode:
            if self.resizing:
                # Handle resizing
                delta = event.pos() - self.offset
                new_size = self.size()
                
                if self.resize_handle in ["top-left", "bottom-left"]:
                    # Left edge moving
                    new_width = max(self.min_size, self.width() - delta.x())
                    if new_width != self.width():
                        self.move(self.x() + (self.width() - new_width), self.y())
                        new_size.setWidth(new_width)
                        
                if self.resize_handle in ["top-right", "bottom-right"]:
                    # Right edge moving
                    new_size.setWidth(max(self.min_size, self.width() + delta.x()))
                    
                if self.resize_handle in ["top-left", "top-right"]:
                    # Top edge moving
                    new_height = max(self.min_size, self.height() - delta.y())
                    if new_height != self.height():
                        self.move(self.x(), self.y() + (self.height() - new_height))
                        new_size.setHeight(new_height)
                        
                if self.resize_handle in ["bottom-left", "bottom-right"]:
                    # Bottom edge moving
                    new_size.setHeight(max(self.min_size, self.height() + delta.y()))
                    
                self.setFixedSize(new_size)
                self.offset = event.pos()
                
            elif self.dragging:
                new_pos = self.mapToParent(event.pos() - self.offset)
                if len(self.parent().drag_keys) > 1:
                    self.parent().updateDragPosition(event.pos(), self)
                else:
                    new_pos.setX(max(0, min(new_pos.x(), self.parent().width() - self.width())))
                    new_pos.setY(max(0, min(new_pos.y(), self.parent().height() - self.height())))
                    self.move(new_pos)
            else:
                # Update cursor based on mouse position
                handle = self.getResizeHandle(event.pos())
                if handle in ["top-left", "bottom-right"]:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif handle in ["top-right", "bottom-left"]:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        if self.parent().editor_mode:
            # Get new label
            new_label, ok = QInputDialog.getText(self, "Edit Key Label", 
                                               "Enter display label:", text=self.label)
            if ok:
                self.label = new_label
                # Get key binding
                dialog = KeyBindDialog(self.keyboard_manager, self)
                if dialog.exec() == QDialog.DialogCode.Accepted and dialog.key_name:
                    self.key_bind = dialog.key_name
                self.update()

class KeyboardCanvas(QWidget):
    def __init__(self, keyboard_manager, parent=None):
        super().__init__(parent)
        self.keyboard_manager = keyboard_manager
        self.keys = []
        self.editor_mode = True
        self.setMinimumSize(800, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #1D2128;  /* Darker background for contrast */
            }
        """)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # For drag functionality
        self.dragging = False
        self.drag_start = None
        self.drag_keys = []
        self.key_initial_positions = {}
        
    def mousePressEvent(self, event):
        if self.editor_mode and event.button() == Qt.MouseButton.LeftButton:
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                # Clear selection on regular click (not Ctrl+Click)
                self.clearSelection()
                
            # Create new key at click position
            dialog = KeyBindDialog(self.keyboard_manager, self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.key_name:
                key = KeyboardKey(dialog.key_name, dialog.key_name, self.keyboard_manager, self)
                pos = event.pos()
                pos.setX(pos.x() - key.width() // 2)
                pos.setY(pos.y() - key.height() // 2)
                key.move(pos)
                self.keys.append(key)
                key.show()
                
    def clearSelection(self):
        """Clear selection from all keys."""
        for key in self.keys:
            key.selected = False
            key.update()
            
    def startDrag(self, offset):
        """Start dragging selected keys."""
        self.dragging = True
        self.drag_start = self.mapFromGlobal(self.cursor().pos())
        self.drag_keys = [key for key in self.keys if key.selected]
        self.key_initial_positions = {key: key.pos() for key in self.drag_keys}
        
    def updateDragPosition(self, pos, source_key):
        """Update position during drag operation."""
        if not self.dragging or not self.drag_keys:
            return
            
        current_pos = self.mapFromGlobal(self.cursor().pos())
        delta = current_pos - self.drag_start
        
        # Move all selected keys
        for key in self.drag_keys:
            new_pos = self.key_initial_positions[key] + delta
            # Keep the key within the canvas bounds
            new_pos.setX(max(0, min(new_pos.x(), self.width() - key.width())))
            new_pos.setY(max(0, min(new_pos.y(), self.height() - key.height())))
            key.move(new_pos)
            
    def endDrag(self):
        """End the drag operation."""
        self.dragging = False
        self.drag_keys = []
        self.key_initial_positions.clear()
        
    def removeKey(self, key):
        if key in self.keys:
            self.keys.remove(key)
            key.deleteLater()
        
    def clearKeys(self):
        for key in self.keys:
            key.deleteLater()
        self.keys.clear()
        
    def getConfiguration(self):
        return {
            'keys': [
                {
                    'label': key.label,
                    'key_bind': key.key_bind,
                    'x': key.x(),
                    'y': key.y(),
                    'width': key.width(),
                    'height': key.height()
                }
                for key in self.keys
            ]
        }
        
    def loadConfiguration(self, config):
        self.clearKeys()
        for key_data in config['keys']:
            key = KeyboardKey(
                key_data['label'],
                key_data.get('key_bind', ''),
                self.keyboard_manager,
                self
            )
            key.setFixedSize(key_data['width'], key_data['height'])
            key.move(key_data['x'], key_data['y'])
            self.keys.append(key)
            key.show()

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
        
        # Get authentication
        if not self.keyboard_manager.authenticate():
            QMessageBox.critical(self, "Error", 
                               "Authentication required to monitor keyboard input.")
            sys.exit(1)
            
        # Start the keyboard helper
        if not self.keyboard_manager.start():
            QMessageBox.critical(self, "Error", 
                               "Failed to start keyboard helper.")
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
            self.keyboard_manager.stop_monitoring()
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
            self.state_check_timer.stop()
        else:
            self.toggle_mode_btn.setText("Stop Visualizer")
            for widget in editor_widgets:
                widget.setEnabled(False)
            # Start monitoring with current key bindings
            key_binds = [key.key_bind.lower() for key in self.canvas.keys]
            if key_binds:  # Only start monitoring if we have keys to monitor
                self.keyboard_manager.start_monitoring(key_binds)
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
            key_map = {key.key_bind.lower(): key for key in self.canvas.keys}
            
            for key_name, is_pressed in key_states.items():
                if key_name in key_map:
                    key_map[key_name].pressed = is_pressed
                    key_map[key_name].update()
                    
    def closeEvent(self, event):
        self.state_check_timer.stop()
        self.keyboard_manager.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 