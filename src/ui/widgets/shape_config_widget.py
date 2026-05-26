# shape_config_widget.py

from PySide6.QtWidgets import (
    QWidget, QGroupBox, QLabel, QLineEdit, QCheckBox, 
    QFormLayout, QHBoxLayout, QDoubleSpinBox, QSpinBox
)
from PySide6.QtCore import Signal, Slot

class ShapeConfigWidget(QWidget):
    """
    形状配置组件
    
    用于配置多边形、圆形、椭圆形的参数
    """
    
    shape_changed = Signal(dict)
    
    def __init__(self, shape_type: str = "polygon", parent=None):
        super().__init__(parent)
        self.shape_type = shape_type
        self._setup_ui()
    
    def _setup_ui(self):
        """
        设置UI界面
        """
        layout = QFormLayout()
        
        # 根据形状类型定制启用复选框文本
        label_map = {
            "polygon": "启用多边形骨料",
            "circle": "启用圆形骨料",
            "ellipse": "启用椭圆形骨料"
        }
        checkbox_label = label_map.get(self.shape_type, "启用该形状")
        
        self.type_check = QCheckBox(checkbox_label)
        self.type_check.setChecked(True)
        self.type_check.toggled.connect(self._on_type_toggled)
        layout.addRow(self.type_check)
        
        self.weight_spin = QSpinBox()
        self.weight_spin.setRange(0, 100)
        self.weight_spin.setValue(1)
        self.weight_spin.valueChanged.connect(self._emit_changed)
        layout.addRow("选择权重:", self.weight_spin)
        
        self.polygon_group = QGroupBox("多边形参数")
        polygon_layout = QFormLayout()
        
        self.poly_min_size = QDoubleSpinBox()
        self.poly_min_size.setRange(0.1, 100.0)
        self.poly_min_size.setValue(2.0)
        self.poly_min_size.setSingleStep(0.1)
        self.poly_min_size.valueChanged.connect(self._emit_changed)
        polygon_layout.addRow("最小尺寸 (mm):", self.poly_min_size)
        
        self.poly_max_size = QDoubleSpinBox()
        self.poly_max_size.setRange(0.1, 100.0)
        self.poly_max_size.setValue(8.0)
        self.poly_max_size.setSingleStep(0.1)
        self.poly_max_size.valueChanged.connect(self._emit_changed)
        polygon_layout.addRow("最大尺寸 (mm):", self.poly_max_size)
        
        self.poly_min_sides = QSpinBox()
        self.poly_min_sides.setRange(3, 20)
        self.poly_min_sides.setValue(3)
        self.poly_min_sides.valueChanged.connect(self._emit_changed)
        polygon_layout.addRow("最小边数:", self.poly_min_sides)
        
        self.poly_max_sides = QSpinBox()
        self.poly_max_sides.setRange(3, 20)
        self.poly_max_sides.setValue(7)
        self.poly_max_sides.valueChanged.connect(self._emit_changed)
        polygon_layout.addRow("最大边数:", self.poly_max_sides)
        
        self.polygon_group.setLayout(polygon_layout)
        layout.addRow(self.polygon_group)
        
        self.circle_group = QGroupBox("圆形参数")
        circle_layout = QFormLayout()
        
        self.circle_min_radius = QDoubleSpinBox()
        self.circle_min_radius.setRange(0.1, 50.0)
        self.circle_min_radius.setValue(2.0)
        self.circle_min_radius.setSingleStep(0.1)
        self.circle_min_radius.valueChanged.connect(self._emit_changed)
        circle_layout.addRow("最小半径 (mm):", self.circle_min_radius)
        
        self.circle_max_radius = QDoubleSpinBox()
        self.circle_max_radius.setRange(0.1, 50.0)
        self.circle_max_radius.setValue(5.0)
        self.circle_max_radius.setSingleStep(0.1)
        self.circle_max_radius.valueChanged.connect(self._emit_changed)
        circle_layout.addRow("最大半径 (mm):", self.circle_max_radius)
        
        self.circle_segments = QSpinBox()
        self.circle_segments.setRange(8, 100)
        self.circle_segments.setValue(36)
        self.circle_segments.valueChanged.connect(self._emit_changed)
        circle_layout.addRow("分段数:", self.circle_segments)
        
        self.circle_group.setLayout(circle_layout)
        layout.addRow(self.circle_group)
        
        self.ellipse_group = QGroupBox("椭圆形参数")
        ellipse_layout = QFormLayout()
        
        self.ellipse_min_major = QDoubleSpinBox()
        self.ellipse_min_major.setRange(0.1, 100.0)
        self.ellipse_min_major.setValue(3.0)
        self.ellipse_min_major.setSingleStep(0.1)
        self.ellipse_min_major.valueChanged.connect(self._emit_changed)
        ellipse_layout.addRow("最小长轴 (mm):", self.ellipse_min_major)
        
        self.ellipse_max_major = QDoubleSpinBox()
        self.ellipse_max_major.setRange(0.1, 100.0)
        self.ellipse_max_major.setValue(10.0)
        self.ellipse_max_major.setSingleStep(0.1)
        self.ellipse_max_major.valueChanged.connect(self._emit_changed)
        ellipse_layout.addRow("最大长轴 (mm):", self.ellipse_max_major)
        
        self.ellipse_min_minor = QDoubleSpinBox()
        self.ellipse_min_minor.setRange(0.1, 100.0)
        self.ellipse_min_minor.setValue(2.0)
        self.ellipse_min_minor.setSingleStep(0.1)
        self.ellipse_min_minor.valueChanged.connect(self._emit_changed)
        ellipse_layout.addRow("最小短轴 (mm):", self.ellipse_min_minor)
        
        self.ellipse_max_minor = QDoubleSpinBox()
        self.ellipse_max_minor.setRange(0.1, 100.0)
        self.ellipse_max_minor.setValue(8.0)
        self.ellipse_max_minor.setSingleStep(0.1)
        self.ellipse_max_minor.valueChanged.connect(self._emit_changed)
        ellipse_layout.addRow("最大短轴 (mm):", self.ellipse_max_minor)
        
        self.ellipse_segments = QSpinBox()
        self.ellipse_segments.setRange(8, 100)
        self.ellipse_segments.setValue(36)
        self.ellipse_segments.valueChanged.connect(self._emit_changed)
        ellipse_layout.addRow("分段数:", self.ellipse_segments)
        
        self.ellipse_group.setLayout(ellipse_layout)
        layout.addRow(self.ellipse_group)
        
        self.setLayout(layout)
        
        # 初始状态：仅显示该组件对应的形状参数面板，且受 checkbox 勾选状态控制
        checked = self.type_check.isChecked()
        self.polygon_group.setVisible(self.shape_type == "polygon" and checked)
        self.circle_group.setVisible(self.shape_type == "circle" and checked)
        self.ellipse_group.setVisible(self.shape_type == "ellipse" and checked)
    
    @Slot(bool)
    def _on_type_toggled(self, checked: bool):
        """
        类型切换槽函数
        """
        if self.shape_type == "polygon":
            self.polygon_group.setVisible(checked)
        elif self.shape_type == "circle":
            self.circle_group.setVisible(checked)
        elif self.shape_type == "ellipse":
            self.ellipse_group.setVisible(checked)
        self._emit_changed()
    
    @Slot()
    def _emit_changed(self):
        """
        发射形状变化信号
        """
        config = self.get_config()
        self.shape_changed.emit(config)
    
    def get_config(self) -> dict:
        """
        获取形状配置
        
        Returns:
            dict: 形状配置字典
        """
        config = {
            'type': self.shape_type,
            'weight': self.weight_spin.value(),
        }
        
        if self.shape_type == "polygon":
            config.update({
                'min_size': self.poly_min_size.value(),
                'max_size': self.poly_max_size.value(),
                'min_sides': self.poly_min_sides.value(),
                'max_sides': self.poly_max_sides.value(),
                'irregularity': 0.3,
                'spikiness': 0.2,
                'optimize_sides': True
            })
        elif self.shape_type == "circle":
            config.update({
                'min_radius': self.circle_min_radius.value(),
                'max_radius': self.circle_max_radius.value(),
                'segments': self.circle_segments.value(),
            })
        elif self.shape_type == "ellipse":
            config.update({
                'min_major': self.ellipse_min_major.value(),
                'max_major': self.ellipse_max_major.value(),
                'min_minor': self.ellipse_min_minor.value(),
                'max_minor': self.ellipse_max_minor.value(),
                'segments': self.ellipse_segments.value(),
            })
            
        return config
    
    def set_config(self, config: dict):
        """
        设置形状配置
        
        Args:
            config: 形状配置字典
        """
        # 如果从加载的配置中包含 weight 或启用状态
        weight = config.get('weight', 1)
        self.type_check.setChecked(weight > 0)
        self.weight_spin.setValue(weight)
        
        if self.shape_type == "polygon":
            self.poly_min_size.setValue(config.get('min_size', 2.0))
            self.poly_max_size.setValue(config.get('max_size', 8.0))
            self.poly_min_sides.setValue(config.get('min_sides', 3))
            self.poly_max_sides.setValue(config.get('max_sides', 7))
        elif self.shape_type == "circle":
            self.circle_min_radius.setValue(config.get('min_radius', 2.0) if 'min_radius' in config else config.get('min_size', 2.0))
            self.circle_max_radius.setValue(config.get('max_radius', 5.0) if 'max_radius' in config else config.get('max_size', 5.0))
            self.circle_segments.setValue(config.get('segments', 36))
        elif self.shape_type == "ellipse":
            self.ellipse_min_major.setValue(config.get('min_major', 3.0) if 'min_major' in config else config.get('min_size', 3.0))
            self.ellipse_max_major.setValue(config.get('max_major', 10.0) if 'max_major' in config else config.get('max_size', 10.0))
            self.ellipse_min_minor.setValue(config.get('min_minor', 2.0) if 'min_minor' in config else config.get('min_size', 2.0)/1.5)
            self.ellipse_max_minor.setValue(config.get('max_minor', 8.0) if 'max_minor' in config else config.get('max_size', 8.0)/1.2)
            self.ellipse_segments.setValue(config.get('segments', 36))
