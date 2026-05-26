"""
CAD连接诊断和测试工具

用于诊断和测试AutoCAD/中望CAD连接问题
"""

import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_dependencies():
    """检查依赖库"""
    print("\n" + "=" * 60)
    print("检查依赖库")
    print("=" * 60)
    
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
    
    return dependencies


def check_cad_installations():
    """检查CAD安装"""
    print("\n" + "=" * 60)
    print("检查CAD安装")
    print("=" * 60)
    
    from src.core.cad_connection import detect_autocad_installations, detect_zwcad_installations
    
    autocad_installations = detect_autocad_installations()
    zwcad_installations = detect_zwcad_installations()
    
    if autocad_installations:
        print(f"\n检测到 {len(autocad_installations)} 个AutoCAD安装:")
        for i, inst in enumerate(autocad_installations, 1):
            print(f"\n  [{i}] 版本: {inst['version']}")
            print(f"      发行版: {inst['release']}")
            print(f"      位置: {inst['location']}")
            print(f"      AutoCAD版本: {inst.get('acad_version', '未知')}")
    else:
        print("\n✗ 未检测到AutoCAD安装")
        print("  请确保已安装AutoCAD并正确注册COM组件")
    
    if zwcad_installations:
        print(f"\n检测到 {len(zwcad_installations)} 个中望CAD安装:")
        for i, inst in enumerate(zwcad_installations, 1):
            print(f"\n  [{i}] 版本: {inst['version']}")
            print(f"      位置: {inst['location']}")
    else:
        print("\n未检测到中望CAD安装 (可选)")
    
    return autocad_installations, zwcad_installations


def test_autocad_connection():
    """测试AutoCAD连接"""
    print("\n" + "=" * 60)
    print("测试AutoCAD连接")
    print("=" * 60)
    
    from src.core.cad_connection import CADConnection, ConnectionState
    
    print("\n创建CAD连接管理器...")
    cad_conn = CADConnection(auto_start=False, cad_type="autocad")
    
    print(f"当前状态: {cad_conn.state.value}")
    
    print("\n尝试连接AutoCAD...")
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
    else:
        print(f"✗ 连接失败！状态: {cad_conn.state.value}")
        print("\n请检查:")
        print("1. AutoCAD是否正在运行")
        print("2. 是否以管理员权限运行")
        print("3. AutoCAD版本是否支持COM自动化")
        print("4. COM组件是否正确注册")
    
    return success


def test_zwcad_connection():
    """测试中望CAD连接"""
    print("\n" + "=" * 60)
    print("测试中望CAD连接")
    print("=" * 60)
    
    try:
        from src.core.cad_connection import CADConnection, ConnectionState
        
        print("\n创建CAD连接管理器...")
        cad_conn = CADConnection(auto_start=False, cad_type="zwcad")
        
        print(f"当前状态: {cad_conn.state.value}")
        
        print("\n尝试连接中望CAD...")
        success = cad_conn.connect()
        
        if success:
            print(f"✓ 连接成功！状态: {cad_conn.state.value}")
            
            if cad_conn.doc:
                print(f"  文档名称: {cad_conn.doc.Name}")
            
            if cad_conn.model_space:
                print(f"  模型空间: {type(cad_conn.model_space).__name__}")
            
            print("\n断开连接...")
            cad_conn.disconnect()
            print(f"  当前状态: {cad_conn.state.value}")
        else:
            print(f"✗ 连接失败！状态: {cad_conn.state.value}")
        
        return success
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("CAD连接诊断和测试工具")
    print("=" * 60)
    
    print("\n请选择测试模式:")
    print("1. 完整诊断 (依赖库 + CAD安装 + 连接测试)")
    print("2. 仅检查依赖库")
    print("3. 仅检查CAD安装")
    print("4. 仅测试AutoCAD连接")
    print("5. 仅测试中望CAD连接")
    
    try:
        choice = input("\n请输入选项 (1-5): ").strip()
    except KeyboardInterrupt:
        print("\n\n用户取消")
        return
    
    if choice == "1":
        deps = check_dependencies()
        if not deps.get("comtypes") or not deps.get("pyautocad"):
            print("\n✗ 缺少必要的依赖库，无法继续测试")
            return
        
        check_cad_installations()
        test_autocad_connection()
    
    elif choice == "2":
        check_dependencies()
    
    elif choice == "3":
        check_cad_installations()
    
    elif choice == "4":
        test_autocad_connection()
    
    elif choice == "5":
        test_zwcad_connection()
    
    else:
        print("\n无效的选项")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
