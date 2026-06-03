# tests/test_helpers.py
"""测试 src/utils/helpers.py 中的工具函数"""

import math
import pytest
from src.utils.helpers import (
    clip, calculate_polygon_area, calculate_circle_area, calculate_ellipse_area,
    calculate_bounding_circle, is_near_boundary, move_toward_boundary,
    adjust_points_to_boundary, calculate_distance, normalize_angle, linear_interpolate,
    _get_xy
)


class TestClip:
    def test_within_range(self):
        assert clip(5, 0, 10) == 5

    def test_below_lower(self):
        assert clip(-1, 0, 10) == 0

    def test_above_upper(self):
        assert clip(15, 0, 10) == 10

    def test_at_boundaries(self):
        assert clip(0, 0, 10) == 0
        assert clip(10, 0, 10) == 10

    def test_float_values(self):
        assert clip(5.5, 0.0, 10.0) == 5.5


class TestGetXy:
    def test_tuple(self):
        assert _get_xy((3, 4)) == (3, 4)

    def test_list(self):
        assert _get_xy([3, 4]) == (3, 4)

    def test_object_with_xy(self):
        class Point:
            x = 3
            y = 4
        assert _get_xy(Point()) == (3, 4)


class TestCalculatePolygonArea:
    def test_triangle(self):
        # 直角三角形: (0,0), (4,0), (0,3) -> 面积 = 6
        points = [(0, 0), (4, 0), (0, 3)]
        area = calculate_polygon_area(points)
        assert abs(area - 6.0) < 1e-10

    def test_square(self):
        points = [(0, 0), (1, 0), (1, 1), (0, 1)]
        area = calculate_polygon_area(points)
        assert abs(area - 1.0) < 1e-10

    def test_empty(self):
        assert calculate_polygon_area([]) == 0.0

    def test_too_few_points(self):
        assert calculate_polygon_area([(0, 0), (1, 1)]) == 0.0

    def test_with_object_points(self):
        class P:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        points = [P(0, 0), P(4, 0), P(0, 3)]
        area = calculate_polygon_area(points)
        assert abs(area - 6.0) < 1e-10


class TestCalculateCircleArea:
    def test_unit_circle(self):
        area = calculate_circle_area(1.0)
        assert abs(area - math.pi) < 1e-10

    def test_zero_radius(self):
        assert calculate_circle_area(0) == 0.0


class TestCalculateEllipseArea:
    def test_circle(self):
        area = calculate_ellipse_area(3.0, 3.0)
        assert abs(area - math.pi * 9) < 1e-10

    def test_ellipse(self):
        area = calculate_ellipse_area(5.0, 3.0)
        assert abs(area - math.pi * 15) < 1e-10


class TestCalculateBoundingCircle:
    def test_triangle(self):
        points = [(0, 0), (4, 0), (0, 3)]
        center, radius = calculate_bounding_circle(points)
        assert center is not None
        # 质心 = (4/3, 1)
        assert abs(center[0] - 4 / 3) < 1e-10
        assert abs(center[1] - 1.0) < 1e-10
        # 半径应该是中心到最远点的距离
        expected_radius = max(
            math.hypot(0 - center[0], 0 - center[1]),
            math.hypot(4 - center[0], 0 - center[1]),
            math.hypot(0 - center[0], 3 - center[1])
        )
        assert abs(radius - expected_radius) < 1e-10

    def test_empty(self):
        center, radius = calculate_bounding_circle([])
        assert center is None
        assert radius == 0.0

    def test_single_point(self):
        center, radius = calculate_bounding_circle([(5, 5)])
        assert center == (5.0, 5.0)
        assert radius == 0.0


class TestIsNearBoundary:
    def test_inside_not_near(self):
        result = is_near_boundary((50, 50), 5, (0, 0), (100, 100), 1.0)
        assert result is False

    def test_near_left_boundary(self):
        result = is_near_boundary((3, 50), 5, (0, 0), (100, 100), 1.0)
        assert result is True  # 3 < 5 + 1

    def test_near_right_boundary(self):
        result = is_near_boundary((97, 50), 5, (0, 0), (100, 100), 1.0)
        assert result is True  # 3 < 5 + 1

    def test_min_distance_respected(self):
        # 不靠近边界时 min_distance 很大
        result = is_near_boundary((50, 50), 5, (0, 0), (100, 100), 100.0)
        assert result is True  # 50 < 5 + 100


class TestMoveTowardBoundary:
    def test_move_to_left(self):
        result = move_toward_boundary((2, 50), (0, 0), (100, 100), 1.0)
        assert result[0] == 1.0  # min_x + max(min_distance, 0.1)
        assert result[1] == 50

    def test_move_to_right(self):
        result = move_toward_boundary((98, 50), (0, 0), (100, 100), 1.0)
        assert result[0] == 99.0
        assert result[1] == 50

    def test_min_distance_respected(self):
        result = move_toward_boundary((2, 50), (0, 0), (100, 100), 5.0)
        assert result[0] == 5.0


class TestAdjustPointsToBoundary:
    def test_points_inside(self):
        class P:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        points = [P(50, 50), P(60, 60)]
        result = adjust_points_to_boundary(points, 1.0, (0, 0), (100, 100))
        assert len(result) == 2
        assert result[0] == (50, 50)

    def test_points_clipped(self):
        class P:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        points = [P(-5, 50), P(105, 50)]
        result = adjust_points_to_boundary(points, 1.0, (0, 0), (100, 100))
        assert result[0][0] == 1.0  # clipped to min_x + max(min_distance, 0.1)
        assert result[1][0] == 99.0

    def test_with_tuples(self):
        points = [(50, 50)]
        result = adjust_points_to_boundary(points, 1.0, (0, 0), (100, 100))
        assert result[0] == (50, 50)


class TestCalculateDistance:
    def test_horizontal(self):
        assert calculate_distance((0, 0), (3, 0)) == 3.0

    def test_vertical(self):
        assert calculate_distance((0, 0), (0, 4)) == 4.0

    def test_diagonal(self):
        assert abs(calculate_distance((0, 0), (3, 4)) - 5.0) < 1e-10

    def test_same_point(self):
        assert calculate_distance((5, 5), (5, 5)) == 0.0


class TestNormalizeAngle:
    def test_zero(self):
        assert normalize_angle(0) == 0

    def test_positive(self):
        assert abs(normalize_angle(math.pi) - math.pi) < 1e-10

    def test_negative(self):
        result = normalize_angle(-math.pi)
        assert abs(result - math.pi) < 1e-10

    def test_over_2pi(self):
        result = normalize_angle(3 * math.pi)
        assert abs(result - math.pi) < 1e-10


class TestLinearInterpolate:
    def test_start(self):
        assert linear_interpolate(0, 10, 0) == 0

    def test_end(self):
        assert linear_interpolate(0, 10, 1) == 10

    def test_midpoint(self):
        assert linear_interpolate(0, 10, 0.5) == 5

    def test_negative_t(self):
        assert linear_interpolate(0, 10, -1) == -10
