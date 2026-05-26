"""
CAD 连接测试

测试 AutoCAD 和中望CAD 的连接功能
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from src.core.cad_connection import CADConnection, CADType, ConnectionState


class TestCADConnection(unittest.TestCase):
    """CAD 连接测试类"""
    
    def test_autocad_available(self):
        """测试 AutoCAD 库是否可用"""
        from src.core.cad_connection import AUTOCAD_AVAILABLE
        self.assertIsInstance(AUTOCAD_AVAILABLE, bool)
    
    def test_zwcad_available(self):
        """测试中望CAD 库是否可用"""
        from src.core.cad_connection import ZWCAD_AVAILABLE
        self.assertIsInstance(ZWCAD_AVAILABLE, bool)
    
    def test_cad_connection_init(self):
        """测试 CAD 连接初始化"""
        conn = CADConnection(auto_start=False, cad_type="autocad")
        self.assertEqual(conn._cad_type, CADType.AUTOCAD)
        self.assertEqual(conn.state, ConnectionState.DISCONNECTED)
    
    def test_cad_type_enum(self):
        """测试 CAD 类型枚举"""
        self.assertEqual(CADType.AUTOCAD.value, "autocad")
        self.assertEqual(CADType.ZWCAD.value, "zwcad")
    
    def test_connection_state_enum(self):
        """测试连接状态枚举"""
        self.assertEqual(ConnectionState.DISCONNECTED.value, "disconnected")
        self.assertEqual(ConnectionState.CONNECTING.value, "connecting")
        self.assertEqual(ConnectionState.CONNECTED.value, "connected")
        self.assertEqual(ConnectionState.ERROR.value, "error")


if __name__ == '__main__':
    unittest.main()
