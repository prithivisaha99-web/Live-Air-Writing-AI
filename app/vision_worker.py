"""Asynchronous Vision Worker Thread for OpenCV, MediaPipe, Gesture, and Air Writing."""
import time
import logging
import cv2
import numpy as np

from PySide6.QtCore import QThread, Signal, Slot, QMutex, QMutexLocker

from app.hand_tracking import HandTracker
from app.gesture_detection import GestureDetector, GestureType, GestureMode
from app.air_writing import AirWritingEngine

logger = logging.getLogger(__name__)


def list_available_cameras(max_tested: int = 5) -> list[dict[str, int | str]]:
    """Enumerate accessible camera indices on the system."""
    available = []
    for idx in range(max_tested):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            available.append({
                "index": idx,
                "name": f"Camera {idx}"
            })
            cap.release()
    if not available:
        available.append({"index": 0, "name": "Default Camera (0)"})
    return available


class VisionWorkerThread(QThread):
    """
    Dedicated background worker thread for webcam frame capture,
    MediaPipe hand tracking, gesture detection, and stroke calculation.
    """

    frame_processed = Signal(dict)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        flip_h: bool = True,
        draw_skeleton: bool = True,
        gesture_mode: GestureMode = GestureMode.POINTING,
        smoothing_factor: float = 0.65,
        parent=None
    ):
        super().__init__(parent)
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.flip_h = flip_h

        # Initialize HandTracker, GestureDetector, AirWritingEngine ONCE
        self.hand_tracker = HandTracker(draw_skeleton=draw_skeleton)
        self.gesture_detector = GestureDetector(mode=gesture_mode)
        self.air_engine = AirWritingEngine(smoothing_factor=smoothing_factor)

        self._running = False
        self._paused = False
        self._mutex = QMutex()
        self.cap = None
        
        self.camera_fps = 0.0
        self.vision_fps = 0.0
        self._frame_counter = 0

    def set_camera_index(self, index: int) -> None:
        with QMutexLocker(self._mutex):
            self.camera_index = index
            if self._running and self.cap:
                self._reopen_camera()

    def set_resolution(self, width: int, height: int) -> None:
        with QMutexLocker(self._mutex):
            self.width = width
            self.height = height
            if self.cap and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def set_flip(self, flip_h: bool) -> None:
        with QMutexLocker(self._mutex):
            self.flip_h = flip_h

    def set_draw_skeleton(self, draw: bool) -> None:
        with QMutexLocker(self._mutex):
            self.hand_tracker.set_draw_skeleton(draw)

    def set_gesture_mode(self, mode: GestureMode) -> None:
        with QMutexLocker(self._mutex):
            self.gesture_detector.set_mode(mode)

    def set_smoothing(self, alpha: float) -> None:
        with QMutexLocker(self._mutex):
            self.air_engine.set_smoothing(alpha)

    def _reopen_camera(self) -> bool:
        if self.cap:
            self.cap.release()
            self.cap = None

        self.status_changed.emit("Initializing Camera...")

        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            err_msg = (
                f"Unable to access camera (Index {self.camera_index}). "
                "Please check webcam connection or privacy settings."
            )
            logger.error(f"[Vision] {err_msg}")
            self.error_occurred.emit(err_msg)
            self.status_changed.emit("Camera Error")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, 30)

        self.cap = cap
        self.status_changed.emit("Camera Ready")
        return True

    def run(self) -> None:
        logger.info("[Vision] Worker started")
        with QMutexLocker(self._mutex):
            self._running = True

        if not self._reopen_camera():
            with QMutexLocker(self._mutex):
                self._running = False
            logger.info("[Vision] Worker stopped due to camera open failure")
            return

        last_cam_time = time.perf_counter()

        while True:
            with QMutexLocker(self._mutex):
                if not self._running:
                    break
                paused = self._paused

            if paused:
                self.msleep(30)
                continue

            t_read_start = time.perf_counter()
            ret, frame = self.cap.read()

            # DEFENSIVE VALIDATION: Verify frame before flip/processing
            if not ret or frame is None or not isinstance(frame, np.ndarray) or frame.size == 0 or len(frame.shape) != 3:
                self.msleep(10)
                continue

            t_read_end = time.perf_counter()
            cam_delta = t_read_end - last_cam_time
            last_cam_time = t_read_end
            if cam_delta > 0:
                self.camera_fps = 0.85 * self.camera_fps + 0.15 * (1.0 / cam_delta) if self.camera_fps > 0 else 1.0 / cam_delta

            self._frame_counter += 1

            t_proc_start = time.perf_counter()

            # 1. MediaPipe HandLandmarker Task process (background thread!)
            # Pass original un-flipped frame; hand_tracker handles display mirroring via flip_h
            skeleton_frame, hand_data, hand_count = self.hand_tracker.process_frame(frame, flip_h=self.flip_h)

            # 2. Gesture Detection & Finger States Diagnostic
            gesture = self.gesture_detector.update(hand_data)
            finger_states = self.gesture_detector.get_finger_states(hand_data)

            # 3. Extract normalized index fingertip coordinates
            raw_norm_pt = None
            if hand_data and "landmarks" in hand_data and len(hand_data["landmarks"]) > HandTracker.INDEX_TIP:
                lm8 = hand_data["landmarks"][HandTracker.INDEX_TIP]
                raw_norm_pt = (float(lm8[0]), float(lm8[1]))

            is_drawing_gesture = (gesture == GestureType.DRAW and hand_count > 0)
            frame_size = (self.width, self.height)

            finished_stroke, new_points, is_currently_drawing, smooth_norm_pt, interp_count = self.air_engine.process_point(
                raw_norm_pt, frame_size, is_drawing_gesture
            )

            raw_count = 1 if raw_norm_pt is not None else 0
            active_stroke_pts = len(self.air_engine.current_stroke_points)

            t_proc_end = time.perf_counter()
            proc_delta = t_proc_end - t_proc_start
            if proc_delta > 0:
                self.vision_fps = 0.85 * self.vision_fps + 0.15 * (1.0 / proc_delta) if self.vision_fps > 0 else 1.0 / proc_delta

            # Throttled Diagnostic Logging (once every 60 frames)
            if self._frame_counter % 60 == 0:
                logger.info(
                    f"[StrokeTrace] Raw pts/frame: {raw_count} | Interp pts/frame: {interp_count} | "
                    f"Active stroke points: {active_stroke_pts} | Gesture: {gesture.name}"
                )

            # 4. Emit processed result package to Qt GUI thread
            self.frame_processed.emit({
                "frame": skeleton_frame,
                "hand_data": hand_data,
                "hand_count": hand_count,
                "gesture": gesture,
                "finger_states": finger_states,
                "raw_index": raw_norm_pt,
                "smooth_index": smooth_norm_pt,
                "is_drawing": is_currently_drawing,
                "new_points": new_points,
                "finished_stroke": finished_stroke,
                "raw_count": raw_count,
                "interp_count": interp_count,
                "stroke_points": active_stroke_pts,
                "camera_fps": round(self.camera_fps, 1),
                "vision_fps": round(self.vision_fps, 1)
            })

            # Target ~30 FPS loop spacing
            self.msleep(8)

        if self.cap:
            self.cap.release()
            self.cap = None
        self.hand_tracker.close()
        logger.info("[Vision] Worker stopped")
        self.status_changed.emit("Camera Stopped")

    def stop(self) -> None:
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(1500)

    def pause(self) -> None:
        with QMutexLocker(self._mutex):
            self._paused = True

    def resume(self) -> None:
        with QMutexLocker(self._mutex):
            self._paused = False
