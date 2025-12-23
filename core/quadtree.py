# core/quadtree.py

import logging
from typing import List, Tuple, Dict, Any, Optional, Union
from shapely.geometry import Polygon

class QuadtreeNode:
    def __init__(self, bounds: Tuple[float, float, float, float], depth: int = 0, max_depth: int = 5, max_objects: int = 10):
        """
        四叉树节点初始化
        
        Args:
            bounds: 节点边界 (min_x, min_y, max_x, max_y)
            depth: 当前节点深度
            max_depth: 最大深度
            max_objects: 节点内最大对象数，超过则分裂
        """
        self.bounds = bounds
        self.depth = depth
        self.max_depth = max_depth
        self.max_objects = max_objects
        self.objects: List[Dict[str, Any]] = []
        self.children: List[Optional[QuadtreeNode]] = [None, None, None, None]  # 四个子节点：NW, NE, SW, SE
        self.is_divided = False
    
    def _divide(self) -> None:
        """
        分裂节点为四个子节点
        """
        if self.is_divided:
            return
        
        min_x, min_y, max_x, max_y = self.bounds
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        
        # 创建四个子节点
        self.children[0] = QuadtreeNode((min_x, mid_y, mid_x, max_y), self.depth + 1, self.max_depth, self.max_objects)  # NW
        self.children[1] = QuadtreeNode((mid_x, mid_y, max_x, max_y), self.depth + 1, self.max_depth, self.max_objects)  # NE
        self.children[2] = QuadtreeNode((min_x, min_y, mid_x, mid_y), self.depth + 1, self.max_depth, self.max_objects)  # SW
        self.children[3] = QuadtreeNode((mid_x, min_y, max_x, mid_y), self.depth + 1, self.max_depth, self.max_objects)  # SE
        
        self.is_divided = True
    
    def insert(self, obj: Dict[str, Any]) -> bool:
        """
        插入对象到四叉树
        
        Args:
            obj: 要插入的对象，必须包含shapely_obj或shapely_itz属性
        
        Returns:
            bool: 是否成功插入
        """
        # 检查对象是否在当前节点边界内
        shapely_obj = obj.get('shapely_obj') or obj.get('shapely_itz')
        if not shapely_obj:
            return False
        
        obj_bounds = shapely_obj.bounds
        if not self._intersects_bounds(obj_bounds):
            return False
        
        # 如果当前节点未分裂且对象数量未达上限，直接插入
        if not self.is_divided and len(self.objects) < self.max_objects:
            self.objects.append(obj)
            return True
        
        # 如果未分裂且达到上限，分裂节点
        if not self.is_divided:
            self._divide()
        
        # 尝试插入到子节点
        inserted = False
        for child in self.children:
            if child and child.insert(obj):
                inserted = True
        
        # 如果无法插入到任何子节点，保留在当前节点
        if not inserted:
            self.objects.append(obj)
        
        return True
    
    def query_range(self, bounds: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """
        查询指定边界内的所有对象
        
        Args:
            bounds: 查询边界 (min_x, min_y, max_x, max_y)
        
        Returns:
            List[Dict[str, Any]]: 查询到的对象列表
        """
        results: List[Dict[str, Any]] = []
        
        # 如果查询边界与当前节点边界不相交，返回空列表
        if not self._intersects_bounds(bounds):
            return results
        
        # 检查当前节点中的对象
        for obj in self.objects:
            shapely_obj = obj.get('shapely_obj') or obj.get('shapely_itz')
            obj_bounds = shapely_obj.bounds
            if self._intersects_bounds(obj_bounds, bounds):
                results.append(obj)
        
        # 递归检查子节点
        if self.is_divided:
            for child in self.children:
                if child:
                    results.extend(child.query_range(bounds))
        
        return results
    
    def _intersects_bounds(self, bounds1: Tuple[float, float, float, float], 
                          bounds2: Optional[Tuple[float, float, float, float]] = None) -> bool:
        """
        检查两个边界是否相交
        
        Args:
            bounds1: 第一个边界 (min_x, min_y, max_x, max_y)
            bounds2: 第二个边界，默认为当前节点边界
        
        Returns:
            bool: 是否相交
        """
        if bounds2 is None:
            bounds2 = self.bounds
        
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
        
        if self.is_divided:
            for child in self.children:
                if child:
                    child.clear()
                    child = None
            self.children = [None, None, None, None]
            self.is_divided = False

class Quadtree:
    def __init__(self, bounds: Tuple[float, float, float, float], max_depth: int = 5, max_objects: int = 10):
        """
        四叉树初始化
        
        Args:
            bounds: 四叉树边界 (min_x, min_y, max_x, max_y)
            max_depth: 最大深度
            max_objects: 节点内最大对象数
        """
        self.root = QuadtreeNode(bounds, max_depth=max_depth, max_objects=max_objects)
        self.bounds = bounds
    
    def insert(self, obj: Dict[str, Any]) -> bool:
        """
        插入对象到四叉树
        
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
        清除四叉树中的所有对象
        """
        self.root.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取四叉树统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        def _count_nodes(node: QuadtreeNode) -> Tuple[int, int]:
            """递归计算节点数和对象数"""
            node_count = 1
            obj_count = len(node.objects)
            
            if node.is_divided:
                for child in node.children:
                    if child:
                        child_nodes, child_objs = _count_nodes(child)
                        node_count += child_nodes
                        obj_count += child_objs
            
            return node_count, obj_count
        
        total_nodes, total_objects = _count_nodes(self.root)
        return {
            'total_nodes': total_nodes,
            'total_objects': total_objects,
            'max_depth': self.root.max_depth,
            'max_objects_per_node': self.root.max_objects
        }
