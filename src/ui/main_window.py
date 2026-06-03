# main_window.py

import sys
import logging
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QProgressBar, QComboBox, QCheckBox,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QApplication, QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Signal, Slot, QThread, Qt, QTimer
from PySide6.QtGui import QAction, QIcon

from .widgets.scrollable_frame import ScrollableFrame
from .widgets.group_config_widget import GroupConfigWidget
from .widgets.preview_widget import PreviewWidget
from ..core.generator import RandomAggregateGenerator
from ..configs.config import (
    CADColorMap, SpecimenType, DEFAULT_REGION, DEFAULT_MIN_DISTANCE,
    DEFAULT_TARGET_POROSITY, DEFAULT_MAX_ATTEMPTS, DEFAULT_BOUNDARY_COLOR,
    DEFAULT_BOUNDARY_OPTIMIZE, DEFAULT_BOUNDARY_STRENGTH, DEFAULT_GROUP
)

class GenerationWorker(QThread):
    """
    骨料生成工作线程
    """
    
    progress_update = Signal(str, int, float, float)
    draw_command = Signal(tuple)
    generation_finished = Signal(int)
    generation_error = Signal(str)
    
    def __init__(self, generator: RandomAggregateGenerator, params: Dict[str, Any]):
        super().__init__()
        self.generator = generator
        self.params = params
    
    def run(self):
        """
        执行生成任务
        """
        try:
            count = self.generator.generate_aggregates_in_region(
                region_min=self.params['region_min'],
                region_max=self.params['region_max'],
                min_distance=self.params['min_distance'],
                max_attempts=self.params['max_attempts'],
                boundary_adjust=self.params['boundary_adjust'],
                progress_callback=self._on_progress_update,
                draw_callback=self._on_draw_command,
                allow_touching=self.params['allow_touching']
            )
            self.generation_finished.emit(count)
        except Exception as e:
            logging.error(f"生成过程出错: {e}", exc_info=True)
            self.generation_error.emit(str(e))
    
    def _on_progress_update(self, msg_type: str, count: int, area: float, porosity: float):
        """
        进度更新回调
        """
        self.progress_update.emit(msg_type, count, area, porosity)
    
    def _on_draw_command(self, command: tuple):
        """
        绘图命令回调
        """
        self.draw_command.emit(command)
    
    def stop(self):
        """
        停止生成
        """
        self.generator.cancel_generation()
        self.wait()

