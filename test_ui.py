#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI Test")
        self.setGeometry(100, 100, 800, 600)
        
        label = QLabel("Test Window - UI is working!")
        self.setCentralWidget(label)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())