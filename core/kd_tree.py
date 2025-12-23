# core/kd_tree.py

import logging
from typing import List, Tuple, Dict, Any, Optional, Union
from shapely.geometry import Polygon

class KDTreeNode:
    def __init__(self, objects: List[Dict[str, Any]], depth: int = 0, max_objects: int = 10, max_depth: int = 10):
        """
        KD树节点初始化
        
        Args:
            objects: 该节点包含的对象列表
            depth: 当前节点深度
            max_objects: 节点内最大对象数，超过则分裂
            max_depth: 最大深度限制
        """
        self.depth = depth
        self.max_objects = max_objects
        self.max_depth = max_depth
        self.objects: List[Dict[str, Any]] = objects
        self.left: Optional[KDTreeNode] = None
        self.right: Optional[KDTreeNode] = None
        self.axis: int = depth % 2  # 0 for x-axis, 1 for y-axis
        self.bounds: Optional[Tuple[float, float, float, float]] = None
        self.median: Optional[float] = None
        
        # 计算节点边界
        self._calculate_bounds()
        
        # 如果达到分裂条件，进行分裂
        if len(self.objects) > self.max_objects and self.depth < self.max_depth:
            self._split()
    
    def _calculate_bounds(self) -> None:
        """
        计算节点的边界框
        """
        if not self.objects:
            self.bounds = None
            return
        
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for obj in self.objects:
            shapely_obj = obj.get('shapely_obj') or obj.get('shapely_itz')
            if shapely_obj:
                obj_bounds = shapely_obj.bounds
                min_x = min(min_x, obj_bounds[0])
                min_y = min(min_y, obj_bounds[1])
                max_x = max(max_x, obj_bounds[2])
                max_y = max(max_y, obj_bounds[3])
        
        self.bounds = (min_x, min_y, max_x, max_y)
    
    def _split(self) -> None:
        """
        分裂节点为左右子节点
        """
        if not self.objects:
            return
        
        # 按当前轴排序对象
        self.objects.sort(key=lambda obj: self._get_object_center(obj)[self.axis])
        
        # 选择中位数
        median_idx = len(self.objects) // 2
        self.median = self._get_object_center(self.objects[median_idx])[self.axis]
        
        # 分裂为左右子树
        left_objects = self.objects[:median_idx]
        right_objects = self.objects[median_idx:]
        
        self.left = KDTreeNode(left_objects, self.depth + 1, self.max_objects, self.max_depth)
        self.right = KDTreeNode(right_objects, self.depth + 1, self.max_objects, self.max_depth)
        
        # 清空当前节点的对象列表，因为它们现在存储在子节点中
        self.objects = []
    
    def _get_object_center(self, obj: Dict[str, Any]) -> Tuple[float, float]:
        """
        获取对象的中心点
        
        Args:
            obj: 包含shapely_obj或center属性的对象
        
        Returns:
            Tuple[float, float]: 对象中心点坐标
        """
        if 'center' in obj:
            return obj['center']
        
        shapely_obj = obj.get('shapely_obj') or obj.get('shapely_itz')
        if shapely_obj:
            obj_bounds = shapely_obj.bounds
            center_x = (obj_bounds[0] + obj_bounds[2]) / 2
            center_y = (obj_bounds[1] + obj_bounds[3]) / 2
            return (center_x, center_y)
        
        return (0.0, 0.0)
    
    def insert(self, obj: Dict[str, Any]) -> bool:
        """
        插入对象到KD树
        
        Args:
            obj: 要插入的对象
        
        Returns:
            bool: 是否成功插入
        """
        # 如果是叶子节点，直接插入
        if not self.left and not self.right:
            self.objects.append(obj)
            # 重新计算边界
            self._calculate_bounds()
            
            # 如果超过分裂条件，进行分裂
            if len(self.objects) > self.max_objects and self.depth < self.max_depth:
                self._split()
            return True
        
        # 非叶子节点，根据当前轴和中位数决定插入到左还是右子树
        if self.median is not None:
            obj_center = self._get_object_center(obj)
            if obj_center[self.axis] < self.median:
                if self.left:
                    return self.left.insert(obj)
            else:
                if self.right:
                    return self.right.insert(obj)
        
        return False
    
    def query_range(self, bounds: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """
        查询指定边界内的所有对象
        
        Args:
            bounds: 查询边界 (min_x, min_y, max_x, max_y)
        
        Returns:
            List[Dict[str, Any]]: 查询到的对象列表
        """
        results: List[Dict[str, Any]] = []
        
        # 检查当前节点边界是否与查询边界相交
        if not self.bounds or not self._intersects_bounds(self.bounds, bounds):
            return results
        
        # 如果是叶子节点，检查所有对象
        if not self.left and not self.right:
            for obj in self.objects:
                shapely_obj = obj.get('shapely_obj') or obj.get('shapely_itz')
                if shapely_obj:
                    obj_bounds = shapely_obj.bounds
                    if self._intersects_bounds(obj_bounds, bounds):
                        results.append(obj)
            return results
        
        # 非叶子节点，递归查询左右子树
        if self.left:
            results.extend(self.left.query_range(bounds))
        if self.right:
            results.extend(self.right.query_range(bounds))
        
        return results
    
    def _intersects_bounds(self, bounds1: Tuple[float, float, float, float], 
                          bounds2: Tuple[float, float, float, float]) -> bool:
        """
        检查两个边界是否相交
        
        Args:
            bounds1: 第一个边界 (min_x, min_y, max_x, max_y)
            bounds2: 第二个边界 (min_x, min_y, max_x, max_y)
        
        Returns:
            bool: 是否相交
        """
        min_x1, min_y1, max_x1, max_y1 = bounds1
        min_x2, min_y2, max_x2, max_y2 = bounds2
        
        # 不相交的情况
        if max_x1 < min_x2 or min_x1 > max_x2 or max_y1 < min_y2 or min_y1 > max_y2:
            return False
        
        return True
    
    def clear(self) -> None:
        """
        清除节点及其子节点中的所有对象
        """
        self.objects.clear()
        
        if self.left:
            self.left.clear()
            self.left = None
        if self.right:
            self.right.clear()
            self.right = None
        
        self.bounds = None
        self.median = None

class KDTree:
    def __init__(self, bounds: Tuple[float, float, float, float], max_depth: int = 10, max_objects: int = 10):
        """
        KD树初始化
        
        Args:
            bounds: 树的初始边界 (min_x, min_y, max_x, max_y)
            max_depth: 最大深度
            max_objects: 节点内最大对象数
        """
        self.root = KDTreeNode([], max_depth=max_depth, max_objects=max_objects)
        self.bounds = bounds
        self.max_depth = max_depth
        self.max_objects = max_objects
    
    def insert(self, obj: Dict[str, Any]) -> bool:
        """
        插入对象到KD树
        
        Args:
            obj: 要插入的对象
        
        Returns:
            bool: 是否成功插入
        """
        return self.root.insert(obj)
    
    def insert_batch(self, objects: List[Dict[str, Any]]) -> int:
        """
        批量插入对象
        
        Args:
            objects: 要插入的对象列表
        
        Returns:
            int: 成功插入的对象数
        """
        count = 0
        for obj in objects:
            if self.insert(obj):
                count += 1
        return count
    
    def query_range(self, bounds: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """
        查询指定边界内的所有对象
        
        Args:
            bounds: 查询边界 (min_x, min_y, max_x, max_y)
        
        Returns:
            List[Dict[str, Any]]: 查询到的对象列表
        """
        return self.root.query_range(bounds)
    
    def query_shapely(self, shapely_obj: Any, min_distance: float = 0.0) -> List[Dict[str, Any]]:
        """
        查询与指定Shapely对象可能碰撞的所有对象
        
        Args:
            shapely_obj: Shapely几何对象
            min_distance: 最小距离，用于扩展查询边界
        
        Returns:
            List[Dict[str, Any]]: 可能碰撞的对象列表
        """
        obj_bounds = shapely_obj.bounds
        # 扩展边界以包含最小距离
        expanded_bounds = (
            obj_bounds[0] - min_distance,
            obj_bounds[1] - min_distance,
            obj_bounds[2] + min_distance,
            obj_bounds[3] + min_distance
        )
        return self.query_range(expanded_bounds)
    
    def clear(self) -> None:
        """
        清除KD树中的所有对象
        """
        self.root.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取KD树统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        def _count_nodes(node: KDTreeNode) -> Tuple[int, int, int]:
            """递归计算节点数、对象数和最大深度"""
            node_count = 1
            obj_count = len(node.objects)
            max_depth = node.depth
            
            if node.left:
                left_nodes, left_objs, left_max_depth = _count_nodes(node.left)
                node_count += left_nodes
                obj_count += left_objs
                max_depth = max(max_depth, left_max_depth)
            
            if node.right:
                right_nodes, right_objs, right_max_depth = _count_nodes(node.right)
                node_count += right_nodes
                obj_count += right_objs
                max_depth = max(max_depth, right_max_depth)
            
            return node_count, obj_count, max_depth
        
        total_nodes, total_objects, max_depth = _count_nodes(self.root)
        return {
            'total_nodes': total_nodes,
            'total_objects': total_objects,
            'max_depth': max_depth,
            'max_objects_per_node': self.max_objects
        }
