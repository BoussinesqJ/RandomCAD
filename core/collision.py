# core/collision.py

import logging
from typing import List, Optional, Union, Any
from shapely.geometry import Polygon


class GPUDistanceCalculator:
    """
    GPU加速的距离计算器，用于加速碰撞检测
    """
    def __init__(self):
        self.cuda_available = False
        self.torch = None
        self.device = None
        
        # 尝试导入PyTorch
        try:
            import torch
            self.torch = torch
            self.cuda_available = torch.cuda.is_available()
            self.device = torch.device("cuda" if self.cuda_available else "cpu")
            logging.info(f"GPU距离计算器已初始化，使用设备: {self.device}")
        except ImportError:
            logging.info("PyTorch未安装，无法使用GPU加速碰撞检测")
        except Exception as e:
            logging.warning(f"初始化GPU距离计算器时出错: {str(e)}")
    
    def calculate_distances_gpu(self, new_shape_bounds: tuple, 
                               existing_bounds_list: List[tuple], 
                               min_distance: float) -> List[bool]:
        """
        使用GPU计算新形状与多个现有形状的边界框距离
        
        Args:
            new_shape_bounds: 新形状的边界框 (min_x, min_y, max_x, max_y)
            existing_bounds_list: 现有形状的边界框列表
            min_distance: 最小间距
            
        Returns:
            List[bool]: 每个现有形状是否与新形状可能碰撞
        """
        if not self.cuda_available or not self.torch or not existing_bounds_list:
            # 回退到CPU计算
            results = []
            for bounds in existing_bounds_list:
                collision = not (
                    new_shape_bounds[2] + min_distance < bounds[0] or
                    new_shape_bounds[0] - min_distance > bounds[2] or
                    new_shape_bounds[3] + min_distance < bounds[1] or
                    new_shape_bounds[1] - min_distance > bounds[3]
                )
                results.append(collision)
            return results
        
        try:
            # 将边界框转换为张量
            new_bounds_tensor = self.torch.tensor(new_shape_bounds, device=self.device, dtype=self.torch.float32)
            existing_bounds_tensor = self.torch.tensor(existing_bounds_list, device=self.device, dtype=self.torch.float32)
            
            # 扩展新形状边界框
            expanded_min_x = new_bounds_tensor[0] - min_distance
            expanded_min_y = new_bounds_tensor[1] - min_distance
            expanded_max_x = new_bounds_tensor[2] + min_distance
            expanded_max_y = new_bounds_tensor[3] + min_distance
            
            # 计算所有现有形状与新形状的边界框碰撞情况
            # 碰撞条件：不满足任何分离轴条件
            collision_mask = ~(
                (expanded_max_x < existing_bounds_tensor[:, 0]) |
                (expanded_min_x > existing_bounds_tensor[:, 2]) |
                (expanded_max_y < existing_bounds_tensor[:, 1]) |
                (expanded_min_y > existing_bounds_tensor[:, 3])
            )
            
            # 将结果转换为列表
            return collision_mask.cpu().tolist()
        except Exception as e:
            logging.warning(f"GPU距离计算出错，回退到CPU: {str(e)}")
            # 回退到CPU计算
            results = []
            for bounds in existing_bounds_list:
                collision = not (
                    new_shape_bounds[2] + min_distance < bounds[0] or
                    new_shape_bounds[0] - min_distance > bounds[2] or
                    new_shape_bounds[3] + min_distance < bounds[1] or
                    new_shape_bounds[1] - min_distance > bounds[3]
                )
                results.append(collision)
            return results

# 创建全局GPU距离计算器实例
gpu_calculator = GPUDistanceCalculator()


