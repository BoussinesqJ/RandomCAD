# run_app.py
# 用于 PyInstaller 打包的启动引导脚本。
# 可以在不修改原始主程序代码的前提下，为打包后的可执行文件提供运行期配置。

import sys
import os
import tempfile
import logging

# 1. 解决 comtypes 库在打包环境（只读目录）下生成 CAD 包装缓存失败的问题
if getattr(sys, 'frozen', False):
    try:
        import comtypes.client
        # 在系统临时目录创建专门的 comtypes 缓存文件夹
        comtypes_cache = os.path.join(tempfile.gettempdir(), 'comtypes_cache')
        os.makedirs(comtypes_cache, exist_ok=True)
        # 强制指定 comtypes 的动态代码生成目录
        comtypes.client.gen_dir = comtypes_cache
        logging.info(f"已重定向 comtypes 写入缓存目录为: {comtypes_cache}")
    except Exception as e:
        print(f"警告：重定向 comtypes 缓存失败: {e}", file=sys.stderr)

# 2. 将项目根目录加入模块搜索路径，确保 PyInstaller 能正确解析模块导入
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 3. 动态寻找并载入系统 Python 的 site-packages，允许轻量级打包版本动态调用外部安装的 PyTorch
if getattr(sys, 'frozen', False):
    try:
        import subprocess
        # 运行系统 Python 获取其 site-packages 路径
        result = subprocess.run(
            ['python', '-c', 'import site; print(repr(site.getsitepackages()))'],
            capture_output=True, text=True, timeout=2, shell=True
        )
        if result.returncode == 0:
            import ast
            paths = ast.literal_eval(result.stdout.strip())
            for path in paths:
                if os.path.exists(path) and path not in sys.path:
                    sys.path.append(path)
                    # 同时也加入 DLL 搜索路径，以便正确加载 CUDA DLL 文件
                    if hasattr(os, 'add_dll_directory'):
                        try:
                            os.add_dll_directory(path)
                        except Exception:
                            pass
    except Exception:
        pass

# 4. 导入并启动实际的主程序
from main import main

if __name__ == '__main__':
    # 显式以 GUI 模式运行
    main()
