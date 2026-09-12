"""Unit tests for Web Canvas pure drawing logic, EMA smoothing, stroke lifecycle, undo/redo stack, and coordinate mapping."""
import unittest
import math


class WebVectorStroke:
    """Python representation of web VectorStroke for pure math unit testing."""
    def __init__(self, color="#00F0FF", width=8, is_eraser=False):
        self.points = []
        self.color = color
        self.width = width
        self.is_eraser = is_eraser

    def add_point(self, x: float, y: float):
        self.points.append({"x": max(0.0, min(1.0, float(x))), "y": max(0.0, min(1.0, float(y)))})


class WebCanvasEngine:
    """Python state machine replicating BrowserAirCanvas drawing & history stack logic."""
    def __init__(self):
        self.history = []
        self.redo_stack = []
        self.active_stroke = None
        self.is_writing = False
        self.prev_smoothed = None

        self.min_alpha = 0.20
        self.max_alpha = 0.80
        self.min_dist_threshold = 0.0008
        self.interp_step = 0.004
        self.current_color = "#00F0FF"
        self.brush_width = 8
        self.is_eraser = False
        self.eraser_width = 30

    def apply_ema(self, raw_x: float, raw_y: float) -> tuple[float, float]:
        if self.prev_smoothed is None:
            self.prev_smoothed = (raw_x, raw_y)
            return (raw_x, raw_y)

        dist = math.hypot(raw_x - self.prev_smoothed[0], raw_y - self.prev_smoothed[1])
        low_dist, high_dist = 0.0015, 0.020

        if dist <= low_dist:
            alpha = self.min_alpha
        elif dist >= high_dist:
            alpha = self.max_alpha
        else:
            t = (dist - low_dist) / (high_dist - low_dist)
            alpha = self.min_alpha + t * (self.max_alpha - self.min_alpha)

        smoothed_x = alpha * raw_x + (1.0 - alpha) * self.prev_smoothed[0]
        smoothed_y = alpha * raw_y + (1.0 - alpha) * self.prev_smoothed[1]
        self.prev_smoothed = (smoothed_x, smoothed_y)
        return (smoothed_x, smoothed_y)

    def process_point(self, raw_pt: tuple[float, float] | None, is_drawing: bool, gesture: str) -> dict:
        is_eraser_gesture = (gesture == "ERASER") or self.is_eraser

        if raw_pt is None:
            self.commit_active_stroke()
            self.prev_smoothed = None
            return {"is_writing": False, "point_count": 0}

        norm_x = max(0.0, min(1.0, raw_pt[0]))
        norm_y = max(0.0, min(1.0, raw_pt[1]))
        smoothed_x, smoothed_y = self.apply_ema(norm_x, norm_y)

        if not is_drawing and gesture != "ERASER":
            self.commit_active_stroke()
            return {"is_writing": False, "point_count": 0}

        color = "rgba(0,0,0,0)" if is_eraser_gesture else self.current_color
        width = self.eraser_width if is_eraser_gesture else self.brush_width

        if not self.is_writing or self.active_stroke is None:
            self.is_writing = True
            self.active_stroke = WebVectorStroke(color=color, width=width, is_eraser=is_eraser_gesture)
            self.active_stroke.add_point(smoothed_x, smoothed_y)
            return {"is_writing": True, "point_count": 1}

        last_pt = self.active_stroke.points[-1]
        dist = math.hypot(smoothed_x - last_pt["x"], smoothed_y - last_pt["y"])

        if dist < self.min_dist_threshold:
            return {"is_writing": True, "point_count": len(self.active_stroke.points)}

        step_size = self.interp_step if self.interp_step > 0 else 0.004
        num_steps = max(1, math.ceil(dist / step_size))

        for i in range(1, num_steps + 1):
            t = i / float(num_steps)
            interp_x = last_pt["x"] + t * (smoothed_x - last_pt["x"])
            interp_y = last_pt["y"] + t * (smoothed_y - last_pt["y"])
            self.active_stroke.add_point(interp_x, interp_y)

        return {"is_writing": True, "point_count": len(self.active_stroke.points)}

    def commit_active_stroke(self):
        if self.active_stroke and len(self.active_stroke.points) > 0:
            self.history.append(self.active_stroke)
            self.redo_stack.clear()
        self.active_stroke = None
        self.is_writing = False

    def undo(self) -> bool:
        if not self.history:
            return False
        stroke = self.history.pop()
        self.redo_stack.append(stroke)
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        stroke = self.redo_stack.pop()
        self.history.append(stroke)
        return True

    def clear(self):
        self.history.clear()
        self.redo_stack.clear()
        self.active_stroke = None
        self.is_writing = False


