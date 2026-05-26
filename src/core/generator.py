# generator.py

import random
import time
import math
import logging
import threading
from typing import List, Tuple, Dict, Any, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .shapes import generate_random_polygon, generate_circle, generate_ellipse
from .collision import check_collision_hierarchical, gpu_calculator
from .group_manager import GroupManager
from .quadtree import Quadtree
from .kd_tree import KDTree
from .cad_connection import CADConnection, ConnectionState
from ..utils import (
    calculate_polygon_area, calculate_circle_area, calculate_ellipse_area,
    calculate_bounding_circle, is_near_boundary, move_toward_boundary,
    adjust_points_to_boundary
)
from ..configs.config import (
    SpecimenType, CADColorMap, DEFAULT_SPECIMEN_TYPE,
    DEFAULT_CIRCLE_DIAMETER, DEFAULT_ITERATION_LIMIT
)

try:
    from pyautocad import APoint, aDouble
    PYAUTOCAD_AVAILABLE = True
except ImportError:
    PYAUTOCAD_AVAILABLE = False
    logging.warning("pyautocad未安装")

try:
    from shapely.geometry import Polygon as ShapelyPolygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    logging.warning("Shapely未安装")


class RandomAggregateGenerator:
    """
    随机骨料生成器
    
    功能：
    - 支持多种骨料形状（多边形、圆形、椭圆形）
    - 支持多组粒径配置
    - 支持ITZ（界面过渡区）生成
    - 支持空间索引优化（四叉树/KD树）
    - 支持并行计算和GPU加速
    - 支持AutoCAD集成
    """
    
    def __init__(self, auto_start: bool = True, cad_type: str = "autocad"):
        """
        初始化随机骨料生成器
        
        Args:
            auto_start: 如果CAD未运行，是否自动启动
            cad_type: CAD类型，可选值: "autocad", "zwcad"
        """
        self.cad_connection = CADConnection(auto_start=auto_start, cad_type=cad_type)
        
        self.generation_mode: str = "count"
        self.target_porosity: float = 0.0
        self.generated_aggregates: List[Dict[str, Any]] = []
        self.groups = GroupManager()
        self.itz_layers: List[Any] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.allow_touching: bool = True
        self.total_area: float = 0.0
        self.region_area: float = 0.0
        self.region_boundary: Any = None
        self.boundary_color: int = CADColorMap.WHITE
        self.boundary_min: Optional[Tuple[float, float]] = None
        self.boundary_max: Optional[Tuple[float, float]] = None
        self.generation_canceled: bool = False
        self.last_progress_time: float = 0.0
        self.draw_objects: List[Any] = []
        
        self.specimen_type: str = DEFAULT_SPECIMEN_TYPE
        self.rectangle_region: Tuple[float, float, float, float] = (0, 0, 100, 100)
        self.circle_diameter: float = DEFAULT_CIRCLE_DIAMETER
        self.circle_center: Tuple[float, float] = (50, 50)
        
        self.iteration_limit: int = DEFAULT_ITERATION_LIMIT
        self.current_iteration: int = 0
        
        self.space_partitioning: str = "quadtree"
        self.spatial_index: Optional[Union[Quadtree, KDTree]] = None
        
        self.executor: Optional[ThreadPoolExecutor] = None
        self.max_workers: int = 4
        
        self.use_gpu: bool = False
        self.cuda_available: bool = gpu_calculator.cuda_available
        
        self._check_cuda_availability()
        if auto_start:
            self._connect_to_cad()
    
    def _check_cuda_availability(self) -> None:
        """
        检查CUDA是否可用
        """
        if self.cuda_available:
            logging.info("CUDA可用，将使用GPU加速碰撞检测")
        else:
            logging.info("CUDA不可用，将使用CPU计算")
    
    def _connect_to_cad(self) -> None:
        """
        连接到AutoCAD
        """
        if not self.cad_connection.connect():
            logging.error("无法连接到AutoCAD")
            raise ConnectionError("无法连接到AutoCAD")
    
    @property
    def acad(self):
        """
        获取AutoCAD对象（向后兼容）
        """
        return self.cad_connection.acad
    
    @property
    def doc(self):
        """
        获取AutoCAD文档对象（向后兼容）
        """
        return self.cad_connection.doc
    
    @property
    def model_space(self):
        """
        获取模型空间对象（向后兼容）
        """
        return self.cad_connection.model_space
    
    def set_space_partitioning(self, method: str) -> None:
        """
        设置空间划分算法
        
        Args:
            method: 空间划分算法，可选值: quadtree, kdtree
        """
        if method in ["quadtree", "kdtree"]:
            self.space_partitioning = method
            logging.info(f"已设置空间划分算法: {method}")
        else:
            logging.warning(f"未知的空间划分算法: {method}，将使用默认值 quadtree")
    
    def set_use_gpu(self, use_gpu: bool) -> None:
        """
        设置是否使用GPU加速
        
        Args:
            use_gpu: 是否使用GPU加速
        """
        self.use_gpu = use_gpu and self.cuda_available
        if self.use_gpu:
            logging.info("将使用GPU加速碰撞检测")
        else:
            logging.info("将使用CPU进行计算")
    
    def set_specimen_type(self, specimen_type: str, params: Dict[str, Any]) -> None:
        """
        设置试件类型
        
        Args:
            specimen_type: 试件类型，可选值: rectangle, circle
            params: 试件参数
                - rectangle: {"region": (min_x, min_y, max_x, max_y)}
                - circle: {"center": (x, y), "diameter": float}
        """
        self.specimen_type = specimen_type
        
        if specimen_type == SpecimenType.RECTANGLE:
            self.rectangle_region = params.get("region", (0, 0, 100, 100))
            self.boundary_min = (self.rectangle_region[0], self.rectangle_region[1])
            self.boundary_max = (self.rectangle_region[2], self.rectangle_region[3])
            width = self.rectangle_region[2] - self.rectangle_region[0]
            height = self.rectangle_region[3] - self.rectangle_region[1]
            self.region_area = width * height
        
        elif specimen_type == SpecimenType.CIRCLE:
            self.circle_center = params.get("center", (50, 50))
            self.circle_diameter = params.get("diameter", DEFAULT_CIRCLE_DIAMETER)
            radius = self.circle_diameter / 2
            self.boundary_min = (self.circle_center[0] - radius, self.circle_center[1] - radius)
            self.boundary_max = (self.circle_center[0] + radius, self.circle_center[1] + radius)
            self.region_area = math.pi * radius * radius
        
        logging.info(f"已设置试件类型: {specimen_type}，区域面积: {self.region_area:.2f}")
    
    def check_point_in_specimen(self, point: Tuple[float, float]) -> bool:
        """
        检查点是否在试件范围内
        
        Args:
            point: 要检查的点 (x, y)
            
        Returns:
            bool: 点在试件范围内返回True，否则返回False
        """
        x, y = point
        
        if self.specimen_type == SpecimenType.RECTANGLE:
            min_x, min_y, max_x, max_y = self.rectangle_region
            return min_x <= x <= max_x and min_y <= y <= max_y
        
        elif self.specimen_type == SpecimenType.CIRCLE:
            center_x, center_y = self.circle_center
            radius = self.circle_diameter / 2
            distance = math.hypot(x - center_x, y - center_y)
            return distance <= radius
        
        return False
    
    def set_groups(self, groups_config: List[Dict[str, Any]]) -> None:
        """
        设置多组粒径配置
        
        Args:
            groups_config: 组配置列表
        """
        self.groups.set_config(groups_config)
        logging.info(f"设置 {len(groups_config)} 个粒径组")

    def set_generation_mode(self, mode: str) -> None:
        """
        设置生成模式
        
        Args:
            mode: 生成模式，可选值："count"（按数量）、"porosity"（按孔隙度）
        """
        if mode not in ["count", "porosity"]:
            raise ValueError(f"无效的生成模式: {mode}，必须是 'count' 或 'porosity'")
        self.generation_mode = mode

    def set_target_porosity(self, porosity: float) -> None:
        """
        设置目标孔隙度
        
        Args:
            porosity: 目标孔隙度，范围0-100
        """
        if porosity < 0 or porosity > 100:
            raise ValueError("目标孔隙度必须在0到100之间")
        self.target_porosity = porosity / 100.0

    def cancel_generation(self) -> None:
        """
        取消生成过程
        """
        self.generation_canceled = True
        if self.cad_connection.is_connected:
            self.cad_connection.prompt("用户取消生成过程\n")
        logging.info("用户取消生成过程")

    def set_boundary_color(self, color_name: str) -> None:
        """
        设置边界颜色
        
        Args:
            color_name: 颜色名称
        """
        color_map = CADColorMap.get_color_map()
        self.boundary_color = color_map.get(color_name, CADColorMap.WHITE)

    def generate_aggregates_in_region(self, region_min: Tuple[float, float], 
                                      region_max: Tuple[float, float],
                                      min_distance: float = 1.0,
                                      max_attempts: int = 100,
                                      boundary_adjust: bool = True,
                                      progress_callback: Optional[Callable] = None,
                                      draw_callback: Optional[Callable] = None,
                                      allow_touching: bool = True) -> int:
        """
        生成骨料
        
        Args:
            region_min: 区域左下角坐标 (x, y)
            region_max: 区域右上角坐标 (x, y)
            min_distance: 骨料之间的最小间距
            max_attempts: 每组的最大尝试次数
            boundary_adjust: 是否进行边界优化
            progress_callback: 进度更新回调
            draw_callback: 绘图命令回调
            allow_touching: 是否允许颗粒直接接触
            
        Returns:
            int: 生成的骨料数量
        """
        try:
            min_x, min_y = region_min
            max_x, max_y = region_max
            if min_x >= max_x or min_y >= max_y:
                raise ValueError("区域坐标无效: 右上角坐标必须大于左下角坐标")
            
            self.start_time = time.time()
            self.total_area = 0.0
            self.generation_canceled = False
            
            region_width = max_x - min_x
            region_height = max_y - min_y
            self.region_area = region_width * region_height
            self.boundary_min = (min_x, min_y)
            self.boundary_max = (max_x, max_y)
            
            self._clear_old_boundary()
            self._create_boundary(min_x, min_y, max_x, max_y, draw_callback)
            
            # 创建 ITZ 分图层
            self.cad_connection.create_layer("RandomCAD-Boundary", 7)
            self.cad_connection.create_layer("RandomCAD-Aggregates", 7)
            self.cad_connection.create_layer("RandomCAD-ITZ", 4)
            
            max_possible_radius = self._calculate_max_possible_radius()
            avg_particle_size = max_possible_radius / 2.0
            
            dynamic_max_objects = max(5, int(20 / (avg_particle_size / 5.0)))
            dynamic_max_depth = max(5, min(10, int(8 + (5.0 / avg_particle_size))))
            
            logging.info(f"动态空间索引参数: max_depth={dynamic_max_depth}, max_objects={dynamic_max_objects}")
            
            spatial_bounds = (min_x, min_y, max_x, max_y)
            
            if self.space_partitioning == "kdtree":
                self.spatial_index = KDTree(spatial_bounds, max_depth=dynamic_max_depth, max_objects=dynamic_max_objects)
                logging.info("使用KD树作为空间索引")
            else:
                self.spatial_index = Quadtree(spatial_bounds, max_depth=dynamic_max_depth, max_objects=dynamic_max_objects)
                logging.info("使用四叉树作为空间索引")
            
            generated_count = 0
            total_attempts = 0
            last_update_time = time.time()
            last_success_time = time.time()
            consecutive_failures = 0
            MAX_CONSECUTIVE_FAILURES = 500
            STALL_TIMEOUT = 60  # 60秒内无成功生成则视为停滞
            
            self._initialize_group_targets()
            
            target_total_area = 0.0
            if self.generation_mode == "porosity":
                target_total_area = self.region_area * (1 - self.target_porosity)
                logging.info(f"孔隙度模式: 目标总骨料面积 {target_total_area:.2f}")
            
            self.allow_touching = allow_touching
            
            base_parallelism = self.max_workers
            dynamic_parallelism = max(2, min(8, int(base_parallelism * (1 + (5.0 / avg_particle_size)))))
            
            self.executor = ThreadPoolExecutor(max_workers=dynamic_parallelism)
            logging.info(f"创建线程池，初始并行度: {dynamic_parallelism}")
            
            self.last_parallelism_adjustment = time.time()
            self.parallelism_adjustment_interval = 5.0
            self.successful_generations_in_interval = 0
            self.attempts_in_interval = 0
            
            while True:
                if self.generation_canceled:
                    if progress_callback:
                        progress_callback("info", 0, 0.0, 0.0)
                    # 同时尝试发送文本消息到 CAD
                    if self.cad_connection.is_connected:
                        try:
                            self.cad_connection.prompt("生成过程已被用户取消\n")
                        except Exception:
                            pass
                    break

                if self._check_exit_conditions(target_total_area, max_attempts):
                    break
                
                # 停滞检测：连续失败或长时间无进展
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logging.warning(f"连续 {consecutive_failures} 次失败，生成空间可能已满，停止生成")
                    if progress_callback:
                        progress_callback("info", 0, 0.0, 0.0)
                    if self.cad_connection.is_connected:
                        try:
                            self.cad_connection.prompt("空间已满，生成停止\n")
                        except Exception:
                            pass
                    break
                
                if generated_count > 0 and time.time() - last_success_time > STALL_TIMEOUT:
                    logging.warning(f"超过 {STALL_TIMEOUT}s 无成功生成，停止生成")
                    if progress_callback:
                        progress_callback("info", 0, 0.0, 0.0)
                    break

                current_time = time.time()
                if current_time - last_update_time > 0.5 and progress_callback is not None:
                    progress_callback("progress", generated_count, self.total_area, self.calculate_porosity())
                    last_update_time = current_time

                chosen_group = self.groups.select_next_group(self.generation_mode)
                if not chosen_group:
                    break

                if self.generation_mode == "porosity" and target_total_area > 0:
                    progress_ratio = min(1.0, self.total_area / target_total_area)
                else:
                    group_progress = []
                    for group in self.groups.get_config():
                        if group['target_area'] > 0:
                            group_progress.append(min(1.0, group['generated_area'] / group['target_area']))
                    progress_ratio = sum(group_progress) / len(group_progress) if group_progress else 0
                
                base_attempts = dynamic_parallelism * 2
                dynamic_attempts = max(2, int(base_attempts * (1 - progress_ratio * 0.7)))
                
                futures = []
                
                for _ in range(dynamic_attempts):
                    future = self.executor.submit(
                        self._parallel_generate_attempt,
                        chosen_group, min_x, min_y, max_x, max_y, max_possible_radius,
                        min_distance, boundary_adjust
                    )
                    futures.append(future)
                
                agg_data = None
                timeout = 5.0
                
                for future in as_completed(futures, timeout=timeout):
                    try:
                        result = future.result(timeout=timeout)
                        if result is not None:
                            # 空间索引可用时跳过全量列表构建，让 quadtree 自行过滤
                            if self.spatial_index:
                                all_existing_objects = []
                            else:
                                all_existing_objects = []
                                for g in self.groups.get_config():
                                    all_existing_objects.extend(g['shapes_and_itz'])
                            
                            collision = check_collision_hierarchical(
                                result['shapely_obj'], result['shapely_itz'], 
                                all_existing_objects, min_distance, self.spatial_index, self.use_gpu,
                                self.allow_touching
                            )
                            
                            if not collision:
                                agg_data = result
                                for f in futures:
                                    if not f.done():
                                        f.cancel()
                                break
                    except Exception as e:
                        logging.warning(f"并行任务处理异常: {str(e)}")
                        continue
                
                if agg_data:
                    generated_count += 1
                    total_attempts = 0
                    consecutive_failures = 0
                    last_success_time = time.time()
                    self.successful_generations_in_interval += 1
                    self.attempts_in_interval += 1
                    
                    self._add_aggregate_to_spatial_index_and_collections(agg_data)
                    
                    if draw_callback:
                        self._send_draw_command(agg_data, chosen_group, draw_callback)
                        
                    if generated_count % 10 == 0 and time.time() - self.last_progress_time > 1.0:
                        if draw_callback:
                            draw_callback('regen',)
                        self.last_progress_time = time.time()
                else:
                    total_attempts += 1
                    consecutive_failures += 1
                    self.attempts_in_interval += 1
                
                current_time = time.time()
                if current_time - self.last_parallelism_adjustment > self.parallelism_adjustment_interval:
                    if self.attempts_in_interval > 0:
                        success_rate = self.successful_generations_in_interval / self.attempts_in_interval
                        
                        if success_rate > 0.7:
                            new_parallelism = min(12, dynamic_parallelism + 1)
                        elif success_rate < 0.3:
                            new_parallelism = max(2, dynamic_parallelism - 1)
                        else:
                            new_parallelism = dynamic_parallelism
                        
                        if new_parallelism != dynamic_parallelism:
                            dynamic_parallelism = new_parallelism
                            logging.info(f"自适应调整并行度: {dynamic_parallelism}, 成功率: {success_rate:.2f}")
                            self.executor.shutdown(wait=True)
                            self.executor = ThreadPoolExecutor(max_workers=dynamic_parallelism)
                    
                    self.successful_generations_in_interval = 0
                    self.attempts_in_interval = 0
                    self.last_parallelism_adjustment = current_time
            
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None
                logging.info("线程池已关闭")

        except Exception as e:
            logging.error(f"生成错误：{str(e)}", exc_info=True)
            raise
        finally:
            self.end_time = time.time()
            logging.info(f"生成完成，耗时: {self.end_time - self.start_time:.2f}秒")
        
        return len(self.generated_aggregates)

    def _clear_old_boundary(self) -> None:
        """
        删除旧边界
        """
        if self.region_boundary:
            try:
                self.cad_connection.delete_object(self.region_boundary)
                logging.info("已删除旧边界")
            except Exception as e:
                logging.warning(f"删除旧边界时出错: {str(e)}")
            self.region_boundary = None
            self.boundary_min = None
            self.boundary_max = None

    def _create_boundary(self, min_x: float, min_y: float, max_x: float, max_y: float, draw_callback: Any) -> None:
        """
        创建边界
        """
        try:
            boundary_points = [
                float(min_x), float(min_y), 0.0,
                float(max_x), float(min_y), 0.0,
                float(max_x), float(max_y), 0.0,
                float(min_x), float(max_y), 0.0,
                float(min_x), float(min_y), 0.0
            ]
            logging.info(f"创建边界点: {boundary_points}")
            if draw_callback:
                draw_callback(('boundary', boundary_points, self.boundary_color, "RandomCAD-Boundary"))
                logging.info("边界创建请求已放入队列")
        except Exception as e:
            if self.cad_connection.is_connected:
                self.cad_connection.prompt(f"警告: 创建边界失败 - {str(e)}\n")
            logging.error(f"创建边界失败: {str(e)}")

    def _calculate_max_possible_radius(self) -> float:
        """
        计算最大可能的半径（考虑所有组的所有形态）
        """
        max_radius = 0.0
        for group in self.groups.get_config():
            for shape in group['shapes']:
                if shape['type'] == 'polygon':
                    shape_max_radius = shape.get('max_size', 8.0) * 1.5
                elif shape['type'] == 'circle':
                    shape_max_radius = shape.get('max_radius', 8.0) * 1.5
                elif shape['type'] == 'ellipse':
                    shape_max_radius = max(shape.get('max_major', 10.0), shape.get('max_minor', 8.0)) * 1.5
                else:
                    continue
                    
                if shape_max_radius > max_radius:
                    max_radius = shape_max_radius
        return max_radius

    def _initialize_group_targets(self) -> None:
        """
        初始化组目标面积
        """
        total_area_ratio = sum(g['area_ratio'] for g in self.groups.get_config())
        for group in self.groups.get_config():
            group['target_area'] = self.region_area * (group['area_ratio'] / 100.0)
            group['generated_area'] = 0.0
            group['count'] = 0
            group['shapes_and_itz'] = []
            logging.info(f"Group {group['id']}: Target Area {group['target_area']:.2f}")

    def _check_exit_conditions(self, target_total_area: float, max_attempts: int) -> bool:
        """
        检查生成退出条件
        
        Returns:
            bool: 是否满足退出条件
        """
        groups = self.groups.get_config()
        
        if self.generation_mode == "porosity":
            current_porosity = self.calculate_porosity()
            target_porosity_percent = self.target_porosity * 100
            
            logging.debug(f"孔隙度调试: 目标={target_porosity_percent:.2f}%, 当前={current_porosity:.2f}%, 总面积={self.total_area:.2f}, 区域面积={self.region_area:.2f}")
            
            tolerance = 1.0
            if abs(current_porosity - target_porosity_percent) <= tolerance:
                logging.info(f"孔隙度模式: 已达到目标孔隙度 {target_porosity_percent:.2f}% (当前 {current_porosity:.2f}%)")
                return True
            
            if current_porosity < target_porosity_percent - tolerance:
                logging.info(f"孔隙度模式: 当前孔隙度 {current_porosity:.2f}% 已小于目标孔隙度 {target_porosity_percent:.2f}%，生成过程结束")
                return True
            
            has_remaining_groups = False
            for group in groups:
                if group['count'] < group['max_count']:
                    has_remaining_groups = True
                    break
            
            if not has_remaining_groups:
                logging.info(f"孔隙度模式: 所有组都已达到最大数量限制，生成过程结束")
                return True
        else:
            has_remaining_groups = False
            for group in groups:
                if group['count'] < group['max_count']:
                    has_remaining_groups = True
                    break
            
            if not has_remaining_groups:
                logging.info(f"所有组都已达到最大数量限制，生成过程结束")
                return True
        
        total_max_count = sum(g['max_count'] for g in groups)
        global_max_attempts = max_attempts * total_max_count
        
        if len(self.generated_aggregates) > global_max_attempts:
            logging.info(f"已达到全局最大尝试次数 {global_max_attempts}，生成过程结束")
            return True
        
        return False

    def _generate_single_aggregate(self, 
                                 chosen_group: Dict[str, Any],
                                 min_x: float, min_y: float, max_x: float, max_y: float,
                                 max_possible_radius: float,
                                 min_distance: float,
                                 boundary_adjust: bool) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        生成单个骨料
        
        Args:
            chosen_group: 选中的组配置
            min_x, min_y, max_x, max_y: 区域边界
            max_possible_radius: 最大可能半径
            min_distance: 最小间距
            boundary_adjust: 是否进行边界优化
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: (是否成功, 骨料数据)
        """
        if not SHAPELY_AVAILABLE or not PYAUTOCAD_AVAILABLE:
            return False, None
        
        buffer = max_possible_radius * 0.5
        x = random.uniform(min_x + buffer, max_x - buffer)
        y = random.uniform(min_y + buffer, max_y - buffer)
        center = (x, y)

        group_shapes = chosen_group['shapes']
        group_weights = [s['weight'] for s in group_shapes]
        shape_config = random.choices(group_shapes, weights=group_weights, k=1)[0]

        shape_data = self._generate_shape(shape_config, center)
        if not shape_data:
            return False, None
        
        points, actual_radius, area, shape_info, coords = shape_data
        
        shapely_poly = self._create_shapely_polygon(coords)
        if not shapely_poly:
            return False, None

        itz_thickness = chosen_group.get('itz_thickness', 0.0)
        shapely_itz = shapely_poly.buffer(itz_thickness) if itz_thickness > 0 else None

        all_existing_objects = []
        for g in self.groups.get_config():
            all_existing_objects.extend(g['shapes_and_itz'])
        
        collision = check_collision_hierarchical(shapely_poly, shapely_itz, all_existing_objects, min_distance, self.spatial_index, self.use_gpu, self.allow_touching)
        if collision:
            return False, None

        if boundary_adjust:
            boundary_check_radius = actual_radius + itz_thickness
            if is_near_boundary(center, boundary_check_radius, (min_x, min_y), (max_x, max_y), min_distance):
                itz_safe_distance = 0.1
                
                center = move_toward_boundary(center, (min_x, min_y), (max_x, max_y), itz_safe_distance)
                for i in range(len(points)):
                    px, py = points[i]
                    points[i] = (center[0] + (px - x), center[1] + (py - y))
                
                points = adjust_points_to_boundary([APoint(p[0], p[1], 0) for p in points], itz_safe_distance, (min_x, min_y), (max_x, max_y))
                # adjust_points_to_boundary 返回 tuple，重新包装为 APoint
                points = [APoint(p[0], p[1], 0) for p in points]
                _, actual_radius = calculate_bounding_circle(points)
                
                coords = []
                for p in points:
                    if hasattr(p, 'x') and hasattr(p, 'y'):
                        coords.append((p.x, p.y))
                    else:
                        coords.append(p)
                
                shapely_poly = self._create_shapely_polygon(coords)
                if not shapely_poly:
                    return False, None
                
                shapely_itz = shapely_poly.buffer(itz_thickness) if itz_thickness > 0 else None
                
                if hasattr(shapely_poly, 'area'):
                    area = shapely_poly.area
            
            all_existing_objects = []
            for g in self.groups.get_config():
                all_existing_objects.extend(g['shapes_and_itz'])
            
            collision = check_collision_hierarchical(shapely_poly, shapely_itz, all_existing_objects, min_distance, self.spatial_index, self.use_gpu, self.allow_touching)
            if collision:
                return False, None

        agg_data = {
            "center": center,
            "radius": actual_radius,
            "area": area,
            "points": points,
            "shape_info": shape_info,
            "group_id": chosen_group['id'],
            "itz_thickness": itz_thickness,
            "shapely_obj": shapely_poly,
            "shapely_itz": shapely_itz
        }
        
        return True, agg_data

    def _generate_shape(self, shape_config: Dict[str, Any], center: Tuple[float, float]) -> Optional[Tuple]:
        """
        生成指定类型的骨料形状
        
        Returns:
            Optional[Tuple]: (点列表, 实际半径, 面积, 形状信息, 坐标列表)
        """
        points = []
        actual_radius = 0.0
        area = 0.0
        shape_info = {}
        
        try:
            if shape_config['type'] == 'polygon':
                min_size = shape_config.get('min_size', 2.0)
                max_size = shape_config.get('max_size', 8.0)
                min_sides = shape_config.get('min_sides', 3)
                max_sides = shape_config.get('max_sides', 7)
                irregularity = shape_config.get('irregularity', 0.3)
                spikiness = shape_config.get('spikiness', 0.2)
                optimize_sides = shape_config.get('optimize_sides', True)
                min_edge_length = shape_config.get('min_edge_length', None)
                
                size = random.uniform(min_size, max_size)
                sides = random.randint(min_sides, max_sides)
                points = generate_random_polygon(center, size, sides, irregularity, spikiness, optimize_sides, min_edge_length)
                _, actual_radius = calculate_bounding_circle([APoint(p[0], p[1], 0) for p in points])
                area = calculate_polygon_area([APoint(p[0], p[1], 0) for p in points])
                shape_info = {"shape": "polygon", "size": size, "sides": sides, "irregularity": irregularity, "spikiness": spikiness}
            
            elif shape_config['type'] == 'circle':
                min_radius = shape_config.get('min_radius', 2.0)
                max_radius = shape_config.get('max_radius', 8.0)
                segments = shape_config.get('segments', 36)
                
                radius = random.uniform(min_radius, max_radius)
                actual_radius = radius
                area = calculate_circle_area(radius)
                points = generate_circle(center, radius, segments)
                shape_info = {"shape": "circle", "radius": radius, "segments": segments}
            
            elif shape_config['type'] == 'ellipse':
                min_major = shape_config.get('min_major', 3.0)
                max_major = shape_config.get('max_major', 10.0)
                min_minor = shape_config.get('min_minor', 2.0)
                max_minor = shape_config.get('max_minor', 8.0)
                segments = shape_config.get('segments', 36)
                
                major_axis = random.uniform(min_major, max_major)
                minor_axis = random.uniform(min_minor, max_minor)
                rotation = random.uniform(0, 2 * math.pi)
                actual_radius = max(major_axis, minor_axis)
                area = calculate_ellipse_area(major_axis, minor_axis)
                points = generate_ellipse(center, major_axis, minor_axis, rotation, segments)
                shape_info = {"shape": "ellipse", "major_axis": major_axis, "minor_axis": minor_axis, "rotation": rotation, "segments": segments}
            
            else:
                logging.warning(f"未知的形状类型: {shape_config['type']}")
                return None
                
            coords = [(p[0], p[1]) for p in points]
            
            return points, actual_radius, area, shape_info, coords
            
        except Exception as e:
            logging.warning(f"生成形状时出错: {str(e)}")
            return None

    def _create_shapely_polygon(self, coords: List[Tuple[float, float]]) -> Optional[Any]:
        """
        创建Shapely多边形对象
        """
        if not SHAPELY_AVAILABLE:
            return None
            
        if len(coords) > 2:
            try:
                return ShapelyPolygon(coords)
            except Exception as e:
                logging.warning(f"创建Shapely多边形失败: {str(e)}, 跳过此骨料")
        else:
            logging.warning(f"点数不足，无法创建Shapely多边形: {coords}")
        return None

    def _add_aggregate_to_spatial_index_and_collections(self, agg_data: Dict[str, Any]) -> None:
        """
        将骨料添加到空间索引和集合中
        """
        self.total_area += agg_data["area"]
        
        for group in self.groups.get_config():
            if group['id'] == agg_data["group_id"]:
                group['generated_area'] += agg_data["area"]
                group['count'] += 1
                group['shapes_and_itz'].append(agg_data["shapely_obj"])
                if agg_data["shapely_itz"]:
                    group['shapes_and_itz'].append(agg_data["shapely_itz"])
                break
        
        if self.spatial_index:
            self.spatial_index.insert(agg_data)
        
        self.generated_aggregates.append(agg_data)

    def _send_draw_command(self, agg_data: Dict[str, Any], chosen_group: Dict[str, Any], draw_callback: Any) -> None:
        """
        发送绘图命令到队列
        """
        point_array = []
        for p in agg_data["points"]:
            if hasattr(p, 'x') and hasattr(p, 'y'):
                point_array.extend([p.x, p.y, 0.0])
            else:
                point_array.extend([p[0], p[1], 0.0])
        
        color_map = CADColorMap.get_color_map()
        color = color_map.get(chosen_group.get('layer_color', "红色"), CADColorMap.RED)
        draw_callback(('aggregate', point_array, color, "RandomCAD-Aggregates"))
        logging.debug(f"骨料点数据放入队列: {point_array[:6]}...")
        
        itz_thickness = agg_data.get('itz_thickness', 0.0)
        if itz_thickness > 0 and 'shapely_itz' in agg_data and agg_data['shapely_itz']:
            try:
                itz_polygon = agg_data['shapely_itz']
                if hasattr(itz_polygon, 'exterior'):
                    itz_points = list(itz_polygon.exterior.coords)
                    itz_point_array = []
                    for p in itz_points:
                        itz_point_array.extend([p[0], p[1], 0.0])
                    
                    itz_color = (color % 7) + 1
                    draw_callback(('aggregate', itz_point_array, itz_color, "RandomCAD-ITZ"))
                    logging.debug(f"ITZ点数据放入队列: {itz_point_array[:6]}...")
            except Exception as e:
                logging.warning(f"绘制ITZ失败: {str(e)}")

    def calculate_porosity(self) -> float:
        """
        计算当前孔隙度
        
        Returns:
            float: 孔隙度百分比 (0-100)
        """
        if self.region_area <= 0:
            return 0.0
        if self.total_area <= 0:
            return 100.0
        porosity = 1 - (self.total_area / self.region_area)
        return max(0.0, min(1.0, porosity)) * 100

    def export_to_csv(self, filename: str = "aggregates.csv") -> bool:
        """
        导出骨料数据到CSV文件
        
        Args:
            filename: 输出文件名
            
        Returns:
            bool: 导出成功返回True，否则返回False
        """
        if not self.generated_aggregates:
            logging.warning("没有骨料数据可导出")
            return False
        
        try:
            import csv
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Group_ID", "Center_X", "Center_Y", "Radius", "Area", "Shape", "Shape Parameters", "ITZ_Thickness"])
                
                for i, agg in enumerate(self.generated_aggregates):
                    center = agg["center"]
                    shape_info = agg["shape_info"]
                    shape_type = shape_info["shape"]
                    params_str = ""
                    
                    if shape_type == "polygon":
                        params_str = f"Size={shape_info['size']:.2f}, Sides={shape_info['sides']}, Irregularity={shape_info['irregularity']:.2f}, Spikiness={shape_info['spikiness']:.2f}"
                    elif shape_type == "circle":
                        params_str = f"Radius={shape_info['radius']:.2f}, Segments={shape_info['segments']}"
                    elif shape_type == "ellipse":
                        params_str = f"Major={shape_info['major_axis']:.2f}, Minor={shape_info['minor_axis']:.2f}, Rotation={shape_info['rotation']:.2f}, Segments={shape_info['segments']}"
                    
                    writer.writerow([
                        i + 1,
                        agg["group_id"],
                        round(center[0], 4),
                        round(center[1], 4),
                        round(agg["radius"], 4),
                        round(agg["area"], 4),
                        shape_type,
                        params_str,
                        agg.get("itz_thickness", 0.0)
                    ])
            
            logging.info(f"数据已成功导出到: {filename}")
            return True
        except Exception as e:
            logging.error(f"导出失败：{str(e)}", exc_info=True)
            return False

    def export_to_json(self, filename: str = "aggregates.json") -> bool:
        """
        导出骨料数据到JSON文件
        
        Args:
            filename: 输出文件名
            
        Returns:
            bool: 导出成功返回True，否则返回False
        """
        if not self.generated_aggregates:
            logging.warning("没有骨料数据可导出")
            return False
        
        try:
            import json
            data = {
                "metadata": {
                    "version": "2.0.1",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "count": len(self.generated_aggregates),
                    "porosity": round(self.calculate_porosity(), 2),
                    "generation_time": self.get_generation_time()
                },
                "specimen": {"type": self.specimen_type, "region_area": self.region_area},
                "groups": [{"id": g['id'], "area_ratio": g['area_ratio'], "itz_thickness": g['itz_thickness'], 
                             "max_count": g['max_count'], "count": g['count'], "generated_area": g['generated_area']} 
                            for g in self.groups.get_config()],
                "aggregates": [{"id": i+1, "group_id": a['group_id'], "center": list(a['center']),
                                 "radius": a['radius'], "area": a['area'], 
                                 "shape": a['shape_info'], "itz_thickness": a.get('itz_thickness', 0)}
                                for i, a in enumerate(self.generated_aggregates)]
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            logging.info(f"JSON数据已成功导出到: {filename}")
            return True
        except Exception as e:
            logging.error(f"JSON导出失败：{str(e)}", exc_info=True)
            return False

    def clear_generated(self) -> int:
        """
        清除所有生成的骨料和相关数据
        
        Returns:
            int: 删除的骨料数量
        """
        deleted_count = 0
        
        for obj in self.draw_objects:
            try:
                self.cad_connection.delete_object(obj)
                deleted_count += 1
            except Exception as e:
                logging.warning(f"删除对象时出错: {str(e)}")
        
        self.draw_objects = []
        self.generated_aggregates = []
        self.itz_layers = []
        self.groups.reset_group_stats()
        self.total_area = 0.0
        self.region_boundary = None
        self.boundary_min = None
        self.boundary_max = None
        
        if self.spatial_index:
            self.spatial_index.clear()
            self.spatial_index = None
        
        logging.info(f"已删除{deleted_count}个骨料")
        return deleted_count
    
    def _parallel_generate_attempt(self, chosen_group: Dict[str, Any],
                                 min_x: float, min_y: float, max_x: float, max_y: float,
                                 max_possible_radius: float,
                                 min_distance: float,
                                 boundary_adjust: bool) -> Optional[Dict[str, Any]]:
        """
        并行生成尝试 - 用于线程池执行单个骨料生成
        
        Args:
            chosen_group: 选中的组配置
            min_x, min_y, max_x, max_y: 区域边界
            max_possible_radius: 最大可能半径
            min_distance: 最小间距
            boundary_adjust: 是否进行边界优化
            
        Returns:
            Optional[Dict[str, Any]]: 成功则返回骨料数据，失败则返回None
        """
        try:
            success, agg_data = self._generate_single_aggregate(
                chosen_group, min_x, min_y, max_x, max_y, max_possible_radius,
                min_distance, boundary_adjust
            )
            return agg_data if success else None
        except Exception as e:
            logging.warning(f"并行生成尝试失败: {str(e)}")
            return None

    def get_generation_time(self) -> float:
        """
        获取生成耗时
        
        Returns:
            float: 耗时（秒）
        """
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 2)
        return 0.0

    def save_config(self, filename: str) -> bool:
        """
        保存组配置到 JSON 文件
        
        Args:
            filename: 输出文件名
            
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            import json
            config = []
            for g in self.groups.get_config():
                config.append({
                    'area_ratio': g['area_ratio'],
                    'itz_thickness': g['itz_thickness'],
                    'max_count': g['max_count'],
                    'layer_color': g['layer_color'],
                    'shapes': g['shapes']
                })
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'groups': config, 
                    'mode': self.generation_mode, 
                    'porosity': round(self.target_porosity * 100, 1)
                }, f, ensure_ascii=False, indent=2)
            logging.info(f"配置已保存到: {filename}")
            return True
        except Exception as e:
            logging.error(f"保存配置失败: {str(e)}", exc_info=True)
            return False

    def load_config(self, filename: str) -> dict:
        """
        从 JSON 加载组配置，返回配置字典
        
        Args:
            filename: 输入文件名
            
        Returns:
            dict: 包含 groups、mode、porosity 的配置字典
        """
        import json
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info(f"配置已从 {filename} 加载")
        return data
