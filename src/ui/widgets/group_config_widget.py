# group_config_widget.py

from PySide6.QtWidgets import (
    QWidget, QGroupBox, QLabel, QLineEdit, QDoubleSpinBox, 
    QSpinBox, QComboBox, QPushButton, QFormLayout, QVBoxLayout,
    QHBoxLayout
)
from PySide6.QtCore import Signal, Slot

from .shape_config_widget import ShapeConfigWidget
from ...configs.config import CADColorMap, DEFAULT_GROUP, DEFAULT_SHAPE_POLYGON, DEFAULT_SHAPE_CIRCLE, DEFAULT_SHAPE_ELLIPSE

class GroupConfigWidget(QGroupBox):
    """
    组配置组件
    
    用于配置单个骨料组的参数，包括面积占比、ITZ厚度、形状等
    """
    
    config_changed = Signal(dict)
    remove_requested = Signal()
    
    def __init__(self, group_id: int, parent=None):
        super().__init__(f"第 {group_id} 组", parent)
        self.group_id = group_id
        self._setup_ui()
    
    def _setup_ui(self):
        """
        设置UI界面
        """
        layout = QFormLayout()
        
        delete_btn_layout = QHBoxLayout()
        delete_btn_layout.addStretch()
        delete_btn = QPushButton("删除此组")
        delete_btn.clicked.connect(self.remove_requested.emit)
        delete_btn_layout.addWidget(delete_btn)
        layout.addRow(delete_btn_layout)
        
        self.area_ratio_spin = QDoubleSpinBox()
        self.area_ratio_spin.setRange(0.1, 100.0)
        self.area_ratio_spin.setValue(DEFAULT_GROUP['area_ratio'])
        self.area_ratio_spin.setSingleStep(1.0)
        self.area_ratio_spin.setSuffix(" %")
        self.area_ratio_spin.valueChanged.connect(self._emit_changed)
        layout.addRow("面积占比:", self.area_ratio_spin)
        
        self.itz_thickness_spin = QDoubleSpinBox()
        self.itz_thickness_spin.setRange(0.0, 10.0)
        self.itz_thickness_spin.setValue(DEFAULT_GROUP['itz_thickness'])
        self.itz_thickness_spin.setSingleStep(0.1)
        self.itz_thickness_spin.setSuffix(" mm")
        self.itz_thickness_spin.valueChanged.connect(self._emit_changed)
        layout.addRow("ITZ 厚度:", self.itz_thickness_spin)
        
        color_map = CADColorMap.get_color_map()
        self.color_combo = QComboBox()
        self.color_combo.addItems(list(color_map.keys()))
        self.color_combo.setCurrentText(DEFAULT_GROUP['layer_color'])
        self.color_combo.currentTextChanged.connect(self._emit_changed)
        layout.addRow("图层颜色:", self.color_combo)
        
        self.max_count_spin = QSpinBox()
        self.max_count_spin.setRange(1, 1000)
        self.max_count_spin.setValue(DEFAULT_GROUP['max_count'])
        self.max_count_spin.valueChanged.connect(self._emit_changed)
        layout.addRow("最大数量:", self.max_count_spin)
        
        self.polygon_widget = ShapeConfigWidget("polygon")
        self.polygon_widget.set_config(DEFAULT_SHAPE_POLYGON)
        self.polygon_widget.shape_changed.connect(self._emit_changed)
        layout.addRow(self.polygon_widget)
        
        self.circle_widget = ShapeConfigWidget("circle")
        self.circle_widget.set_config(DEFAULT_SHAPE_CIRCLE)
        self.circle_widget.shape_changed.connect(self._emit_changed)
        layout.addRow(self.circle_widget)
        
        self.ellipse_widget = ShapeConfigWidget("ellipse")
        self.ellipse_widget.set_config(DEFAULT_SHAPE_ELLIPSE)
        self.ellipse_widget.shape_changed.connect(self._emit_changed)
        layout.addRow(self.ellipse_widget)
        
        self.setLayout(layout)
    
    @Slot()
    def _emit_changed(self):
        """
        发射配置变化信号
        """
        config = self.get_config()
        self.config_changed.emit(config)
    
    def get_config(self) -> dict:
        """
        获取组配置
        
        Returns:
            dict: 组配置字典
        """
        shapes = []
        
        if self.polygon_widget.type_check.isChecked():
            shapes.append(self.polygon_widget.get_config())
        
        if self.circle_widget.type_check.isChecked():
            shapes.append(self.circle_widget.get_config())
        
        if self.ellipse_widget.type_check.isChecked():
            shapes.append(self.ellipse_widget.get_config())
        
        color_map = CADColorMap.get_color_map()
        
        return {
            'id': self.group_id,
            'area_ratio': self.area_ratio_spin.value(),
            'itz_thickness': self.itz_thickness_spin.value(),
            'max_count': self.max_count_spin.value(),
            'layer_color': self.color_combo.currentText(),
            'shapes': shapes
        }
    
    def set_config(self, config: dict):
        """
        设置组配置
        
        Args:
            config: 组配置字典
        """
        self.area_ratio_spin.setValue(config.get('area_ratio', DEFAULT_GROUP['area_ratio']))
        self.itz_thickness_spin.setValue(config.get('itz_thickness', DEFAULT_GROUP['itz_thickness']))
        self.max_count_spin.setValue(config.get('max_count', DEFAULT_GROUP['max_count']))
        self.color_combo.setCurrentText(config.get('layer_color', DEFAULT_GROUP['layer_color']))
        
        shapes = config.get('shapes', [])
        for shape in shapes:
            shape_type = shape.get('type', '')
            if shape_type == 'polygon':
                self.polygon_widget.set_config(shape)
            elif shape_type == 'circle':
                self.circle_widget.set_config(shape)
            elif shape_type == 'ellipse':
                self.ellipse_widget.set_config(shape)