class MainWindow(QMainWindow):
    """
    AutoCAD随机骨料生成器主窗口
    
    使用PySide6实现，提供现代化的用户界面
    """
    
    def __init__(self):
        super().__init__()
        self.generator: Optional[RandomAggregateGenerator] = None
        self.generation_worker: Optional[GenerationWorker] = None
        self.group_widgets: List[GroupConfigWidget] = []
        self.draw_objects: List[Any] = []
        self.cad_type = "autocad"
        
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        
        logging.info("PySide6主窗口已初始化")
    
    def _setup_ui(self):
        """
        设置UI界面
        """
        self.setWindowTitle("RandomCAD - 随机骨料生成器")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局改为水平布局以实现左右分栏
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 左侧控制面板容器
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # 滚动区域用于容纳所有的参数配置小部件
        scrollable_frame = ScrollableFrame()
        content_layout = scrollable_frame.get_layout()
        content_layout.setSpacing(8)
        
        self._create_region_panel(content_layout)
        self._create_groups_panel(content_layout)
        self._create_mode_panel(content_layout)
        self._create_parameters_panel(content_layout)
        self._create_advanced_panel(content_layout)
        
        left_layout.addWidget(scrollable_frame)
        
        # 进度、按钮、状态和信息放到左侧底部
        self._create_progress_panel(left_layout)
        self._create_buttons_panel(left_layout)
        
        # GPU 加速开关
        self.gpu_checkbox = QCheckBox("使用 GPU 加速")
        self.gpu_checkbox.setChecked(False)
        self.gpu_checkbox.stateChanged.connect(self._on_gpu_checkbox_changed)
        left_layout.addWidget(self.gpu_checkbox)

        # 同步到 CAD 按钮
        self.sync_cad_btn = QPushButton("同步绘制到 CAD")
        self.sync_cad_btn.setMinimumHeight(40)
        self.sync_cad_btn.setEnabled(False)
        self.sync_cad_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
            QPushButton:disabled {
                background-color: #c0c4cc;
            }
        """)
        self.sync_cad_btn.clicked.connect(self._sync_to_cad)
        left_layout.addWidget(self.sync_cad_btn)
        
        left_layout.addSpacing(5)
        self._create_status_panel(left_layout)
        self._create_info_panel(left_layout)

        # GPU 状态标签（位于状态面板下方）
        self.gpu_status_label = QLabel("GPU 加速: 未启用")
        self.gpu_status_label.setStyleSheet("color: #909399; font-size: 12px;")
        left_layout.addWidget(self.gpu_status_label)
        
        left_widget.setFixedWidth(400)
        main_layout.addWidget(left_widget)
        
        # 右侧预览画布区
        self.preview_widget = PreviewWidget(self)
        main_layout.addWidget(self.preview_widget, stretch=1)
        
        self._set_default_values()
    
    def _setup_menu(self):
        """
        设置菜单栏
        """
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件(&F)")
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """
        连接信号和槽
        """
        pass
    
    def _create_region_panel(self, layout: QVBoxLayout):
        """
        创建区域设置面板
        """
        panel = QGroupBox("生成区域设置")
        form_layout = QFormLayout()
        
        self.cad_type_combo = QComboBox()
        self.cad_type_combo.addItems(["AutoCAD", "中望CAD (ZWCAD)"])
        self.cad_type_combo.setCurrentIndex(0)
        self.cad_type_combo.currentTextChanged.connect(self._on_cad_type_changed)
        form_layout.addRow("CAD类型:", self.cad_type_combo)
        
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1000.0, 1000.0)
        self.x_min_spin.setValue(DEFAULT_REGION[0])
        self.x_min_spin.setSingleStep(1.0)
        form_layout.addRow("左下角 X:", self.x_min_spin)
        
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1000.0, 1000.0)
        self.y_min_spin.setValue(DEFAULT_REGION[1])
        self.y_min_spin.setSingleStep(1.0)
        form_layout.addRow("左下角 Y:", self.y_min_spin)
        
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1000.0, 1000.0)
        self.x_max_spin.setValue(DEFAULT_REGION[2])
        self.x_max_spin.setSingleStep(1.0)
        form_layout.addRow("右上角 X:", self.x_max_spin)
        
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1000.0, 1000.0)
        self.y_max_spin.setValue(DEFAULT_REGION[3])
        self.y_max_spin.setSingleStep(1.0)
        form_layout.addRow("右上角 Y:", self.y_max_spin)
        
        color_map = CADColorMap.get_color_map()
        self.boundary_color_combo = QComboBox()
        self.boundary_color_combo.addItems(list(color_map.keys()))
        self.boundary_color_combo.setCurrentText(DEFAULT_BOUNDARY_COLOR)
        form_layout.addRow("边界颜色:", self.boundary_color_combo)
        
        self.boundary_optimize_check = QCheckBox("边界优化")
        self.boundary_optimize_check.setChecked(DEFAULT_BOUNDARY_OPTIMIZE)
        form_layout.addRow("", self.boundary_optimize_check)
        
        panel.setLayout(form_layout)
        layout.addWidget(panel)
    
    def _create_groups_panel(self, layout: QVBoxLayout):
        """
        创建多组粒径设置面板
        """
        self.groups_panel = QGroupBox("多组粒径设置")
        groups_layout = QVBoxLayout()
        
        self.add_group_btn = QPushButton("添加一组")
        self.add_group_btn.clicked.connect(self._add_group)
        groups_layout.addWidget(self.add_group_btn)
        
        self.groups_container = QWidget()
        self.groups_container_layout = QVBoxLayout(self.groups_container)
        groups_layout.addWidget(self.groups_container)
        
        self.groups_panel.setLayout(groups_layout)
        layout.addWidget(self.groups_panel)
        
        self._add_group()
    
    def _create_mode_panel(self, layout: QVBoxLayout):
        """
        创建生成模式面板
        """
        panel = QGroupBox("生成模式")
        mode_layout = QVBoxLayout()
        
        self.count_radio = QRadioButton("按骨料数量生成")
        self.porosity_radio = QRadioButton("按孔隙度生成")
        
        mode_group = QButtonGroup()
        mode_group.addButton(self.count_radio)
        mode_group.addButton(self.porosity_radio)
        
        self.count_radio.setChecked(True)
        
        mode_layout.addWidget(self.count_radio)
        mode_layout.addWidget(self.porosity_radio)
        
        mode_tip = QLabel("孔隙度模式: 通过骨料面积占比控制材料密度")
        mode_tip.setStyleSheet("color: #666666;")
        mode_layout.addWidget(mode_tip)
        
        panel.setLayout(mode_layout)
        layout.addWidget(panel)
        
        self.count_radio.toggled.connect(self._update_mode_visibility)
        self.porosity_radio.toggled.connect(self._update_mode_visibility)
    
    def _create_parameters_panel(self, layout: QVBoxLayout):
        """
        创建骨料参数面板
        """
        self.params_panel = QGroupBox("骨料参数")
        form_layout = QFormLayout()
        
        self.porosity_label = QLabel("目标孔隙度(%):")
        self.porosity_spin = QDoubleSpinBox()
        self.porosity_spin.setRange(0.0, 100.0)
        self.porosity_spin.setValue(DEFAULT_TARGET_POROSITY)
        self.porosity_spin.setSingleStep(1.0)
        self.porosity_spin.setSuffix(" %")
        form_layout.addRow(self.porosity_label, self.porosity_spin)
        
        self.min_distance_spin = QDoubleSpinBox()
        self.min_distance_spin.setRange(0.0, 10.0)
        self.min_distance_spin.setValue(DEFAULT_MIN_DISTANCE)
        self.min_distance_spin.setSingleStep(0.1)
        self.min_distance_spin.setSuffix(" mm")
        form_layout.addRow("最小间距:", self.min_distance_spin)
        
        self.params_panel.setLayout(form_layout)
        layout.addWidget(self.params_panel)
        
        self.porosity_label.setVisible(False)
        self.porosity_spin.setVisible(False)
    
    def _create_advanced_panel(self, layout: QVBoxLayout):
        """
        创建高级设置面板
        """
        panel = QGroupBox("高级设置")
        form_layout = QFormLayout()
        
        self.max_attempts_spin = QSpinBox()
        self.max_attempts_spin.setRange(10, 1000)
        self.max_attempts_spin.setValue(DEFAULT_MAX_ATTEMPTS)
        form_layout.addRow("最大尝试次数:", self.max_attempts_spin)
        
        self.boundary_strength_spin = QDoubleSpinBox()
        self.boundary_strength_spin.setRange(0.5, 2.0)
        self.boundary_strength_spin.setValue(DEFAULT_BOUNDARY_STRENGTH)
        self.boundary_strength_spin.setSingleStep(0.1)
        form_layout.addRow("边界优化强度:", self.boundary_strength_spin)
        
        panel.setLayout(form_layout)
        layout.addWidget(panel)
    
    def _create_progress_panel(self, layout: QVBoxLayout):
        """
        创建进度面板
        """
        self.progress_panel = QWidget()
        progress_layout = QVBoxLayout(self.progress_panel)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("准备生成...")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(self.progress_panel)
        self.progress_panel.setVisible(False)
    
    def _create_buttons_panel(self, layout: QVBoxLayout):
        """
        创建按钮面板
        """
        buttons_layout = QHBoxLayout()
        
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setMinimumHeight(40)
        self.save_config_btn.clicked.connect(self._save_config)
        buttons_layout.addWidget(self.save_config_btn)
        
        self.load_config_btn = QPushButton("加载配置")
        self.load_config_btn.setMinimumHeight(40)
        self.load_config_btn.clicked.connect(self._load_config)
        buttons_layout.addWidget(self.load_config_btn)
        
        layout.addLayout(buttons_layout)
        
        buttons_layout2 = QHBoxLayout()
        
        self.generate_btn = QPushButton("生成骨料")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.clicked.connect(self._start_generation)
        buttons_layout2.addWidget(self.generate_btn)
        
        self.cancel_btn = QPushButton("取消生成")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_generation)
        buttons_layout2.addWidget(self.cancel_btn)
        
        self.clear_btn = QPushButton("清除骨料")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self._clear_aggregates)
        buttons_layout2.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.setMinimumHeight(40)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_data)
        buttons_layout2.addWidget(self.export_btn)
        
        layout.addLayout(buttons_layout2)
    
    def _create_status_panel(self, layout: QVBoxLayout):
        """
        创建状态面板
        """
        self.status_label = QLabel("就绪 - 等待用户操作")
        self.status_label.setStyleSheet("background: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        layout.addWidget(self.status_label)
    
    def _create_info_panel(self, layout: QVBoxLayout):
        """
        创建信息显示面板
        """
        info_layout = QHBoxLayout()
        
        self.perf_label = QLabel("性能: 未生成")
        self.perf_label.setStyleSheet("color: #0066cc;")
        info_layout.addWidget(self.perf_label)
        
        self.porosity_label = QLabel("孔隙度: 未计算")
        self.porosity_label.setStyleSheet("color: #cc6600; font-weight: bold;")
        info_layout.addWidget(self.porosity_label)
        
        self.density_label = QLabel("骨料面积占比: 未计算")
        self.density_label.setStyleSheet("color: #006600;")
        info_layout.addWidget(self.density_label)
        
        layout.addLayout(info_layout)
    
    def _set_default_values(self):
        """
        设置默认值
        """
        self._update_mode_visibility()
    
    def _update_mode_visibility(self):
        """
        更新模式可见性
        """
        is_count_mode = self.count_radio.isChecked()
        mode = "count" if is_count_mode else "porosity"
        self.porosity_label.setVisible(not is_count_mode)
        self.porosity_spin.setVisible(not is_count_mode)
        
        for widget in self.group_widgets:
            widget.set_mode(mode)
    
    @Slot()
    def _add_group(self):
        """
        添加新组
        """
        group_id = len(self.group_widgets) + 1
        group_widget = GroupConfigWidget(group_id)
        group_widget.config_changed.connect(self._on_group_config_changed)
        group_widget.remove_requested.connect(lambda: self._remove_group(group_widget))
        
        self.group_widgets.append(group_widget)
        self.groups_container_layout.addWidget(group_widget)
        
        mode = "count" if self.count_radio.isChecked() else "porosity"
        group_widget.set_mode(mode)
    
    @Slot(str)
    def _on_cad_type_changed(self, cad_type: str):
        """
        CAD类型变化处理
        """
        if "中望" in cad_type or "ZWCAD" in cad_type:
            self.cad_type = "zwcad"
            logging.info("已选择中望CAD")
        else:
            self.cad_type = "autocad"
            logging.info("已选择AutoCAD")
    
    @Slot()
    def _remove_group(self, widget: GroupConfigWidget):
        """
        移除组
        """
        if widget in self.group_widgets:
            self.group_widgets.remove(widget)
            self.groups_container_layout.removeWidget(widget)
            widget.deleteLater()
    
    @Slot(dict)
    def _on_group_config_changed(self, config: dict):
        """
        组配置变化处理
        """
        pass
    
    @Slot()
    def _start_generation(self):
        """
        开始生成
        """
        if self.generation_worker and self.generation_worker.isRunning():
            QMessageBox.warning(self, "警告", "生成过程正在进行中")
            return
        
        try:
            self._initialize_generator()
            
            # 清理旧的本地预览和状态
            self.preview_widget.clear()
            self.sync_cad_btn.setEnabled(False)
            
            params = {
                'region_min': (self.x_min_spin.value(), self.y_min_spin.value()),
                'region_max': (self.x_max_spin.value(), self.y_max_spin.value()),
                'min_distance': self.min_distance_spin.value(),
                'max_attempts': self.max_attempts_spin.value(),
                'boundary_adjust': self.boundary_optimize_check.isChecked(),
                'allow_touching': True
            }
            
            self.generation_worker = GenerationWorker(self.generator, params)
            self.generation_worker.progress_update.connect(self._on_progress_update)
            self.generation_worker.draw_command.connect(self._on_draw_command)
            self.generation_worker.generation_finished.connect(self._on_generation_finished)
            self.generation_worker.generation_error.connect(self._on_generation_error)
            
            self._set_generating_state(True)
            self.generation_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动生成失败: {str(e)}")
            logging.error(f"启动生成失败: {e}", exc_info=True)
    
    @Slot()
    def _cancel_generation(self):
        """
        取消生成
        """
        if self.generation_worker and self.generation_worker.isRunning():
            self.generation_worker.stop()
            self.status_label.setText("生成已取消")
    
    @Slot()
    def _clear_aggregates(self):
        """
        清除骨料
        """
        if not self.generator:
            QMessageBox.warning(self, "警告", "生成器未初始化")
            return
        
        reply = QMessageBox.question(
            self, "确认", "确定要清除所有骨料吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 先清除本地画布
                self.preview_widget.clear()
                self.sync_cad_btn.setEnabled(False)
                
                # 先删除 MainWindow 持有的 CAD 对象
                deleted = 0
                for obj in self.draw_objects:
                    try:
                        self.generator.cad_connection.delete_object(obj)
                        deleted += 1
                    except Exception:
                        pass
                self.draw_objects.clear()
                
                # 重置生成器状态
                self.generator.clear_generated()
                QMessageBox.information(self, "成功", f"已清除 {deleted} 个 CAD 对象")
                self._update_info_display()
                self.export_btn.setEnabled(False)
                self.clear_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清除失败: {str(e)}")
                logging.error(f"清除失败: {e}", exc_info=True)
    
    @Slot()
    def _export_data(self):
        """
        导出数据
        """
        if not self.generator or not self.generator.generated_aggregates:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        try:
            filename, selected_filter = self._get_save_filename(
                "CSV文件 (*.csv);;JSON文件 (*.json)", "aggregates.csv"
            )
            if filename:
                if filename.endswith('.json'):
                    success = self.generator.export_to_json(filename)
                else:
                    success = self.generator.export_to_csv(filename)
                if success:
                    QMessageBox.information(self, "成功", f"数据已导出到: {filename}")
                else:
                    QMessageBox.critical(self, "错误", "导出失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
            logging.error(f"导出失败: {e}", exc_info=True)
    
    @Slot(str, int, float, float)
    def _on_progress_update(self, msg_type: str, count: int, area: float, porosity: float):
        """
        进度更新处理
        """
        if msg_type == "progress":
            if self.generator:
                if self.generator.generation_mode == "count":
                    total_max = sum(g['max_count'] for g in self.generator.groups.get_config())
                    if total_max > 0:
                        progress_pct = int(count / total_max * 100)
                    else:
                        progress_pct = 0
                    self.progress_bar.setValue(progress_pct)
                    self.progress_label.setText(f"已生成 {count}/{total_max} 个骨料 ({progress_pct}%)")
                else:
                    target_area = self.generator.region_area * (1 - self.generator.target_porosity)
                    if target_area > 0:
                        progress_pct = min(100, int(area / target_area * 100))
                    else:
                        progress_pct = 0
                    self.progress_bar.setValue(progress_pct)
                    self.progress_label.setText(f"已生成 {count} 个骨料 | 面积: {area:.1f} (目标 {target_area:.1f}, {progress_pct}%)")
            self._update_info_display()
        elif msg_type == "info":
            self.status_label.setText(msg)
    
    @Slot(tuple)
    def _on_draw_command(self, command: tuple):
        """
        绘图命令处理
        """
        if not self.generator:
            return
        
        cmd_type = command[0]
        
        # 1. 始终渲染在软件内置本地画布上（即便是 CAD 未连接）
        if hasattr(self, 'preview_widget') and self.preview_widget:
            if cmd_type == 'boundary':
                points, color = command[1], command[2]
                self.preview_widget.draw_boundary(points, color)
            elif cmd_type == 'aggregate':
                points, color = command[1], command[2]
                layer_name = command[3] if len(command) > 3 else None
                self.preview_widget.draw_aggregate(points, color, layer_name)
            elif cmd_type == 'regen':
                self.preview_widget.fit_view()
        
        # 2. 如果已连接 CAD，同步绘制到 CAD
        if self.generator.cad_connection.is_connected:
            if cmd_type == 'boundary':
                points, color = command[1], command[2]
                layer_name = command[3] if len(command) > 3 else None
                obj = self.generator.cad_connection.draw_boundary(points, color, layer_name)
                if obj:
                    self.draw_objects.append(obj)
            
            elif cmd_type == 'aggregate':
                points, color = command[1], command[2]
                layer_name = command[3] if len(command) > 3 else None
                obj = self.generator.cad_connection.draw_aggregate(points, color, layer_name)
                if obj:
                    self.draw_objects.append(obj)
            
            elif cmd_type == 'regen':
                self.generator.cad_connection.regen()
    
    @Slot(int)
    def _on_generation_finished(self, count: int):
        """
        生成完成处理
        """
        self._set_generating_state(False)
        
        if self.generator and self.generator.cad_connection.is_connected:
            cad_status = "且已渲染至 CAD"
        else:
            cad_status = "（仅限本地预览，点击“同步绘制到 CAD”导入）"
            
        self.status_label.setText(f"生成完成，共生成 {count} 个骨料 {cad_status}")
        self.export_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.sync_cad_btn.setEnabled(True) # 启用同步到 CAD 按钮
        self._update_info_display()
        self._show_statistics()
        logging.info(f"生成完成，共生成 {count} 个骨料")
    
    @Slot(str)
    def _on_generation_error(self, error_msg: str):
        """
        生成错误处理
        """
        self._set_generating_state(False)
        self.status_label.setText(f"生成失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"生成失败: {error_msg}")
        logging.error(f"生成失败: {error_msg}")
    
    def _show_statistics(self):
        """
        显示生成统计摘要
        """
        if not self.generator or not self.generator.generated_aggregates:
            return
        
        g = self.generator
        time_str = f"{g.get_generation_time():.2f} 秒"
        count = len(g.generated_aggregates)
        porosity = g.calculate_porosity()
        total_area = g.total_area
        
        group_stats = []
        for group in g.groups.get_config():
            name = f"第 {group['id']} 组"
            cnt = group['count']
            area = group['generated_area']
            target = group['target_area']
            pct = (area / target * 100) if target > 0 else 0
            group_stats.append(f"{name}: {cnt} 个, 面积 {area:.2f} (目标 {target:.2f}, {pct:.0f}%)")
        
        msg = f"=== 生成统计 ===\n\n"
        msg += f"总骨料数: {count}\n"
        msg += f"总骨料面积: {total_area:.2f}\n"
        msg += f"孔隙度: {porosity:.2f}%\n"
        msg += f"总耗时: {time_str}\n\n"
        msg += "--- 分组明细 ---\n"
        for s in group_stats:
            msg += f"{s}\n"
        
        QMessageBox.information(self, "生成统计", msg)
    
    @Slot(int)
    def _on_gpu_checkbox_changed(self, state: int) -> None:
        """Handle GPU checkbox changes"""
        use_gpu = self.gpu_checkbox.isChecked()
        if self.generator:
            self.generator.set_use_gpu(use_gpu)
            actual_use_gpu = self.generator.use_gpu
        else:
            try:
                import torch
                actual_use_gpu = use_gpu and torch.cuda.is_available()
            except ImportError:
                actual_use_gpu = False

        # Update status label
        if actual_use_gpu:
            self.gpu_status_label.setText("GPU 加速: ✅ 已启用")
            self.gpu_status_label.setStyleSheet("color: #67c23a; font-size: 12px; font-weight: bold;")
        else:
            if use_gpu:  # User checked it but CUDA is not available
                self.gpu_status_label.setText("GPU 加速: ❌ 未启用 (CUDA 不可用)")
                self.gpu_status_label.setStyleSheet("color: #f56c6c; font-size: 12px; font-weight: bold;")
                self.gpu_checkbox.blockSignals(True)
                self.gpu_checkbox.setChecked(False)
                self.gpu_checkbox.blockSignals(False)
            else:
                self.gpu_status_label.setText("GPU 加速: 已禁用")
                self.gpu_status_label.setStyleSheet("color: #909399; font-size: 12px;")

    def _set_generating_state(self, generating: bool) -> None:
        """
        设置生成状态
        """
        self.generate_btn.setEnabled(not generating)
        self.cancel_btn.setEnabled(generating)
        self.progress_panel.setVisible(generating)
        self.gpu_checkbox.setEnabled(not generating)
        
        if generating:
            self.progress_bar.setValue(0)
            self.progress_label.setText("正在生成...")
    
    def _initialize_generator(self) -> None:
        """
        初始化生成器
        """
        # 如果生成器不为空，但是 CAD 类型发生了切换，需要重新创建生成器以匹配正确的 CAD API
        if self.generator is not None and self.generator.cad_connection._cad_type.value != self.cad_type:
            self.generator.clear_generated()
            self.generator = None
            
        if self.generator is None:
            # 默认不自动启动 CAD 连接，避免抛出 ConnectionError，支持仅限本地生成模式
            self.generator = RandomAggregateGenerator(auto_start=False, cad_type=self.cad_type)
            
            # 尝试静默连接 CAD
            self.status_label.setText("正在尝试连接 CAD 软件...")
            QApplication.processEvents()
            success = self.generator.cad_connection.connect()
            if success:
                self.status_label.setText("已连接至 CAD，开始双通道生成绘制")
            else:
                self.status_label.setText("未检测到运行中的 CAD，进入仅限本地预览模式")
            QApplication.processEvents()
        
        self.generator.set_generation_mode("count" if self.count_radio.isChecked() else "porosity")
        self.generator.set_target_porosity(self.porosity_spin.value())
        
        groups_config = []
        for widget in self.group_widgets:
            groups_config.append(widget.get_config())
        
        if groups_config:
            self.generator.set_groups(groups_config)
        
        # 同步 GPU 加速状态到生成器
        self.generator.set_use_gpu(self.gpu_checkbox.isChecked())

    @Slot()
    def _sync_to_cad(self):
        """
        将本地生成的骨料数据一键同步绘制到 CAD
        """
        if not self.generator:
            QMessageBox.warning(self, "警告", "没有已生成的骨料数据")
            return
            
        if not self.generator.generated_aggregates:
            QMessageBox.warning(self, "警告", "请先生成骨料后再同步")
            return
            
        self.status_label.setText("正在尝试连接 CAD 软件...")
        QApplication.processEvents()
        
        # 尝试连接 CAD
        if not self.generator.cad_connection.is_connected:
            success = self.generator.cad_connection.connect()
            if not success:
                QMessageBox.critical(self, "错误", "无法连接到 CAD，请确保 AutoCAD 或中望CAD 已经运行并打开了空白图纸。")
                self.status_label.setText("同步失败：无法连接 CAD")
                return
                
        self.status_label.setText("正在同步骨料到 CAD 中，请稍候...")
        QApplication.processEvents()
        
        try:
            # 创建图层
            self.generator.cad_connection.create_layer("RandomCAD-Boundary", 7)
            self.generator.cad_connection.create_layer("RandomCAD-Aggregates", 7)
            self.generator.cad_connection.create_layer("RandomCAD-ITZ", 4)
            
            # 绘制边界（支持矩形和圆形试件）
            from src.configs.config import SpecimenType
            from src.core.shapes import generate_circle
            
            if hasattr(self.generator, 'specimen_type') and self.generator.specimen_type == SpecimenType.CIRCLE:
                # 圆形试件：生成圆形边界点
                center = self.generator.circle_center
                radius = self.generator.circle_diameter / 2.0
                circle_points = generate_circle(center, radius, 72)
                boundary_points = []
                for p in circle_points:
                    boundary_points.extend([float(p[0]), float(p[1]), 0.0])
                boundary_points.extend([float(circle_points[0][0]), float(circle_points[0][1]), 0.0])
            else:
                # 矩形试件
                min_x, min_y = self.x_min_spin.value(), self.y_min_spin.value()
                max_x, max_y = self.x_max_spin.value(), self.y_max_spin.value()
                boundary_points = [
                    float(min_x), float(min_y), 0.0,
                    float(max_x), float(min_y), 0.0,
                    float(max_x), float(max_y), 0.0,
                    float(min_x), float(max_y), 0.0,
                    float(min_x), float(min_y), 0.0
                ]
            
            # 清除旧边界，绘制新边界
            if self.generator.region_boundary:
                try:
                    self.generator.cad_connection.delete_object(self.generator.region_boundary)
                except Exception:
                    pass
            
            boundary_obj = self.generator.cad_connection.draw_boundary(
                boundary_points, self.generator.boundary_color, "RandomCAD-Boundary"
            )
            if boundary_obj:
                self.generator.region_boundary = boundary_obj
                self.draw_objects.append(boundary_obj)
                
            # 绘制每一个骨料和 ITZ
            color_map = CADColorMap.get_color_map()
            for agg in self.generator.generated_aggregates:
                group_id = agg["group_id"]
                chosen_group = next((g for g in self.generator.groups.get_config() if g["id"] == group_id), None)
                if not chosen_group:
                    continue
                    
                color_name = chosen_group.get('layer_color', "红色")
                color = color_map.get(color_name, CADColorMap.RED)
                
                point_array = []
                for p in agg["points"]:
                    if hasattr(p, 'x') and hasattr(p, 'y'):
                        point_array.extend([p.x, p.y, 0.0])
                    else:
                        point_array.extend([p[0], p[1], 0.0])
                
                # 绘制骨料
                obj = self.generator.cad_connection.draw_aggregate(point_array, color, "RandomCAD-Aggregates")
                if obj:
                    self.draw_objects.append(obj)
                    
                # 绘制 ITZ
                itz_thickness = agg.get('itz_thickness', 0.0)
                if itz_thickness > 0 and agg.get('shapely_itz'):
                    try:
                        itz_polygon = agg['shapely_itz']
                        if hasattr(itz_polygon, 'exterior'):
                            itz_points = list(itz_polygon.exterior.coords)
                            itz_point_array = []
                            for p in itz_points:
                                itz_point_array.extend([p[0], p[1], 0.0])
                            
                            itz_color = (color % 7) + 1
                            itz_obj = self.generator.cad_connection.draw_aggregate(itz_point_array, itz_color, "RandomCAD-ITZ")
                            if itz_obj:
                                self.draw_objects.append(itz_obj)
                    except Exception as e:
                        logging.warning(f"同步绘制 ITZ 失败: {e}")
            
            self.generator.cad_connection.regen()
            self.status_label.setText(f"同步成功：已将 {len(self.generator.generated_aggregates)} 个骨料同步至 CAD")
            QMessageBox.information(self, "成功", f"已成功将 {len(self.generator.generated_aggregates)} 个骨料同步绘制到 CAD 软件中！")
            
        except Exception as e:
            self.status_label.setText("同步出错")
            QMessageBox.critical(self, "错误", f"同步绘制到 CAD 失败: {str(e)}")
            logging.error(f"同步绘制到 CAD 失败: {e}", exc_info=True)
    
    def _update_info_display(self):
        """
        更新信息显示
        """
        if self.generator:
            time_elapsed = self.generator.get_generation_time()
            self.perf_label.setText(f"性能: {time_elapsed:.2f} 秒")
            
            porosity = self.generator.calculate_porosity()
            self.porosity_label.setText(f"孔隙度: {porosity:.2f}%")
            
            density = 100.0 - porosity
            self.density_label.setText(f"骨料面积占比: {density:.2f}%")
    
    @Slot()
    def _save_config(self):
        """
        保存组配置到文件
        """
        if not self.generator:
            self._initialize_generator()
        
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "保存配置", "groups_config.json", "JSON文件 (*.json)"
            )
            if filename:
                groups_config = []
                for widget in self.group_widgets:
                    groups_config.append(widget.get_config())
                self.generator.set_groups(groups_config)
                self.generator.set_generation_mode("count" if self.count_radio.isChecked() else "porosity")
                self.generator.set_target_porosity(self.porosity_spin.value())
                
                success = self.generator.save_config(filename)
                if success:
                    QMessageBox.information(self, "成功", f"配置已保存到: {filename}")
                else:
                    QMessageBox.critical(self, "错误", "保存配置失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
            logging.error(f"保存配置失败: {e}", exc_info=True)

    @Slot()
    def _load_config(self):
        """
        从文件加载组配置
        """
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "加载配置", "", "JSON文件 (*.json)"
            )
            if not filename:
                return
            
            if not self.generator:
                self.generator = RandomAggregateGenerator(auto_start=True, cad_type=self.cad_type)
            
            data = self.generator.load_config(filename)
            
            groups_config = data.get('groups', [])
            if not groups_config:
                QMessageBox.warning(self, "警告", "配置文件中没有组配置数据")
                return
            
            mode = data.get('mode', 'count')
            porosity = data.get('porosity', 0.0)
            
            if mode == 'count':
                self.count_radio.setChecked(True)
                self.porosity_radio.setChecked(False)
            else:
                self.count_radio.setChecked(False)
                self.porosity_radio.setChecked(True)
            self._update_mode_visibility()
            self.porosity_spin.setValue(porosity)
            
            for widget in self.group_widgets:
                self.groups_container_layout.removeWidget(widget)
                widget.deleteLater()
            self.group_widgets.clear()
            
            for i, group_conf in enumerate(groups_config):
                group_id = i + 1
                group_widget = GroupConfigWidget(group_id)
                group_widget.config_changed.connect(self._on_group_config_changed)
                group_widget.remove_requested.connect(lambda w=group_widget: self._remove_group(w))
                group_widget.set_config(group_conf)
                self.group_widgets.append(group_widget)
                self.groups_container_layout.addWidget(group_widget)
            
            QMessageBox.information(self, "成功", f"已加载 {len(groups_config)} 个组配置")
            logging.info(f"已从 {filename} 加载配置: {len(groups_config)} 个组, 模式: {mode}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")
            logging.error(f"加载配置失败: {e}", exc_info=True)

    def _get_save_filename(self, file_filter: str, default_name: str) -> tuple:
        """
        获取保存文件名
        
        Returns:
            tuple: (文件名, 文件类型)
        """
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存文件", default_name, file_filter
        )
        return filename, _
    
    def _show_about(self):
        """
        显示关于对话框
        """
        QMessageBox.about(
            self, "关于 RandomCAD",
            "RandomCAD v2.0.0\n\n"
            "随机骨料生成器\n\n"
            "使用PySide6构建\n"
            "支持AutoCAD集成"
        )
    
    def closeEvent(self, event):
        """
        关闭事件处理
        """
        if self.generation_worker and self.generation_worker.isRunning():
            reply = QMessageBox.question(
                self, "确认", "生成过程正在进行，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            self.generation_worker.stop()
        
        if self.generator:
            self.generator.clear_generated()
        
        logging.info("程序已关闭")
        event.accept()

def main():
    """
    主函数
    """
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    logging.info("程序启动")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
