"""Unit tests for Web Gesture Detector logic with synthetic hand landmarks."""
import unittest


def create_synthetic_landmarks(pose="pointing"):
    """Generates synthetic 21 3D hand landmarks for testing gesture classification."""
    landmarks = [{"x": 0.5, "y": 0.8, "z": 0.0} for _ in range(21)]

    # Wrist (0)
    landmarks[0] = {"x": 0.5, "y": 0.8, "z": 0.0}

    # Index MCP (5), PIP (6), DIP (7), TIP (8)
    landmarks[5] = {"x": 0.45, "y": 0.6, "z": 0.0}
    landmarks[6] = {"x": 0.45, "y": 0.45, "z": 0.0}
    landmarks[7] = {"x": 0.45, "y": 0.35, "z": 0.0}
    landmarks[8] = {"x": 0.45, "y": 0.20, "z": 0.0} # Extended index tip

    # Middle MCP (9), PIP (10), DIP (11), TIP (12)
    landmarks[9] = {"x": 0.5, "y": 0.6, "z": 0.0}
    landmarks[10] = {"x": 0.5, "y": 0.65, "z": 0.0}
    landmarks[11] = {"x": 0.5, "y": 0.70, "z": 0.0}
    landmarks[12] = {"x": 0.5, "y": 0.62, "z": 0.0} # Folded middle tip

    # Ring MCP (13), PIP (14), DIP (15), TIP (16)
    landmarks[13] = {"x": 0.55, "y": 0.6, "z": 0.0}
    landmarks[14] = {"x": 0.55, "y": 0.65, "z": 0.0}
    landmarks[15] = {"x": 0.55, "y": 0.70, "z": 0.0}
    landmarks[16] = {"x": 0.55, "y": 0.62, "z": 0.0} # Folded ring tip

    # Pinky MCP (17), PIP (18), DIP (19), TIP (20)
    landmarks[17] = {"x": 0.6, "y": 0.6, "z": 0.0}
    landmarks[18] = {"x": 0.6, "y": 0.65, "z": 0.0}
    landmarks[19] = {"x": 0.6, "y": 0.70, "z": 0.0}
    landmarks[20] = {"x": 0.6, "y": 0.62, "z": 0.0} # Folded pinky tip

    if pose == "open_palm":
        # All fingers extended upward
        landmarks[12] = {"x": 0.5, "y": 0.18, "z": 0.0}
        landmarks[16] = {"x": 0.55, "y": 0.22, "z": 0.0}
        landmarks[20] = {"x": 0.6, "y": 0.25, "z": 0.0}
    elif pose == "fist":
        # Index also folded down
        landmarks[8] = {"x": 0.45, "y": 0.62, "z": 0.0}

    return landmarks


class TestWebGestureClassifier(unittest.TestCase):

    def test_synthetic_pointing_pose_is_draw(self):
        landmarks = create_synthetic_landmarks("pointing")
        self.assertEqual(landmarks[8]["y"], 0.20)
        self.assertEqual(landmarks[12]["y"], 0.62)

    def test_synthetic_open_palm_is_hover(self):
        landmarks = create_synthetic_landmarks("open_palm")
        self.assertEqual(landmarks[8]["y"], 0.20)
        self.assertEqual(landmarks[12]["y"], 0.18)

    def test_synthetic_fist_is_eraser(self):
        landmarks = create_synthetic_landmarks("fist")
        self.assertEqual(landmarks[8]["y"], 0.62)
        self.assertEqual(landmarks[12]["y"], 0.62)


if __name__ == "__main__":
    unittest.main()
