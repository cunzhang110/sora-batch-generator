#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback
import os

# 添加更多调试信息
print("=== Debug Main Window Creation ===")

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    
    app = QApplication(sys.argv)
    print("QApplication created successfully")
    
    # 尝试导入main模块
    import main
    print("Main module imported successfully")
    
    print("Attempting to create MainWindow...")
    
    # 详细的创建过程调试
    try:
        window = main.MainWindow()
        print("MainWindow instance created successfully!")
        
        print("Attempting to show window...")
        window.show()
        print("Window shown successfully!")
        
        print("Everything looks good. The error must be elsewhere.")
        
    except Exception as create_error:
        print(f"ERROR during MainWindow creation: {create_error}")
        print(f"Error type: {type(create_error).__name__}")
        print("Full traceback:")
        traceback.print_exc()
        
        # 显示更详细的错误信息
        error_msg = f"""
MainWindow Creation Failed!

Error: {create_error}
Type: {type(create_error).__name__}

Traceback:
{traceback.format_exc()}
"""
        print(error_msg)
        
        # 保存错误到文件
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(error_msg)
        print("Error details saved to error_log.txt")
        
except Exception as outer_error:
    print(f"ERROR during setup: {outer_error}")
    traceback.print_exc()

print("=== Debug Complete ===")