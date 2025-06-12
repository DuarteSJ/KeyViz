from typing import List, Dict, Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget, QDialog
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QResizeEvent, QMouseEvent
from keyboard_visualizer.ui.components.keyboard_key import KeyboardKey
from keyboard_visualizer.ui.dialogs.settings_dialog import KeyBindDialog
from keyboard_visualizer.core.keyboard_manager import KeyboardManager


class KeyboardCanvas(QWidget):
    """
    Canvas widget for displaying and managing keyboard keys in a visual layout.

    This widget serves as the main display area for keyboard visualization and editing.
    It supports two modes: editor mode for creating and arranging keys, and visualizer
    mode for real-time key state display with automatic scaling.

    The canvas handles key creation, selection, dragging, and scaling operations.
    In editor mode, users can create new keys by clicking and drag existing keys
    around. In visualizer mode, the canvas automatically scales keys to maintain
    aspect ratio when the window is resized.

    Attributes:
        keyboard_manager (KeyboardManager): Manager for keyboard input monitoring.
        keys (List[KeyboardKey]): List of all keyboard keys on the canvas.
        editor_mode (bool): Whether the canvas is in editor mode (True) or visualizer mode (False).
        dragging (bool): Whether a drag operation is currently in progress.
        drag_start (Optional[QPoint]): Starting position of the current drag operation.
        drag_keys (List[KeyboardKey]): List of keys being dragged in the current operation.
        key_initial_positions (Dict[KeyboardKey, QPoint]): Initial positions of keys being dragged.
        base_size (Optional[QSize]): Original canvas size used for scaling calculations.
        key_original_sizes (Dict[KeyboardKey, QSize]): Original sizes of keys for scaling.
        key_original_positions (Dict[KeyboardKey, QPoint]): Original positions of keys for scaling.
    """

    def __init__(
        self, keyboard_manager: KeyboardManager, parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize the KeyboardCanvas.

        Args:
            keyboard_manager (KeyboardManager): The keyboard manager instance for handling input.
            parent (Optional[QWidget]): Parent widget, defaults to None.
        """
        super().__init__(parent)
        self.keyboard_manager: KeyboardManager = keyboard_manager
        self.keys: List[KeyboardKey] = []
        self.editor_mode: bool = True
        self.setMinimumSize(800, 400)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # For drag functionality
        self.dragging: bool = False
        self.drag_start: Optional[QPoint] = None
        self.drag_keys: List[KeyboardKey] = []
        self.key_initial_positions: Dict[KeyboardKey, QPoint] = {}

        # For scaling functionality
        self.base_size: Optional[QSize] = None
        self.key_original_sizes: Dict[KeyboardKey, QSize] = {}
        self.key_original_positions: Dict[KeyboardKey, QPoint] = {}

    def saveOriginalLayout(self) -> None:
        """
        Save the original layout dimensions for scaling operations.

        Stores the current canvas size and all key positions and sizes as reference
        points for proportional scaling when the canvas is resized in visualizer mode.
        This method should be called before entering visualizer mode.
        """
        if not self.base_size:
            self.base_size = self.size()
            self.key_original_sizes = {key: key.size() for key in self.keys}
            self.key_original_positions = {key: key.pos() for key in self.keys}

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Handle canvas resize events with proportional key scaling.

        In visualizer mode, automatically scales all keys proportionally to maintain
        the visual layout when the canvas is resized. Uses the smaller of width or
        height scale factors to preserve aspect ratios.

        Args:
            event (QResizeEvent): The resize event containing old and new sizes.

        Note:
            Scaling only occurs in visualizer mode. In editor mode, keys maintain
            their original sizes and positions.
        """
        super().resizeEvent(event)

        if not self.editor_mode and self.keys:
            if not self.base_size:
                self.saveOriginalLayout()

            # Calculate scale factors
            width_scale: float = event.size().width() / self.base_size.width()
            height_scale: float = event.size().height() / self.base_size.height()

            # Use the smaller scale to maintain aspect ratio
            scale: float = min(width_scale, height_scale)

            for key in self.keys:
                # Scale size
                original_size = self.key_original_sizes[key]
                new_width: int = int(original_size.width() * scale)
                new_height: int = int(original_size.height() * scale)
                key.setFixedSize(new_width, new_height)

                # Scale position
                original_pos = self.key_original_positions[key]
                new_x: int = int(original_pos.x() * scale)
                new_y: int = int(original_pos.y() * scale)
                key.move(new_x, new_y)

    def toggleEditorMode(self, enabled: bool) -> None:
        """
        Toggle between editor and visualization modes.

        In editor mode:
        - Keys can be created, moved, and edited
        - Keys maintain their original sizes and positions
        - Scaling data is cleared

        In visualizer mode:
        - Keys are scaled proportionally with canvas resizing
        - Original layout dimensions are saved for scaling reference
        - Key editing is disabled

        Args:
            enabled (bool): True to enable editor mode, False for visualizer mode.
        """
        self.editor_mode = enabled
        if enabled:
            # Reset to original sizes and positions when entering editor mode
            if self.base_size:
                for key in self.keys:
                    key.setFixedSize(self.key_original_sizes[key])
                    key.move(self.key_original_positions[key])
                self.base_size = None
                self.key_original_sizes.clear()
                self.key_original_positions.clear()
        else:
            # Save original layout when entering visualization mode
            self.saveOriginalLayout()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events for key creation and selection.

        In editor mode, left clicks create new keys through a key binding dialog.
        If Ctrl is not held, existing selections are cleared before creating new keys.
        The new key is centered at the click position.

        Args:
            event (QMouseEvent): The mouse press event containing position and button info.

        Note:
            Only responds to left mouse button clicks in editor mode.
            Key creation requires successful completion of the key binding dialog.
        """
        if self.editor_mode and event.button() == Qt.MouseButton.LeftButton:
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                # Clear selection on regular click (not Ctrl+Click)
                self.clearSelection()

            # Create new key at click position
            dialog: KeyBindDialog = KeyBindDialog(self.keyboard_manager, self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.key_info:
                key: KeyboardKey = KeyboardKey(
                    dialog.key_info["name"],
                    dialog.key_info["name"],
                    None,  # Don't pass keyboard_manager to key
                    self,
                )
                key.scan_code = dialog.key_info["scan_code"]
                pos: QPoint = event.pos()
                pos.setX(pos.x() - key.width() // 2)
                pos.setY(pos.y() - key.height() // 2)
                key.move(pos)
                key.setParent(self)  # Ensure parent is set
                self.keys.append(key)
                key.show()

    def clearSelection(self) -> None:
        """
        Clear selection from all keys on the canvas.

        Sets the selected state of all keys to False and triggers a visual update
        to reflect the deselection. This is typically called when starting a new
        selection or when clearing all selections.
        """
        for key in self.keys:
            key.selected = False
            key.update()

    def startDrag(self, offset: QPoint) -> None:
        """
        Start a drag operation for selected keys.

        Initializes the drag state by recording the starting position and identifying
        which keys are currently selected for dragging. Stores the initial position
        of each selected key for relative movement calculations.

        Args:
            offset (QPoint): The offset from the key's origin to the drag start point.
                This parameter is currently unused but maintained for API compatibility.
        """
        self.dragging = True
        self.drag_start = self.mapFromGlobal(self.cursor().pos())
        self.drag_keys = [key for key in self.keys if key.selected]
        self.key_initial_positions = {key: key.pos() for key in self.drag_keys}

    def updateDragPosition(self, pos: QPoint, source_key: KeyboardKey) -> None:
        """
        Update positions of keys during a drag operation.

        Calculates the movement delta from the drag start position and applies it
        to all selected keys. Ensures keys remain within the canvas boundaries
        by clamping their positions.

        Args:
            pos (QPoint): The current mouse position (currently unused).
            source_key (KeyboardKey): The key that initiated the drag (currently unused).

        Note:
            The pos and source_key parameters are maintained for API compatibility
            but the actual position is calculated from the global cursor position.
        """
        if not self.dragging or not self.drag_keys:
            return

        current_pos: QPoint = self.mapFromGlobal(self.cursor().pos())
        delta: QPoint = current_pos - self.drag_start

        # Move all selected keys
        for key in self.drag_keys:
            new_pos: QPoint = self.key_initial_positions[key] + delta
            # Keep the key within the canvas bounds
            new_pos.setX(max(0, min(new_pos.x(), self.width() - key.width())))
            new_pos.setY(max(0, min(new_pos.y(), self.height() - key.height())))
            key.move(new_pos)

    def endDrag(self) -> None:
        """
        End the current drag operation and clean up drag state.

        Resets all drag-related flags and clears temporary storage used during
        the drag operation. This method should be called when the drag operation
        is completed or cancelled.
        """
        self.dragging = False
        self.drag_keys = []
        self.key_initial_positions.clear()

    def removeKey(self, key: KeyboardKey) -> None:
        """
        Remove a key from the canvas.

        Removes the specified key from the keys list, clears its parent relationship,
        and schedules it for deletion. This method safely handles cleanup to prevent
        memory leaks and orphaned widgets.

        Args:
            key (KeyboardKey): The key to remove from the canvas.
        """
        if key in self.keys:
            self.keys.remove(key)
            key.setParent(None)  # Clear parent before deletion
            key.deleteLater()

    def clearKeys(self) -> None:
        """
        Remove all keys from the canvas.

        Clears all keys from the canvas by removing their parent relationships
        and scheduling them for deletion. This method is typically used when
        loading a new layout or resetting the canvas.
        """
        for key in self.keys:
            key.setParent(None)  # Clear parent before deletion
            key.deleteLater()
        self.keys.clear()

    def getConfiguration(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get the current keyboard layout configuration.

        Exports the current state of all keys on the canvas as a dictionary
        suitable for saving to a configuration file. Includes key properties
        such as label, key binding, scan code, and position/size information.

        Returns:
            Dict[str, List[Dict[str, Any]]]: Configuration dictionary containing
                a 'keys' list with each key's properties including label, key_bind,
                scan_code, position (x, y) and dimensions (width, height).
        """
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

    def loadConfiguration(self, config: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Load a keyboard layout configuration.

        Clears the current canvas and creates new keys based on the provided
        configuration data. Each key is created with the specified properties
        including position, size, label, and scan code.

        Args:
            config (Dict[str, List[Dict[str, Any]]]): Configuration dictionary
                containing a 'keys' list with key properties. Each key should
                have label, key_bind, scan_code, x, y, width, and height properties.

        Note:
            This method will clear all existing keys before loading the new configuration.
            Missing key_bind or scan_code values will default to empty string or None.
        """
        self.clearKeys()
        for key_data in config["keys"]:
            key: KeyboardKey = KeyboardKey(
                key_data["label"],
                key_data.get("key_bind", ""),
                key_data.get("scan_code"),  # Pass scan_code directly
                self,  # Pass parent
            )
            key.setFixedSize(key_data["width"], key_data["height"])
            key.move(key_data["x"], key_data["y"])
            key.setParent(self)  # Ensure parent is set
            self.keys.append(key)
            key.show()
