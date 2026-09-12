"""Entry point for Live Air Writing AI application."""
import os
# Restrict OpenBLAS / OpenMP thread pools to prevent memory allocation errors on Windows
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
import logging
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont

from app.ui.main_window import MainWindow

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def global_exception_handler(exctype, value, tb):
    """Global exception trap to log unexpected errors and display user alert."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)
    logger.error(f"Unhandled Exception:\n{err_msg}")
    
    try:
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setWindowTitle("Application Error")
        dialog.setText(f"Application Error: {exctype.__name__}")
        dialog.setInformativeText(str(value))
        dialog.setDetailedText(err_msg)
        dialog.exec()
    except Exception as e:
        print(f"Error displaying exception dialog: {e}")


def main():
    sys.excepthook = global_exception_handler
    
    app = QApplication(sys.argv)
    app.setApplicationName("Live Air Writing AI")
    app.setOrganizationName("LiveAirWriting")

    # Set valid default application font (fixes QFont::setPointSize warning)
    app_font = QFont("Segoe UI", 10)
    app.setFont(app_font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
