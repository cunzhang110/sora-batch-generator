#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback
import os
from PyQt6.QtWidgets import QApplication

def test_step_by_step():
    print("=== Step by Step MainWindow Creation Test ===")
    
    app = QApplication(sys.argv)
    print("✓ QApplication created")
    
    import main
    print("✓ Main module imported")
    
    try:
        print("Creating MainWindow instance...")
        window = main.MainWindow()
        print("✓ MainWindow.__init__() completed")
        
        print("Testing delayed initialization...")
        # 模拟延迟初始化
        window.delayed_initialization()
        print("✓ delayed_initialization() completed")
        
        print("Testing window display...")
        window.show()
        print("✓ Window shown successfully")
        
        print("SUCCESS: All steps completed!")
        
    except Exception as e:
        print(f"ERROR at step: {e}")
        print(f"Error type: {type(e).__name__}")
        print("Traceback:")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_step_by_step()
    if success:
        print("\n=== CONCLUSION: MainWindow creation works fine ===")
        print("The error might be in the event loop or a race condition.")
    else:
        print("\n=== CONCLUSION: Found the error source ===")