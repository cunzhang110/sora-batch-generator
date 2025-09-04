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
    
    print("=== 强制刷新测试 ===")
    
    # 等待一会儿让异步初始化完成
    import time
    time.sleep(1)
    
    # 手动调用load_config
    print("手动加载配置...")
    window.load_config()
    
    print(f"加载后 - Sora API密钥: '{window.sora_api_key}'")
    print(f"加载后 - 保存路径: '{window.save_path}'")
    print(f"加载后 - 当前模型: {window.image_model}")
    
    # 强制刷新表格
    if hasattr(window, 'refresh_prompt_table'):
        print("强制刷新提示词表格...")
        window.refresh_prompt_table()
    
    # 测试当前API密钥
    current_key = window.get_current_api_key()
    print(f"get_current_api_key()返回: '{current_key}'")
    
    # 检查生成按钮启用条件
    has_api_key = bool(current_key and current_key.strip())
    has_save_path = bool(window.save_path and window.save_path.strip())
    
    print(f"API密钥检查: {has_api_key}")
    print(f"保存路径检查: {has_save_path}")
    print(f"按钮应该启用: {has_api_key and has_save_path}")
    
    # 显示窗口让用户查看
    window.show()
    print("窗口已显示，请查看生成按钮是否启用")
    
    # 运行一小会儿
    time.sleep(3)
    
    print("=== 测试完成 ===")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()