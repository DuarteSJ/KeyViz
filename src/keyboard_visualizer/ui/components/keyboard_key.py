from PyQt6.QtWidgets import QWidget, QInputDialog, QDialog
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QRadialGradient
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl
from pathlib import Path
import json
import random

from ui.dialogs.settings_dialog import KeyBindDialog
from utils.config import load_key_colors

KEY_COLORS = load_key_colors()

class KeyboardKey(QWidget):
    def __init__(self, label="", key_bind="", scan_code=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.key_bind = key_bind
        self.scan_code = scan_code
        self.pressed = False
        self.selected = False
        self.setFixedSize(40, 40)

        self.dragging = False
        self.resizing = False
        self.resize_handle = None
        self.offset = QPoint()
        self.min_size = 30

        self.setMouseTracking(True)
        self.sound_effect = self.setSoundEffect(key_bind)



    def setSoundEffect(self, key_bind):
        sound_path = Path(__file__).parent.parent.parent / "sounds" / f"{key_bind}.wav"
        if not sound_path.exists():
            # choose random letter of the alphabet to replace the sound
            choice = random.choice("abcdefghijklmnopqrstuvwxyz")
            sound_path = Path(__file__).parent.parent.parent / "sounds" / f"{choice}.wav"
            if not sound_path.exists():
                # default to the sound of a if the chosen sound also does not exist
                sound_path = Path(__file__).parent.parent.parent / "sounds" / "a.wav"
        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile(str(sound_path)))
        self.sound_effect.setVolume(0.3)
        return self.sound_effect

    def paintEvent(self, event):
        parent = self.parent()
        if parent is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.pressed:
            color = QColor(KEY_COLORS["pressed"])
            glow = QRadialGradient(
                self.width() / 2, self.height() / 2, self.width() / 2
            )
            glow.setColorAt(0, QColor(KEY_COLORS["glow_center"]))
            glow.setColorAt(1, QColor(KEY_COLORS["glow_edge"]))
            painter.fillRect(0, 0, self.width(), self.height(), glow)
        else:
            color = (
                QColor(KEY_COLORS["selected"])
                if self.selected
                else QColor(KEY_COLORS["normal"])
            )

        main_face = QPainterPath()
        main_face.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 5, 5)
        painter.fillPath(main_face, color)

        if not self.pressed:
            highlight_path = QPainterPath()
            highlight_path.moveTo(2, 2)
            highlight_path.lineTo(self.width() - 2, 2)
            pen = QPen(
                QColor(
                    KEY_COLORS["highlight_selected"]
                    if self.selected
                    else KEY_COLORS["highlight_normal"]
                )
            )
            pen.setWidth(1)
            painter.strokePath(highlight_path, pen)

        painter.setPen(
            QPen(
                QColor(
                    KEY_COLORS["text_normal"]
                    if not self.pressed
                    else KEY_COLORS["text_pressed"]
                )
            )
        )
        font = painter.font()
        # Scale font size based on key size
        base_size = 40  # Original key size
        scale_factor = min(self.width() / base_size, self.height() / base_size)
        font_size = max(6, int(9 * scale_factor))  # Minimum font size of 6
        font.setPointSize(font_size)
        font.setFamily("Arial")
        font.setBold(True)
        painter.setFont(font)

        text_rect = painter.fontMetrics().boundingRect(self.label)
        x = (self.width() - text_rect.width()) / 2
        y = (self.height() + text_rect.height()) / 2

        if self.pressed:
            x += 2
            y += 2

        if not self.pressed:
            painter.setPen(QPen(QColor(KEY_COLORS["text_shadow"])))
            painter.drawText(int(x + 1), int(y + 1), self.label)
            painter.setPen(QPen(QColor(KEY_COLORS["text_normal"])))
        painter.drawText(int(x), int(y), self.label)

        if self.selected and parent.editor_mode:
            handle_size = min(6, int(self.width() * 0.15))  # Scale handle size with key size
            handle_color = QColor(KEY_COLORS["resize_handle"])
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
        handle_size = 6
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
        parent = self.parent()
        if parent is None:
            return

        if parent.editor_mode and event.button() == Qt.MouseButton.LeftButton:
            handle = self.getResizeHandle(event.pos())
            if handle and self.selected:
                self.resizing = True
                self.resize_handle = handle
                self.offset = event.pos()
            else:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.selected = not self.selected
                    self.update()
                else:
                    if not self.selected:
                        parent.clearSelection()
                        self.selected = True
                        self.update()
                    self.dragging = True
                    self.offset = event.pos()
                    parent.startDrag(event.pos())
        elif event.button() == Qt.MouseButton.RightButton:
            parent.removeKey(self)

    def mouseReleaseEvent(self, event):
        parent = self.parent()
        if parent and event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            self.resize_handle = None
            parent.endDrag()

    def mouseMoveEvent(self, event):
        parent = self.parent()
        if parent is None or not parent.editor_mode:
            return

        if self.resizing:
            delta = event.pos() - self.offset
            new_size = self.size()

            if self.resize_handle in ["top-left", "bottom-left"]:
                new_width = max(self.min_size, self.width() - delta.x())
                if new_width != self.width():
                    self.move(self.x() + (self.width() - new_width), self.y())
                    new_size.setWidth(new_width)

            if self.resize_handle in ["top-right", "bottom-right"]:
                new_size.setWidth(max(self.min_size, self.width() + delta.x()))

            if self.resize_handle in ["top-left", "top-right"]:
                new_height = max(self.min_size, self.height() - delta.y())
                if new_height != self.height():
                    self.move(self.x(), self.y() + (self.height() - new_height))
                    new_size.setHeight(new_height)

            if self.resize_handle in ["bottom-left", "bottom-right"]:
                new_size.setHeight(max(self.min_size, self.height() + delta.y()))

            self.setFixedSize(new_size)
            self.offset = event.pos()

        elif self.dragging:
            new_pos = self.mapToParent(event.pos() - self.offset)
            if len(parent.drag_keys) > 1:
                parent.updateDragPosition(event.pos(), self)
            else:
                new_pos.setX(max(0, min(new_pos.x(), parent.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), parent.height() - self.height())))
                self.move(new_pos)
        else:
            handle = self.getResizeHandle(event.pos())
            if handle in ["top-left", "bottom-right"]:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in ["top-right", "bottom-left"]:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        parent = self.parent()
        if parent and parent.editor_mode:
            new_label, ok = QInputDialog.getText(
                self, "Edit Key Label", "Enter display label:", text=self.label
            )
            if ok:
                self.label = new_label
                dialog = KeyBindDialog(parent.keyboard_manager, self)
                if dialog.exec() == QDialog.DialogCode.Accepted and dialog.key_info:
                    self.key_bind = dialog.key_info["name"]
                    self.scan_code = dialog.key_info["scan_code"]
                self.update()

    def playSound(self):
        """Play a sound when the key is pressed."""
        if self.sound_effect.isLoaded():
            self.sound_effect.play()
        else:
            print("Sound not loaded.")
