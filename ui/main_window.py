# ui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import queue
import threading
import sys
import os
import csv
import logging
from typing import List, Dict, Any, Tuple, Optional, Union
from ui.widgets import ScrollableFrame
from core.generator import RandomAggregateGenerator
from configs.config import DEFAULT_REGION, DEFAULT_MIN_DISTANCE, DEFAULT_TARGET_POROSITY, DEFAULT_MAX_ATTEMPTS, DEFAULT_MAX_AGGREGATES, DEFAULT_BOUNDARY_COLOR, DEFAULT_BOUNDARY_OPTIMIZE, DEFAULT_BOUNDARY_STRENGTH, DEFAULT_SHAPE_POLYGON, DEFAULT_SHAPE_CIRCLE, DEFAULT_SHAPE_ELLIPSE, DEFAULT_GROUP, CAD_COLOR_MAP


class AggregateGeneratorGUI:
    """
    AutoCAD随机骨料生成器主界面
    """
    
    def __init__(self, root: tk.Tk):
        """
        初始化主界面
        
        Args:
            root: 主窗口对象
        """
        self.root: tk.Tk = root
        self.root.title("AutoCAD随机骨料生成器 ")
        self.root.geometry("800x1000")
        self.root.resizable(True, True)
        self.root.minsize(800, 800)
        
        # 设置应用图标
        try:
            if sys.platform == "win32":
                icon_path = 'aggregate_icon.ico'
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
        except Exception as e:
            logging.debug(f"设置图标失败: {str(e)}")
        
        self.generator: Optional[RandomAggregateGenerator] = None
        self.generation_thread: Optional[threading.Thread] = None
        self.progress_queue: queue.Queue = queue.Queue()
        self.draw_queue: queue.Queue = queue.Queue()
        self.groups_data: List[Dict[str, Any]] = []  # 存储多组配置
        self.group_frames: List[ttk.LabelFrame] = []  # 存储UI上的组框架
        
        self.create_widgets()
        self.set_default_values()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<MouseWheel>", self.on_mousewheel)
        self.root.bind("<Button-4>", self.on_mousewheel_linux)
        self.root.bind("<Button-5>", self.on_mousewheel_linux)
        
        # 定期检查进度更新
        self.root.after(100, self.check_progress)
        # 定期处理绘图队列
        self.root.after(100, self.process_draw_queue)
        
        logging.info("界面初始化完成")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.scrollable_frame = ScrollableFrame(main_frame)
        self.scrollable_frame.pack(fill=tk.BOTH, expand=True)
        content_frame = self.scrollable_frame.scrollable_frame

        # === 区域设置 ===
        region_frame = ttk.LabelFrame(content_frame, text="生成区域设置", padding=10)
        region_frame.grid(row=0, column=0, sticky="we", padx=5, pady=10, columnspan=2)
        ttk.Label(region_frame, text="左下角坐标:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Label(region_frame, text="X:").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.x_min_var = tk.DoubleVar()
        ttk.Entry(region_frame, textvariable=self.x_min_var, width=8).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(region_frame, text="Y:").grid(row=0, column=3, sticky="w", padx=(10, 0))
        self.y_min_var = tk.DoubleVar()
        ttk.Entry(region_frame, textvariable=self.y_min_var, width=8).grid(row=0, column=4, padx=5, pady=5)
        ttk.Label(region_frame, text="右上角坐标:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Label(region_frame, text="X:").grid(row=1, column=1, sticky="w", padx=(10, 0))
        self.x_max_var = tk.DoubleVar()
        ttk.Entry(region_frame, textvariable=self.x_max_var, width=8).grid(row=1, column=2, padx=5, pady=5)
        ttk.Label(region_frame, text="Y:").grid(row=1, column=3, sticky="w", padx=(10, 0))
        self.y_max_var = tk.DoubleVar()
        ttk.Entry(region_frame, textvariable=self.y_max_var, width=8).grid(row=1, column=4, padx=5, pady=5)
        ttk.Label(region_frame, text="边界颜色:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.boundary_color_var = tk.StringVar(value=DEFAULT_BOUNDARY_COLOR)
        color_options = list(CAD_COLOR_MAP.keys())
        color_combo = ttk.Combobox(region_frame, textvariable=self.boundary_color_var,
                                   values=color_options, width=8, state="readonly")
        color_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(region_frame, text="边界优化:").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.boundary_optimize_var = tk.BooleanVar(value=DEFAULT_BOUNDARY_OPTIMIZE)
        boundary_check = ttk.Checkbutton(region_frame, variable=self.boundary_optimize_var)
        boundary_check.grid(row=2, column=3, padx=5, pady=5, sticky="w")
        ttk.Label(region_frame, text="(使骨料贴近边界)").grid(row=2, column=4, sticky="w", padx=5)

        # === 骨料形态设置 (多组) ===
        self.shape_groups_frame = ttk.LabelFrame(content_frame, text="多组粒径设置", padding=10)
        self.shape_groups_frame.grid(row=1, column=0, sticky="we", padx=5, pady=10, columnspan=2)

        # 按钮：添加组
        self.add_group_btn = ttk.Button(self.shape_groups_frame, text="添加一组", command=self.add_group_ui)
        self.add_group_btn.pack(side=tk.TOP, anchor="w", pady=5)

        # 添加第一组
        self.add_group_ui()

        # === 生成模式选择 ===
        mode_frame = ttk.LabelFrame(content_frame, text="生成模式", padding=10)
        mode_frame.grid(row=2, column=0, sticky="we", padx=5, pady=10, columnspan=2)
        self.mode_var = tk.StringVar(value="count")
        ttk.Radiobutton(mode_frame, text="按骨料数量生成", variable=self.mode_var, value="count",
                        command=self.toggle_generation_mode).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ttk.Radiobutton(mode_frame, text="按孔隙度生成", variable=self.mode_var, value="porosity",
                        command=self.toggle_generation_mode).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        mode_tip = ttk.Label(mode_frame, text="孔隙度模式: 通过骨料面积占比控制材料密度", foreground="#666666")
        mode_tip.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))

        # === 骨料参数 ===
        agg_frame = ttk.LabelFrame(content_frame, text="骨料参数", padding=10)
        agg_frame.grid(row=3, column=0, sticky="we", padx=5, pady=10, columnspan=2)
        self.count_label = ttk.Label(agg_frame, text="骨料数量:")
        self.count_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.count_var = tk.IntVar()
        self.count_entry = ttk.Entry(agg_frame, textvariable=self.count_var, width=8)
        self.count_entry.grid(row=0, column=1, padx=5, pady=5)
        self.porosity_label = ttk.Label(agg_frame, text="目标孔隙度(%):")
        self.porosity_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.target_porosity_var = tk.DoubleVar()
        self.target_porosity_entry = ttk.Entry(agg_frame, textvariable=self.target_porosity_var, width=8)
        self.target_porosity_entry.grid(row=0, column=1, padx=5, pady=5)
        self.porosity_label.grid_remove()
        self.target_porosity_entry.grid_remove()
        ttk.Label(agg_frame, text="最小间距 (mm):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.min_distance_var = tk.DoubleVar()
        ttk.Entry(agg_frame, textvariable=self.min_distance_var, width=8).grid(row=1, column=1, padx=5, pady=5)

        # === 高级设置 ===
        adv_frame = ttk.LabelFrame(content_frame, text="高级设置", padding=10)
        adv_frame.grid(row=4, column=0, sticky="we", padx=5, pady=10, columnspan=2)
        self.attempts_label = ttk.Label(adv_frame, text="最大尝试次数:")
        self.attempts_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.max_attempts_var = tk.IntVar()
        self.max_attempts_entry = ttk.Entry(adv_frame, textvariable=self.max_attempts_var, width=8)
        self.max_attempts_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(adv_frame, text="(建议: 100-500)").grid(row=0, column=2, sticky="w", padx=5)
        self.max_agg_label = ttk.Label(adv_frame, text="最大骨料数量:")
        self.max_agg_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.max_aggregates_var = tk.IntVar()
        self.max_aggregates_entry = ttk.Entry(adv_frame, textvariable=self.max_aggregates_var, width=8)
        self.max_aggregates_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(adv_frame, text="(防止无限循环)").grid(row=0, column=2, sticky="w", padx=5)
        self.max_agg_label.grid_remove()
        self.max_aggregates_entry.grid_remove()
        ttk.Label(adv_frame, text="边界优化强度:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.boundary_strength_var = tk.DoubleVar(value=DEFAULT_BOUNDARY_STRENGTH)
        strength_scale = ttk.Scale(adv_frame, from_=0.5, to=2.0, variable=self.boundary_strength_var,
                                   orient=tk.HORIZONTAL, length=150)
        strength_scale.grid(row=1, column=1, columnspan=2, sticky="we", padx=5, pady=5)
        self.strength_value = ttk.Label(adv_frame, text="1.0", width=4)
        self.strength_value.grid(row=1, column=3, padx=5)
        strength_scale.bind("<Motion>", lambda e: self.update_slider_value("str"))

        # === 进度条 ===
        self.progress_frame = ttk.Frame(content_frame)
        self.progress_frame.grid(row=5, column=0, sticky="we", padx=5, pady=10, columnspan=2)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var,
                                            orient="horizontal", length=500, mode="determinate")
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        self.progress_label = ttk.Label(self.progress_frame, text="准备生成...")
        self.progress_label.pack(pady=5)
        # 初始隐藏进度条
        self.progress_frame.grid_remove()

        # === 按钮区域 ===
        btn_frame = ttk.Frame(content_frame)
        btn_frame.grid(row=6, column=0, sticky="we", padx=5, pady=20, columnspan=2)
        btn_style = ttk.Style()
        btn_style.configure('Action.TButton', font=('Arial', 10, 'bold'), padding=5)
        self.generate_btn = ttk.Button(btn_frame, text="生成骨料", command=self.start_generation_thread,
                                       style='Action.TButton', width=12)
        self.generate_btn.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        self.cancel_btn = ttk.Button(btn_frame, text="取消生成", command=self.cancel_generation,
                                     state=tk.DISABLED, style='Action.TButton', width=12)
        self.cancel_btn.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        self.clear_btn = ttk.Button(btn_frame, text="清除骨料", command=self.clear_aggregates,
                                    state=tk.DISABLED, style='Action.TButton', width=12)
        self.clear_btn.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        self.export_btn = ttk.Button(btn_frame, text="导出数据", command=self.export_data,
                                     state=tk.DISABLED, style='Action.TButton', width=12)
        self.export_btn.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)

        # === 状态区域 ===
        status_frame = ttk.Frame(content_frame)
        status_frame.grid(row=7, column=0, sticky="we", padx=5, pady=10, columnspan=2)
        self.status_var = tk.StringVar(value="就绪 - 等待用户操作")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN,
                               anchor=tk.W, padding=5, background="#f0f0f0")
        status_bar.pack(fill=tk.X, ipady=3)

        # === 性能信息 ===
        perf_frame = ttk.Frame(content_frame)
        perf_frame.grid(row=8, column=0, sticky="we", padx=5, pady=5, columnspan=2)
        self.perf_var = tk.StringVar(value="性能: 未生成")
        perf_label = ttk.Label(perf_frame, textvariable=self.perf_var, foreground="#0066cc")
        perf_label.pack(anchor=tk.W)

        # === 孔隙度信息 ===
        self.porosity_frame = ttk.Frame(content_frame)
        self.porosity_frame.grid(row=9, column=0, sticky="we", padx=5, pady=5, columnspan=2)
        self.porosity_var_text = tk.StringVar(value="孔隙度: 未计算")
        porosity_label = ttk.Label(self.porosity_frame, textvariable=self.porosity_var_text,
                                   foreground="#cc6600", font=("Arial", 9, "bold"))
        porosity_label.pack(anchor=tk.W)

        # === 骨料密度信息 ===
        self.density_frame = ttk.Frame(content_frame)
        self.density_frame.grid(row=10, column=0, sticky="we", padx=5, pady=5, columnspan=2)
        self.density_var_text = tk.StringVar(value="骨料面积占比: 未计算")
        density_label = ttk.Label(self.density_frame, textvariable=self.density_var_text,
                                  foreground="#006600", font=("Arial", 9))
        density_label.pack(anchor=tk.W)

    def add_group_ui(self):
        """为每一组创建UI框架"""
        group_id = len(self.group_frames) + 1
        group_frame = ttk.LabelFrame(self.shape_groups_frame, text=f"第 {group_id} 组", padding=10)
        group_frame.pack(fill=tk.X, padx=5, pady=5, anchor="n")

        # 删除按钮框架
        delete_frame = ttk.Frame(group_frame)
        delete_frame.grid(row=0, column=0, columnspan=6, sticky="e", padx=5, pady=2)
        delete_btn = ttk.Button(delete_frame, text="删除此组", command=lambda f=group_frame, i=group_id-1: self.delete_group_ui(f, i))
        delete_btn.pack(side=tk.RIGHT)

        # 面积占比
        ttk.Label(group_frame, text="面积占比 (%):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        area_var = tk.DoubleVar(value=DEFAULT_GROUP['area_ratio'])
        ttk.Entry(group_frame, textvariable=area_var, width=6).grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # ITZ 厚度
        ttk.Label(group_frame, text="ITZ 厚度 (mm):").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        itz_var = tk.DoubleVar(value=DEFAULT_GROUP['itz_thickness'])
        ttk.Entry(group_frame, textvariable=itz_var, width=6).grid(row=1, column=3, sticky="w", padx=5, pady=2)

        # 图层颜色 (可选，用于在CAD中区分)
        ttk.Label(group_frame, text="图层颜色:").grid(row=1, column=4, sticky="w", padx=5, pady=2)
        color_var = tk.StringVar(value=DEFAULT_GROUP['layer_color'])
        color_combo = ttk.Combobox(group_frame, textvariable=color_var, values=list(CAD_COLOR_MAP.keys()), width=6, state="readonly")
        color_combo.grid(row=1, column=5, sticky="w", padx=5, pady=2)

        # 最大数量 (用于孔隙度模式下的安全限制)
        ttk.Label(group_frame, text="最大数量:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        max_count_var = tk.IntVar(value=DEFAULT_GROUP['max_count'])
        ttk.Entry(group_frame, textvariable=max_count_var, width=6).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # 形态选择框架 (与原版类似，但属于此组)
        shape_select_frame = ttk.Frame(group_frame)
        shape_select_frame.grid(row=3, column=0, columnspan=6, sticky="w", padx=5, pady=5)
        poly_var = tk.BooleanVar(value=DEFAULT_SHAPE_POLYGON['weight'] > 0)
        circle_var = tk.BooleanVar(value=DEFAULT_SHAPE_CIRCLE['weight'] > 0)
        ellipse_var = tk.BooleanVar(value=DEFAULT_SHAPE_ELLIPSE['weight'] > 0)
        ttk.Checkbutton(shape_select_frame, text="多边形", variable=poly_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(shape_select_frame, text="圆形", variable=circle_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(shape_select_frame, text="椭圆形", variable=ellipse_var).pack(side=tk.LEFT, padx=5)

        # 权重设置框架
        weight_frame = ttk.Frame(group_frame)
        weight_frame.grid(row=4, column=0, columnspan=6, sticky="w", padx=5, pady=5)
        ttk.Label(weight_frame, text="形态权重比例 (多边形:圆形:椭圆形):").pack(side=tk.LEFT, padx=5)
        weight_poly_var = tk.IntVar(value=DEFAULT_SHAPE_POLYGON['weight'])
        ttk.Entry(weight_frame, textvariable=weight_poly_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(weight_frame, text=":").pack(side=tk.LEFT)
        weight_circle_var = tk.IntVar(value=DEFAULT_SHAPE_CIRCLE['weight'])
        ttk.Entry(weight_frame, textvariable=weight_circle_var, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(weight_frame, text=":").pack(side=tk.LEFT)
        weight_ellipse_var = tk.IntVar(value=DEFAULT_SHAPE_ELLIPSE['weight'])
        ttk.Entry(weight_frame, textvariable=weight_ellipse_var, width=3).pack(side=tk.LEFT, padx=2)

        # 形态参数框架 (与原版类似，但属于此组)
        # 多边形参数
        polygon_frame = ttk.LabelFrame(group_frame, text="多边形参数", padding=5)
        polygon_frame.grid(row=5, column=0, sticky="we", padx=5, pady=5)
        ttk.Label(polygon_frame, text="尺寸范围 (mm):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        poly_min_size_var = tk.DoubleVar(value=DEFAULT_SHAPE_POLYGON['min_size'])
        ttk.Entry(polygon_frame, textvariable=poly_min_size_var, width=6).grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(polygon_frame, text="-").grid(row=0, column=2, padx=2)
        poly_max_size_var = tk.DoubleVar(value=DEFAULT_SHAPE_POLYGON['max_size'])
        ttk.Entry(polygon_frame, textvariable=poly_max_size_var, width=6).grid(row=0, column=3, padx=2, pady=2)
        ttk.Label(polygon_frame, text="边数范围:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        poly_min_sides_var = tk.IntVar(value=DEFAULT_SHAPE_POLYGON['min_sides'])
        ttk.Entry(polygon_frame, textvariable=poly_min_sides_var, width=6).grid(row=1, column=1, padx=2, pady=2)
        ttk.Label(polygon_frame, text="-").grid(row=1, column=2, padx=2)
        poly_max_sides_var = tk.IntVar(value=DEFAULT_SHAPE_POLYGON['max_sides'])
        ttk.Entry(polygon_frame, textvariable=poly_max_sides_var, width=6).grid(row=1, column=3, padx=2, pady=2)

        # 圆形参数
        circle_frame = ttk.LabelFrame(group_frame, text="圆形参数", padding=5)
        circle_frame.grid(row=5, column=1, sticky="we", padx=5, pady=5)
        circle_frame.grid_remove() # 默认隐藏
        ttk.Label(circle_frame, text="半径范围 (mm):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        circle_min_radius_var = tk.DoubleVar(value=DEFAULT_SHAPE_CIRCLE['min_radius'])
        ttk.Entry(circle_frame, textvariable=circle_min_radius_var, width=6).grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(circle_frame, text="-").grid(row=0, column=2, padx=2)
        circle_max_radius_var = tk.DoubleVar(value=DEFAULT_SHAPE_CIRCLE['max_radius'])
        ttk.Entry(circle_frame, textvariable=circle_max_radius_var, width=6).grid(row=0, column=3, padx=2, pady=2)

        # 椭圆参数
        ellipse_frame = ttk.LabelFrame(group_frame, text="椭圆形参数", padding=5)
        ellipse_frame.grid(row=5, column=2, sticky="we", padx=5, pady=5)
        ellipse_frame.grid_remove() # 默认隐藏
        ttk.Label(ellipse_frame, text="长轴范围 (mm):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ellipse_min_major_var = tk.DoubleVar(value=DEFAULT_SHAPE_ELLIPSE['min_major'])
        ttk.Entry(ellipse_frame, textvariable=ellipse_min_major_var, width=6).grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(ellipse_frame, text="-").grid(row=0, column=2, padx=2)
        ellipse_max_major_var = tk.DoubleVar(value=DEFAULT_SHAPE_ELLIPSE['max_major'])
        ttk.Entry(ellipse_frame, textvariable=ellipse_max_major_var, width=6).grid(row=0, column=3, padx=2, pady=2)
        ttk.Label(ellipse_frame, text="短轴范围 (mm):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ellipse_min_minor_var = tk.DoubleVar(value=DEFAULT_SHAPE_ELLIPSE['min_minor'])
        ttk.Entry(ellipse_frame, textvariable=ellipse_min_minor_var, width=6).grid(row=1, column=1, padx=2, pady=2)
        ttk.Label(ellipse_frame, text="-").grid(row=1, column=2, padx=2)
        ellipse_max_minor_var = tk.DoubleVar(value=DEFAULT_SHAPE_ELLIPSE['max_minor'])
        ttk.Entry(ellipse_frame, textvariable=ellipse_max_minor_var, width=6).grid(row=1, column=3, padx=2, pady=2)

        # 绑定形态选择事件 (作用于此组)
        poly_var.trace_add("write", lambda *args: self.toggle_shape_frame(polygon_frame, circle_frame, ellipse_frame, poly_var, circle_var, ellipse_var))
        circle_var.trace_add("write", lambda *args: self.toggle_shape_frame(polygon_frame, circle_frame, ellipse_frame, poly_var, circle_var, ellipse_var))
        ellipse_var.trace_add("write", lambda *args: self.toggle_shape_frame(polygon_frame, circle_frame, ellipse_frame, poly_var, circle_var, ellipse_var))

        # 将此组的所有变量存储起来
        group_data = {
            'id': group_id,
            'area_ratio_var': area_var,
            'itz_thickness_var': itz_var,
            'layer_color_var': color_var,
            'max_count_var': max_count_var,
            'shapes': [ # 存储形态配置的列表
                {'type': 'polygon', 'enabled_var': poly_var, 'weight_var': weight_poly_var, 'min_size_var': poly_min_size_var, 'max_size_var': poly_max_size_var, 'min_sides_var': poly_min_sides_var, 'max_sides_var': poly_max_sides_var},
                {'type': 'circle', 'enabled_var': circle_var, 'weight_var': weight_circle_var, 'min_radius_var': circle_min_radius_var, 'max_radius_var': circle_max_radius_var},
                {'type': 'ellipse', 'enabled_var': ellipse_var, 'weight_var': weight_ellipse_var, 'min_major_var': ellipse_min_major_var, 'max_major_var': ellipse_max_major_var, 'min_minor_var': ellipse_min_minor_var, 'max_minor_var': ellipse_max_minor_var}
            ]
        }
        self.groups_data.append(group_data)
        self.group_frames.append(group_frame)

    def delete_group_ui(self, frame, index):
        """删除UI上的一个组"""
        if len(self.group_frames) <= 1:
            messagebox.showwarning("警告", "至少需要保留一组配置")
            return
        frame.destroy()
        self.group_frames.pop(index)
        self.groups_data.pop(index)
        # 重新编号
        for i, f in enumerate(self.group_frames):
            f.config(text=f"第 {i+1} 组")
        # 更新数据中的ID
        for i, d in enumerate(self.groups_data):
            d['id'] = i+1


    def toggle_shape_frame(self, polygon_frame, circle_frame, ellipse_frame, poly_var, circle_var, ellipse_var):
        """切换形态参数框架的显示/隐藏 (作用于传入的框架)"""
        if poly_var.get():
            polygon_frame.grid()
        else:
            polygon_frame.grid_remove()
        if circle_var.get():
            circle_frame.grid()
        else:
            circle_frame.grid_remove()
        if ellipse_var.get():
            ellipse_frame.grid()
        else:
            ellipse_frame.grid_remove()

    def toggle_generation_mode(self):
        """切换生成模式"""
        mode = self.mode_var.get()
        if mode == "count":
            self.count_label.grid()
            self.count_entry.grid()
            self.attempts_label.grid()
            self.max_attempts_entry.grid()
            self.porosity_label.grid_remove()
            self.target_porosity_entry.grid_remove()
            self.max_agg_label.grid_remove()
            self.max_aggregates_entry.grid_remove()
        elif mode == "porosity":
            self.porosity_label.grid()
            self.target_porosity_entry.grid()
            self.max_agg_label.grid()
            self.max_aggregates_entry.grid()
            self.count_label.grid_remove()
            self.count_entry.grid_remove()
            self.attempts_label.grid_remove()
            self.max_attempts_entry.grid_remove()

    def update_slider_value(self, slider_type):
        """更新滑块数值"""
        if slider_type == "str":
            value = self.boundary_strength_var.get()
            self.strength_value.config(text=f"{value:.2f}")

    def on_mousewheel(self, event):
        """鼠标滚轮"""
        if event.delta:
            self.scrollable_frame.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_mousewheel_linux(self, event):
        """Linux鼠标滚轮"""
        if event.num == 4:
            self.scrollable_frame.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.scrollable_frame.canvas.yview_scroll(1, "units")

    def set_default_values(self):
        """设置默认值"""
        self.x_min_var.set(DEFAULT_REGION[0])
        self.y_min_var.set(DEFAULT_REGION[1])
        self.x_max_var.set(DEFAULT_REGION[2])
        self.y_max_var.set(DEFAULT_REGION[3])
        self.boundary_color_var.set(DEFAULT_BOUNDARY_COLOR)
        self.boundary_optimize_var.set(DEFAULT_BOUNDARY_OPTIMIZE)
        self.count_var.set(50) # 示例值
        self.min_distance_var.set(DEFAULT_MIN_DISTANCE)
        self.target_porosity_var.set(DEFAULT_TARGET_POROSITY)
        self.max_aggregates_var.set(DEFAULT_MAX_AGGREGATES)
        self.max_attempts_var.set(DEFAULT_MAX_ATTEMPTS)
        self.boundary_strength_var.set(DEFAULT_BOUNDARY_STRENGTH)
        self.update_slider_value("str")

    def start_generation_thread(self):
        """启动生成线程"""
        try:
            # 收集参数
            region_min = (self.x_min_var.get(), self.y_min_var.get())
            region_max = (self.x_max_var.get(), self.y_max_var.get())
            params = {
                "region_min": region_min,
                "region_max": region_max,
                "min_distance": self.min_distance_var.get(),
                "boundary_adjust": self.boundary_optimize_var.get(),
                "progress_queue": self.progress_queue,
                "draw_queue": self.draw_queue
            }

            # 根据模式设置不同参数
            mode = self.mode_var.get()
            if mode == "count":
                params["max_attempts"] = self.max_attempts_var.get()
            elif mode == "porosity":
                params["max_attempts"] = self.max_attempts_var.get()

            # 参数验证
            self.validate_parameters(params, mode)

            # 构建组配置
            groups = []
            total_area_ratio = 0
            for group_data in self.groups_data:
                group_shapes = []
                for shape_conf in group_data['shapes']:
                    if shape_conf['enabled_var'].get():
                        conf = {
                            'type': shape_conf['type'],
                            'weight': shape_conf['weight_var'].get()
                        }
                        if shape_conf['type'] == 'polygon':
                            conf.update({
                                'min_size': shape_conf['min_size_var'].get(),
                                'max_size': shape_conf['max_size_var'].get(),
                                'min_sides': shape_conf['min_sides_var'].get(),
                                'max_sides': shape_conf['max_sides_var'].get(),
                            })
                        elif shape_conf['type'] == 'circle':
                            conf.update({
                                'min_radius': shape_conf['min_radius_var'].get(),
                                'max_radius': shape_conf['max_radius_var'].get(),
                            })
                        elif shape_conf['type'] == 'ellipse':
                            conf.update({
                                'min_major': shape_conf['min_major_var'].get(),
                                'max_major': shape_conf['max_major_var'].get(),
                                'min_minor': shape_conf['min_minor_var'].get(),
                                'max_minor': shape_conf['max_minor_var'].get(),
                            })
                        group_shapes.append(conf)
                
                if not group_shapes:
                    raise ValueError(f"第 {group_data['id']} 组未选择任何形态")
                
                area_ratio = group_data['area_ratio_var'].get()
                total_area_ratio += area_ratio
                if area_ratio < 0:
                    raise ValueError(f"第 {group_data['id']} 组面积占比不能为负")
                
                groups.append({
                    'id': group_data['id'],
                    'area_ratio': area_ratio,
                    'itz_thickness': group_data['itz_thickness_var'].get(),
                    'max_count': group_data['max_count_var'].get(),
                    'layer_color': group_data['layer_color_var'].get(),
                    'shapes': group_shapes
                })

            if mode == "porosity" and total_area_ratio > 100:
                 raise ValueError(f"所有组的面积占比总和 ({total_area_ratio:.2f}%) 超过100%，在孔隙度模式下无法达到。")

            # 初始化生成器
            if not self.generator:
                try:
                    self.generator = RandomAggregateGenerator()
                    self.status_var.set("已成功连接AutoCAD")
                    logging.info("生成器初始化成功")
                except Exception as e:
                    logging.error(f"连接AutoCAD失败: {str(e)}")
                    raise ConnectionError(f"连接AutoCAD失败: {str(e)}")

            # 设置生成模式和参数
            self.generator.set_generation_mode(mode)
            if mode == "porosity":
                self.generator.set_target_porosity(self.target_porosity_var.get())
            self.generator.set_groups(groups)
            self.generator.set_boundary_color(self.boundary_color_var.get())

            # 更新状态
            if mode == "count":
                self.status_var.set(f"正在生成骨料 (多组模式)...")
            else:
                self.status_var.set(f"孔隙度模式: 目标孔隙度 {self.target_porosity_var.get()}% (多组模式)...")

            # 禁用生成按钮，防止重复点击
            self.generate_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.NORMAL)
            self.export_btn.config(state=tk.DISABLED)
            self.clear_btn.config(state=tk.DISABLED)

            # 显示进度条
            self.progress_frame.grid()
            self.progress_var.set(0)
            self.progress_label.config(text="正在初始化...")

            # 启动生成线程
            self.generation_thread = threading.Thread(
                target=self._generate_in_thread,
                args=(params, mode),
                daemon=True
            )
            self.generation_thread.start()
            logging.info("生成线程已启动")

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set(f"错误: {str(e)}")
            self.porosity_var_text.set("孔隙度: 计算失败")
            self.density_var_text.set("骨料面积占比: 计算失败")
            self.generate_btn.config(state=tk.NORMAL)
            self.progress_frame.grid_remove()
            logging.error(f"启动生成线程时出错: {str(e)}")

    def _generate_in_thread(self, params, mode):
        """在子线程中执行生成"""
        try:
            logging.info("开始生成骨料 (多组)")
            generated_count = self.generator.generate_aggregates_in_region(**params)
            self.progress_queue.put(("result", generated_count))
            logging.info(f"生成完成，共生成 {generated_count} 个骨料")
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            self.progress_queue.put(("error", str(e), error_msg))
            logging.error(f"生成过程中出错: {str(e)}\n{error_msg}")

    def process_draw_queue(self):
        """处理绘图队列"""
        try:
            while not self.draw_queue.empty():
                command, *data = self.draw_queue.get_nowait()
                if command == 'boundary':
                    boundary_points, color = data
                    self.create_boundary(boundary_points, color)
                elif command == 'aggregate':
                    point_array = data[0]
                    color = data[1] if len(data) > 1 else 1 # 获取组颜色
                    self.create_aggregate(point_array, color)
                elif command == 'regen':
                    if self.generator and self.generator.acad and self.generator.acad.doc:
                        try:
                            self.generator.acad.doc.Regen(0)
                            logging.debug("已执行重绘命令")
                        except Exception as e:
                            logging.error(f"重绘失败: {str(e)}")
        finally:
            self.root.after(100, self.process_draw_queue)

    def create_boundary(self, points, color):
        """创建边界"""
        from pyautocad import aDouble, APoint
        if not self.generator:
            return
        try:
            if self.generator.region_boundary:
                try:
                    self.generator.region_boundary.Delete()
                    self.generator.draw_objects.remove(self.generator.region_boundary)
                except:
                    pass
            point_array = aDouble(points)
            self.generator.region_boundary = self.generator.model_space.AddPolyline(point_array)
            if self.generator.region_boundary:
                self.generator.region_boundary.Closed = True
                self.generator.region_boundary.Color = color
                self.generator.draw_objects.append(self.generator.region_boundary)
                min_x, min_y = points[0], points[1]
                max_x, max_y = points[3], points[4]
                logging.info("边界创建成功")
        except Exception as e:
            logging.error(f"创建边界失败: {str(e)}")
            try:
                min_x, min_y = points[0], points[1]
                max_x, max_y = points[3], points[4]
                width = max_x - min_x
                height = max_y - min_y
                self.generator.region_boundary = self.generator.model_space.AddRectangle(
                    APoint(min_x, min_y, 0), width, height)
                self.generator.region_boundary.Color = color
                self.generator.draw_objects.append(self.generator.region_boundary)
                logging.info("使用备用方案创建矩形边界成功")
            except Exception as e:
                logging.error(f"备用方案创建边界也失败: {str(e)}")

    def create_aggregate(self, point_array, color=1):
        """创建骨料 (增加颜色参数)"""
        from pyautocad import aDouble
        if not self.generator:
            return
        try:
            polyline = self.generator.model_space.AddPolyline(aDouble(point_array))
            polyline.Closed = True
            polyline.Color = color # 设置颜色
            self.generator.draw_objects.append(polyline)
            logging.debug("骨料创建成功")
            return polyline
        except Exception as e:
            logging.error(f"创建骨料失败: {str(e)}")
            return None

    def check_progress(self):
        """检查进度"""
        try:
            while not self.progress_queue.empty():
                msg_type, *data = self.progress_queue.get_nowait()
                if msg_type == "progress":
                    count, total_area, porosity = data
                    mode = self.mode_var.get()
                    if mode == "count":
                        # 这里可以显示总生成数或各组进度，简化为总进度
                        self.progress_label.config(text=f"已生成 {count} 个骨料")
                    else:
                        self.progress_label.config(text=f"已生成 {count} 个骨料, 当前孔隙度: {porosity:.2f}%")
                    # 进度条可以基于总尝试次数或预估完成度，这里简化
                    self.progress_var.set(0) # 或者根据逻辑计算
                    if self.generator.region_area > 0:
                        self.porosity_var_text.set(f"孔隙度: {porosity:.2f}%")
                        aggregate_ratio = (total_area / self.generator.region_area) * 100
                        self.density_var_text.set(f"骨料面积占比: {aggregate_ratio:.2f}%")
                elif msg_type == "info":
                    info = data[0]
                    self.status_var.set(info)
                    logging.info(f"信息更新: {info}")
                elif msg_type == "result":
                    generated_count = data[0]
                    gen_time = self.generator.get_generation_time()
                    current_porosity = self.generator.calculate_porosity()
                    mode = self.mode_var.get()
                    if mode == "count":
                        self.status_var.set(f"成功生成 {generated_count} 个骨料 (多组)")
                    else:
                        self.status_var.set(f"孔隙度模式完成: 生成 {generated_count} 个骨料 (多组)")
                    self.perf_var.set(f"耗时: {gen_time}秒 | 最终孔隙度: {current_porosity:.2f}%")
                    if self.generator.region_area > 0:
                        self.porosity_var_text.set(f"孔隙度: {current_porosity:.2f}%")
                        aggregate_ratio = (self.generator.total_area / self.generator.region_area) * 100
                        self.density_var_text.set(f"骨料面积占比: {aggregate_ratio:.2f}%")
                    self.export_btn.config(state=tk.NORMAL)
                    self.clear_btn.config(state=tk.NORMAL)
                    self.generate_btn.config(state=tk.NORMAL)
                    self.cancel_btn.config(state=tk.DISABLED)
                    self.progress_frame.grid_remove()
                    self.progress_label.config(text="生成完成!")
                elif msg_type == "error":
                    import traceback
                    error_msg, traceback_msg = data
                    messagebox.showerror("生成错误", f"{error_msg}\n详细信息:\n{traceback_msg}")
                    self.status_var.set(f"错误: {error_msg}")
                    self.porosity_var_text.set("孔隙度: 计算失败")
                    self.density_var_text.set("骨料面积占比: 计算失败")
                    self.generate_btn.config(state=tk.NORMAL)
                    self.cancel_btn.config(state=tk.DISABLED)
                    self.progress_frame.grid_remove()
        except queue.Empty:
            pass
        self.root.after(100, self.check_progress)

    def cancel_generation(self):
        """取消生成"""
        if self.generator and self.generation_thread and self.generation_thread.is_alive():
            self.generator.cancel_generation()
            self.cancel_btn.config(state=tk.DISABLED)
            self.progress_label.config(text="正在取消生成...")
            self.status_var.set("正在取消生成过程...")
            logging.info("已发送取消生成请求")

    def validate_parameters(self, params, mode):
        """验证参数"""
        min_x, min_y = params["region_min"]
        max_x, max_y = params["region_max"]
        if min_x >= max_x or min_y >= max_y:
            raise ValueError("区域坐标设置错误: 右上角坐标应大于左下角坐标")
        if params["min_distance"] < 0:
            raise ValueError("最小间距不能为负数")
        if mode == "porosity":
            porosity = self.target_porosity_var.get()
            if porosity <= 0 or porosity >= 100:
                raise ValueError("目标孔隙度必须在0到100之间")

    def export_data(self):
        """导出数据"""
        if not self.generator or not self.generator.generated_aggregates:
            messagebox.showwarning("警告", "没有骨料数据可导出")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            title="保存骨料数据",
            initialfile="骨料数据.csv"
        )
        if not file_path:
            return
        try:
            if self.generator.export_to_csv(file_path):
                porosity = self.generator.calculate_porosity()
                aggregate_ratio = 100 - porosity
                with open(file_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([])
                    writer.writerow(["区域面积", self.generator.region_area])
                    writer.writerow(["骨料总面积", self.generator.total_area])
                    writer.writerow(["骨料面积占比(%)", f"{aggregate_ratio:.2f}"])
                    writer.writerow(["孔隙度(%)", f"{porosity:.2f}"])
                    writer.writerow(["边界颜色", self.boundary_color_var.get()])
                    writer.writerow(["边界优化", "启用" if self.boundary_optimize_var.get() else "禁用"])
                    writer.writerow(["生成模式", "孔隙度" if self.generator.generation_mode == "porosity" else "骨料数量"])
                    if self.generator.generation_mode == "porosity":
                        writer.writerow(["目标孔隙度(%)", f"{self.target_porosity_var.get():.2f}"])
                    min_x, min_y = self.generator.boundary_min
                    max_x, max_y = self.generator.boundary_max
                    writer.writerow(["边界左下角X", min_x[0]])
                    writer.writerow(["边界左下角Y", min_y[1]])
                    writer.writerow(["边界右上角X", max_x[0]])
                    writer.writerow(["边界右上角Y", max_y[1]])
                    # 添加组配置信息
                    writer.writerow([])
                    writer.writerow(["组配置信息"])
                    for group in self.generator.groups.get_config():
                        writer.writerow([f"组ID", group['id']])
                        writer.writerow(["", f"面积占比(%)", group['area_ratio']])
                        writer.writerow(["", f"ITZ厚度", group['itz_thickness']])
                        writer.writerow(["", f"最大数量", group['max_count']])
                        writer.writerow(["", f"图层颜色", group['layer_color']])
                        writer.writerow(["", "形态配置:"])
                        for shape in group['shapes']:
                            writer.writerow(["", "", f"类型: {shape['type']}, 权重: {shape['weight']}"])
                messagebox.showinfo("导出成功", f"骨料数据已成功导出到:\n{file_path}")
                self.status_var.set(f"数据已导出: {os.path.basename(file_path)}")
            else:
                messagebox.showerror("导出错误", "导出失败，请检查文件路径和权限")
        except Exception as e:
            messagebox.showerror("导出错误", f"导出失败: {str(e)}")

    def clear_aggregates(self):
        """清除骨料"""
        if not self.generator:
            return
        if not messagebox.askyesno("确认清除", "确定要清除所有生成的骨料吗？"):
            return
        try:
            deleted_count = self.generator.clear_generated()
            if deleted_count > 0:
                self.status_var.set(f"已清除 {deleted_count} 个骨料")
                self.export_btn.config(state=tk.DISABLED)
                self.clear_btn.config(state=tk.DISABLED)
                self.perf_var.set("性能: 未生成")
                self.porosity_var_text.set("孔隙度: 未计算")
                self.density_var_text.set("骨料面积占比: 未计算")
            else:
                self.status_var.set("没有可清除的骨料")
        except Exception as e:
            messagebox.showerror("清除错误", f"清除失败: {str(e)}")

    def on_close(self):
        """关闭窗口"""
        try:
            if self.generator:
                try:
                    self.generator.clear_generated()
                except:
                    pass
                try:
                    self.generator.acad.doc.SetVariable("REGENMODE", 1)
                except:
                    pass
            if self.generation_thread and self.generation_thread.is_alive():
                if self.generator:
                    self.generator.cancel_generation()
                self.generation_thread.join(timeout=1.0)
        except Exception as e:
            logging.error(f"关闭时出错: {str(e)}")
        self.root.destroy()
        logging.info("程序已关闭")