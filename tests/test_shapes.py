"""
形状生成测试

测试形状生成的纯函数：generate_random_polygon, generate_circle, generate_ellipse
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import math
from src.core.shapes import generate_random_polygon, generate_circle, generate_ellipse


class TestRandomPolygon(unittest.TestCase):
    """测试随机多边形生成"""

    def test_minimum_sides(self):
        """测试边数<3时抛出异常"""
        with self.assertRaises(ValueError):
            generate_random_polygon((0, 0), 10.0, sides=2)

    def test_output_type(self):
        """测试返回值类型为 list of tuples"""
        points = generate_random_polygon((0, 0), 10.0, sides=6)
        self.assertIsInstance(points, list)
        self.assertTrue(all(isinstance(p, tuple) and len(p) == 2 for p in points))

    def test_output_length(self):
        """测试返回点数 = sides + 1（包含闭合点）"""
        points = generate_random_polygon((0, 0), 10.0, sides=6)
        self.assertEqual(len(points), 7)

    def test_closed_polygon(self):
        """测试多边形闭合（首尾点相同）"""
        points = generate_random_polygon((5, 5), 10.0, sides=8)
        self.assertEqual(points[0], points[-1])

    def test_points_near_center(self):
        """测试所有点都在 center ± 2*radius 范围内"""
        center = (5.0, 5.0)
        radius = 10.0
        points = generate_random_polygon(center, radius, sides=8, irregularity=0.5, spikiness=0.5)
        for x, y in points:
            dist = math.hypot(x - center[0], y - center[1])
            self.assertLessEqual(dist, 2.0 * radius)

    def test_with_optimize_sides(self):
        """测试 optimize_sides=True 返回合法结果"""
        points = generate_random_polygon(
            (0, 0), 10.0, sides=20, optimize_sides=True, min_edge_length=0.5
        )
        self.assertEqual(len(points), 21)
        self.assertEqual(points[0], points[-1])


class TestCircle(unittest.TestCase):
    """测试圆形生成"""

    def test_output_type(self):
        """测试返回值类型"""
        points = generate_circle((0, 0), 5.0)
        self.assertIsInstance(points, list)
        self.assertTrue(all(isinstance(p, tuple) and len(p) == 2 for p in points))

    def test_output_length(self):
        """测试默认segments=36时返回37个点"""
        points = generate_circle((0, 0), 5.0)
        self.assertEqual(len(points), 37)

    def test_custom_segments(self):
        """测试自定义segments"""
        points = generate_circle((3, 4), 7.0, segments=20)
        self.assertEqual(len(points), 21)

    def test_minimum_segments(self):
        """测试segments<8时自动修正为8"""
        points = generate_circle((0, 0), 5.0, segments=3)
        self.assertEqual(len(points), 9)  # 8+1

    def test_all_points_on_circle(self):
        """测试所有点都落在圆上"""
        center = (2.0, 3.0)
        radius = 5.0
        points = generate_circle(center, radius, segments=100)
        for x, y in points:
            dist = math.hypot(x - center[0], y - center[1])
            self.assertAlmostEqual(dist, radius, places=6)


class TestEllipse(unittest.TestCase):
    """测试椭圆形生成"""

    def test_output_type(self):
        """测试返回值类型"""
        points = generate_ellipse((0, 0), 10.0, 5.0)
        self.assertIsInstance(points, list)
        self.assertTrue(all(isinstance(p, tuple) and len(p) == 2 for p in points))

    def test_output_length(self):
        """测试默认segments=36时返回37个点"""
        points = generate_ellipse((0, 0), 10.0, 5.0)
        self.assertEqual(len(points), 37)

    def test_custom_segments(self):
        """测试自定义segments"""
        points = generate_ellipse((0, 0), 10.0, 5.0, segments=24)
        self.assertEqual(len(points), 25)

    def test_minimum_segments(self):
        """测试segments<8时自动修正为8"""
        points = generate_ellipse((0, 0), 10.0, 5.0, segments=4)
        self.assertEqual(len(points), 9)

    def test_closed_ellipse(self):
        """测试椭圆形闭合"""
        points = generate_ellipse((1, 2), 8.0, 4.0, rotation=0.5)
        self.assertAlmostEqual(points[0][0], points[-1][0], places=12)
        self.assertAlmostEqual(points[0][1], points[-1][1], places=12)

    def test_rotation_applied(self):
        """测试旋转参数生效（旋转前后不等）"""
        points_no_rot = generate_ellipse((0, 0), 10.0, 5.0, rotation=0.0)
        points_rot = generate_ellipse((0, 0), 10.0, 5.0, rotation=math.pi / 4)
        self.assertNotEqual(points_no_rot, points_rot)


if __name__ == '__main__':
    unittest.main()
