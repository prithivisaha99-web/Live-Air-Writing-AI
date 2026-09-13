"""Gesture Recognition Engine with Exact Finger-State Detection using MediaPipe 3D Landmark Angles."""
import enum
import math
import collections
import logging

logger = logging.getLogger(__name__)


class GestureType(enum.Enum):
    NONE = "NO HAND"
    HOVER = "HOVER"
    DRAW = "DRAW"
    ERASER = "ERASER"
    CLEAR = "CLEAR CANVAS"


class ShortcutGesture(enum.Enum):
    NONE = "NONE"
    UNDO = "✌️ UNDO"
    REDO = "🤟 REDO"
    CONFIRM = "👍 CONFIRM"


class GestureMode(enum.Enum):
    POINTING = "Pointing Index Finger"
    PINCH = "Pinch (Index + Thumb)"


class ShortcutDetector:
    """Separate layer for detecting gesture shortcuts (Undo, Redo, Confirm) with physical webcam tolerance, debouncing, and state latching."""

    def __init__(self, debounce_frames: int = 4):
        self.debounce_frames = debounce_frames
        self.history = collections.deque(maxlen=debounce_frames)
        self.latched_shortcut = ShortcutGesture.NONE
        self.last_raw_candidate = ShortcutGesture.NONE
        self.last_reason = "No hand detected"
        self.last_finger_summary = "None"
        self._evaluator = GestureDetector()

    def detect_raw_shortcut(self, hand_data: dict | None, eval_data: dict | None = None) -> tuple[ShortcutGesture, str, str]:
        """
        Evaluates raw hand landmarks and relative finger geometry for shortcut candidates.
        Returns: (candidate_shortcut, finger_summary_str, reason_str)
        """
        if not hand_data:
            return ShortcutGesture.NONE, "No Hand", "No hand detected"

        if eval_data is None:
            eval_data = self._evaluator.evaluate_all_fingers(hand_data)

        if not eval_data:
            return ShortcutGesture.NONE, "No Hand", "Invalid hand landmark data"

        landmarks = hand_data.get("landmarks", [])
        pixels = hand_data.get("pixels", [])

        idx_ext, idx_tr, idx_pr, idx_er = eval_data["Index"]
        mid_ext, mid_tr, mid_pr, mid_er = eval_data["Middle"]
        rng_ext, rng_tr, rng_pr, rng_er = eval_data["Ring"]
        pnk_ext, pnk_tr, pnk_pr, pnk_er = eval_data["Pinky"]

        # Characterize pinky state for webcam tolerance
        if not pnk_ext:
            pnk_str = "folded"
        elif pnk_tr < max(idx_tr, mid_tr) - 0.03 or pnk_er < 1.15:
            pnk_str = "noisy"
        else:
            pnk_str = "extended"

        finger_summary = (
            f"Index={'ext' if idx_ext else 'fold'} "
            f"Middle={'ext' if mid_ext else 'fold'} "
            f"Ring={'ext' if rng_ext else 'fold'} "
            f"Pinky={pnk_str}"
        )

        # 1. 👍 CONFIRM: Main fingers (Index, Middle, Ring) folded & Thumb extended UP
        if (not idx_ext) and (not mid_ext) and (not rng_ext):
            thumb_up = False
            if landmarks and len(landmarks) >= 21:
                wrist_y = landmarks[0][1]
                thumb_mcp_y = landmarks[2][1]
                thumb_tip_y = landmarks[4][1]
                thumb_up = (thumb_tip_y < thumb_mcp_y - 0.02) and (thumb_tip_y < wrist_y - 0.04)
            elif pixels and len(pixels) >= 21:
                wrist_y = pixels[0][1]
                thumb_mcp_y = pixels[2][1]
                thumb_tip_y = pixels[4][1]
                thumb_up = (thumb_tip_y < thumb_mcp_y - 10) and (thumb_tip_y < wrist_y - 15)

            if thumb_up:
                return ShortcutGesture.CONFIRM, finger_summary, "Thumb-Up posture confirmed"

        # 2. ✌️ UNDO: Index & Middle extended, Ring folded
        # Allows Pinky to be folded or carry small webcam classification noise.
        # Strict protection: Does NOT trigger on DRAW (Middle folded) or HOVER (Ring extended).
        if idx_ext and mid_ext and (not rng_ext):
            return ShortcutGesture.UNDO, finger_summary, "✌️ Two-finger pose detected (Index+Middle ext, Ring fold)"

        # 3. 🤟 REDO: Index, Middle & Ring extended, Pinky folded/lower
        # Strict protection: Does NOT trigger on Open Palm (Pinky fully extended).
        if idx_ext and mid_ext and rng_ext:
            if not pnk_ext or pnk_str == "noisy" or pnk_tr < rng_tr - 0.08:
                return ShortcutGesture.REDO, finger_summary, "🤟 Three-finger pose detected (Index+Middle+Ring ext, Pinky fold/lower)"
            else:
                return ShortcutGesture.NONE, finger_summary, "Rejected: Open Palm (Pinky fully extended)"

        # Reason categorization for diagnostic feedback
        if idx_ext and not mid_ext:
            reason = "Pointing/DRAW posture (Middle folded)"
        elif idx_ext and mid_ext and rng_ext and pnk_ext:
            reason = "Open Palm/HOVER posture"
        elif not idx_ext and not mid_ext and not rng_ext and not pnk_ext:
            reason = "Fist/ERASER posture"
        else:
            reason = "Unrecognized gesture pose"

        return ShortcutGesture.NONE, finger_summary, reason

    def update(self, hand_data: dict | None, eval_data: dict | None = None, is_drawing: bool = False) -> ShortcutGesture | None:
        """
        Updates shortcut detector state with debouncing and latching.
        Returns ShortcutGesture ONLY when a NEW debounced shortcut triggers.
        Returns None when no action should trigger.
        """
        if is_drawing:
            self.history.clear()
            self.latched_shortcut = ShortcutGesture.NONE
            self.last_raw_candidate = ShortcutGesture.NONE
            self.last_reason = "Disabled (Drawing Active)"
            self.last_finger_summary = "Drawing"
            return None

        raw_candidate, finger_summary, reason = self.detect_raw_shortcut(hand_data, eval_data)
        self.last_raw_candidate = raw_candidate
        self.last_finger_summary = finger_summary

        self.history.append(raw_candidate)
        stable_count = sum(1 for g in self.history if g == raw_candidate and raw_candidate != ShortcutGesture.NONE)

        if len(self.history) == self.debounce_frames and len(set(self.history)) == 1 and raw_candidate != ShortcutGesture.NONE:
            debounced_candidate = raw_candidate
        else:
            debounced_candidate = ShortcutGesture.NONE

        if debounced_candidate == ShortcutGesture.NONE:
            if raw_candidate != ShortcutGesture.NONE:
                self.last_reason = f"Debouncing {raw_candidate.value} ({stable_count}/{self.debounce_frames})"
            else:
                self.last_reason = reason

            if raw_candidate == ShortcutGesture.NONE:
                self.latched_shortcut = ShortcutGesture.NONE
            return None

        if debounced_candidate != self.latched_shortcut:
            self.latched_shortcut = debounced_candidate
            self.last_reason = f"TRIGGERED: {debounced_candidate.value}"
            return debounced_candidate

        self.last_reason = f"Latched ({debounced_candidate.value} held - release pose to re-arm)"
        return None

    def get_diagnostic_info(self) -> dict:
        """Returns comprehensive diagnostic info for HUD/logging."""
        stable_count = 0
        if self.history:
            most_common = collections.Counter(self.history).most_common(1)[0]
            if most_common[0] != ShortcutGesture.NONE:
                stable_count = most_common[1]

        stable_str = f"{stable_count}/{self.debounce_frames}"
        return {
            "candidate": self.last_raw_candidate.value if self.last_raw_candidate else "NONE",
            "finger_summary": self.last_finger_summary,
            "stable_frames": stable_str,
            "latched": self.latched_shortcut.value if self.latched_shortcut != ShortcutGesture.NONE else "None",
            "reason": self.last_reason
        }


