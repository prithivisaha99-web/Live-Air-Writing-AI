"""Unit tests for Gesture Detection Engine."""
import unittest
from app.gesture_detection import GestureDetector, GestureType, GestureMode


class TestGestureDetector(unittest.TestCase):

    def setUp(self):
        self.detector = GestureDetector(mode=GestureMode.POINTING, buffer_size=3)

    def _create_mock_hand(self, index_ext=True, middle_ext=False, ring_ext=False, pinky_ext=False):
        """Create mock 21-landmark pixel list."""
        # Index 0: WRIST, 4: THUMB, 8: INDEX_TIP, 6: INDEX_PIP, 12: MIDDLE_TIP, 10: MIDDLE_PIP, etc.
        pixels = [(100, 100)] * 21
        
        # PIP joints at y = 200
        pixels[6] = (100, 200)   # INDEX_PIP
        pixels[10] = (120, 200)  # MIDDLE_PIP
        pixels[14] = (140, 200)  # RING_PIP
        pixels[18] = (160, 200)  # PINKY_PIP
        pixels[4] = (50, 250)    # THUMB_TIP

        # Tips: extended means y < pip_y (y=100 < 200), folded means y > pip_y (y=250 > 200)
        pixels[8] = (100, 100 if index_ext else 250)
        pixels[12] = (120, 100 if middle_ext else 250)
        pixels[16] = (140, 100 if ring_ext else 250)
        pixels[20] = (160, 100 if pinky_ext else 250)

        return {"pixels": pixels, "landmarks": []}

    def test_none_hand(self):
        gesture = self.detector.update(None)
        self.assertEqual(gesture, GestureType.NONE)

    def test_pointing_drawing_gesture(self):
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=False, ring_ext=False, pinky_ext=False)
        for _ in range(3):
            gesture = self.detector.update(mock_hand)
        self.assertEqual(gesture, GestureType.DRAW)

    def test_hover_stop_gesture(self):
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=False)
        for _ in range(3):
            gesture = self.detector.update(mock_hand)
        self.assertEqual(gesture, GestureType.HOVER)

    def test_eraser_fist_gesture(self):
        mock_hand = self._create_mock_hand(index_ext=False, middle_ext=False, ring_ext=False, pinky_ext=False)
        for _ in range(3):
            gesture = self.detector.update(mock_hand)
        self.assertEqual(gesture, GestureType.ERASER)


if __name__ == "__main__":
    unittest.main()
