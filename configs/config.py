# config.py

# --- AutoCAD 颜色映射 ---
CAD_COLOR_MAP = {
    "红色": 1,
    "黄色": 2,
    "绿色": 3,
    "青色": 4,
    "蓝色": 5,
    "紫色": 6,
    "白色": 7
}

# --- 试件类型配置 ---
class SpecimenType:
    RECTANGLE = "rectangle"
    CIRCLE = "circle"

# --- 默认参数 ---
DEFAULT_SPECIMEN_TYPE = SpecimenType.RECTANGLE  # 默认试件类型
DEFAULT_REGION = (0, 0, 100, 100)  # 长方形: (min_x, min_y, max_x, max_y)
DEFAULT_CIRCLE_DIAMETER = 100.0  # 圆形直径
DEFAULT_MIN_DISTANCE = 0.0  # 默认允许直接接触
DEFAULT_TARGET_POROSITY = 25.0
DEFAULT_MAX_ATTEMPTS = 100
DEFAULT_MAX_AGGREGATES = 500
DEFAULT_ITERATION_LIMIT = 1000  # 迭代指数限制，防止死循环
DEFAULT_BOUNDARY_COLOR = "红色"
DEFAULT_BOUNDARY_OPTIMIZE = True
DEFAULT_BOUNDARY_STRENGTH = 1.0
DEFAULT_ALLOW_TOUCHING = True  # 默认允许颗粒直接接触

# --- 形状默认参数 ---
DEFAULT_SHAPE_POLYGON = {
    'type': 'polygon',
    'min_size': 2.0,
    'max_size': 8.0,
    'min_sides': 3,
    'max_sides': 7,
    'irregularity': 0.3,
    'spikiness': 0.2,
    'weight': 1,
    'optimize_sides': True,  # 是否优化小边
    'min_edge_length': None  # 最小边长度，默认自动计算
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

# --- 组默认参数 ---
DEFAULT_GROUP = {
    'area_ratio': 20.0,  # 面积占比 (%)
    'itz_thickness': 1.0, # ITZ 厚度 (mm)
    'max_count': 200,     # 最大数量 (安全限制)
    'layer_color': "红色" # 图层颜色
}