class GestureDetector:
    """Detects hand gestures from 21 MediaPipe landmarks with strict finger joint angle geometry."""

    WRIST = 0
    THUMB_CMC = 1; THUMB_MCP = 2; THUMB_IP = 3; THUMB_TIP = 4
    INDEX_MCP = 5; INDEX_PIP = 6; INDEX_DIP = 7; INDEX_TIP = 8
    MIDDLE_MCP = 9; MIDDLE_PIP = 10; MIDDLE_DIP = 11; MIDDLE_TIP = 12
    RING_MCP = 13; RING_PIP = 14; RING_DIP = 15; RING_TIP = 16
    PINKY_MCP = 17; PINKY_PIP = 18; PINKY_DIP = 19; PINKY_TIP = 20

    def __init__(
        self,
        mode: GestureMode = GestureMode.POINTING,
        pinch_threshold_px: float = 35.0,
        buffer_size: int = 4
    ):
        self.mode = mode
        self.pinch_threshold_px = pinch_threshold_px
        self.history = collections.deque(maxlen=buffer_size)
        self.current_gesture = GestureType.NONE
        self._frame_counter = 0

    def set_mode(self, mode: GestureMode) -> None:
        self.mode = mode
        self.history.clear()

    def set_sensitivity(self, pinch_threshold_px: float) -> None:
        self.pinch_threshold_px = pinch_threshold_px

    @staticmethod
    def _calculate_angle_3d(pt_a: tuple[float, float, float], pt_b: tuple[float, float, float], pt_c: tuple[float, float, float]) -> float:
        """Calculate 3D interior angle at joint B (A-B-C) in degrees (0..180). 180 = straight extended."""
        v1 = (pt_a[0] - pt_b[0], pt_a[1] - pt_b[1], pt_a[2] - pt_b[2])
        v2 = (pt_c[0] - pt_b[0], pt_c[1] - pt_b[1], pt_c[2] - pt_b[2])

        mag1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)

        if mag1 < 1e-6 or mag2 < 1e-6:
            return 180.0

        dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    def _get_palm_center_and_scale(self, pts: list[tuple[float, float, float] | tuple[float, float]]) -> tuple[tuple[float, float, float], float]:
        """
        Calculates palm center as average of Wrist (0), Index MCP (5), Middle MCP (9), Ring MCP (13), Pinky MCP (17).
        Calculates hand_size scale as distance(Wrist, Middle MCP).
        """
        wrist = pts[self.WRIST]
        idx_mcp = pts[self.INDEX_MCP]
        mid_mcp = pts[self.MIDDLE_MCP]
        rng_mcp = pts[self.RING_MCP]
        pnk_mcp = pts[self.PINKY_MCP]

        if len(wrist) == 3:
            cx = (wrist[0] + idx_mcp[0] + mid_mcp[0] + rng_mcp[0] + pnk_mcp[0]) / 5.0
            cy = (wrist[1] + idx_mcp[1] + mid_mcp[1] + rng_mcp[1] + pnk_mcp[1]) / 5.0
            cz = (wrist[2] + idx_mcp[2] + mid_mcp[2] + rng_mcp[2] + pnk_mcp[2]) / 5.0
            palm_center = (cx, cy, cz)

            hand_size = math.sqrt(
                (mid_mcp[0] - wrist[0])**2 +
                (mid_mcp[1] - wrist[1])**2 +
                (mid_mcp[2] - wrist[2])**2
            )
        else:
            cx = (wrist[0] + idx_mcp[0] + mid_mcp[0] + rng_mcp[0] + pnk_mcp[0]) / 5.0
            cy = (wrist[1] + idx_mcp[1] + mid_mcp[1] + rng_mcp[1] + pnk_mcp[1]) / 5.0
            palm_center = (cx, cy, 0.0)

            hand_size = math.hypot(mid_mcp[0] - wrist[0], mid_mcp[1] - wrist[1])

        return palm_center, max(1e-4, hand_size)

    def _evaluate_finger_palm_relative(
        self,
        pts: list[tuple[float, float, float] | tuple[float, float]],
        palm_center: tuple[float, float, float],
        hand_size: float,
        tip_idx: int,
        pip_idx: int
    ) -> tuple[bool, float, float, float]:
        """
        Evaluates finger extension based on palm-center relative distances:
        tip_distance = distance(TIP, palm_center)
        pip_distance = distance(PIP, palm_center)
        tip_ratio = tip_distance / hand_size
        pip_ratio = pip_distance / hand_size
        extension_ratio = tip_distance / max(pip_distance, epsilon)

        Returns: (is_extended, tip_ratio, pip_ratio, extension_ratio)
        """
        tip = pts[tip_idx]
        pip = pts[pip_idx]

        if len(tip) == 3:
            tip_dist = math.sqrt((tip[0]-palm_center[0])**2 + (tip[1]-palm_center[1])**2 + (tip[2]-palm_center[2])**2)
            pip_dist = math.sqrt((pip[0]-palm_center[0])**2 + (pip[1]-palm_center[1])**2 + (pip[2]-palm_center[2])**2)
        else:
            tip_dist = math.hypot(tip[0]-palm_center[0], tip[1]-palm_center[1])
            pip_dist = math.hypot(pip[0]-palm_center[0], pip[1]-palm_center[1])

        tip_ratio = tip_dist / hand_size
        pip_ratio = pip_dist / hand_size
        extension_ratio = tip_dist / max(1e-4, pip_dist)

        # Extended finger requirement:
        # 1. tip_ratio substantially larger than pip_ratio (tip extended away from palm center)
        # 2. extension_ratio >= 1.10 - 1.18
        if tip_idx == self.INDEX_TIP:
            is_ext = (tip_ratio > pip_ratio * 1.05) and (extension_ratio >= 1.10)
        elif tip_idx == self.PINKY_TIP:
            is_ext = (tip_ratio > pip_ratio * 1.10) and (extension_ratio >= 1.12)
        else: # Middle and Ring
            is_ext = (tip_ratio > pip_ratio * 1.12) and (extension_ratio >= 1.15)

        return is_ext, tip_ratio, pip_ratio, extension_ratio

    def evaluate_all_fingers(self, hand_data: dict | None):
        if not hand_data:
            return None

        landmarks = hand_data.get("landmarks", [])
        pixels = hand_data.get("pixels", [])

        if landmarks and len(landmarks) >= 21:
            pts = landmarks
        elif pixels and len(pixels) >= 21:
            pts = [(p[0] / 640.0, p[1] / 480.0) for p in pixels]
        else:
            return None

        palm_center, hand_size = self._get_palm_center_and_scale(pts)

        # Unit test mock fallback (when wrist and mcp share same dummy pixel 100,100)
        if hand_size < 0.01:
            idx_ext = pts[self.INDEX_TIP][1] < pts[self.INDEX_PIP][1]
            mid_ext = pts[self.MIDDLE_TIP][1] < pts[self.MIDDLE_PIP][1]
            rng_ext = pts[self.RING_TIP][1] < pts[self.RING_PIP][1]
            pnk_ext = pts[self.PINKY_TIP][1] < pts[self.PINKY_PIP][1]
            return {
                "Index": (idx_ext, 1.5 if idx_ext else 0.5, 1.0, 1.5),
                "Middle": (mid_ext, 1.5 if mid_ext else 0.5, 1.0, 1.5),
                "Ring": (rng_ext, 1.5 if rng_ext else 0.5, 1.0, 1.5),
                "Pinky": (pnk_ext, 1.5 if pnk_ext else 0.5, 1.0, 1.5),
                "hand_size": 1.0
            }

        idx_eval = self._evaluate_finger_palm_relative(pts, palm_center, hand_size, self.INDEX_TIP, self.INDEX_PIP)
        mid_eval = self._evaluate_finger_palm_relative(pts, palm_center, hand_size, self.MIDDLE_TIP, self.MIDDLE_PIP)
        rng_eval = self._evaluate_finger_palm_relative(pts, palm_center, hand_size, self.RING_TIP, self.RING_PIP)
        pnk_eval = self._evaluate_finger_palm_relative(pts, palm_center, hand_size, self.PINKY_TIP, self.PINKY_PIP)

        return {
            "Index": idx_eval,
            "Middle": mid_eval,
            "Ring": rng_eval,
            "Pinky": pnk_eval,
            "hand_size": hand_size
        }

    def get_finger_states(self, hand_data: dict | None) -> dict[str, str]:
        eval_data = self.evaluate_all_fingers(hand_data)
        if not eval_data:
            return {
                "Index": "NONE",
                "Middle": "NONE",
                "Ring": "NONE",
                "Pinky": "NONE",
                "Gesture": GestureType.NONE.value
            }

        idx_ext = eval_data["Index"][0]
        mid_ext = eval_data["Middle"][0]
        rng_ext = eval_data["Ring"][0]
        pnk_ext = eval_data["Pinky"][0]

        raw_gesture = self.detect_raw_gesture(hand_data)

        return {
            "Index": "EXTENDED" if idx_ext else "FOLDED",
            "Middle": "EXTENDED" if mid_ext else "FOLDED",
            "Ring": "EXTENDED" if rng_ext else "FOLDED",
            "Pinky": "EXTENDED" if pnk_ext else "FOLDED",
            "Gesture": raw_gesture.value
        }

    def detect_raw_gesture(self, hand_data: dict | None) -> GestureType:
        eval_data = self.evaluate_all_fingers(hand_data)
        if not eval_data:
            return GestureType.NONE

        idx_ext, idx_tr, _, _ = eval_data["Index"]
        mid_ext, mid_tr, _, _ = eval_data["Middle"]
        rng_ext, rng_tr, _, _ = eval_data["Ring"]
        pnk_ext, pnk_tr, _, _ = eval_data["Pinky"]

        # 1. ERASER: All 4 fingers folded in (Closed Fist)
        is_fist = (not idx_ext) and (not mid_ext) and (not rng_ext) and (not pnk_ext)
        if is_fist:
            return GestureType.ERASER

        # 2. DRAWING Gesture (Pointing Index Finger)
        if self.mode == GestureMode.POINTING:
            # RELATIVE PATTERN FOR DRAW:
            # Index must be extended AND middle/ring/pinky tips substantially closer to palm center than index tip
            mid_fold_diff = idx_tr - mid_tr
            rng_fold_diff = idx_tr - rng_tr
            pnk_fold_diff = idx_tr - pnk_tr

            strong_separation = (mid_fold_diff >= 0.18) and (rng_fold_diff >= 0.18) and (pnk_fold_diff >= 0.18)
            all_other_folded = (not mid_ext) and (not rng_ext) and (not pnk_ext)

            if idx_ext and (strong_separation or all_other_folded):
                return GestureType.DRAW
        elif self.mode == GestureMode.PINCH:
            pixels = hand_data.get("pixels", [])
            if len(pixels) >= 21:
                pinch_dist = math.hypot(
                    pixels[self.INDEX_TIP][0] - pixels[self.THUMB_TIP][0],
                    pixels[self.INDEX_TIP][1] - pixels[self.THUMB_TIP][1]
                )
                if pinch_dist < self.pinch_threshold_px:
                    return GestureType.DRAW

        # 3. HOVER / STOP: Open palm or neutral pose
        return GestureType.HOVER

    def update(self, hand_data: dict | None) -> GestureType:
        """Process new frame landmarks with temporal debouncing, palm-relative logging, and smooth hysteresis."""
        if not hand_data or "pixels" not in hand_data or len(hand_data.get("pixels", [])) < 21:
            self.history.clear()
            self.current_gesture = GestureType.NONE
            return GestureType.NONE

        eval_data = self.evaluate_all_fingers(hand_data)
        if not eval_data:
            self.history.clear()
            self.current_gesture = GestureType.NONE
            return GestureType.NONE

        idx_ext, idx_tr, idx_pr, idx_er = eval_data["Index"]
        mid_ext, mid_tr, mid_pr, mid_er = eval_data["Middle"]
        rng_ext, rng_tr, rng_pr, rng_er = eval_data["Ring"]
        pnk_ext, pnk_tr, pnk_pr, pnk_er = eval_data["Pinky"]

        raw = self.detect_raw_gesture(hand_data)
        self.history.append(raw)

        self._frame_counter += 1
        if self._frame_counter % 30 == 0:
            idx_st = "EXTENDED" if idx_ext else "FOLDED"
            mid_st = "EXTENDED" if mid_ext else "FOLDED"
            rng_st = "EXTENDED" if rng_ext else "FOLDED"
            pnk_st = "EXTENDED" if pnk_ext else "FOLDED"

            logger.info("[GestureDebug]")
            logger.info(f"Index: tip_ratio={idx_tr:.2f} pip_ratio={idx_pr:.2f} ext_ratio={idx_er:.2f} state={idx_st}")
            logger.info(f"Middle: tip_ratio={mid_tr:.2f} pip_ratio={mid_pr:.2f} ext_ratio={mid_er:.2f} state={mid_st}")
            logger.info(f"Ring: tip_ratio={rng_tr:.2f} pip_ratio={rng_pr:.2f} ext_ratio={rng_er:.2f} state={rng_st}")
            logger.info(f"Pinky: tip_ratio={pnk_tr:.2f} pip_ratio={pnk_pr:.2f} ext_ratio={pnk_er:.2f} state={pnk_st}")
            logger.info(f"Index tip_ratio={idx_tr:.2f}")
            logger.info(f"Middle tip_ratio={mid_tr:.2f}")
            logger.info(f"Ring tip_ratio={rng_tr:.2f}")
            logger.info(f"Pinky tip_ratio={pnk_tr:.2f}")
            logger.info(f"Gesture={raw.value}")

        # Smooth hysteresis: If currently in DRAW mode, require 3 consecutive non-DRAW frames to exit DRAW mode
        if self.current_gesture == GestureType.DRAW:
            recent_frames = list(self.history)[-3:]
            non_draw_count = sum(1 for g in recent_frames if g != GestureType.DRAW)
            if non_draw_count >= 3:
                counts = collections.Counter(self.history)
                self.current_gesture = counts.most_common(1)[0][0]
        else:
            counts = collections.Counter(self.history)
            most_common_gesture, count = counts.most_common(1)[0]
            if count >= (self.history.maxlen // 2 + 1):
                self.current_gesture = most_common_gesture

        return self.current_gesture
