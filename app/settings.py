"""Application Settings & Configuration Persistence Manager."""
import json
import os
import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

DEFAULT_SETTINGS = {
    "camera_index": 0,
    "camera_resolution": [1280, 720],
    "camera_flip_h": True,
    "draw_skeleton": True,
    "gesture_mode": "Pointing Index Finger",
    "gesture_sensitivity": 35.0,
    "smoothing_factor": 0.4,
    "brush_color": "#00F0FF",
    "brush_size": 8,
    "eraser_size": 30,
    "canvas_mode": "Camera Workspace",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash"
}


class SettingsManager(QObject):
    """Manages application settings with JSON file storage."""

    settings_changed = Signal()

    def __init__(self, config_path: str = CONFIG_FILE, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self._data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._data.update(loaded)
                logger.info(f"Settings loaded from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to read settings file: {e}")
        else:
            self.save()

    def save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
            logger.info(f"Settings saved to {self.config_path}")
            self.settings_changed.emit()
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key: str, default=None):
        return self._data.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def reset_defaults(self) -> None:
        self._data = dict(DEFAULT_SETTINGS)
        self.save()
