#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 设置工作目录
os.chdir(r"D:\claudecode\sora批量生图")

try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    import main
    
    # 创建MainWindow实例
    window = main.MainWindow()
    
    print("=== API密钥调试信息 ===")
    print(f"当前图像模型: {window.image_model}")
    print(f"旧API密钥: '{window.api_key}'")
    print(f"Sora API密钥: '{window.sora_api_key}'")  
    print(f"Nano API密钥: '{window.nano_api_key}'")
    print(f"保存路径: '{window.save_path}'")
    
    # 测试get_current_api_key方法
    current_key = window.get_current_api_key()
    print(f"get_current_api_key()返回: '{current_key}'")
    
    # 检查条件
    has_api_key = bool(current_key and current_key.strip())
    has_save_path = bool(window.save_path and window.save_path.strip())
    
    print(f"\nAPI密钥检查: {has_api_key}")
    print(f"保存路径检查: {has_save_path}")
    print(f"按钮应该启用: {has_api_key and has_save_path}")
    
    if not has_api_key:
        print("⚠️  API密钥为空或未设置")
    if not has_save_path:
        print("⚠️  保存路径为空或未设置")
        
    print("=== 结束 ===")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()