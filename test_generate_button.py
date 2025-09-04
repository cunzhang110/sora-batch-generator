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
    
    print("=== 测试生成按钮启用 ===")
    
    # 设置测试的API密钥和保存路径
    window.sora_api_key = "test-sora-api-key"  # 设置测试密钥
    window.save_path = "D:\\test_images"        # 设置测试保存路径
    
    print(f"设置后 - Sora API密钥: '{window.sora_api_key}'")
    print(f"设置后 - 保存路径: '{window.save_path}'")
    
    # 测试get_current_api_key方法
    current_key = window.get_current_api_key()
    print(f"get_current_api_key()返回: '{current_key}'")
    
    # 检查条件
    has_api_key = bool(current_key and current_key.strip())
    has_save_path = bool(window.save_path and window.save_path.strip())
    
    print(f"\nAPI密钥检查: {has_api_key}")
    print(f"保存路径检查: {has_save_path}")
    print(f"按钮应该启用: {has_api_key and has_save_path}")
    
    # 添加一个提示词来测试按钮
    window.add_prompt()
    
    print("\n添加测试提示词后，检查表格中的按钮状态...")
    print("如果配置正确，生成按钮应该是启用的")
    
    # 显示窗口
    window.show()
    print("\n窗口已显示，可以检查生成按钮是否启用")
    print("提示：现在生成按钮应该是绿色且可点击的")
    
    # 运行一小会儿让用户看到
    import time
    time.sleep(2)
    
    print("=== 测试完成 ===")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()