class TestWebCanvasEngine(unittest.TestCase):

    def setUp(self):
        self.engine = WebCanvasEngine()

    def test_initial_state(self):
        self.assertEqual(len(self.engine.history), 0)
        self.assertEqual(len(self.engine.redo_stack), 0)
        self.assertFalse(self.engine.is_writing)

    def test_single_stroke_lifecycle(self):
        # 1. Start drawing gesture
        res1 = self.engine.process_point((0.2, 0.3), is_drawing=True, gesture="DRAW")
        self.assertTrue(res1["is_writing"])
        self.assertEqual(res1["point_count"], 1)

        # 2. Move finger to continue stroke
        res2 = self.engine.process_point((0.25, 0.35), is_drawing=True, gesture="DRAW")
        self.assertTrue(res2["is_writing"])
        self.assertGreater(res2["point_count"], 1)

        # 3. Stop drawing gesture (e.g. HOVER) -> Stroke should commit to history
        res3 = self.engine.process_point((0.26, 0.36), is_drawing=False, gesture="HOVER")
        self.assertFalse(res3["is_writing"])
        self.assertEqual(len(self.engine.history), 1)
        self.assertEqual(len(self.engine.redo_stack), 0)

    def test_undo_redo_stack(self):
        # Create stroke 1
        self.engine.process_point((0.1, 0.1), is_drawing=True, gesture="DRAW")
        self.engine.process_point((0.2, 0.2), is_drawing=True, gesture="DRAW")
        self.engine.process_point((0.2, 0.2), is_drawing=False, gesture="HOVER")

        # Create stroke 2
        self.engine.process_point((0.5, 0.5), is_drawing=True, gesture="DRAW")
        self.engine.process_point((0.6, 0.6), is_drawing=True, gesture="DRAW")
        self.engine.process_point((0.6, 0.6), is_drawing=False, gesture="HOVER")

        self.assertEqual(len(self.engine.history), 2)

        # Undo stroke 2
        success = self.engine.undo()
        self.assertTrue(success)
        self.assertEqual(len(self.engine.history), 1)
        self.assertEqual(len(self.engine.redo_stack), 1)

        # Redo stroke 2
        success = self.engine.redo()
        self.assertTrue(success)
        self.assertEqual(len(self.engine.history), 2)
        self.assertEqual(len(self.engine.redo_stack), 0)

    def test_clear_canvas(self):
        self.engine.process_point((0.1, 0.1), is_drawing=True, gesture="DRAW")
        self.engine.process_point((0.2, 0.2), is_drawing=True, gesture="DRAW")
        self.engine.process_point((0.2, 0.2), is_drawing=False, gesture="HOVER")

        self.assertEqual(len(self.engine.history), 1)
        self.engine.clear()
        self.assertEqual(len(self.engine.history), 0)
        self.assertEqual(len(self.engine.redo_stack), 0)

    def test_eraser_stroke(self):
        res = self.engine.process_point((0.4, 0.4), is_drawing=False, gesture="ERASER")
        self.assertTrue(res["is_writing"])
        self.assertTrue(self.engine.active_stroke.is_eraser)

    def test_ema_smoothing_clamping(self):
        pt1 = self.engine.apply_ema(-0.5, 1.5)
        self.assertEqual(pt1, (-0.5, 1.5))
        
        # Second point smoothed with EMA
        pt2 = self.engine.apply_ema(0.5, 0.5)
        self.assertLess(pt2[0], 0.5)
        self.assertGreater(pt2[1], 0.5)


if __name__ == "__main__":
    unittest.main()
