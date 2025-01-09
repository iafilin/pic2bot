import sys
from PySide6.QtWidgets import QApplication
from ui import ScreenshotAppUI

def main():
    app = QApplication(sys.argv)
    window = ScreenshotAppUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
