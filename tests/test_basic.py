#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础测试脚本，验证代码可以正常导入和初始化
"""

import sys
import os
import logging

# 设置日志级别为ERROR，减少测试输出
logging.basicConfig(level=logging.ERROR)

def test_imports():
    """测试核心模块导入"""
    print("测试模块导入...")
    try:
        from core.generator import RandomAggregateGenerator
        from core.shapes import generate_random_polygon, generate_circle, generate_ellipse
        from core.collision import check_collision_shapely
        from core.group_manager import GroupManager
        from ui.main_window import AggregateGeneratorGUI
        from ui.widgets import ScrollableFrame
        from utils import calculate_polygon_area, calculate_circle_area, calculate_ellipse_area
        from config import DEFAULT_REGION, CAD_COLOR_MAP
        print("✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {str(e)}")
        return False

def test_utils():
    """测试工具函数"""
    print("测试工具函数...")
    try:
        from utils import calculate_polygon_area, calculate_circle_area, calculate_ellipse_area
        from pyautocad import APoint
        
        # 测试多边形面积计算
        points = [APoint(0, 0, 0), APoint(0, 1, 0), APoint(1, 1, 0), APoint(1, 0, 0)]
        area = calculate_polygon_area(points)
        assert abs(area - 1.0) < 0.001, f"多边形面积计算错误，预期1.0，实际{area}"
        
        # 测试圆形面积计算
        circle_area = calculate_circle_area(1.0)
        assert abs(circle_area - 3.1415926535) < 0.001, f"圆形面积计算错误，预期3.1415926535，实际{circle_area}"
        
        print("✓ 工具函数测试通过")
        return True
    except Exception as e:
        print(f"✗ 工具函数测试失败: {str(e)}")
        return False

def test_shapes():
    """测试形状生成函数"""
    print("测试形状生成函数...")
    try:
        from core.shapes import generate_random_polygon, generate_circle, generate_ellipse
        
        # 测试生成多边形
        polygon = generate_random_polygon((0, 0), 5, 6)
        assert len(polygon) > 3, f"多边形生成失败，点数不足: {len(polygon)}"
        
        # 测试生成圆形
        circle = generate_circle((0, 0), 5)
        assert len(circle) > 8, f"圆形生成失败，点数不足: {len(circle)}"
        
        # 测试生成椭圆形
        ellipse = generate_ellipse((0, 0), 5, 3)
        assert len(ellipse) > 8, f"椭圆形生成失败，点数不足: {len(ellipse)}"
        
        print("✓ 形状生成函数测试通过")
        return True
    except Exception as e:
        print(f"✗ 形状生成函数测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("=== RandomCAD 基础测试 ===")
    
    tests = [
        test_imports,
        test_utils,
        test_shapes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 50)
    
    print(f"测试完成: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有基础测试通过！")
        return 0
    else:
        print("❌ 部分测试失败！")
        return 1

if __name__ == "__main__":
    sys.exit(main())