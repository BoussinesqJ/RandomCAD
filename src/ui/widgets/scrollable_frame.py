# scrollable_frame.py

from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QFrame
from PySide6.QtCore import Qt

class ScrollableFrame(QScrollArea):
    """
    可滚动框架组件
    
    提供一个可滚动的容器，用于容纳大量UI组件
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.scrollable_frame = QFrame()
        self.scrollable_frame.setFrameShape(QFrame.Shape.NoFrame)
        
        self.layout = QVBoxLayout(self.scrollable_frame)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setWidget(self.scrollable_frame)
    
    def get_scrollable_frame(self) -> QFrame:
        """
        获取可滚动框架对象
        
        Returns:
            QFrame: 可滚动框架
        """
        return self.scrollable_frame
    
    def get_layout(self) -> QVBoxLayout:
        """
        获取布局对象
        
        Returns:
            QVBoxLayout: 布局对象
        """
        return self.layout
