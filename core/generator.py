# core/generator.py

import random
import time
import math
import logging
import threading
import comtypes
from typing import List, Tuple, Dict, Any, Optional, Union, Callable
from pyautocad import Autocad, APoint, aDouble
from concurrent.futures import ThreadPoolExecutor, as_completed
# 假设其他模块已正确创建并导出
from core.shapes import generate_random_polygon, generate_circle, generate_ellipse
from core.collision import check_collision_hierarchical
from core.group_manager import GroupManager
from core.quadtree import Quadtree
from core.kd_tree import KDTree
from utils import calculate_polygon_area, calculate_circle_area, calculate_ellipse_area, calculate_bounding_circle, is_near_boundary, move_toward_boundary, adjust_points_to_boundary
from configs.config import CAD_COLOR_MAP

class RandomAggregateGenerator:
    def __init__(self, auto_start: bool = True):
        self.acad: Optional[Autocad] = None
        self.doc: Any = None
        self.model_space: Any = None
        self.generation_mode: str = "count"
        self.target_porosity: float = 0.0
        self.generated_aggregates: List[Dict[str, Any]] = []
        self.groups: GroupManager = GroupManager() # 使用专门的管理器
        self.itz_layers: List[Any] = [] # 存储ITZ的Shapely对象
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.original_regenmode: int = 1
        self.total_area: float = 0.0
        self.region_area: float = 0.0
        self.region_boundary: Any = None
        self.boundary_color: int = CAD_COLOR_MAP["白色"] # 默认白色
        self.boundary_min: Optional[Tuple[float, float]] = None
        self.boundary_max: Optional[Tuple[float, float]] = None
        self.generation_canceled: bool = False
        self.last_progress_time: float = 0.0
        self.draw_objects: List[Any] = []  # 存储所有绘制的对象
        
        # 空间划分算法相关
        self.space_partitioning: str = "quadtree"  # 可选值: quadtree, kdtree
        self.spatial_index: Optional[Union[Quadtree, KDTree]] = None  # 空间索引对象
        
        # 并行计算相关
        self.executor: Optional[ThreadPoolExecutor] = None  # 线程池用于并行计算
        self.max_workers: int = 4  # 最大并行工作线程数
        
        # GPU加速相关
        self.use_gpu: bool = False  # 是否使用GPU加速
        self.cuda_available: bool = False  # CUDA是否可用
        
        # 检查CUDA是否可用
        self._check_cuda_availability()

        # 确保在主线程中创建COM对象
        if threading.current_thread() is threading.main_thread():
            self._initialize_acad(auto_start, is_main_thread=True)
        else:
            # 在子线程中创建新的COM实例
            self._initialize_acad(auto_start, is_main_thread=False)

    def _check_cuda_availability(self) -> None:
        """
        检查CUDA是否可用，用于GPU加速
        """
        try:
            # 尝试导入PyTorch检查CUDA
            import torch
            self.cuda_available = torch.cuda.is_available()
            if self.cuda_available:
                logging.info(f"CUDA可用，设备数量: {torch.cuda.device_count()}")
                logging.info(f"当前CUDA设备: {torch.cuda.get_device_name(0)}")
            else:
                logging.info("CUDA不可用，将使用CPU计算")
        except ImportError:
            logging.info("PyTorch未安装，无法使用GPU加速")
        except Exception as e:
            logging.warning(f"检查CUDA可用性时出错: {str(e)}")
            self.cuda_available = False
    
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
    
    def _initialize_acad(self, auto_start: bool, is_main_thread: bool) -> None:
        """
        初始化AutoCAD连接
        
        Args:
            auto_start: 如果AutoCAD未运行，是否自动启动
            is_main_thread: 是否在主线程中初始化
        """
        try:
            if not is_main_thread:
                comtypes.CoInitialize()
                logging.info("子线程COM已初始化")
            
            self.acad = Autocad(create_if_not_exists=auto_start)
            if self.acad:
                self.doc = self.acad.doc
                self.model_space = self.doc.ModelSpace
                thread_info = "主线程" if is_main_thread else "子线程"
                self.acad.prompt(f"随机骨料生成器已连接AutoCAD ({thread_info})\n")
                logging.info(f"成功连接AutoCAD ({thread_info})")
        except Exception as e:
            logging.error(f"连接AutoCAD失败 ({thread_info}): {str(e)}")
            raise ConnectionError(f"连接AutoCAD失败: {str(e)}")

    def __del__(self):
        """析构函数，清理COM资源"""
        try:
            if threading.current_thread() is not threading.main_thread():
                comtypes.CoUninitialize()
                logging.info("子线程COM资源已清理")
        except Exception as e:
            logging.warning(f"清理COM资源时出错: {str(e)}")

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
        if hasattr(self, 'acad') and self.acad:
            self.acad.prompt("用户取消生成过程\n")
            logging.info("用户取消生成过程")

    def set_boundary_color(self, color_name: str) -> None:
        """设置边界颜色
        
        Args:
            color_name: 颜色名称，必须在CAD_COLOR_MAP中定义
        """
        self.boundary_color = CAD_COLOR_MAP.get(color_name, CAD_COLOR_MAP["白色"])

    def generate_aggregates_in_region(self, region_min: Tuple[float, float], 
                                      region_max: Tuple[float, float],
                                      min_distance: float = 1.0,
                                      max_attempts: int = 100,
                                      boundary_adjust: bool = True,
                                      progress_queue: Optional[Any] = None,
                                      draw_queue: Optional[Any] = None) -> int:
        """
        重构的核心生成方法，支持多组粒径和ITZ。
        
        Args:
            region_min: 区域左下角坐标 (x, y)
            region_max: 区域右上角坐标 (x, y)
            min_distance: 骨料之间的最小间距
            max_attempts: 每组的最大尝试次数
            boundary_adjust: 是否进行边界优化
            progress_queue: 进度更新队列
            draw_queue: 绘图命令队列
            
        Returns:
            int: 生成的骨料数量
        """
        try:
            # 确保区域坐标有效
            min_x, min_y = region_min
            max_x, max_y = region_max
            if min_x >= max_x or min_y >= max_y:
                raise ValueError("区域坐标无效: 右上角坐标必须大于左下角坐标")
            
            # 确保COM已初始化（对于子线程）
            if threading.current_thread() is not threading.main_thread():
                comtypes.CoInitialize()
                logging.info("子线程COM已初始化")
            
            self.start_time = time.time()
            self.total_area = 0.0
            self.generation_canceled = False
            
            # 计算区域参数
            region_width = max_x - min_x
            region_height = max_y - min_y
            self.region_area = region_width * region_height
            self.boundary_min = (min_x, min_y)
            self.boundary_max = (max_x, max_y)
            
            # 删除旧边界
            self._clear_old_boundary()
            
            # 创建边界
            self._create_boundary(min_x, min_y, max_x, max_y, draw_queue)
            
            # 计算最大可能的半径（考虑所有组的所有形态）
            max_possible_radius = self._calculate_max_possible_radius()
            
            # 根据骨料尺寸动态调整空间索引参数
            avg_particle_size = max_possible_radius / 2.0
            
            # 动态计算空间索引参数：根据骨料平均尺寸调整
            # 平均尺寸越大，每个节点可以容纳更多对象
            dynamic_max_objects = max(5, int(20 / (avg_particle_size / 5.0)))
            # 平均尺寸越大，树的深度可以越小
            dynamic_max_depth = max(5, min(10, int(8 + (5.0 / avg_particle_size))))
            
            logging.info(f"动态空间索引参数: max_depth={dynamic_max_depth}, max_objects={dynamic_max_objects}")
            
            # 初始化空间索引（用于空间划分，优化碰撞检测）
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
            
            # --- 初始化组目标 ---
            self._initialize_group_targets()
            
            # --- 孔隙度模式的特定变量 ---
            target_total_area = 0.0
            if self.generation_mode == "porosity":
                target_total_area = self.region_area * (1 - self.target_porosity)
                logging.info(f"孔隙度模式: 目标总骨料面积 {target_total_area:.2f}")
            
            # 根据系统资源和骨料尺寸动态调整并行度
            # 平均尺寸越小，需要生成的骨料越多，并行度可以适当提高
            base_parallelism = self.max_workers
            dynamic_parallelism = max(2, min(8, int(base_parallelism * (1 + (5.0 / avg_particle_size)))))
            
            # 创建线程池用于并行生成
            self.executor = ThreadPoolExecutor(max_workers=dynamic_parallelism)
            logging.info(f"创建线程池，动态并行度: {dynamic_parallelism}")
            
            # 开始生成循环
            while True:
                if self.generation_canceled:
                    if progress_queue:
                        progress_queue.put(("info", "生成过程已被用户取消"))
                    logging.info("生成过程已被用户取消")
                    break

                # --- 退出条件 ---
                if self._check_exit_conditions(target_total_area, max_attempts):
                    break

                # 更新进度
                current_time = time.time()
                if current_time - last_update_time > 0.5 and progress_queue is not None:
                    progress_queue.put(("progress", generated_count, self.total_area, self.calculate_porosity()))
                    last_update_time = current_time

                # --- 选择一个需要生成的组 ---
                chosen_group = self.groups.select_next_group(self.generation_mode)
                if not chosen_group:
                    break

                # --- 动态调整每次并行尝试的数量 ---
                # 生成初期可以尝试更多并行任务，随着骨料增多，减少并行尝试数量
                # 已生成骨料占比
                if self.generation_mode == "porosity" and target_total_area > 0:
                    progress_ratio = min(1.0, self.total_area / target_total_area)
                else:
                    # 按组目标面积计算进度
                    group_progress = []
                    for group in self.groups.get_config():
                        if group['target_area'] > 0:
                            group_progress.append(min(1.0, group['generated_area'] / group['target_area']))
                    progress_ratio = sum(group_progress) / len(group_progress) if group_progress else 0
                
                # 动态调整并行尝试次数：进度越高，尝试次数越少（因为碰撞概率增加）
                base_attempts = dynamic_parallelism * 2
                dynamic_attempts = max(2, int(base_attempts * (1 - progress_ratio * 0.7)))
                
                # --- 并行生成多个骨料尝试 ---
                futures = []
                
                # 提交多个生成任务到线程池
                for _ in range(dynamic_attempts):
                    future = self.executor.submit(
                        self._parallel_generate_attempt,
                        chosen_group, min_x, min_y, max_x, max_y, max_possible_radius,
                        min_distance, boundary_adjust
                    )
                    futures.append(future)
                
                # 等待任务完成并处理结果，使用超时机制避免长时间阻塞
                agg_data = None
                timeout = 5.0  # 单个任务超时时间
                
                for future in as_completed(futures, timeout=timeout):
                    try:
                        result = future.result(timeout=timeout)
                        if result is not None:
                            # 再次检查碰撞（确保线程安全，因为其他线程可能已经添加了新骨料）
                            all_existing_objects = []
                            for g in self.groups.get_config():
                                all_existing_objects.extend(g['shapes_and_itz'])
                            
                            collision = check_collision_hierarchical(
                                result['shapely_obj'], result['shapely_itz'], 
                                all_existing_objects, min_distance, self.spatial_index, self.use_gpu
                            )
                            
                            if not collision:
                                agg_data = result
                                # 取消剩余任务，因为已经找到一个有效的骨料
                                for f in futures:
                                    if not f.done():
                                        f.cancel()
                                break
                    except Exception as e:
                        logging.warning(f"并行任务处理异常: {str(e)}")
                        continue
                
                if agg_data:
                    generated_count += 1
                    total_attempts = 0 # 成功生成后重置尝试次数
                    
                    # 添加到空间索引和集合
                    self._add_aggregate_to_spatial_index_and_collections(agg_data)
                    
                    # 发送绘图命令
                    if draw_queue:
                        self._send_draw_command(agg_data, chosen_group, draw_queue)
                        
                    # 定期请求重绘
                    if generated_count % 10 == 0 and time.time() - self.last_progress_time > 1.0:
                        draw_queue.put(('regen',))
                        self.last_progress_time = time.time()
                else:
                    total_attempts += 1
                    # 尝试次数过多时，适当增加并行度以提高找到有效骨料的概率
                    if total_attempts % 50 == 0:
                        dynamic_parallelism = min(12, dynamic_parallelism + 1)
                        logging.info(f"调整并行度: {dynamic_parallelism}")
                        # 重新创建线程池
                        self.executor.shutdown(wait=True)
                        self.executor = ThreadPoolExecutor(max_workers=dynamic_parallelism)
            
            # 关闭线程池
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None
                logging.info("线程池已关闭")

        except Exception as e:
            logging.error(f"生成错误：{str(e)}", exc_info=True)
            raise
        finally:
            # 清理COM资源（对于子线程）
            if threading.current_thread() is not threading.main_thread():
                try:
                    comtypes.CoUninitialize()
                    logging.info("子线程COM资源已清理")
                except Exception as e:
                    logging.warning(f"清理子线程COM资源时出错: {str(e)}")

            self.end_time = time.time()
            logging.info(f"生成完成，耗时: {self.end_time - self.start_time:.2f}秒")
        
        return len(self.generated_aggregates)

    def _clear_old_boundary(self) -> None:
        """
        删除旧边界
        """
        if self.region_boundary:
            try:
                self.region_boundary.Delete()
                logging.info("已删除旧边界")
            except Exception as e:
                logging.warning(f"删除旧边界时出错: {str(e)}")
            self.region_boundary = None
            self.boundary_min = None
            self.boundary_max = None

    def _create_boundary(self, min_x: float, min_y: float, max_x: float, max_y: float, draw_queue: Any) -> None:
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
            if draw_queue:
                draw_queue.put(('boundary', boundary_points, self.boundary_color))
                logging.info("边界创建请求已放入队列")
        except Exception as e:
            if self.acad:
                self.acad.prompt(f"警告: 创建边界失败 - {str(e)}\n")
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
        # 检查所有组是否都满足面积要求
        all_groups_satisfied = all(g['generated_area'] >= g['target_area'] for g in self.groups.get_config())
        if all_groups_satisfied and self.generation_mode != "porosity":
            logging.info(f"所有组的面积要求已满足")
            return True

        # 检查孔隙度模式是否达到目标
        if self.generation_mode == "porosity" and self.total_area >= target_total_area:
            logging.info(f"孔隙度模式: 已达到目标总面积 {target_total_area:.2f} (当前 {self.total_area:.2f})")
            return True

        # 检查尝试次数是否超过限制
        max_total_attempts = max_attempts * sum(g['max_count'] for g in self.groups.get_config())
        return len(self.generated_aggregates) >= max_total_attempts

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
        # --- 生成随机中心点 ---
        buffer = max_possible_radius * 1.5
        x = random.uniform(min_x + buffer, max_x - buffer)
        y = random.uniform(min_y + buffer, max_y - buffer)
        center = (x, y) # 使用元组 (x, y) 作为中心点

        # --- 根据权重随机选择一种骨料形态 ---
        group_shapes = chosen_group['shapes']
        group_weights = [s['weight'] for s in group_shapes]
        shape_config = random.choices(group_shapes, weights=group_weights, k=1)[0]

        # --- 生成骨料形状 ---
        shape_data = self._generate_shape(shape_config, center)
        if not shape_data:
            return False, None
        
        points, actual_radius, area, shape_info, coords = shape_data
        
        # --- 使用Shapely创建几何对象 ---
        from shapely.geometry import Polygon as ShapelyPolygon
        shapely_poly = self._create_shapely_polygon(coords)
        if not shapely_poly:
            return False, None

        # --- 生成ITZ (Shapely对象) ---
        itz_thickness = chosen_group.get('itz_thickness', 0.0)
        shapely_itz = shapely_poly.buffer(itz_thickness) if itz_thickness > 0 else None

        # --- 碰撞检测：使用层次化碰撞检测和空间索引 ---
        all_existing_objects = []
        for g in self.groups.get_config():
            all_existing_objects.extend(g['shapes_and_itz'])
        
        # 使用层次化碰撞检测，并传入空间索引对象和GPU加速标志
        collision = check_collision_hierarchical(shapely_poly, shapely_itz, all_existing_objects, min_distance, self.spatial_index, self.use_gpu)
        if collision:
            return False, None

        # --- 边界处理 ---
        if boundary_adjust and is_near_boundary(center, actual_radius, (min_x, min_y), (max_x, max_y), min_distance):
            center = move_toward_boundary(center, (min_x, min_y), (max_x, max_y), min_distance)
            # 更新所有点
            for i in range(len(points)):
                px, py = points[i]
                points[i] = (center[0] + (px - x), center[1] + (py - y))
            
            # 调整点到边界
            points = adjust_points_to_boundary([APoint(p[0], p[1], 0) for p in points], min_distance, (min_x, min_y), (max_x, max_y))
            # 重新计算中心点和半径（调整后可能变化）
            _, actual_radius = calculate_bounding_circle(points)

        # --- 构建骨料数据 ---
        agg_data = {
            "center": center,
            "radius": actual_radius,
            "area": area,
            "points": points,
            "shape_info": shape_info,
            "group_id": chosen_group['id'],
            "itz_thickness": itz_thickness,
            "shapely_obj": shapely_poly, # 保存Shapely对象
            "shapely_itz": shapely_itz    # 保存ITZ Shapely对象
        }
        
        return True, agg_data

    def _generate_shape(self, shape_config: Dict[str, Any], center: Tuple[float, float]) -> Optional[Tuple[List[Tuple[float, float]], float, float, Dict[str, Any], List[Tuple[float, float]]]]:
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
                
                size = random.uniform(min_size, max_size)
                sides = random.randint(min_sides, max_sides)
                points = generate_random_polygon(center, size, sides, irregularity, spikiness)
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
                
            # 转换为APoint列表用于后续计算
            a_points = [APoint(p[0], p[1], 0) for p in points]
            coords = [(p.x, p.y) for p in a_points]
            
            return points, actual_radius, area, shape_info, coords
            
        except Exception as e:
            logging.warning(f"生成形状时出错: {str(e)}")
            return None

    def _create_shapely_polygon(self, coords: List[Tuple[float, float]]) -> Optional[Any]:
        """
        创建Shapely多边形对象
        """
        from shapely.geometry import Polygon as ShapelyPolygon
        if len(coords) > 2: # 确保有足够的点构成多边形
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
        # 更新总面积
        self.total_area += agg_data["area"]
        
        # 更新组统计
        for group in self.groups.get_config():
            if group['id'] == agg_data["group_id"]:
                group['generated_area'] += agg_data["area"]
                group['count'] += 1
                # 将Shapely对象添加到对应组的列表中，用于后续碰撞检测
                group['shapes_and_itz'].append(agg_data["shapely_obj"])
                if agg_data["shapely_itz"]:
                    group['shapes_and_itz'].append(agg_data["shapely_itz"])
                break
        
        # 将骨料添加到空间索引
        if self.spatial_index:
            self.spatial_index.insert(agg_data)
        
        # 添加到生成列表
        self.generated_aggregates.append(agg_data)

    def _send_draw_command(self, agg_data: Dict[str, Any], chosen_group: Dict[str, Any], draw_queue: Any) -> None:
        """
        发送绘图命令到队列
        """
        # 将点转换为AutoCAD格式的数组
        point_array = []
        for p in agg_data["points"]:
            if hasattr(p, 'x') and hasattr(p, 'y'):
                # APoint对象
                point_array.extend([p.x, p.y, 0.0])
            else:
                # 元组
                point_array.extend([p[0], p[1], 0.0])
        
        color = CAD_COLOR_MAP.get(chosen_group.get('layer_color', "红色"), 1)
        draw_queue.put(('aggregate', point_array, color))
        logging.debug(f"骨料点数据放入队列: {point_array[:6]}...")

    def calculate_porosity(self) -> float:
        """
        计算当前孔隙度
        
        Returns:
            float: 孔隙度百分比 (0-100)
        """
        if self.region_area <= 0 or self.total_area <= 0:
            return 0.0
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

    def clear_generated(self) -> int:
        """
        清除所有生成的骨料和相关数据
        
        Returns:
            int: 删除的骨料数量
        """
        deleted_count = 0
        
        # 删除所有绘图对象
        for obj in self.draw_objects:
            try:
                obj.Delete()
                deleted_count += 1
            except Exception as e:
                logging.warning(f"删除对象时出错: {str(e)}")
        
        # 清除内部状态
        self.draw_objects = []
        self.generated_aggregates = []
        self.itz_layers = []
        self.groups.reset_group_stats()
        self.total_area = 0.0
        self.region_boundary = None
        self.boundary_min = None
        self.boundary_max = None
        
        # 清除空间索引
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