"""
自动化CAD连接测试

自动执行完整的CAD连接诊断和测试
"""

import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("自动化CAD连接测试")
    print("=" * 60)
    
    print("\n步骤 1: 检查依赖库")
    print("-" * 60)
    
    dependencies = {
        "comtypes": False,
        "pyautocad": False,
    }
    
    try:
        import comtypes
        dependencies["comtypes"] = True
        print("✓ comtypes 已安装 (支持 AutoCAD 和中望CAD)")
    except ImportError:
        print("✗ comtypes 未安装")
        print("  安装命令: pip install comtypes")
    
    try:
        import pyautocad
        dependencies["pyautocad"] = True
        print("✓ pyautocad 已安装 (支持 AutoCAD)")
    except ImportError:
        print("✗ pyautocad 未安装")
        print("  安装命令: pip install pyautocad")
    
    print("\n说明:")
    print("- comtypes: 必需，用于连接 AutoCAD 和中望CAD")
    print("- pyautocad: 必需，用于连接 AutoCAD")
    print("- 中望CAD: 不需要额外的 Python 库，通过 comtypes 直接连接")
    
    if not dependencies.get("comtypes") or not dependencies.get("pyautocad"):
        print("\n✗ 缺少必要的依赖库，无法继续测试")
        print("请运行: pip install comtypes pyautocad")
        return False
    
    print("\n步骤 2: 检查CAD安装")
    print("-" * 60)
    
    from src.core.cad_connection import detect_autocad_installations, detect_zwcad_installations
    
    autocad_installations = detect_autocad_installations()
    zwcad_installations = detect_zwcad_installations()
    
    if autocad_installations:
        print(f"✓ 检测到 {len(autocad_installations)} 个AutoCAD安装:")
        for i, inst in enumerate(autocad_installations, 1):
            print(f"  [{i}] {inst['version']} - {inst['location']}")
    else:
        print("✗ 未检测到AutoCAD安装")
        print("  请确保已安装AutoCAD并正确注册COM组件")
    
    if zwcad_installations:
        print(f"✓ 检测到 {len(zwcad_installations)} 个中望CAD安装:")
        for i, inst in enumerate(zwcad_installations, 1):
            print(f"  [{i}] {inst['version']} - {inst['location']}")
    else:
        print("未检测到中望CAD安装 (可选)")
    
    if not autocad_installations:
        print("\n✗ 未检测到AutoCAD安装，无法测试连接")
        return False
    
    print("\n步骤 3: 测试AutoCAD连接")
    print("-" * 60)
    
    from src.core.cad_connection import CADConnection, ConnectionState
    
    print("创建CAD连接管理器...")
    cad_conn = CADConnection(auto_start=False, cad_type="autocad")
    
    print(f"当前状态: {cad_conn.state.value}")
    
    print("尝试连接AutoCAD...")
    success = cad_conn.connect()
    
    if success:
        print(f"✓ 连接成功！状态: {cad_conn.state.value}")
        
        if cad_conn.doc:
            print(f"  文档名称: {cad_conn.doc.Name}")
        
        if cad_conn.model_space:
            print(f"  模型空间: {type(cad_conn.model_space).__name__}")
        
        cad_conn.prompt("测试消息：连接成功！\n")
        print("  已发送测试消息到AutoCAD命令行")
        
        print("\n断开连接...")
        cad_conn.disconnect()
        print(f"  当前状态: {cad_conn.state.value}")
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return True
    else:
        print(f"✗ 连接失败！状态: {cad_conn.state.value}")
        print("\n请检查:")
        print("1. AutoCAD是否正在运行")
        print("2. 是否以管理员权限运行")
        print("3. AutoCAD版本是否支持COM自动化")
        print("4. COM组件是否正确注册")
        
        print("\n" + "=" * 60)
        print("✗ 测试失败")
        print("=" * 60)
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
