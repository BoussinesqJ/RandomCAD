# core/shapes.py

import random
import math
from typing import List, Tuple
import numpy as np
from utils import clip

def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    计算两点之间的距离
    
    Args:
        point1: 第一个点 (x, y)
        point2: 第二个点 (x, y)
        
    Returns:
        float: 两点之间的距离
    """
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)


def optimize_polygon_sides(points: List[Tuple[float, float]], min_edge_length: float) -> List[Tuple[float, float]]:
    """
    优化多边形，避免出现过小的边
    
    Args:
        points: 多边形的点列表
        min_edge_length: 最小允许边长度
        
    Returns:
        List[Tuple[float, float]]: 优化后的多边形点列表
    """
    if len(points) < 4:  # 至少需要3个顶点 + 1个闭合点
        return points
    
    optimized_points = points.copy()
    sides = len(points) - 1
    
    # 检查并优化每条边
    for i in range(sides):
        current = optimized_points[i]
        next_point = optimized_points[i + 1]
        edge_length = calculate_distance(current, next_point)
        
        if edge_length < min_edge_length:
            # 计算中点
            mid_x = (current[0] + next_point[0]) / 2
            mid_y = (current[1] + next_point[1]) / 2
            
            # 找到相邻的点
            prev_index = (i - 1) % sides
            prev_point = optimized_points[prev_index]
            next_next_index = (i + 2) % len(optimized_points)
            next_next_point = optimized_points[next_next_index]
            
            # 调整当前点和下一个点的位置，使边长度符合要求
            # 沿着相邻边的方向调整点位置
            prev_vector = (prev_point[0] - current[0], prev_point[1] - current[1])
            next_vector = (next_next_point[0] - next_point[0], next_next_point[1] - next_point[1])
            
            # 归一化向量
            prev_length = calculate_distance((0, 0), prev_vector)
            next_length = calculate_distance((0, 0), next_vector)
            
            if prev_length > 0:
                prev_vector = (prev_vector[0] / prev_length, prev_vector[1] / prev_length)
            else:
                prev_vector = (0, 0)
            
            if next_length > 0:
                next_vector = (next_vector[0] / next_length, next_vector[1] / next_length)
            else:
                next_vector = (0, 0)
            
            # 计算调整量
            adjustment = (min_edge_length - edge_length) / 2
            current_adjust = (prev_vector[0] * adjustment, prev_vector[1] * adjustment)
            next_adjust = (next_vector[0] * adjustment, next_vector[1] * adjustment)
            
            # 调整点位置
            new_current = (current[0] - current_adjust[0], current[1] - current_adjust[1])
            new_next = (next_point[0] + next_adjust[0], next_point[1] + next_adjust[1])
            
            optimized_points[i] = new_current
            optimized_points[i + 1] = new_next
    
    return optimized_points


def generate_random_polygon(center: Tuple[float, float], 
                           radius: float, 
                           sides: int, 
                           irregularity: float = 0.3, 
                           spikiness: float = 0.2, 
                           optimize_sides: bool = True, 
                           min_edge_length: float = None) -> List[Tuple[float, float]]:
    """
    在指定中心点附近生成一个随机多边形的点列表。
    
    Args:
        center: 中心点坐标 (x, y)
        radius: 平均半径
        sides: 边数，必须≥3
        irregularity: 不规则程度，范围0-1，控制各边角度的变化
        spikiness: 尖锐程度，范围0-1，控制点到中心距离的变化
        optimize_sides: 是否优化多边形，避免出现小边
        min_edge_length: 最小允许边长度，默认值为半径的1/10
        
    Returns:
        List[Tuple[float, float]]: 多边形的点列表，包含闭合点
    """
    if sides < 3:
        raise ValueError("边数必须≥3")
    
    # 确保参数在有效范围内
    irregularity = clip(irregularity, 0.0, 1.0)
    spikiness = clip(spikiness, 0.0, 1.0)
    
    # 设置默认最小边长度
    if min_edge_length is None:
        min_edge_length = radius / 10
    
    # 计算角度步长的变化范围
    angle_variation = irregularity * 2 * math.pi / sides
    lower_angle = (2 * math.pi / sides) - angle_variation
    upper_angle = (2 * math.pi / sides) + angle_variation
    
    # 生成随机角度步长
    angle_steps = []
    total_angle = 0.0
    for _ in range(sides):
        step = random.uniform(lower_angle, upper_angle)
        angle_steps.append(step)
        total_angle += step
    
    # 归一化角度步长，确保总和为2π
    angle_steps = [step * (2 * math.pi / total_angle) for step in angle_steps]
    
    # 生成多边形顶点
    points = []
    current_angle = random.uniform(0, 2 * math.pi)
    radius_variation = spikiness * radius
    
    for i in range(sides):
        # 使用高斯分布生成随机半径，确保分布更自然
        current_radius = clip(random.gauss(radius, radius_variation), 0.3 * radius, 1.8 * radius)
        
        # 计算顶点坐标
        x = center[0] + current_radius * math.cos(current_angle)
        y = center[1] + current_radius * math.sin(current_angle)
        points.append((x, y))
        
        # 更新当前角度
        current_angle += angle_steps[i]
    
    # 闭合多边形
    points.append(points[0])
    
    # 优化多边形，避免小边
    if optimize_sides:
        points = optimize_polygon_sides(points, min_edge_length)
    
    return points

def generate_circle(center: Tuple[float, float], 
                    radius: float, 
                    segments: int = 36) -> List[Tuple[float, float]]:
    """
    生成圆形的点列表。
    
    Args:
        center: 中心点坐标 (x, y)
        radius: 半径
        segments: 分段数，控制圆形的平滑度
        
    Returns:
        List[Tuple[float, float]]: 圆形的点列表，包含闭合点
    """
    if segments < 8:
        segments = 8  # 确保最小分段数
    
    points = []
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append((x, y))
    return points

def generate_ellipse(center: Tuple[float, float], 
                     major_axis: float, 
                     minor_axis: float, 
                     rotation: float = 0.0, 
                     segments: int = 36) -> List[Tuple[float, float]]:
    """
    生成椭圆形的点列表。
    
    Args:
        center: 中心点坐标 (x, y)
        major_axis: 长轴长度
        minor_axis: 短轴长度
        rotation: 旋转角度（弧度）
        segments: 分段数，控制椭圆形的平滑度
        
    Returns:
        List[Tuple[float, float]]: 椭圆形的点列表，包含闭合点
    """
    if segments < 8:
        segments = 8  # 确保最小分段数
    
    points = []
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        
        # 计算旋转后的坐标
        x = (major_axis * math.cos(angle) * math.cos(rotation) - 
             minor_axis * math.sin(angle) * math.sin(rotation))
        y = (major_axis * math.cos(angle) * math.sin(rotation) + 
             minor_axis * math.sin(angle) * math.cos(rotation))
        
        # 平移到中心点
        points.append((center[0] + x, center[1] + y))
    return points