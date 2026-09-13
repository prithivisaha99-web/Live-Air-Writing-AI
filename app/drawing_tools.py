"""Drawing Tool models, preset color palettes, and Undo/Redo Stack Manager."""
from dataclasses import dataclass, field
import logging
from PySide6.QtGui import QColor
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


@dataclass
class VectorStroke:
    """Represents a vector stroke on the air writing canvas."""
    points: list[tuple[float, float]] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor("#00F0FF")) # Neon Cyan default
    width: int = 6
    is_eraser: bool = False


class UndoRedoManager(QObject):
    """Manages stroke history stack for Undo and Redo operations."""

    can_undo_changed = Signal(bool)
    can_redo_changed = Signal(bool)
    history_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[VectorStroke] = []
        self._redo_stack: list[VectorStroke] = []

    @property
    def history(self) -> list[VectorStroke]:
        return list(self._history)

    def add_stroke(self, stroke: VectorStroke) -> None:
        if not stroke.points:
            return
        self._history.append(stroke)
        self._redo_stack.clear()
        self._notify_state()

    def undo(self) -> VectorStroke | None:
        if not self._history:
            logger.info("[ShortcutDebug] undo_called -> history is empty, returning None")
            return None
        stroke = self._history.pop()
        self._redo_stack.append(stroke)
        logger.info(f"[ShortcutDebug] undo_called -> popped stroke with {len(stroke.points)} points. Remaining history={len(self._history)}")
        self._notify_state()
        return stroke

    def redo(self) -> VectorStroke | None:
        if not self._redo_stack:
            logger.info("[ShortcutDebug] redo_called -> redo stack is empty, returning None")
            return None
        stroke = self._redo_stack.pop()
        self._history.append(stroke)
        logger.info(f"[ShortcutDebug] redo_called -> restored stroke with {len(stroke.points)} points. History={len(self._history)}")
        self._notify_state()
        return stroke

    def clear(self) -> None:
        self._history.clear()
        self._redo_stack.clear()
        self._notify_state()

    def _notify_state(self) -> None:
        self.can_undo_changed.emit(bool(self._history))
        self.can_redo_changed.emit(bool(self._redo_stack))
        self.history_changed.emit()


# Preset Color Definitions for UI & Brush
PRESET_COLORS = [
    {"name": "Neon Cyan", "hex": "#00F0FF"},
    {"name": "Electric Purple", "hex": "#A855F7"},
    {"name": "Neon Green", "hex": "#10B981"},
    {"name": "Vibrant Yellow", "hex": "#FFE600"},
    {"name": "Hot Pink", "hex": "#FF007F"},
    {"name": "Bright Red", "hex": "#FF334B"},
    {"name": "Pure White", "hex": "#FFFFFF"},
    {"name": "Deep Black", "hex": "#000000"},
]
