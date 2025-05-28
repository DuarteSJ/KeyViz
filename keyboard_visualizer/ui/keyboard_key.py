from PyQt6.QtWidgets import QWidget, QInputDialog, QDialog
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QRadialGradient
from .dialogs import KeyBindDialog


class KeyboardKey(QWidget):
    def __init__(self, label="", key_bind="", keyboard_manager=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.key_bind = key_bind
        self.keyboard_manager = keyboard_manager
        self.pressed = False
        self.selected = False
        self.setFixedSize(40, 40)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #2E3440;
                border-radius: 5px;
            }
        """
        )

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
        path.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 5, 5)

        # Define colors for different states and parts
        if self.pressed:
            # Brighter, more noticeable color when pressed
            top_color = QColor("#88C0D0")  # Bright blue when pressed
            side_color = QColor("#5E81AC")  # Darker blue for sides
            bottom_color = QColor("#4C566A")

            # Add a glow effect when pressed
            glow = QRadialGradient(
                self.width() / 2, self.height() / 2, self.width() / 2
            )
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
            main_face.addRoundedRect(3, 3, self.width() - 4, self.height() - 4, 5, 5)
        else:
            main_face.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 5, 5)
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
        painter.setPen(QPen(QColor("#ECEFF4" if not self.pressed else "#2E3440")))
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
            painter.fillRect(
                self.width() - handle_size, 0, handle_size, handle_size, handle_color
            )
            painter.fillRect(
                0, self.height() - handle_size, handle_size, handle_size, handle_color
            )
            painter.fillRect(
                self.width() - handle_size,
                self.height() - handle_size,
                handle_size,
                handle_size,
                handle_color,
            )

    def getResizeHandle(self, pos):
        """Return which resize handle the position is over, if any."""
        handle_size = 6

        # Check each corner
        if QRect(0, 0, handle_size, handle_size).contains(pos):
            return "top-left"
        elif QRect(self.width() - handle_size, 0, handle_size, handle_size).contains(
            pos
        ):
            return "top-right"
        elif QRect(0, self.height() - handle_size, handle_size, handle_size).contains(
            pos
        ):
            return "bottom-left"
        elif QRect(
            self.width() - handle_size,
            self.height() - handle_size,
            handle_size,
            handle_size,
        ).contains(pos):
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
                    new_pos.setX(
                        max(0, min(new_pos.x(), self.parent().width() - self.width()))
                    )
                    new_pos.setY(
                        max(0, min(new_pos.y(), self.parent().height() - self.height()))
                    )
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
            new_label, ok = QInputDialog.getText(
                self, "Edit Key Label", "Enter display label:", text=self.label
            )
            if ok:
                self.label = new_label
                # Get key binding
                dialog = KeyBindDialog(self.keyboard_manager, self)
                if dialog.exec() == QDialog.DialogCode.Accepted and dialog.key_name:
                    self.key_bind = dialog.key_name
                self.update()
