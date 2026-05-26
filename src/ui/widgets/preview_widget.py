# preview_widget.py

import logging
from typing import List, Tuple, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QBrush, QPolygonF, QPainter, QWheelEvent, QMouseEvent

# CAD 颜色索引映射到现代美化 QColor
COLOR_MAP = {
    1: QColor(235, 87, 87, 210),    # 红色 (Red)
    2: QColor(242, 201, 76, 210),   # 黄色 (Yellow)
    3: QColor(39, 174, 96, 210),    # 绿色 (Green)
    4: QColor(45, 156, 219, 210),   # 青色 (Cyan)
    5: QColor(47, 128, 237, 210),   # 蓝色 (Blue)
    6: QColor(155, 81, 224, 210),   # 紫色 (Magenta)
    7: QColor(80, 80, 80, 210),     # 白色/灰色 (White)
}

# ITZ 颜色（偏浅，高透明度）
ITZ_COLOR_MAP = {
    1: QColor(235, 87, 87, 60),
    2: QColor(242, 201, 76, 60),
    3: QColor(39, 174, 96, 60),
    4: QColor(45, 156, 219, 60),
    5: QColor(47, 128, 237, 60),
    6: QColor(155, 81, 224, 60),
    7: QColor(180, 180, 180, 60),
}


class InteractiveGraphicsView(QGraphicsView):
    """
    支持滚轮缩放和鼠标拖拽平移的 QGraphicsView
    """
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor(248, 249, 250))) # 极浅灰色背景，现代清爽
        
        # 翻转 Y 轴，使 Y 轴指向上方，与 CAD/Cartesian 坐标系一致
        self.scale(1, -1)
        
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0

    def wheelEvent(self, event: QWheelEvent):
        """
        滚轮进行缩放
        """
        zoom_factor = 1.15
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
            
        # 限制缩放范围
        current_scale = self.transform().m11()
        if (zoom_factor < 1.0 and current_scale < 0.1) or (zoom_factor > 1.0 and current_scale > 100.0):
            return
            
        self.scale(zoom_factor, zoom_factor)


class PreviewWidget(QWidget):
    """
    RandomCAD 骨料生成本地实时预览组件
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._boundary_rect: QRectF = QRectF(0, 0, 100, 100)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.scene = QGraphicsScene(self)
        self.view = InteractiveGraphicsView(self.scene, self)
        layout.addWidget(self.view)
        
        # 控制按钮栏（居中，悬浮感）
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(6, 4, 6, 6)
        
        self.fit_btn = QPushButton("适应视图 (Fit View)", self)
        self.fit_btn.setMinimumHeight(28)
        self.fit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                color: #606266;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background-color: #ecf5ff;
            }
            QPushButton:pressed {
                background-color: #b3d8ff;
                border-color: #409eff;
                color: #409eff;
            }
        """)
        self.fit_btn.clicked.connect(self.fit_view)
        
        self.clear_btn = QPushButton("清空画布 (Clear)", self)
        self.clear_btn.setMinimumHeight(28)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                color: #f56c6c;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                color: #ffffff;
                border-color: #f56c6c;
                background-color: #f56c6c;
            }
            QPushButton:pressed {
                background-color: #f78989;
                border-color: #f78989;
                color: #ffffff;
            }
        """)
        self.clear_btn.clicked.connect(self.clear)
        
        btn_layout.addWidget(self.fit_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

    def clear(self):
        """
        清空画布
        """
        self.scene.clear()
        # 重新绘制默认背景
        self.scene.setSceneRect(self._boundary_rect)

    def draw_boundary(self, points: List[float], color_idx: int):
        """
        绘制边界
        """
        qpoints = []
        for i in range(0, len(points), 3):
            x = points[i]
            y = points[i+1]
            qpoints.append(QPointF(x, y))
            
        polygon = QPolygonF(qpoints)
        self._boundary_rect = polygon.boundingRect()
        self.scene.setSceneRect(self._boundary_rect.adjusted(-20, -20, 20, 20))
        
        pen_color = COLOR_MAP.get(color_idx, QColor(0, 0, 0))
        pen = QPen(pen_color, 1.5, Qt.DashLine)
        pen.setCosmetic(True) # 保持线宽不随缩放改变
        
        # 边界通常没有填充
        brush = QBrush(Qt.NoBrush)
        
        item = QGraphicsPolygonItem(polygon)
        item.setPen(pen)
        item.setBrush(brush)
        item.setZValue(-10) # 保证在最底层
        
        self.scene.addItem(item)
        self.fit_view()

    def draw_aggregate(self, points: List[float], color_idx: int, layer_name: str = None):
        """
        绘制骨料或 ITZ
        """
        qpoints = []
        for i in range(0, len(points), 3):
            x = points[i]
            y = points[i+1]
            qpoints.append(QPointF(x, y))
            
        polygon = QPolygonF(qpoints)
        
        is_itz = (layer_name == "RandomCAD-ITZ")
        
        # 决定画笔和画刷
        if is_itz:
            color = ITZ_COLOR_MAP.get(color_idx, QColor(180, 180, 180, 60))
            pen = QPen(QColor(color.red(), color.green(), color.blue(), 100), 0.5, Qt.SolidLine)
            pen.setCosmetic(True)
            brush = QBrush(color)
            z_value = 1  # ITZ 在中层
        else:
            color = COLOR_MAP.get(color_idx, QColor(80, 80, 80, 210))
            pen = QPen(QColor(40, 40, 40, 220), 0.8, Qt.SolidLine)
            pen.setCosmetic(True)
            brush = QBrush(color)
            z_value = 2  # 骨料在顶层
            
        item = QGraphicsPolygonItem(polygon)
        item.setPen(pen)
        item.setBrush(brush)
        item.setZValue(z_value)
        
        self.scene.addItem(item)

    def fit_view(self):
        """
        使视图自适应显示所有对象
        """
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            rect = self._boundary_rect
            
        if not rect.isEmpty():
            # 留出 10% 的边距
            margin = max(rect.width(), rect.height()) * 0.05
            self.view.fitInView(rect.adjusted(-margin, -margin, margin, margin), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_view()
