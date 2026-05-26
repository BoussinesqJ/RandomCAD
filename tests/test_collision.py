"""
碰撞检测测试

测试碰撞检测算法和GPU距离计算器
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from src.core.collision import (
    SHAPELY_AVAILABLE,
    check_collision_hierarchical,
    GPUDistanceCalculator,
    gpu_calculator,
)


class TestCollisionDetection(unittest.TestCase):
    """碰撞检测测试类"""

    def _make_circle_polygon(self, cx: float, cy: float, r: float, n: int = 32):
        """
        用正多边形近似圆形，返回 Shapely Polygon
        """
        import math
        from shapely.geometry import Polygon
        points = []
        for i in range(n):
            angle = 2 * math.pi * i / n
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        return Polygon(points)

    @unittest.skipIf(not SHAPELY_AVAILABLE, "Shapely未安装，跳过碰撞检测测试")
    def test_overlapping_shapes_detected(self):
        """重叠形状应检测到碰撞，返回 True"""
        shape1 = self._make_circle_polygon(0, 0, 10)
        shape2 = self._make_circle_polygon(5, 5, 10)

        result = check_collision_hierarchical(
            new_shape=shape1,
            new_itz_shape=None,
            existing_shapes_and_itzs=[shape2],
            min_distance=0.0,
        )
        self.assertTrue(result, "两个重叠的圆应检测到碰撞")

    @unittest.skipIf(not SHAPELY_AVAILABLE, "Shapely未安装，跳过碰撞检测测试")
    def test_separated_shapes_not_colliding(self):
        """分开很远的形状不应检测到碰撞，返回 False"""
        shape1 = self._make_circle_polygon(0, 0, 5)
        shape2 = self._make_circle_polygon(100, 100, 5)

        result = check_collision_hierarchical(
            new_shape=shape1,
            new_itz_shape=None,
            existing_shapes_and_itzs=[shape2],
            min_distance=0.0,
        )
        self.assertFalse(result, "两个远离的圆不应检测到碰撞")

    @unittest.skipIf(not SHAPELY_AVAILABLE, "Shapely未安装，跳过碰撞检测测试")
    def test_with_itz_shape_overlaps(self):
        """带ITZ的新形状与已有形状重叠时应检测到碰撞"""
        shape1 = self._make_circle_polygon(0, 0, 10)
        shape1_itz = self._make_circle_polygon(0, 0, 12)  # ITZ 比本体大
        shape2 = self._make_circle_polygon(18, 0, 8)

        # shape2 不与 shape1 重叠，但可能与 ITZ 重叠
        result = check_collision_hierarchical(
            new_shape=shape1,
            new_itz_shape=shape1_itz,
            existing_shapes_and_itzs=[shape2],
            min_distance=0.0,
        )
        self.assertTrue(result, "ITZ与已有形状重叠应检测到碰撞")

    @unittest.skipIf(not SHAPELY_AVAILABLE, "Shapely未安装，跳过碰撞检测测试")
    def test_with_itz_shape_separated(self):
        """ITZ和形状都不重叠时不应检测到碰撞"""
        shape1 = self._make_circle_polygon(0, 0, 5)
        shape1_itz = self._make_circle_polygon(0, 0, 8)
        shape2 = self._make_circle_polygon(100, 100, 5)

        result = check_collision_hierarchical(
            new_shape=shape1,
            new_itz_shape=shape1_itz,
            existing_shapes_and_itzs=[shape2],
            min_distance=0.0,
        )
        self.assertFalse(result, "远距离的ITZ不应检测到碰撞")


class TestGPUDistanceCalculator(unittest.TestCase):
    """GPU距离计算器测试类"""

    def test_cuda_availability_detection(self):
        """测试 CUDA 可用性检测不会崩溃"""
        calc = GPUDistanceCalculator()
        self.assertIsInstance(calc.cuda_available, bool)

    def test_calculate_distances_gpu_empty_list(self):
        """传递空列表应返回空列表"""
        calc = GPUDistanceCalculator()
        result = calc.calculate_distances_gpu(
            new_shape_bounds=(0, 0, 10, 10),
            existing_bounds_list=[],
            min_distance=0.0,
        )
        self.assertEqual(result, [])

    def test_calculate_distances_gpu_non_empty(self):
        """基本距离计算测试"""
        calc = GPUDistanceCalculator()
        result = calc.calculate_distances_gpu(
            new_shape_bounds=(0, 0, 10, 10),
            existing_bounds_list=[(5, 5, 15, 15), (100, 100, 110, 110)],
            min_distance=0.0,
        )
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], bool)
        # 第一个与 (0,0,10,10) 重叠
        self.assertTrue(result[0])
        # 第二个在远处
        self.assertFalse(result[1])

    def test_global_gpu_calculator_instance(self):
        """全局 gpu_calculator 实例应存在"""
        self.assertIsNotNone(gpu_calculator)
        self.assertIsInstance(gpu_calculator, GPUDistanceCalculator)
        self.assertIsInstance(gpu_calculator.cuda_available, bool)


if __name__ == '__main__':
    unittest.main()
