# core/shapes.py

import random
import math
from typing import List, Tuple
import numpy as np
from utils import clip

def generate_random_polygon(center: Tuple[float, float], 
                           radius: float, 
                           sides: int, 
                           irregularity: float = 0.3, 
                           spikiness: float = 0.2) -> List[Tuple[float, float]]:
    """
    在指定中心点附近生成一个随机多边形的点列表。
    
    Args:
        center: 中心点坐标 (x, y)
        radius: 平均半径
        sides: 边数，必须≥3
        irregularity: 不规则程度，范围0-1，控制各边角度的变化
        spikiness: 尖锐程度，范围0-1，控制点到中心距离的变化
        
    Returns:
        List[Tuple[float, float]]: 多边形的点列表，包含闭合点
    """
    if sides < 3:
        raise ValueError("边数必须≥3")
    
    # 确保参数在有效范围内
    irregularity = clip(irregularity, 0.0, 1.0)
    spikiness = clip(spikiness, 0.0, 1.0)
    
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