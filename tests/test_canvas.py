"""Unit tests for Undo/Redo Manager & Vector Stroke History."""
import unittest
from PySide6.QtGui import QColor
from app.drawing_tools import VectorStroke, UndoRedoManager


class TestUndoRedoManager(unittest.TestCase):

    def setUp(self):
        self.mgr = UndoRedoManager()

    def test_undo_redo_lifecycle(self):
        s1 = VectorStroke(points=[(10, 10), (20, 20)], color=QColor("#00F0FF"), width=5)
        s2 = VectorStroke(points=[(30, 30), (40, 40)], color=QColor("#A855F7"), width=8)

        self.mgr.add_stroke(s1)
        self.mgr.add_stroke(s2)

        self.assertEqual(len(self.mgr.history), 2)

        # Test Undo
        undone = self.mgr.undo()
        self.assertEqual(undone, s2)
        self.assertEqual(len(self.mgr.history), 1)

        # Test Redo
        redone = self.mgr.redo()
        self.assertEqual(redone, s2)
        self.assertEqual(len(self.mgr.history), 2)

    def test_clear(self):
        s1 = VectorStroke(points=[(10, 10), (20, 20)])
        self.mgr.add_stroke(s1)
        self.mgr.clear()
        self.assertEqual(len(self.mgr.history), 0)


class TestCanvasColorPersistence(unittest.TestCase):

    def setUp(self):
        from PySide6.QtWidgets import QApplication
        import sys
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.mgr = UndoRedoManager()
        from app.canvas import AirWritingCanvas
        self.canvas = AirWritingCanvas(self.mgr)

    def test_selected_color_persists(self):
        selected_color = QColor("#000000") # Deep Black
        self.canvas.current_color = selected_color
        
        self.canvas.start_active_stroke((0.1, 0.1))
        self.canvas.update_active_stroke((0.2, 0.2))
        
        self.assertIsNotNone(self.canvas.active_stroke)
        self.assertEqual(self.canvas.active_stroke.color, selected_color)
        
        self.canvas.commit_active_stroke()
        self.assertEqual(len(self.mgr.history), 1)
        self.assertEqual(self.mgr.history[0].color, selected_color)


if __name__ == "__main__":
    unittest.main()
