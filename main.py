"""
main.py
프로그램 실행
"""
import sys
from PyQt6.QtWidgets import QApplication
from theme import apply as apply_theme
from mainwindow import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FDTD 시뮬레이터")
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
