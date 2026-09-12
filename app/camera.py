"""Camera utility functions for Live Air Writing AI."""
import logging
import cv2

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
