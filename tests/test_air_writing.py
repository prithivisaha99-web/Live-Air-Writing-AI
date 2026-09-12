"""Unit tests for Air Writing Engine."""
import unittest
from app.air_writing import AirWritingEngine, StrokePoint


class TestAirWritingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AirWritingEngine(smoothing_factor=0.65)
        self.frame_size = (640, 480)

    def test_stroke_start_and_continue(self):
        finished, new_pts, drawing, smooth_pt, interp_cnt = self.engine.process_point((100, 100), self.frame_size, is_drawing_gesture=True)
        self.assertIsNone(finished)
        self.assertTrue(drawing)
        self.assertEqual(len(self.engine.current_stroke_points), 1)
        self.assertEqual(len(new_pts), 1)

        # Continue drawing
        finished, new_pts, drawing, smooth_pt, interp_cnt = self.engine.process_point((110, 105), self.frame_size, is_drawing_gesture=True)
        self.assertIsNone(finished)
        self.assertTrue(drawing)
        self.assertGreaterEqual(len(self.engine.current_stroke_points), 2)

    def test_stroke_finish_on_gesture_release(self):
        self.engine.process_point((100, 100), self.frame_size, is_drawing_gesture=True)
        self.engine.process_point((110, 105), self.frame_size, is_drawing_gesture=True)
        
        finished_stroke, new_pts, drawing, smooth_pt, interp_cnt = self.engine.process_point(None, self.frame_size, is_drawing_gesture=False)
        self.assertFalse(drawing)
        self.assertIsNotNone(finished_stroke)


if __name__ == "__main__":
    unittest.main()
