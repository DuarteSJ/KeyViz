from PyQt6.QtWidgets import QWidget, QDialog
from PyQt6.QtCore import Qt
from .keyboard_key import KeyboardKey
from .dialogs import KeyBindDialog


class KeyboardCanvas(QWidget):
    def __init__(self, keyboard_manager, parent=None):
        super().__init__(parent)
        self.keyboard_manager = keyboard_manager
        self.keys = []
        self.editor_mode = True
        self.setMinimumSize(800, 400)
        self.updateBackground()
        self.setCursor(Qt.CursorShape.CrossCursor)

        # For drag functionality
        self.dragging = False
        self.drag_start = None
        self.drag_keys = []
        self.key_initial_positions = {}

    def updateBackground(self):
        """Update the background color based on the editor mode."""
        if self.editor_mode:
            self.setStyleSheet("QWidget { background-color: #2E3440; }")
        else:
            # Transparent background for visualizer mode
            self.setStyleSheet("QWidget { background-color: transparent; }")

    def mousePressEvent(self, event):
        if self.editor_mode and event.button() == Qt.MouseButton.LeftButton:
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                # Clear selection on regular click (not Ctrl+Click)
                self.clearSelection()

            # Create new key at click position
            dialog = KeyBindDialog(self.keyboard_manager, self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.key_info:
                key = KeyboardKey(
                    dialog.key_info["name"],
                    dialog.key_info["name"],
                    None,  # Don't pass keyboard_manager to key
                    self
                )
                key.scan_code = dialog.key_info["scan_code"]
                pos = event.pos()
                pos.setX(pos.x() - key.width() // 2)
                pos.setY(pos.y() - key.height() // 2)
                key.move(pos)
                key.setParent(self)  # Ensure parent is set
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
            key.setParent(None)  # Clear parent before deletion
            key.deleteLater()

    def clearKeys(self):
        for key in self.keys:
            key.setParent(None)  # Clear parent before deletion
            key.deleteLater()
        self.keys.clear()

    def getConfiguration(self):
        return {
            "keys": [
                {
                    "label": key.label,
                    "key_bind": key.key_bind,
                    "scan_code": key.scan_code,
                    "x": key.x(),
                    "y": key.y(),
                    "width": key.width(),
                    "height": key.height(),
                }
                for key in self.keys
            ]
        }

    def loadConfiguration(self, config):
        self.clearKeys()
        for key_data in config["keys"]:
            key = KeyboardKey(
                key_data["label"],
                key_data.get("key_bind", ""),
                key_data.get("scan_code"),  # Pass scan_code directly
                self  # Pass parent
            )
            key.setFixedSize(key_data["width"], key_data["height"])
            key.move(key_data["x"], key_data["y"])
            key.setParent(self)  # Ensure parent is set
            self.keys.append(key)
            key.show()
