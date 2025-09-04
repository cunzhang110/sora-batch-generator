#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback

try:
    print("Step 1: Testing PyQt6...")
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print("PyQt6 OK")
    
    print("Step 2: Testing main import...")
    import main
    print("Main import OK")
    
    print("Step 3: Checking MainWindow class...")
    if hasattr(main, 'MainWindow'):
        print("MainWindow class found")
        
        print("Step 4: Creating MainWindow...")
        window = main.MainWindow()
        print("MainWindow created successfully")
        
        print("Step 5: Showing window...")
        window.show()
        print("SUCCESS: Program should work now!")
        
        # 立即退出而不是运行事件循环
        app.quit()
        
    else:
        print("ERROR: MainWindow class not found")
        print("Available attributes:", [attr for attr in dir(main) if not attr.startswith('_')])
    
except Exception as e:
    print("ERROR:", str(e))
    print("Error type:", type(e).__name__)
    print("Traceback:")
    traceback.print_exc()

print("Test completed")