# cad_connection.py

import logging
import threading
import time
import winreg
from typing import Optional, Any, Callable, List
from enum import Enum

try:
    import comtypes
    from pyautocad import Autocad, APoint, aDouble
    AUTOCAD_AVAILABLE = True
    PYAUTOCAD_AVAILABLE = True
except ImportError as e:
    AUTOCAD_AVAILABLE = False
    PYAUTOCAD_AVAILABLE = False
    logging.warning(f"AutoCAD库未安装: {e}")
except Exception as e:
    AUTOCAD_AVAILABLE = False
    PYAUTOCAD_AVAILABLE = False
    logging.error(f"导入AutoCAD库时出错: {e}")

try:
    import comtypes
    ZWCAD_AVAILABLE = True
except ImportError as e:
    ZWCAD_AVAILABLE = False
    logging.warning(f"COM库未安装，无法使用中望CAD: {e}")
except Exception as e:
    ZWCAD_AVAILABLE = False
    logging.error(f"导入COM库时出错: {e}")


def detect_autocad_installations() -> List[dict]:
    """
    检测系统中安装的AutoCAD版本
    
    Returns:
        List[dict]: 检测到的AutoCAD版本信息列表
    """
    installations = []
    
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Autodesk\AutoCAD") as autocad_key:
            index = 0
            while True:
                try:
                    version_key_name = winreg.EnumKey(autocad_key, index)
                    index += 1
                    
                    try:
                        with winreg.OpenKey(autocad_key, version_key_name) as version_key:
                            sub_index = 0
                            while True:
                                try:
                                    release_key_name = winreg.EnumKey(version_key, sub_index)
                                    sub_index += 1
                                    
                                    try:
                                        with winreg.OpenKey(version_key, release_key_name) as release_key:
                                            acad_location = winreg.QueryValueEx(release_key, "AcadLocation")[0]
                                            acad_version = winreg.QueryValueEx(release_key, "AcadVersion")[0]
                                            
                                            installations.append({
                                                "version": version_key_name,
                                                "release": release_key_name,
                                                "location": acad_location,
                                                "acad_version": acad_version
                                            })
                                    except (WindowsError, FileNotFoundError):
                                        pass
                                except WindowsError:
                                    break
                    except (WindowsError, FileNotFoundError):
                        pass
                except WindowsError:
                    break
    except WindowsError:
        pass
    
    return installations


def detect_zwcad_installations() -> List[dict]:
    """
    检测系统中安装的中望CAD版本
    
    Returns:
        List[dict]: 检测到的中望CAD版本信息列表
    """
    installations = []
    
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\ZWSOFT") as zwcad_key:
            index = 0
            while True:
                try:
                    version_key_name = winreg.EnumKey(zwcad_key, index)
                    index += 1
                    
                    if "ZWCAD" in version_key_name:
                        try:
                            with winreg.OpenKey(zwcad_key, version_key_name) as version_key:
                                install_path = winreg.QueryValueEx(version_key, "InstallPath")[0]
                                installations.append({
                                    "version": version_key_name,
                                    "location": install_path
                                })
                        except (WindowsError, FileNotFoundError):
                            pass
                except WindowsError:
                    break
    except WindowsError:
        pass
    
    return installations


