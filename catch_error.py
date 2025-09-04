#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback
import os

def main():
    try:
        # 设置工作目录
        os.chdir(r"D:\claudecode\sora批量生图")
        
        # 清除之前的导入
        if 'main' in sys.modules:
            del sys.modules['main']
        
        # 导入并运行main
        import main as main_module
        
        print("Starting main function...")
        sys.exit(main_module.main())
        
    except SystemExit:
        # 正常退出
        pass
    except Exception as e:
        error_info = f"""
=== DETAILED ERROR INFORMATION ===

Error: {str(e)}
Type: {type(e).__name__}
Module: {getattr(e, '__module__', 'Unknown')}

Full Traceback:
{traceback.format_exc()}

Python Version: {sys.version}
Platform: {sys.platform}

Working Directory: {os.getcwd()}

=== END OF ERROR INFORMATION ===
"""
        
        print(error_info)
        
        # 保存到文件
        with open("detailed_error.log", "w", encoding="utf-8") as f:
            f.write(error_info)
        
        print("\nDetailed error saved to detailed_error.log")
        return 1

if __name__ == "__main__":
    main()