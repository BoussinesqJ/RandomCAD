# utils.py

import math
import logging
from typing import List, Tuple, Optional, Any


def clip(value: float, lower: float, upper: float) -> float:
    """
    限制值在指定范围内
    
    Args:
        value: 要限制的值
        lower: 最小值
        upper: 最大值
        
    Returns:
        float: 限制后的值
    """
    return lower if value < lower else upper if value > upper else value


def calculate_polygon_area(points: List[Any]) -> float:
    """
    计算多边形面积 (使用鞋带公式)
    
    Args:
        points: 多边形的点列表，每个点需有x和y属性
        
    Returns:
        float: 多边形面积
    """
    n = len(points)
    if n < 3:
        return 0.0
    
    area = 0.0
    for i in range(n - 1):
        x1, y1 = points[i].x, points[i].y
        x2, y2 = points[i + 1].x, points[i + 1].y
        area += (x1 * y2 - x2 * y1)
    
    return abs(area) / 2.0


def calculate_circle_area(radius: float) -> float:
    """
    计算圆形面积
    
    Args:
        radius: 圆的半径
        
    Returns:
        float: 圆形面积
    """
    return math.pi * radius ** 2


def calculate_ellipse_area(major_axis: float, minor_axis: float) -> float:
    """
    计算椭圆形面积
    
    Args:
        major_axis: 长轴长度
        minor_axis: 短轴长度
        
    Returns:
        float: 椭圆形面积
    """
    return math.pi * major_axis * minor_axis


def calculate_bounding_circle(points: List[Any]) -> Tuple[Optional[Tuple[float, float]], float]:
    """
    计算包围圆的中心和半径
    
    Args:
        points: 点列表，每个点需有x和y属性
        
    Returns:
        Tuple[Optional[Tuple[float, float]], float]: (中心点, 半径)
    """
    if not points:
        return None, 0.0
    
    # 计算中心点（重心）
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    center_point = (center_x, center_y)
    
    # 计算最大半径
    max_radius = 0.0
    for point in points:
        distance = math.hypot(point.x - center_x, point.y - center_y)
        if distance > max_radius:
            max_radius = distance
    
    return center_point, max_radius


def is_near_boundary(center: Tuple[float, float], radius: float, 
                     boundary_min: Tuple[float, float], boundary_max: Tuple[float, float], 
                     min_distance: float) -> bool:
    """
    检查点是否靠近边界
    
    Args:
        center: 中心点坐标 (x, y)
        radius: 包围圆半径
        boundary_min: 区域左下角坐标 (min_x, min_y)
        boundary_max: 区域右上角坐标 (max_x, max_y)
        min_distance: 最小距离阈值
        
    Returns:
        bool: 是否靠近边界
    """
    min_x, min_y = boundary_min
    max_x, max_y = boundary_max
    
    left_dist = center[0] - min_x
    right_dist = max_x - center[0]
    bottom_dist = center[1] - min_y
    top_dist = max_y - center[1]
    
    # 检查是否在边界附近
    threshold = radius + min_distance * 2
    return (left_dist < threshold or
            right_dist < threshold or
            bottom_dist < threshold or
            top_dist < threshold)


def move_toward_boundary(center: Tuple[float, float], 
                         boundary_min: Tuple[float, float], boundary_max: Tuple[float, float], 
                         min_distance: float) -> Tuple[float, float]:
    """
    向最近的边界移动中心点
    
    Args:
        center: 当前中心点坐标 (x, y)
        boundary_min: 区域左下角坐标 (min_x, min_y)
        boundary_max: 区域右上角坐标 (max_x, max_y)
        min_distance: 距离边界的最小距离
        
    Returns:
        Tuple[float, float]: 调整后的中心点坐标
    """
    min_x, min_y = boundary_min
    max_x, max_y = boundary_max
    
    # 计算到各边界的距离
    distances = {
        'left': center[0] - min_x,
        'right': max_x - center[0],
        'bottom': center[1] - min_y,
        'top': max_y - center[1]
    }
    
    # 找到最近的边界
    closest_boundary = min(distances, key=distances.get)
    min_dist = distances[closest_boundary]
    
    # 调整中心点到边界附近
    if closest_boundary == 'left':
        return (min_x + min_distance, center[1])
    elif closest_boundary == 'right':
        return (max_x - min_distance, center[1])
    elif closest_boundary == 'bottom':
        return (center[0], min_y + min_distance)
    elif closest_boundary == 'top':
        return (center[0], max_y - min_distance)
    
    return center


def adjust_points_to_boundary(points: List[Any], 
                             min_distance: float, 
                             boundary_min: Tuple[float, float], 
                             boundary_max: Tuple[float, float]) -> List[Tuple[float, float]]:
    """
    调整点集到边界内，确保与边界保持最小距离
    
    Args:
        points: 点列表，每个点需有x和y属性
        min_distance: 与边界的最小距离
        boundary_min: 区域左下角坐标 (min_x, min_y)
        boundary_max: 区域右上角坐标 (max_x, max_y)
        
    Returns:
        List[Tuple[float, float]]: 调整后的点列表
    """
    min_x, min_y = boundary_min
    max_x, max_y = boundary_max
    adjusted_points = []
    
    for point in points:
        x, y = point.x, point.y
        
        # 限制x坐标在边界内
        x = clip(x, min_x + min_distance, max_x - min_distance)
        # 限制y坐标在边界内
        y = clip(y, min_y + min_distance, max_y - min_distance)
        
        adjusted_points.append((x, y))
    
    return adjusted_points


def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    计算两点之间的距离
    
    Args:
        point1: 第一个点坐标 (x1, y1)
        point2: 第二个点坐标 (x2, y2)
        
    Returns:
        float: 两点之间的距离
    """
    return math.hypot(point2[0] - point1[0], point2[1] - point1[1])


def normalize_angle(angle: float) -> float:
    """
    将角度归一化到 [0, 2π) 范围内
    
    Args:
        angle: 弧度值
        
    Returns:
        float: 归一化后的弧度值
    """
    return angle % (2 * math.pi)


def linear_interpolate(a: float, b: float, t: float) -> float:
    """
    线性插值
    
    Args:
        a: 起始值
        b: 结束值
        t: 插值系数 (0-1)
        
    Returns:
        float: 插值结果
    """
    return a + t * (b - a)