class CADType(Enum):
    """CAD类型枚举"""
    AUTOCAD = "autocad"
    ZWCAD = "zwcad"


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class CADConnection:
    """
    CAD连接管理器（支持AutoCAD和中望CAD）
    
    提供健壮的CAD连接管理，包括：
    - 连接状态监控
    - 自动重连机制
    - 心跳检测
    - COM资源管理
    - 支持AutoCAD和中望CAD
    """
    
    def __init__(self, auto_start: bool = True, cad_type: str = "autocad"):
        """
        初始化CAD连接管理器
        
        Args:
            auto_start: 如果CAD未运行，是否自动启动
            cad_type: CAD类型，可选值: "autocad", "zwcad"
        """
        self._acad_autocad: Optional[Autocad] = None
        self._acad_zwcad: Optional[Any] = None
        self._doc: Optional[Any] = None
        self._model_space: Optional[Any] = None
        self._cad_type = CADType(cad_type) if isinstance(cad_type, str) and cad_type in [e.value for e in CADType] else cad_type
        self._connection_state = ConnectionState.DISCONNECTED
        self._auto_start = auto_start
        self._connection_lock = threading.Lock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 2.0
        self._state_callbacks: list[Callable[[ConnectionState], None]] = []
        
        self._autocad_installations: List[dict] = []
        self._zwcad_installations: List[dict] = []
        
        self._check_installations()
        
        logging.info(f"CAD连接管理器已初始化 (类型: {cad_type})")
    
    def _check_installations(self) -> None:
        """
        检测系统中安装的CAD版本
        """
        self._autocad_installations = detect_autocad_installations()
        self._zwcad_installations = detect_zwcad_installations()
        
        if self._autocad_installations:
            logging.info(f"检测到 {len(self._autocad_installations)} 个AutoCAD安装:")
            for inst in self._autocad_installations:
                logging.info(f"  - 版本: {inst['version']}, 位置: {inst['location']}")
        else:
            logging.warning("未检测到AutoCAD安装")
        
        if self._zwcad_installations:
            logging.info(f"检测到 {len(self._zwcad_installations)} 个中望CAD安装:")
            for inst in self._zwcad_installations:
                logging.info(f"  - 版本: {inst['version']}, 位置: {inst['location']}")
        else:
            logging.info("未检测到中望CAD安装")
    
    def get_autocad_installations(self) -> List[dict]:
        """
        获取检测到的AutoCAD安装信息
        
        Returns:
            List[dict]: AutoCAD安装信息列表
        """
        return self._autocad_installations
    
    def get_zwcad_installations(self) -> List[dict]:
        """
        获取检测到的中望CAD安装信息
        
        Returns:
            List[dict]: 中望CAD安装信息列表
        """
        return self._zwcad_installations
    
    def add_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """
        添加连接状态变化回调
        
        Args:
            callback: 状态变化回调函数
        """
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)
    
    def remove_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """
        移除连接状态变化回调
        
        Args:
            callback: 状态变化回调函数
        """
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)
    
    def _notify_state_change(self, new_state: ConnectionState) -> None:
        """
        通知所有状态变化回调
        
        Args:
            new_state: 新的连接状态
        """
        self._connection_state = new_state
        for callback in self._state_callbacks:
            try:
                callback(new_state)
            except Exception as e:
                logging.error(f"状态回调执行失败: {e}")
    
    @property
    def state(self) -> ConnectionState:
        """
        获取当前连接状态
        
        Returns:
            ConnectionState: 当前连接状态
        """
        return self._connection_state
    
    @property
    def is_connected(self) -> bool:
        """
        检查是否已连接
        
        Returns:
            bool: 是否已连接
        """
        return self._connection_state == ConnectionState.CONNECTED
    
    @property
    def acad(self) -> Optional[Any]:
        """
        获取CAD对象（AutoCAD或中望CAD）
        
        Returns:
            Optional[Any]: CAD对象，未连接时返回None
        """
        if self._cad_type == CADType.AUTOCAD:
            return self._acad_autocad
        elif self._cad_type == CADType.ZWCAD:
            return self._acad_zwcad
        return None
    
    @property
    def doc(self) -> Optional[Any]:
        """
        获取AutoCAD文档对象
        
        Returns:
            Optional[Any]: 文档对象，未连接时返回None
        """
        return self._doc
    
    @property
    def model_space(self) -> Optional[Any]:
        """
        获取模型空间对象
        
        Returns:
            Optional[Any]: 模型空间对象，未连接时返回None
        """
        return self._model_space
    
    def connect(self) -> bool:
        """
        连接到CAD（AutoCAD或中望CAD）
        
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        with self._connection_lock:
            if self._cad_type == CADType.AUTOCAD:
                if not AUTOCAD_AVAILABLE:
                    logging.error("AutoCAD库未安装，无法连接")
                    logging.error("请安装 pyautocad 和 comtypes 库:")
                    logging.error("  pip install pyautocad comtypes")
                    self._notify_state_change(ConnectionState.ERROR)
                    return False
                
                if not self._autocad_installations:
                    logging.error("未检测到AutoCAD安装")
                    logging.error("请确保已安装AutoCAD并正确注册COM组件")
                    self._notify_state_change(ConnectionState.ERROR)
                    return False
                    
            elif self._cad_type == CADType.ZWCAD:
                if not ZWCAD_AVAILABLE:
                    logging.error("COM库未安装，无法连接中望CAD")
                    logging.error("请安装 comtypes 库:")
                    logging.error("  pip install comtypes")
                    self._notify_state_change(ConnectionState.ERROR)
                    return False
                
                if not self._zwcad_installations:
                    logging.warning("未检测到中望CAD安装，但仍尝试连接")
            else:
                logging.error(f"未知的CAD类型: {self._cad_type}")
                self._notify_state_change(ConnectionState.ERROR)
                return False
            
            if self.is_connected:
                logging.info("CAD已连接，无需重新连接")
                return True
            
            max_retries = 3
            retry_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    self._notify_state_change(ConnectionState.CONNECTING)
                    
                    thread_info = "主线程" if threading.current_thread() is threading.main_thread() else "子线程"
                    
                    if threading.current_thread() is not threading.main_thread():
                        comtypes.CoInitialize()
                        logging.info("子线程COM已初始化")
                    
                    if attempt > 0:
                        logging.info(f"连接尝试 {attempt + 1}/{max_retries}，等待 {retry_delay} 秒...")
                        time.sleep(retry_delay)
                    
                    if self._cad_type == CADType.AUTOCAD:
                        logging.info(f"正在尝试连接AutoCAD (自动启动: {self._auto_start})...")
                        
                        try:
                            self._acad_autocad = Autocad(create_if_not_exists=self._auto_start)
                        except Exception as e:
                            error_msg = str(e)
                            logging.error(f"创建AutoCAD对象失败: {error_msg}")
                            
                            if "无效的类字符串" in error_msg or "invalid class string" in error_msg.lower():
                                logging.error("=" * 60)
                                logging.error("检测到COM组件错误！")
                                logging.error("=" * 60)
                                logging.error("可能的原因:")
                                logging.error("1. AutoCAD未正确安装")
                                logging.error("2. AutoCAD版本不兼容")
                                logging.error("3. COM组件未正确注册")
                                logging.error("4. AutoCAD未以管理员权限运行")
                                logging.error("=" * 60)
                                logging.error("建议的解决方案:")
                                logging.error("1. 确认AutoCAD已正确安装")
                                logging.error("2. 尝试以管理员身份运行AutoCAD")
                                logging.error("3. 在AutoCAD中运行: acadreg")
                                logging.error("4. 重新安装AutoCAD")
                                logging.error("5. 检查AutoCAD版本是否支持COM自动化")
                                logging.error("=" * 60)
                            
                            if attempt < max_retries - 1:
                                retry_delay *= 2
                                continue
                            self._notify_state_change(ConnectionState.ERROR)
                            return False
                        
                        if self._acad_autocad is None:
                            logging.error("AutoCAD连接失败：无法创建Autocad对象")
                            logging.error("请检查:")
                            logging.error("1. AutoCAD是否正在运行")
                            logging.error("2. 是否有权限访问AutoCAD")
                            logging.error("3. AutoCAD版本是否支持")
                            if attempt < max_retries - 1:
                                retry_delay *= 2
                                continue
                            self._notify_state_change(ConnectionState.ERROR)
                            return False
                        
                        try:
                            self._doc = self._acad_autocad.doc
                            self._model_space = self._doc.ModelSpace
                            
                            self._reconnect_attempts = 0
                            self._notify_state_change(ConnectionState.CONNECTED)
                            
                            self._acad_autocad.prompt(f"随机骨料生成器已连接AutoCAD ({thread_info})\n")
                            logging.info(f"成功连接AutoCAD ({thread_info})")
                            
                            self._start_heartbeat()
                            return True
                        except Exception as doc_error:
                            logging.error(f"获取AutoCAD文档失败: {str(doc_error)}")
                            logging.error("请检查:")
                            logging.error("1. AutoCAD中是否打开了文档")
                            logging.error("2. 文档是否为只读")
                            if attempt < max_retries - 1:
                                retry_delay *= 2
                                continue
                            self._notify_state_change(ConnectionState.ERROR)
                            return False
                    
                    elif self._cad_type == CADType.ZWCAD:
                        logging.info(f"正在尝试连接中望CAD...")
                        
                        try:
                            import comtypes.client
                            self._acad_zwcad = comtypes.client.GetActiveObject("ZWCAD.Application", dynamic=True)
                            logging.info("已连接到运行中的中望CAD")
                        except Exception as e:
                            if self._auto_start:
                                logging.info("未检测到运行中的中望CAD，尝试启动...")
                                try:
                                    self._acad_zwcad = comtypes.client.CreateObject("ZWCAD.Application", dynamic=True)
                                    self._acad_zwcad.Visible = True
                                    logging.info("中望CAD已启动")
                                except Exception as start_error:
                                    logging.error(f"启动中望CAD失败: {str(start_error)}")
                                    if attempt < max_retries - 1:
                                        retry_delay *= 2
                                        continue
                                    self._notify_state_change(ConnectionState.ERROR)
                                    return False
                            else:
                                logging.error("未检测到运行中的中望CAD且未启用自动启动")
                                if attempt < max_retries - 1:
                                    retry_delay *= 2
                                    continue
                                self._notify_state_change(ConnectionState.ERROR)
                                return False
                        
                        try:
                            self._doc = self._acad_zwcad.ActiveDocument
                            self._model_space = self._doc.ModelSpace
                            
                            self._reconnect_attempts = 0
                            self._notify_state_change(ConnectionState.CONNECTED)
                            
                            logging.info(f"成功连接中望CAD ({thread_info})")
                            
                            try:
                                self._acad_zwcad.Prompt(f"随机骨料生成器已连接中望CAD ({thread_info})\n")
                            except Exception:
                                pass  # 动态绑定时 Prompt 可能不可用
                            
                            self._start_heartbeat()
                            return True
                        except Exception as doc_error:
                            logging.error(f"获取中望CAD文档失败: {str(doc_error)}")
                            logging.error("请确保中望CAD中已打开文档")
                            if attempt < max_retries - 1:
                                retry_delay *= 2
                                continue
                            self._notify_state_change(ConnectionState.ERROR)
                            return False
                        
                except Exception as e:
                    error_msg = str(e)
                    cad_name = "AutoCAD" if self._cad_type == CADType.AUTOCAD else "中望CAD"
                    logging.error(f"连接{cad_name}失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}", exc_info=True)
                    
                    if "无效的类字符串" in error_msg or "invalid class string" in error_msg.lower():
                        logging.warning("检测到CAD版本兼容性问题")
                    
                    if attempt < max_retries - 1:
                        retry_delay *= 2
                        continue
                    
                    self._notify_state_change(ConnectionState.ERROR)
                    return False
            
            logging.error(f"CAD连接失败：已达到最大重试次数 {max_retries}")
            self._notify_state_change(ConnectionState.ERROR)
            return False
    
    def disconnect(self) -> None:
        """
        断开AutoCAD连接
        """
        with self._connection_lock:
            self._stop_heartbeat()
            
            self._acad_autocad = None
            self._acad_zwcad = None
            self._doc = None
            self._model_space = None
            
            if threading.current_thread() is not threading.main_thread():
                try:
                    comtypes.CoUninitialize()
                    logging.info("子线程COM资源已清理")
                except Exception as e:
                    logging.warning(f"清理COM资源时出错: {str(e)}")
            
            self._notify_state_change(ConnectionState.DISCONNECTED)
            logging.info("AutoCAD连接已断开")
    
    def reconnect(self) -> bool:
        """
        重新连接到AutoCAD
        
        Returns:
            bool: 重连成功返回True，否则返回False
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logging.error(f"已达到最大重连次数 ({self._max_reconnect_attempts})")
            return False
        
        self._reconnect_attempts += 1
        logging.info(f"尝试重连 ({self._reconnect_attempts}/{self._max_reconnect_attempts})")
        
        self.disconnect()
        time.sleep(self._reconnect_delay)
        
        return self.connect()
    
    def _start_heartbeat(self) -> None:
        """
        启动心跳检测线程
        """
        if self._heartbeat_running:
            return
        
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logging.info("心跳检测已启动")
    
    def _stop_heartbeat(self) -> None:
        """
        停止心跳检测线程
        """
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
            self._heartbeat_thread = None
        logging.info("心跳检测已停止")
    
    def _heartbeat_loop(self) -> None:
        """
        心跳检测循环
        """
        while self._heartbeat_running:
            try:
                if self._cad_type == CADType.AUTOCAD:
                    cad = self._acad_autocad
                else:
                    cad = self._acad_zwcad
                if cad and self._doc:
                    try:
                        # 尝试访问文档属性确认连接存活
                        # ZWCAD 动态绑定时 Name 可能不可用，用 try/except 容忍
                        _ = self._doc.Name
                    except Exception as e:
                        logging.debug(f"心跳检测警告: {e}")
                
                time.sleep(5.0)  # 每5秒检测一次
                
            except Exception as e:
                logging.error(f"心跳检测异常: {e}")
                time.sleep(5.0)
    
    def prompt(self, message: str) -> None:
        """
        在CAD命令行显示消息（AutoCAD或中望CAD）
        
        Args:
            message: 要显示的消息
        """
        if self._cad_type == CADType.AUTOCAD and self._acad_autocad:
            try:
                self._acad_autocad.prompt(message + "\n")
            except Exception as e:
                logging.error(f"发送消息到AutoCAD失败: {e}")
        elif self._cad_type == CADType.ZWCAD and self._acad_zwcad:
            try:
                self._acad_zwcad.Prompt(message + "\n")
            except Exception as e:
                logging.error(f"发送消息到中望CAD失败: {e}")
    
    def create_layer(self, name: str, color: int = 7) -> bool:
        """
        创建 CAD 图层，已存在则跳过
        
        Args:
            name: 图层名称
            color: 图层颜色索引
            
        Returns:
            bool: 创建成功或已存在返回True，否则返回False
        """
        if not self.is_connected:
            return False
        try:
            layers = self._doc.Layers
            for layer in layers:
                if layer.Name == name:
                    return True
            new_layer = layers.Add(name)
            new_layer.color = color
            return True
        except Exception as e:
            logging.debug(f"创建图层 {name} 失败: {e}")
            return False

    def set_object_layer(self, obj, layer_name: str) -> bool:
        """
        将对象移动到指定图层
        
        Args:
            obj: CAD对象
            layer_name: 目标图层名称
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        if not obj:
            return False
        try:
            obj.Layer = layer_name
            return True
        except Exception as e:
            logging.debug(f"设置对象图层失败: {e}")
            return False

    def draw_boundary(self, points: list[float], color: int, layer_name: str = None) -> Optional[Any]:
        """
        在CAD中绘制边界（AutoCAD或中望CAD）
        
        Args:
            points: 边界点列表 [x1, y1, z1, x2, y2, z2, ...]
            color: 颜色索引
            layer_name: 目标图层名称
            
        Returns:
            Optional[Any]: 绘制的多段线对象，失败时返回None
        """
        if not self.is_connected or not self._model_space:
            logging.error("CAD未连接，无法绘制边界")
            return None
        
        try:
            if self._cad_type == CADType.AUTOCAD:
                polyline = self._model_space.AddPolyline(aDouble(points))
                polyline.color = color
                if layer_name:
                    self.set_object_layer(polyline, layer_name)
                return polyline
            elif self._cad_type == CADType.ZWCAD:
                import comtypes
                points_array = comtypes.automation.VARIANT(list(points))
                polyline = self._model_space.AddPolyline(points_array)
                polyline.color = color
                if layer_name:
                    self.set_object_layer(polyline, layer_name)
                return polyline
            else:
                logging.error(f"未知的CAD类型: {self._cad_type}")
                return None
        except Exception as e:
            logging.error(f"绘制边界失败: {e}")
            return None
    
    def draw_aggregate(self, points: list[float], color: int, layer_name: str = None) -> Optional[Any]:
        """
        在CAD中绘制骨料（AutoCAD或中望CAD）
        
        Args:
            points: 骨料点列表 [x1, y1, z1, x2, y2, z2, ...]
            color: 颜色索引
            layer_name: 目标图层名称
            
        Returns:
            Optional[Any]: 绘制的多段线对象，失败时返回None
        """
        if not self.is_connected or not self._model_space:
            logging.error("CAD未连接，无法绘制骨料")
            return None
        
        try:
            if self._cad_type == CADType.AUTOCAD:
                polyline = self._model_space.AddPolyline(aDouble(points))
                polyline.color = color
                if layer_name:
                    self.set_object_layer(polyline, layer_name)
                return polyline
            elif self._cad_type == CADType.ZWCAD:
                import comtypes
                points_array = comtypes.automation.VARIANT(list(points))
                polyline = self._model_space.AddPolyline(points_array)
                polyline.color = color
                if layer_name:
                    self.set_object_layer(polyline, layer_name)
                return polyline
            else:
                logging.error(f"未知的CAD类型: {self._cad_type}")
                return None
        except Exception as e:
            logging.error(f"绘制骨料失败: {e}")
            return None
    
    def delete_object(self, obj: Any) -> bool:
        """
        删除CAD对象（AutoCAD或中望CAD）
        
        Args:
            obj: 要删除的对象
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        try:
            if obj:
                if self._cad_type == CADType.AUTOCAD:
                    obj.Delete()
                elif self._cad_type == CADType.ZWCAD:
                    if hasattr(obj, 'Delete'):
                        obj.Delete()
                    else:
                        logging.warning("中望CAD对象不支持Delete方法")
                else:
                    logging.warning("未知的CAD类型")
                return True
        except Exception as e:
            logging.error(f"删除对象时出错: {e}")
            return False
    
    def regen(self, mode: int = 0) -> bool:
        """
        重绘AutoCAD视图
        
        Args:
            mode: 重绘模式 (0=全部, 1=部分)
            
        Returns:
            bool: 重绘成功返回True，否则返回False
        """
        if not self.is_connected or not self._doc:
            return False
        
        try:
            self._doc.Regen(mode)
            return True
        except Exception as e:
            logging.error(f"重绘失败: {e}")
            return False
    
    def __del__(self):
        """
        析构函数，清理资源
        """
        self.disconnect()
