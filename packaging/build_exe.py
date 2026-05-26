# build_exe.py
# 自动化编译生成 .exe 文件的构建脚本。
# 支持轻量级打包（排除 torch，动态加载）和完整打包（包含 torch）两种模式。

import os
import sys
import subprocess
import shutil

def install_pyinstaller():
    """安装 pyinstaller"""
    print("正在检查 pyinstaller 安装状态...")
    try:
        import PyInstaller
        print("PyInstaller 已安装！")
    except ImportError:
        print("未检测到 PyInstaller，正在为您自动安装...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
            print("PyInstaller 安装成功！")
        except Exception as e:
            print(f"安装 PyInstaller 失败，请手动运行 'pip install pyinstaller': {e}")
            sys.exit(1)

def run_build():
    install_pyinstaller()
    
    # 路径定义
    packaging_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(packaging_dir)
    entry_point = os.path.join(packaging_dir, "run_app.py")
    
    # 清理旧的编译缓存
    dist_dir = os.path.join(packaging_dir, "dist")
    build_dir = os.path.join(packaging_dir, "build")
    for d in [dist_dir, build_dir]:
        if os.path.exists(d):
            print(f"清理旧目录: {d}...")
            shutil.rmtree(d)
            
    print("\n" + "="*50)
    print(" RandomCAD 自动化打包构建工具")
    print("="*50)
    print("请选择打包模式:")
    print(" 1. 轻量级模式 (体积约 60MB, 推荐) - 排除 PyTorch")
    print("    * 自动运行 CPU 碰撞检测")
    print("    * 若用户系统已安装 PyTorch，则仍能动态调用实现 GPU 加速")
    print(" 2. 完整模式 (体积 >1.5GB) - 强制包含整个 PyTorch")
    print("    * 开箱即用支持 GPU 加速，但打包文件极大且构建缓慢")
    
    # 支持非交互模式运行（默认选择1）
    choice = "1"
    if sys.stdin.isatty():
        try:
            user_input = input("请输入选项 (1/2, 默认 1): ").strip()
            if user_input in ["1", "2"]:
                choice = user_input
        except (KeyboardInterrupt, SystemExit):
            print("\n已取消构建。")
            sys.exit(0)
        except Exception:
            pass
            
    print("\n请选择打包格式:")
    print(" A. 单一文件模式 (.exe 单文件，方便分发，但启动略慢)")
    print(" B. 文件夹模式 (一个包，启动快，便于调试或放入安装包程序)")
    
    format_choice = "A"
    if sys.stdin.isatty():
        try:
            user_input = input("请输入格式选项 (A/B, 默认 A): ").strip().upper()
            if user_input in ["A", "B"]:
                format_choice = user_input
        except Exception:
            pass

    # 组装 PyInstaller 参数
    args = [
        entry_point,
        "--name=RandomCAD",
        f"--workpath={build_dir}",
        f"--distpath={dist_dir}",
        "--noconsole",           # 不显示黑色命令行窗口
        "--clean",               # 清除缓存
    ]
    
    # 格式选择
    if format_choice == "A":
        args.append("--onefile")
    else:
        args.append("--onedir")
        
    # 模式选择：排除或包含 torch
    if choice == "1":
        print("\n[模式选定] 轻量级模式 (排除 PyTorch)...")
        args.extend([
            "--exclude-module=torch",
            "--exclude-module=torchvision",
            "--exclude-module=torchaudio",
            "--exclude-module=tensorboard",
            "--exclude-module=caffe2",
        ])
    else:
        print("\n[模式选定] 完整模式 (包含 PyTorch)...")
        # 显式加入一些必要的隐藏导入
        args.extend([
            "--hidden-import=torch",
            "--hidden-import=numpy",
        ])

    # 包含 shapely 和 PySide6 必要 hooks 的导入
    args.extend([
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=shapely",
        "--hidden-import=comtypes",
    ])
    
    # 调用 PyInstaller 编译
    print("\n开始启动 PyInstaller 打包构建，请耐心等待...")
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args)
        print("\n" + "="*50)
        print("🎉 恭喜！打包构建完成！")
        print(f"可执行输出目录: {dist_dir}")
        print("="*50)
    except Exception as e:
        print(f"\n❌ 打包出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
