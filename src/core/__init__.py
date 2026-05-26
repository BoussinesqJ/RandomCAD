# 核心模块

from .cad_connection import CADConnection
from .generator import RandomAggregateGenerator
from .shapes import generate_random_polygon, generate_circle, generate_ellipse
from .collision import check_collision_hierarchical, GPUDistanceCalculator
from .group_manager import GroupManager
from .quadtree import Quadtree
from .kd_tree import KDTree

__all__ = [
    'CADConnection',
    'RandomAggregateGenerator',
    'generate_random_polygon',
    'generate_circle',
    'generate_ellipse',
    'check_collision_hierarchical',
    'GPUDistanceCalculator',
    'GroupManager',
    'Quadtree',
    'KDTree'
]
