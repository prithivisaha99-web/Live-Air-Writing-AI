"""MediaPipe Hand Tracking Engine using MediaPipe Tasks HandLandmarker VIDEO Mode with High-Sensitivity Tracking."""
import os
import time
import urllib.request
import logging
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

logger = logging.getLogger(__name__)

MODEL_FILENAME = "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


def ensure_model_file() -> str:
    """Ensure hand_landmarker.task model is available locally."""
    model_path = os.path.join(os.path.dirname(__file__), "..", MODEL_FILENAME)
    model_path = os.path.abspath(model_path)
    
    if not os.path.exists(model_path):
        logger.info(f"[Vision] Downloading MediaPipe HandLandmarker model to {model_path}...")
        try:
            urllib.request.urlretrieve(MODEL_URL, model_path)
            logger.info("[Vision] HandLandmarker model downloaded successfully.")
        except Exception as e:
            logger.error(f"[Vision] Failed to download hand_landmarker.task: {e}")
    return model_path


class HandTracker:
    """Encapsulates MediaPipe Tasks HandLandmarker in VIDEO RunningMode for continuous webcam tracking."""

    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20

    CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index finger
        (5, 9), (9, 10), (10, 11), (11, 12),   # Middle finger
        (9, 13), (13, 14), (14, 15), (15, 16), # Ring finger
        (13, 17), (17, 18), (18, 19), (19, 20),# Pinky finger
        (0, 17)                                # Palm base
    ]

    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.20,
        min_tracking_confidence: float = 0.20,
        draw_skeleton: bool = True
    ):
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.draw_skeleton = draw_skeleton
        self._frame_counter = 0
        
        self._start_time_ms = int(time.time() * 1000)
        self._last_timestamp_ms = 0

        # Grace period state for temporary landmark hold filter (100-150ms)
        self._last_valid_hand_data = None
        self._last_valid_timestamp_ms = 0
        self._held_frames_count = 0
        
        self.detector = None
        self._init_mediapipe()

    def _init_mediapipe(self) -> None:
        try:
            model_path = ensure_model_file()
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_hands=self.max_num_hands,
                min_hand_detection_confidence=self.min_detection_confidence,
                min_hand_presence_confidence=self.min_tracking_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            self.detector = vision.HandLandmarker.create_from_options(options)
            logger.info("[Vision] Backend: MediaPipe Tasks HandLandmarker (RunningMode.VIDEO) initialized ONCE")
            logger.info(f"[Vision] Debug Thresholds: detect={self.min_detection_confidence}, track={self.min_tracking_confidence}")
        except Exception as e:
            logger.error(f"[Vision] Failed to initialize MediaPipe HandLandmarker: {e}")
            self.detector = None

    def process_frame(self, frame_bgr: np.ndarray, flip_h: bool = True) -> tuple[np.ndarray, dict | None, int]:
        """
        Process a BGR frame with MediaPipe HandLandmarker in VIDEO mode with 150ms landmark hold filter.
        
        Args:
            frame_bgr: Original un-flipped BGR OpenCV camera frame.
            flip_h: If True, returns mirrored frame and display coordinates.

        Returns:
            processed_frame (np.ndarray): Frame with optional drawn visual skeleton.
            hand_data (dict | None): Landmark pixels and metadata for primary writing hand.
            hand_count (int): Total number of hands detected (0 or 1).
        """
        # Defensive video frame validation
        if (
            frame_bgr is None or
            not isinstance(frame_bgr, np.ndarray) or
            frame_bgr.size == 0 or
            frame_bgr.dtype != np.uint8 or
            len(frame_bgr.shape) != 3 or
            self.detector is None
        ):
            return frame_bgr, None, 0

        self._frame_counter += 1
        h, w, _ = frame_bgr.shape

        # Convert original BGR frame to RGB without pre-flipping before MediaPipe
        frame_rgb = np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # Monotonically increasing timestamp for VIDEO mode
        current_ms = int(time.time() * 1000) - self._start_time_ms
        if current_ms <= self._last_timestamp_ms:
            current_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = current_ms

        try:
            results = self.detector.detect_for_video(mp_image, current_ms)
        except Exception as e:
            logger.error(f"[Vision] Error during MediaPipe detect_for_video process: {e}")
            return frame_bgr, None, 0

        raw_hands_count = len(results.hand_landmarks) if (results and results.hand_landmarks) else 0

        if raw_hands_count >= 1:
            # Valid raw MediaPipe detection in current frame
            self._last_valid_timestamp_ms = current_ms
            self._held_frames_count = 0

            primary_landmarks = results.hand_landmarks[0]
            handedness_label = "Right"
            if results.handedness and len(results.handedness) > 0:
                handedness_label = results.handedness[0][0].category_name

            lm_pixel_list = []
            lm_norm_list = []

            for lm in primary_landmarks:
                norm_x = (1.0 - lm.x) if flip_h else lm.x
                norm_y = lm.y
                norm_z = lm.z

                cx = int(norm_x * w)
                cy = int(norm_y * h)

                lm_pixel_list.append((cx, cy))
                lm_norm_list.append((norm_x, norm_y, norm_z))

            hand_data = {
                "pixels": lm_pixel_list,      # List of (x_px, y_px)
                "landmarks": lm_norm_list,    # List of (x, y, z) normalized
                "handedness": handedness_label,
                "index_tip": lm_pixel_list[self.INDEX_TIP],
                "thumb_tip": lm_pixel_list[self.THUMB_TIP],
                "frame_size": (w, h)
            }
            self._last_valid_hand_data = hand_data
            valid_hand_count = 1
            landmark_age_ms = 0
        else:
            # MediaPipe returned 0 hands for raw frame -> Check landmark hold grace period (<= 150ms)
            landmark_age_ms = current_ms - self._last_valid_timestamp_ms if self._last_valid_timestamp_ms > 0 else 9999

            if self._last_valid_hand_data is not None and landmark_age_ms <= 150:
                self._held_frames_count += 1
                hand_data = self._last_valid_hand_data
                valid_hand_count = 1
                if self._held_frames_count == 1 or self._frame_counter % 30 == 0:
                    logger.info(f"[Vision] Temporary landmark hold: frame {self._held_frames_count} (age {landmark_age_ms} ms)")
            else:
                self._last_valid_hand_data = None
                self._held_frames_count = 0
                hand_data = None
                valid_hand_count = 0

        # Throttled debug logging as specified in Part 4
        if self._frame_counter % 30 == 0:
            logger.info(f"[Vision] Raw MediaPipe hands: {raw_hands_count}")
            logger.info(f"[Vision] Valid hand output: {valid_hand_count}")
            logger.info(f"[Vision] Landmark age: {landmark_age_ms} ms")

        output_frame = cv2.flip(frame_bgr, 1) if flip_h else frame_bgr.copy()
        if self.draw_skeleton and hand_data is not None and "pixels" in hand_data:
            self._render_futuristic_skeleton(output_frame, hand_data["pixels"])

        return output_frame, hand_data, valid_hand_count

    def _render_futuristic_skeleton(self, frame: np.ndarray, lm_pixels: list[tuple[int, int]]) -> None:
        """Render high-tech neon cybernetic hand skeleton onto the image frame."""
        for start_idx, end_idx in self.CONNECTIONS:
            pt1 = lm_pixels[start_idx]
            pt2 = lm_pixels[end_idx]
            cv2.line(frame, pt1, pt2, (255, 230, 0), 3, cv2.LINE_AA)
            cv2.line(frame, pt1, pt2, (255, 255, 255), 1, cv2.LINE_AA)

        for idx, (x, y) in enumerate(lm_pixels):
            if idx == self.INDEX_TIP:
                cv2.circle(frame, (x, y), 10, (255, 180, 0), 2, cv2.LINE_AA)
                cv2.circle(frame, (x, y), 5, (0, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, (x, y), 2, (255, 255, 255), -1, cv2.LINE_AA)
            elif idx in (self.THUMB_TIP, self.MIDDLE_TIP, self.RING_TIP, self.PINKY_TIP):
                cv2.circle(frame, (x, y), 5, (255, 0, 180), -1, cv2.LINE_AA)
                cv2.circle(frame, (x, y), 2, (255, 255, 255), -1, cv2.LINE_AA)
            else:
                cv2.circle(frame, (x, y), 3, (200, 200, 0), -1, cv2.LINE_AA)

    def set_draw_skeleton(self, draw: bool) -> None:
        self.draw_skeleton = draw

    def close(self) -> None:
        if self.detector:
            self.detector.close()
            self.detector = None
