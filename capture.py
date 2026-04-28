import os

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QApplication


def remove_file(path):
    if not path:
        return

    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        print(f"Failed to remove file: {exc}")


def capture_overlay(save_dir, left, top, right, bottom, previous_path=None):
    crop_width = right - left
    crop_height = bottom - top
    if crop_width <= 0 or crop_height <= 0:
        raise ValueError("Invalid crop area.")

    screen = QApplication.primaryScreen()
    if not screen:
        raise RuntimeError("Unable to access the screen.")

    screenshot = screen.grabWindow(0)
    remove_file(previous_path)

    timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
    save_path = os.path.join(save_dir, f"screenshot_{timestamp}.png")
    screenshot.save(save_path, "PNG")

    return screenshot.copy(left, top, crop_width, crop_height), save_path
