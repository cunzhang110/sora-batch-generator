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
    
    print("=== 生成按钮状态调试 ===")
    print("初始状态:")
    print(f"当前图像模型: {window.image_model}")
    print(f"API密钥: '{window.api_key}'")
    print(f"Sora API密钥: '{window.sora_api_key}'")  
    print(f"Nano API密钥: '{window.nano_api_key}'")
    print(f"保存路径: '{window.save_path}'")
    print(f"API平台: {window.api_platform}")
    
    # 手动加载配置看看能否获取到数据
    print("\n手动加载配置:")
    window.load_config()
    print(f"加载后 API密钥: '{window.api_key}'")
    print(f"加载后 Sora API密钥: '{window.sora_api_key}'")  
    print(f"加载后 Nano API密钥: '{window.nano_api_key}'")
    print(f"加载后 保存路径: '{window.save_path}'")
    
    # 测试get_current_api_key方法
    try:
        current_key = window.get_current_api_key()
        print(f"get_current_api_key()返回: '{current_key}'")
    except Exception as e:
        print(f"get_current_api_key()错误: {e}")
    
    # 检查生成按钮启用条件
    has_api_key = bool(current_key and current_key.strip())
    has_save_path = bool(window.save_path and window.save_path.strip())
    
    print(f"\nAPI密钥检查: {has_api_key}")
    print(f"保存路径检查: {has_save_path}")
    print(f"按钮应该启用: {has_api_key and has_save_path}")
    
    if not has_api_key:
        print("X API密钥为空或未设置")
        print("   - 请检查设置中心的API密钥配置")
        print(f"   - 当前模型: {window.image_model}")
        if window.image_model == "sora":
            print("   - 需要配置Sora模型API密钥")
        elif window.image_model == "nano-banana":
            print("   - 需要配置Nano-banana模型API密钥")
    
    if not has_save_path:
        print("X 保存路径为空或未设置")
        print("   - 请在设置中心的保存路径中选择文件夹")
        
    # 添加一个提示词来检查按钮状态
    if len(window.prompt_table_data) == 0:
        window.add_prompt()
        print("\n已添加测试提示词，现在可以查看生成按钮状态")
    
    print("=== 调试完成 ===")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()