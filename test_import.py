#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback

try:
    print("Testing basic imports...")
    
    # 测试基础模块
    import os
    import json
    import logging
    print("✓ 基础模块导入成功")
    
    # 测试第三方模块
    import requests
    import pandas as pd
    print("✓ 第三方模块导入成功")
    
    # 测试PyQt6
    from PyQt6.QtWidgets import QApplication
    print("✓ PyQt6基础模块导入成功")
    
    # 测试完整PyQt6导入
    from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton,
                                QFileDialog, QListWidget, QTableWidget, QTableWidgetItem, 
                                QHeaderView, QDialog, QTextEdit, QComboBox, QCheckBox, QListWidgetItem,
                                QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox,
                                QSplitter, QPlainTextEdit, QGroupBox, QGridLayout, QScrollArea,
                                QFrame, QProgressBar, QTabWidget, QAbstractItemView, QStyledItemDelegate, QStyle,
                                QSizePolicy)
    print("✓ PyQt6 Widgets导入成功")
    
    from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, QObject, QTimer, QSize, QUrl, QMimeData
    print("✓ PyQt6 Core导入成功")
    
    from PyQt6.QtGui import QPixmap, QImage, QFont, QPalette, QColor, QIcon, QTextOption, QDragEnterEvent, QDropEvent
    print("✓ PyQt6 Gui导入成功")
    
    # 尝试创建最基本的应用
    app = QApplication(sys.argv)
    print("✓ QApplication创建成功")
    
    # 现在尝试导入main模块
    print("尝试导入main模块...")
    import main
    print("✓ main模块导入成功")
    
    # 检查类是否存在
    if hasattr(main, 'MainWindow'):
        print("✓ MainWindow类存在")
        
        # 尝试创建最小实例
        print("尝试创建MainWindow实例...")
        window = main.MainWindow()
        print("✓ MainWindow实例创建成功")
        
        print("程序启动应该没有问题。")
    else:
        print("✗ MainWindow类不存在")
        print("可用的属性:", dir(main))
    
except Exception as e:
    print(f"✗ 错误发生在: {e}")
    print(f"错误类型: {type(e).__name__}")
    print("详细追踪:")
    traceback.print_exc()

print("测试完成")