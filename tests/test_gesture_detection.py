"""Unit tests for Gesture Detection Engine."""
import unittest
from app.gesture_detection import GestureDetector, GestureType, GestureMode, ShortcutDetector, ShortcutGesture


class TestGestureDetector(unittest.TestCase):

    def setUp(self):
        self.detector = GestureDetector(mode=GestureMode.POINTING, buffer_size=3)
        self.shortcut_detector = ShortcutDetector(debounce_frames=4)

    def _create_mock_hand(self, index_ext=True, middle_ext=False, ring_ext=False, pinky_ext=False, thumb_up=False):
        """Create mock 21-landmark pixel list."""
        pixels = [(100, 100)] * 21
        
        pixels[0] = (100, 300)   # WRIST
        pixels[5] = (100, 250)   # INDEX_MCP
        pixels[9] = (120, 250)   # MIDDLE_MCP
        pixels[13] = (140, 250)  # RING_MCP
        pixels[17] = (160, 250)  # PINKY_MCP

        pixels[2] = (80, 260)    # THUMB_MCP
        pixels[6] = (100, 200)   # INDEX_PIP
        pixels[10] = (120, 200)  # MIDDLE_PIP
        pixels[14] = (140, 200)  # RING_PIP
        pixels[18] = (160, 200)  # PINKY_PIP

        if thumb_up:
            pixels[4] = (80, 100) # THUMB_TIP high up
        else:
            pixels[4] = (80, 270) # THUMB_TIP folded

        # Tips: extended means tip is high up (y=100), folded means tip is near palm (y=270)
        pixels[8] = (100, 100 if index_ext else 270)
        pixels[12] = (120, 100 if middle_ext else 270)
        pixels[16] = (140, 100 if ring_ext else 270)
        pixels[20] = (160, 100 if pinky_ext else 270)

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

    def test_two_finger_undo_shortcut_debouncing_and_latching(self):
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=False)
        eval_data = self.detector.evaluate_all_fingers(mock_hand)

        # Frames 1..3: debouncing (buffer size 4 not yet full / clear)
        for _ in range(3):
            res = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
            self.assertIsNone(res)

        # Frame 4: 4th consecutive frame -> TRIGGERS UNDO!
        res_4 = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        self.assertEqual(res_4, ShortcutGesture.UNDO)

        # Frame 5: Held gesture -> LATCHED, returns None!
        res_5 = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        self.assertIsNone(res_5)

        # Lower hand (NONE) -> Releases latch
        for _ in range(4):
            self.shortcut_detector.update(None, None, is_drawing=False)

        # Raise two fingers again -> Triggers UNDO again after 4 frames!
        for _ in range(3):
            self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        res_retrigger = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        self.assertEqual(res_retrigger, ShortcutGesture.UNDO)

    def test_three_finger_redo_shortcut(self):
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=True, ring_ext=True, pinky_ext=False)
        eval_data = self.detector.evaluate_all_fingers(mock_hand)

        for _ in range(3):
            self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        res = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        self.assertEqual(res, ShortcutGesture.REDO)

    def test_thumb_up_confirm_shortcut(self):
        mock_hand = self._create_mock_hand(index_ext=False, middle_ext=False, ring_ext=False, pinky_ext=False, thumb_up=True)
        eval_data = self.detector.evaluate_all_fingers(mock_hand)

        for _ in range(3):
            self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        res = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        self.assertEqual(res, ShortcutGesture.CONFIRM)

    def test_shortcut_disabled_while_drawing(self):
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=False)
        eval_data = self.detector.evaluate_all_fingers(mock_hand)

        # Even with 4 consecutive frames, if is_drawing is True -> returns None!
        for _ in range(5):
            res = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=True)
            self.assertIsNone(res)

    def test_two_finger_undo_with_pinky_noise(self):
        """Verify ✌️ Undo triggers even if pinky has classification noise."""
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=True)
        eval_data = self.detector.evaluate_all_fingers(mock_hand)

        cand, summary, reason = self.shortcut_detector.detect_raw_shortcut(mock_hand, eval_data)
        self.assertEqual(cand, ShortcutGesture.UNDO)

        for _ in range(3):
            self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        res = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
        self.assertEqual(res, ShortcutGesture.UNDO)

    def test_rejection_of_open_palm(self):
        """Verify Open Palm (all 4 fingers extended) is strictly rejected as a shortcut."""
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=True, ring_ext=True, pinky_ext=True)
        eval_data = self.detector.evaluate_all_fingers(mock_hand)

        cand, summary, reason = self.shortcut_detector.detect_raw_shortcut(mock_hand, eval_data)
        self.assertEqual(cand, ShortcutGesture.NONE)
        self.assertIn("Open Palm", reason)

        for _ in range(5):
            res = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
            self.assertIsNone(res)

    def test_rejection_of_pointing_draw(self):
        """Verify normal pointing finger (DRAW posture) is strictly rejected as a shortcut."""
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=False, ring_ext=False, pinky_ext=False)
        eval_data = self.detector.evaluate_all_fingers(mock_hand)

        cand, summary, reason = self.shortcut_detector.detect_raw_shortcut(mock_hand, eval_data)
        self.assertEqual(cand, ShortcutGesture.NONE)
        self.assertIn("Pointing", reason)

        for _ in range(5):
            res = self.shortcut_detector.update(mock_hand, eval_data, is_drawing=False)
            self.assertIsNone(res)

    def test_shortcut_diagnostic_info(self):
        """Verify diagnostic dictionary contains required reporting fields."""
        mock_hand = self._create_mock_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=False)
        self.shortcut_detector.update(mock_hand, is_drawing=False)
        diag = self.shortcut_detector.get_diagnostic_info()

        self.assertIn("candidate", diag)
        self.assertIn("finger_summary", diag)
        self.assertIn("stable_frames", diag)
        self.assertIn("latched", diag)
        self.assertIn("reason", diag)


if __name__ == "__main__":
    unittest.main()
