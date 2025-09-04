#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试启动程序 - 捕获详细错误信息
"""

import sys
import traceback
import os

def main():
    try:
        # 设置工作目录
        os.chdir(r"D:\claudecode\sora批量生图")
        
        # 导入主程序
        print("正在导入模块...")
        import main
        print("模块导入成功")
        
        # 尝试创建应用
        print("正在创建QApplication...")
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        print("QApplication创建成功")
        
        # 尝试创建主窗口
        print("正在创建主窗口...")
        window = main.MainWindow()
        print("主窗口创建成功")
        
        # 尝试显示窗口
        print("正在显示窗口...")
        window.show()
        print("窗口显示成功")
        
        # 运行应用
        print("启动应用事件循环...")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"发生错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        print("详细错误信息:")
        traceback.print_exc()
        
        # 等待用户按键
        input("按回车键退出...")

if __name__ == "__main__":
    main()