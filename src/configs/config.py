# config.py

from enum import Enum
from typing import Dict

class SpecimenType(Enum):
    """试件类型枚举"""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"

class CADColorMap:
    """AutoCAD颜色映射"""
    RED = 1
    YELLOW = 2
    GREEN = 3
    CYAN = 4
    BLUE = 5
    MAGENTA = 6
    WHITE = 7

    @staticmethod
    def get_color_map() -> Dict[str, int]:
        """获取颜色映射字典"""
        return {
            "红色": CADColorMap.RED,
            "黄色": CADColorMap.YELLOW,
            "绿色": CADColorMap.GREEN,
            "青色": CADColorMap.CYAN,
            "蓝色": CADColorMap.BLUE,
            "紫色": CADColorMap.MAGENTA,
            "白色": CADColorMap.WHITE
        }

# 默认参数
DEFAULT_SPECIMEN_TYPE = SpecimenType.RECTANGLE
DEFAULT_REGION = (0, 0, 100, 100)
DEFAULT_CIRCLE_DIAMETER = 100.0
DEFAULT_MIN_DISTANCE = 0.0
DEFAULT_TARGET_POROSITY = 25.0
DEFAULT_MAX_ATTEMPTS = 100
DEFAULT_MAX_AGGREGATES = 500
DEFAULT_ITERATION_LIMIT = 1000
DEFAULT_BOUNDARY_COLOR = "红色"
DEFAULT_BOUNDARY_OPTIMIZE = True
DEFAULT_BOUNDARY_STRENGTH = 1.0
DEFAULT_ALLOW_TOUCHING = True

# 形状默认参数
DEFAULT_SHAPE_POLYGON = {
    'type': 'polygon',
    'min_size': 2.0,
    'max_size': 8.0,
    'min_sides': 3,
    'max_sides': 7,
    'irregularity': 0.3,
    'spikiness': 0.2,
    'weight': 1,
    'optimize_sides': True,
    'min_edge_length': None
}

DEFAULT_SHAPE_CIRCLE = {
    'type': 'circle',
    'min_radius': 2.0,
    'max_radius': 5.0,
    'segments': 36,
    'weight': 1
}

DEFAULT_SHAPE_ELLIPSE = {
    'type': 'ellipse',
    'min_major': 3.0,
    'max_major': 10.0,
    'min_minor': 2.0,
    'max_minor': 8.0,
    'segments': 36,
    'weight': 1
}

# 组默认参数
DEFAULT_GROUP = {
    'area_ratio': 20.0,
    'itz_thickness': 1.0,
    'max_count': 200,
    'layer_color': "红色"
}
