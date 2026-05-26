# collision.py

import logging
from typing import List, Optional, Any

try:
    from shapely.geometry import Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    logging.warning("Shapely未安装，碰撞检测功能将受限")


class GPUDistanceCalculator:
    """
    GPU加速的距离计算器，用于加速碰撞检测
    """
    def __init__(self):
        self.cuda_available = False
        self.torch = None
        self.device = None
        
        try:
            import torch
            self.torch = torch
            self.cuda_available = torch.cuda.is_available()
            self.device = self.torch.device("cuda" if self.cuda_available else "cpu")
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
            new_bounds_tensor = self.torch.tensor(new_shape_bounds, device=self.device, dtype=self.torch.float32)
            existing_bounds_tensor = self.torch.tensor(existing_bounds_list, device=self.device, dtype=self.torch.float32)
            
            expanded_min_x = new_bounds_tensor[0] - min_distance
            expanded_min_y = new_bounds_tensor[1] - min_distance
            expanded_max_x = new_bounds_tensor[2] + min_distance
            expanded_max_y = new_bounds_tensor[3] + min_distance
            
            collision_mask = ~(
                (expanded_max_x < existing_bounds_tensor[:, 0]) |
                (expanded_min_x > existing_bounds_tensor[:, 2]) |
                (expanded_max_y < existing_bounds_tensor[:, 1]) |
                (expanded_min_y > existing_bounds_tensor[:, 3])
            )
            
            return collision_mask.cpu().tolist()
        except Exception as e:
            logging.warning(f"GPU距离计算出错，回退到CPU: {str(e)}")
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

gpu_calculator = GPUDistanceCalculator()

def check_collision_hierarchical(new_shape: Any, 
                                 new_itz_shape: Optional[Any], 
                                 existing_shapes_and_itzs: List[Any], 
                                 min_distance: float, 
                                 quadtree: Optional[Any] = None, 
                                 use_gpu: bool = False, 
                                 allow_touching: bool = True) -> bool:
    """
    层次化碰撞检测：先边界框快速排除，再精确碰撞检测。
    
    Args:
        new_shape: 新骨料的Shapely几何对象
        new_itz_shape: 新骨料ITZ的Shapely几何对象，可为None
        existing_shapes_and_itzs: 包含所有已存在骨料和ITZ的Shapely对象列表
        min_distance: 最小间距
        quadtree: 可选的空间索引对象，用于优化碰撞检测
        use_gpu: 是否使用GPU加速碰撞检测
        allow_touching: 是否允许颗粒直接接触，True表示允许接触，False表示必须保持最小距离
        
    Returns:
        bool: 如果发生碰撞返回True，否则返回False
    """
    if not SHAPELY_AVAILABLE:
        logging.error("Shapely未安装，无法进行碰撞检测")
        return True
    
    if quadtree is not None:
        query_obj = new_itz_shape if new_itz_shape else new_shape
        temp_obj = {'shapely_obj': new_shape}
        potential_collisions = quadtree.query_shapely(query_obj, min_distance)
        
        potential_shapes = []
        for obj in potential_collisions:
            if 'shapely_obj' in obj:
                potential_shapes.append(obj['shapely_obj'])
            if 'shapely_itz' in obj and obj['shapely_itz']:
                potential_shapes.append(obj['shapely_itz'])
        
        if potential_shapes:
            existing_shapes_and_itzs = potential_shapes
    
    if new_itz_shape:
        main_bbox = new_itz_shape.bounds
        expanded_bbox = (
            main_bbox[0] - min_distance,
            main_bbox[1] - min_distance,
            main_bbox[2] + min_distance,
            main_bbox[3] + min_distance
        )
    else:
        main_bbox = new_shape.bounds
        expanded_bbox = (
            main_bbox[0] - min_distance,
            main_bbox[1] - min_distance,
            main_bbox[2] + min_distance,
            main_bbox[3] + min_distance
        )
    
    possible_colliders = []
    
    if use_gpu and gpu_calculator.cuda_available:
        existing_bounds_list = [shape.bounds for shape in existing_shapes_and_itzs]
        potential_collisions = gpu_calculator.calculate_distances_gpu(
            expanded_bbox, existing_bounds_list, 0.0
        )
        
        for i, collision in enumerate(potential_collisions):
            if collision:
                possible_colliders.append(existing_shapes_and_itzs[i])
    else:
        for shape in existing_shapes_and_itzs:
            shape_bbox = shape.bounds
            if not (expanded_bbox[2] < shape_bbox[0] or 
                    expanded_bbox[0] > shape_bbox[2] or 
                    expanded_bbox[3] < shape_bbox[1] or 
                    expanded_bbox[1] > shape_bbox[3]):
                possible_colliders.append(shape)
    
    for shape in possible_colliders:
        try:
            if new_shape.intersects(shape):
                return True
            
            if new_itz_shape:
                if new_itz_shape.intersects(shape):
                    return True
        except Exception as e:
            logging.warning(f"精确碰撞检测时出错: {str(e)}")
            continue
    
    return False