def check_collision_shapely(new_shape: Any, 
                           new_itz_shape: Optional[Any], 
                           existing_shapes_and_itzs: List[Any], 
                           min_distance: float, 
                           quadtree: Optional[Any] = None, 
                           use_gpu: bool = False) -> bool:
    """
    使用Shapely库进行精确的碰撞检测，包含边界框快速排除和四叉树优化。
    
    Args:
        new_shape: 新骨料的Shapely几何对象
        new_itz_shape: 新骨料ITZ的Shapely几何对象，可为None
        existing_shapes_and_itzs: 包含所有已存在骨料和ITZ的Shapely对象列表
        min_distance: 最小间距
        quadtree: 可选的空间索引对象，用于优化碰撞检测
        use_gpu: 是否使用GPU加速碰撞检测
        
    Returns:
        bool: 如果发生碰撞返回True，否则返回False
    """
    # 获取新对象的边界框
    new_bbox = new_shape.bounds
    expanded_bbox = (
        new_bbox[0] - min_distance,
        new_bbox[1] - min_distance,
        new_bbox[2] + min_distance,
        new_bbox[3] + min_distance
    )
    
    # 如果有ITZ，使用ITZ的边界框进行扩展
    if new_itz_shape:
        itz_bbox = new_itz_shape.bounds
        expanded_bbox = (
            min(expanded_bbox[0], itz_bbox[0] - min_distance),
            min(expanded_bbox[1], itz_bbox[1] - min_distance),
            max(expanded_bbox[2], itz_bbox[2] + min_distance),
            max(expanded_bbox[3], itz_bbox[3] + min_distance)
        )
    
    # 要检查的对象列表
    objects_to_check = existing_shapes_and_itzs
    
    # 如果使用空间索引，先查询可能碰撞的对象
    if quadtree is not None:
        # 构建临时对象用于空间索引查询
        temp_obj = {'shapely_obj': new_shape}
        # 查询可能碰撞的对象
        potential_collisions = quadtree.query_shapely(new_shape, min_distance)
        # 从查询结果中提取Shapely对象
        potential_shapes = []
        for obj in potential_collisions:
            if 'shapely_obj' in obj:
                potential_shapes.append(obj['shapely_obj'])
            if 'shapely_itz' in obj and obj['shapely_itz']:
                potential_shapes.append(obj['shapely_itz'])
        
        # 只检查可能碰撞的对象
        if potential_shapes:
            objects_to_check = potential_shapes
    
    if use_gpu and gpu_calculator.cuda_available:
        # 使用GPU加速边界框检测
        existing_bounds_list = [shape.bounds for shape in objects_to_check]
        potential_collisions = gpu_calculator.calculate_distances_gpu(
            expanded_bbox, existing_bounds_list, 0.0
        )
        
        # 只对可能碰撞的对象进行精确检测
        for i, collision in enumerate(potential_collisions):
            if collision:
                existing_shape = objects_to_check[i]
                try:
                    # 精确检测：使用Shapely的distance方法
                    if new_shape.distance(existing_shape) < min_distance:
                        return True
                    if new_itz_shape and new_itz_shape.distance(existing_shape) < min_distance:
                        return True
                except Exception as e:
                    logging.warning(f"碰撞检测时出错: {str(e)}")
                    continue
    else:
        # CPU模式：传统的碰撞检测
        for existing_shape in objects_to_check:
            # 快速排除：检查两个边界框是否可能碰撞
            existing_bbox = existing_shape.bounds
            if (expanded_bbox[2] < existing_bbox[0] or  # 新对象在已有对象左侧
                expanded_bbox[0] > existing_bbox[2] or  # 新对象在已有对象右侧
                expanded_bbox[3] < existing_bbox[1] or  # 新对象在已有对象下方
                expanded_bbox[1] > existing_bbox[3]):   # 新对象在已有对象上方
                continue  # 边界框不重叠，跳过
            
            # 精确检测：使用Shapely的distance方法
            try:
                # 检查新骨料与已存在对象的距离
                if new_shape.distance(existing_shape) < min_distance:
                    return True
                # 检查新骨料的ITZ与已存在对象的距离
                if new_itz_shape and new_itz_shape.distance(existing_shape) < min_distance:
                    return True
            except Exception as e:
                logging.warning(f"碰撞检测时出错: {str(e)}")
                continue  # 出错时跳过该对象，继续检测其他对象
    
    return False


def check_collision_hierarchical(new_shape: Any, 
                                 new_itz_shape: Optional[Any], 
                                 existing_shapes_and_itzs: List[Any], 
                                 min_distance: float, 
                                 quadtree: Optional[Any] = None, 
                                 use_gpu: bool = False) -> bool:
    """
    层次化碰撞检测：先边界框快速排除，再精确碰撞检测。
    
    Args:
        new_shape: 新骨料的Shapely几何对象
        new_itz_shape: 新骨料ITZ的Shapely几何对象，可为None
        existing_shapes_and_itzs: 包含所有已存在骨料和ITZ的Shapely对象列表
        min_distance: 最小间距
        quadtree: 可选的空间索引对象，用于优化碰撞检测
        use_gpu: 是否使用GPU加速碰撞检测
        
    Returns:
        bool: 如果发生碰撞返回True，否则返回False
    """
    # 第一步：使用空间索引（如果可用）缩小检查范围
    if quadtree is not None:
        temp_obj = {'shapely_obj': new_shape}
        potential_collisions = quadtree.query_shapely(new_shape, min_distance)
        
        # 从查询结果中提取Shapely对象
        potential_shapes = []
        for obj in potential_collisions:
            if 'shapely_obj' in obj:
                potential_shapes.append(obj['shapely_obj'])
            if 'shapely_itz' in obj and obj['shapely_itz']:
                potential_shapes.append(obj['shapely_itz'])
        
        if potential_shapes:
            existing_shapes_and_itzs = potential_shapes
    
    # 第二步：边界框快速检测
    new_bbox = new_shape.bounds
    expanded_bbox = (
        new_bbox[0] - min_distance,
        new_bbox[1] - min_distance,
        new_bbox[2] + min_distance,
        new_bbox[3] + min_distance
    )
    
    if new_itz_shape:
        itz_bbox = new_itz_shape.bounds
        expanded_bbox = (
            min(expanded_bbox[0], itz_bbox[0] - min_distance),
            min(expanded_bbox[1], itz_bbox[1] - min_distance),
            max(expanded_bbox[2], itz_bbox[2] + min_distance),
            max(expanded_bbox[3], itz_bbox[3] + min_distance)
        )
    
    possible_colliders = []
    
    if use_gpu and gpu_calculator.cuda_available:
        # 使用GPU加速边界框检测
        existing_bounds_list = [shape.bounds for shape in existing_shapes_and_itzs]
        potential_collisions = gpu_calculator.calculate_distances_gpu(
            expanded_bbox, existing_bounds_list, 0.0
        )
        
        # 收集可能碰撞的对象
        for i, collision in enumerate(potential_collisions):
            if collision:
                possible_colliders.append(existing_shapes_and_itzs[i])
    else:
        # 传统CPU边界框检测
        for shape in existing_shapes_and_itzs:
            shape_bbox = shape.bounds
            if not (expanded_bbox[2] < shape_bbox[0] or 
                    expanded_bbox[0] > shape_bbox[2] or 
                    expanded_bbox[3] < shape_bbox[1] or 
                    expanded_bbox[1] > shape_bbox[3]):
                possible_colliders.append(shape)
    
    # 第三步：精确碰撞检测
    for shape in possible_colliders:
        try:
            if new_shape.distance(shape) < min_distance:
                return True
            if new_itz_shape and new_itz_shape.distance(shape) < min_distance:
                return True
        except Exception as e:
            logging.warning(f"精确碰撞检测时出错: {str(e)}")
            continue
    
    return False