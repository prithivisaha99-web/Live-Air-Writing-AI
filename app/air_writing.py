"""Air Writing Engine with Strict State Machine, Continuous EMA Smoothing, and High-Density Linear Stroke Interpolation."""
import math
import logging

logger = logging.getLogger(__name__)


class StrokePoint:
    """Represents a single normalized 2D point along a handwriting stroke (0.0 to 1.0)."""
    def __init__(self, x: float, y: float, pressure: float = 1.0):
        self.x = max(0.0, min(1.0, float(x)))
        self.y = max(0.0, min(1.0, float(y)))
        self.pressure = pressure

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


class AirWritingEngine:
    """Processes raw index fingertip normalized coordinates into interpolated, smoothed continuous stroke paths."""

    def __init__(
        self,
        smoothing_factor: float = 0.65,
        interp_step_norm: float = 0.004,  # ~2.5 pixels spacing for dense continuous ink
        min_alpha: float = 0.20,
        max_alpha: float = 0.80,
        min_dist_threshold: float = 0.0008  # ~0.5px threshold to suppress stationary jitter
    ):
        self.smoothing_factor = smoothing_factor
        self.interp_step = interp_step_norm
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.min_dist_threshold = min_dist_threshold
        
        self._prev_smoothed: tuple[float, float] | None = None
        self.current_stroke_points: list[StrokePoint] = []
        self.is_writing = False

    def set_smoothing(self, alpha: float) -> None:
        self.smoothing_factor = max(0.1, min(0.9, alpha))
        self.max_alpha = max(self.min_alpha + 0.1, self.smoothing_factor)

    def _apply_ema(self, new_norm_pt: tuple[float, float]) -> tuple[float, float]:
        """Apply velocity-adaptive Exponential Moving Average smoothing to normalized (x, y) coordinates."""
        if self._prev_smoothed is None:
            self._prev_smoothed = new_norm_pt
            return new_norm_pt

        # Calculate raw frame-to-frame displacement
        raw_dist = math.hypot(new_norm_pt[0] - self._prev_smoothed[0], new_norm_pt[1] - self._prev_smoothed[1])

        # Velocity-adaptive alpha:
        # Small displacement (slow movement / stationary tremor) -> lower alpha (0.25) for strong tremor suppression.
        # Large displacement (fast movement) -> higher alpha (0.80) for low-latency responsiveness.
        low_dist, high_dist = 0.0015, 0.020
        if raw_dist <= low_dist:
            alpha = self.min_alpha
        elif raw_dist >= high_dist:
            alpha = self.max_alpha
        else:
            t = (raw_dist - low_dist) / (high_dist - low_dist)
            alpha = self.min_alpha + t * (self.max_alpha - self.min_alpha)

        smoothed_x = alpha * new_norm_pt[0] + (1.0 - alpha) * self._prev_smoothed[0]
        smoothed_y = alpha * new_norm_pt[1] + (1.0 - alpha) * self._prev_smoothed[1]
        
        self._prev_smoothed = (smoothed_x, smoothed_y)
        return (smoothed_x, smoothed_y)

    def process_point(
        self,
        raw_pt: tuple[float, float] | tuple[int, int] | None,
        frame_size: tuple[int, int] = (640, 480),
        is_drawing_gesture: bool = False
    ) -> tuple[list[StrokePoint] | None, list[tuple[float, float]], bool, tuple[float, float] | None, int]:
        """
        Process a new frame point with strict state checking.
        
        Returns:
            finished_stroke (list[StrokePoint] | None): Completed stroke points when DRAW ends or hand lost.
            new_points (list[tuple[float, float]]): ALL new normalized points (including interpolated ones) added this frame.
            is_currently_drawing (bool): True if actively writing.
            smooth_pt (tuple[float, float] | None): Latest smoothed normalized coordinate.
            interp_count (int): Number of interpolated step points generated this frame.
        """
        w, h = frame_size

        # If raw_pt is None or invalid, hand tracking is lost -> terminate stroke
        if raw_pt is None:
            finished_stroke = None
            if self.is_writing and self.current_stroke_points:
                finished_stroke = list(self.current_stroke_points)
            self.reset()
            return finished_stroke, [], False, None, 0

        # Handle both normalized (0..1) and pixel input defensively
        if isinstance(raw_pt[0], int) or raw_pt[0] > 1.0 or raw_pt[1] > 1.0:
            if w > 0 and h > 0:
                norm_x = raw_pt[0] / float(w)
                norm_y = raw_pt[1] / float(h)
            else:
                norm_x, norm_y = 0.0, 0.0
        else:
            norm_x, norm_y = float(raw_pt[0]), float(raw_pt[1])

        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Always update smoothed position if hand is visible
        smoothed_norm = self._apply_ema((norm_x, norm_y))

        # STATE RULE 1: If gesture is NOT DRAW -> END ACTIVE STROKE
        if not is_drawing_gesture:
            finished_stroke = None
            if self.is_writing and self.current_stroke_points:
                finished_stroke = list(self.current_stroke_points)
            self.is_writing = False
            self.current_stroke_points = []
            return finished_stroke, [], False, smoothed_norm, 0

        # STATE RULE 2: Start new stroke if writing was not active
        if not self.is_writing or not self.current_stroke_points:
            self.is_writing = True
            first_pt = StrokePoint(smoothed_norm[0], smoothed_norm[1])
            self.current_stroke_points = [first_pt]
            return None, [first_pt.to_tuple()], True, smoothed_norm, 0

        # STATE RULE 3: Active stroke continuing -> Check distance to avoid micro-jitter points
        last_pt = self.current_stroke_points[-1]
        dist = math.hypot(smoothed_norm[0] - last_pt.x, smoothed_norm[1] - last_pt.y)

        if dist < self.min_dist_threshold:
            # Suppress redundant micro-point when virtually stationary
            return None, [], True, smoothed_norm, 0

        # STROKE INTERPOLATION (Requirement 4):
        # Calculate number of steps based on 2-4 pixel spacing (~0.004 normalized step)
        step_size = self.interp_step if self.interp_step > 0 else 0.004
        num_steps = max(1, math.ceil(dist / step_size))

        new_tuples: list[tuple[float, float]] = []
        for i in range(1, num_steps + 1):
            t = i / float(num_steps)
            interp_x = last_pt.x + t * (smoothed_norm[0] - last_pt.x)
            interp_y = last_pt.y + t * (smoothed_norm[1] - last_pt.y)
            sp = StrokePoint(interp_x, interp_y)
            self.current_stroke_points.append(sp)
            new_tuples.append(sp.to_tuple())

        interp_count = max(0, len(new_tuples) - 1)
        return None, new_tuples, True, smoothed_norm, interp_count

    def reset(self) -> None:
        self.is_writing = False
        self.current_stroke_points = []
        self._prev_smoothed = None
