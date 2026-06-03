# spatial_index.py
# 空间索引统一接口定义

from typing import List, Tuple, Dict, Any, Protocol, runtime_checkable


@runtime_checkable
class SpatialIndex(Protocol):
    """
    空间索引统一接口
    
    Quadtree 和 KDTree 都实现此协议，可互换使用。
    """
    
    def insert(self, obj: Dict[str, Any]) -> bool:
        """插入单个对象"""
        ...
    
    def insert_batch(self, objects: List[Dict[str, Any]]) -> int:
        """批量插入对象"""
        ...
    
    def query_range(self, bounds: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """按范围查询"""
        ...
    
    def query_shapely(self, shapely_obj: Any, min_distance: float = 0.0) -> List[Dict[str, Any]]:
        """按 Shapely 对象查询"""
        ...
    
    def clear(self) -> None:
        """清空索引"""
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        ...
